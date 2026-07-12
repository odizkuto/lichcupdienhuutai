import os
import re
import hashlib
import json
import unicodedata

import requests
from bs4 import BeautifulSoup

# ----------------------------------------------------------------------
# CẤU HÌNH
# ----------------------------------------------------------------------

# Trang nguồn cần quét. Override bằng biến môi trường TARGET_URLS (phân cách bởi dấu phẩy)
TARGET_URLS = [
    u.strip()
    for u in os.environ.get(
        "TARGET_URLS", "https://lichcupdien.org/lich-cup-dien-phu-tan-an-giang"
    ).split(",")
    if u.strip()
]

# Từ khóa khu vực cần theo dõi. Override bằng biến môi trường KEYWORDS (phân cách bởi dấu phẩy)
DEFAULT_KEYWORDS = ["Phú An", "Tân Trung", "Đường Cồn", "Quốc lộ 80B", "QL80B", "QL 80B"]
KEYWORDS = [
    k.strip()
    for k in os.environ.get("KEYWORDS", ",".join(DEFAULT_KEYWORDS)).split(",")
    if k.strip()
]

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
SEEN_FILE = os.path.join(DATA_DIR, "seen.json")

LABELS = ["Điện lực:", "Ngày:", "Thời gian:", "Khu vực:", "Lý do:", "Trạng thái:"]

# ----------------------------------------------------------------------
# TIỆN ÍCH
# ----------------------------------------------------------------------


def normalize(text: str) -> str:
    """Bỏ dấu tiếng Việt + hạ thường, để so khớp từ khóa không phân biệt dấu/hoa-thường."""
    text = unicodedata.normalize("NFD", text)
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")
    text = text.replace("đ", "d").replace("Đ", "D")
    return text.lower().strip()


def load_seen():
    try:
        with open(SEEN_FILE, "r", encoding="utf-8") as f:
            return set(json.load(f))
    except Exception:
        return set()


def save_seen(seen_set):
    os.makedirs(DATA_DIR, exist_ok=True)
    arr = list(seen_set)[-2000:]  # giới hạn kích thước
    with open(SEEN_FILE, "w", encoding="utf-8") as f:
        json.dump(arr, f)


def hash_entry(entry: dict) -> str:
    raw = f"{entry['dien_luc']}|{entry['ngay']}|{entry['thoi_gian']}|{entry['khu_vuc']}"
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()


def html_to_text(html: str) -> str:
    """Chuyển HTML thô thành text có xuống dòng hợp lý ở mỗi thẻ block."""
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "header", "footer", "nav", "noscript", "iframe"]):
        tag.decompose()
    for br in soup.find_all("br"):
        br.replace_with("\n")

    block_tags = ["p", "div", "li", "tr", "h1", "h2", "h3", "h4", "h5", "h6", "section", "article"]
    for tag_name in block_tags:
        for tag in soup.find_all(tag_name):
            tag.append("\n")

    text = soup.get_text()
    lines = [l.strip() for l in text.splitlines()]
    lines = [l for l in lines if l]
    return "\n".join(lines)


def parse_entries(text: str):
    """Parse các block Điện lực/Ngày/Thời gian/Khu vực/Lý do/Trạng thái."""
    lines = text.split("\n")
    entries = []
    i = 0
    n = len(lines)

    while i < n:
        if lines[i] == LABELS[0]:
            cursor = i
            values = {}
            ok = True
            for idx, label in enumerate(LABELS):
                if cursor >= n or lines[cursor] != label:
                    ok = False
                    break
                cursor += 1
                next_label = LABELS[idx + 1] if idx + 1 < len(LABELS) else None
                value_lines = []
                while cursor < n and lines[cursor] not in LABELS:
                    value_lines.append(lines[cursor])
                    cursor += 1
                values[label] = " ".join(value_lines).strip()
            if ok:
                entries.append(
                    {
                        "dien_luc": values.get("Điện lực:", ""),
                        "ngay": values.get("Ngày:", ""),
                        "thoi_gian": values.get("Thời gian:", ""),
                        "khu_vuc": values.get("Khu vực:", ""),
                        "ly_do": values.get("Lý do:", ""),
                        "trang_thai": values.get("Trạng thái:", ""),
                    }
                )
                i = cursor
                continue
        i += 1
    return entries


def matches_keyword(entry: dict):
    haystack = normalize(f"{entry['khu_vuc']} {entry['dien_luc']}")
    for kw in KEYWORDS:
        if normalize(kw) in haystack:
            return kw
    return None


# ----------------------------------------------------------------------
# LOGIC CHÍNH
# ----------------------------------------------------------------------


def fetch_all_entries():
    all_entries = []
    headers = {"User-Agent": "Mozilla/5.0 (PowerNotifyBot/1.0)"}
    for url in TARGET_URLS:
        try:
            res = requests.get(url, headers=headers, timeout=15)
            res.raise_for_status()
            text = html_to_text(res.text)
            entries = parse_entries(text)
            for e in entries:
                e["source_url"] = url
            all_entries.extend(entries)
        except Exception as err:
            print(f"[scraper] Lỗi khi lấy dữ liệu từ {url}: {err}")
    return all_entries


def check_now():
    """Trả về TẤT CẢ mục khớp từ khóa (dùng cho nút 'Kiểm tra' trên giao diện)."""
    entries = fetch_all_entries()
    matched = []
    for e in entries:
        kw = matches_keyword(e)
        if kw:
            e = dict(e)
            e["matched_keyword"] = kw
            matched.append(e)
    return matched


def check_and_notify(send_push_fn):
    """Quét, so khớp, và gọi send_push_fn(entry) cho các mục MỚI (chưa từng thông báo)."""
    seen = load_seen()
    entries = fetch_all_entries()
    matched = [e for e in entries if matches_keyword(e)]

    new_ones = []
    for entry in matched:
        eid = hash_entry(entry)
        if eid not in seen:
            seen.add(eid)
            new_ones.append(entry)

    if new_ones:
        save_seen(seen)
        for entry in new_ones:
            send_push_fn(entry)
        print(f"[scraper] Đã gửi thông báo cho {len(new_ones)} mục mới.")
    else:
        print("[scraper] Không có mục mới nào khớp từ khóa.")

    return {
        "total_scanned": len(entries),
        "total_matched": len(matched),
        "newly_notified": len(new_ones),
    }
