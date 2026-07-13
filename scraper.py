import os
import re
import hashlib
import json
import unicodedata
from datetime import datetime

try:
    from zoneinfo import ZoneInfo
    VN_TZ = ZoneInfo("Asia/Ho_Chi_Minh")
except Exception:
    VN_TZ = None  # fallback nếu môi trường không có tzdata

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

    # Cắt bỏ phần text SEO rác bắt đầu từ dòng "Nguồn:" hoặc "Để mọi người thuận tiện..."
    CUT_MARKERS = [
        "Nguồn: Thông tin từ các trang web chính thức",
        "Để mọi người thuận tiện tra cứu",
        "Việc xảy ra tình trạng mất điện",
        "Khi có sự cố về điện tại địa phương",
        "Thông báo lịch cúp điện Huyện",
    ]
    cut_at = len(lines)
    for i, line in enumerate(lines):
        if any(line.startswith(m) for m in CUT_MARKERS):
            cut_at = i
            break

    # Lọc bỏ các dòng rác lẻ tẻ nằm giữa các mục lịch
    JUNK_LINES = {
        "Thông tin đang cập nhật",
        "*Thông tin đang cập nhật",
        "* Thông tin đang cập nhật",
    }
    lines = [l for l in lines[:cut_at] if l not in JUNK_LINES]

    return "\n".join(lines)


def parse_entries(text: str):
    """Parse các block Điện lực/Ngày/Thời gian/Khu vực/Lý do/Trạng thái.
    Hỗ trợ cả 2 dạng: label trên 1 dòng riêng, value trên dòng kế tiếp."""
    lines = text.split("\n")
    entries = []
    i = 0
    n = len(lines)

    # Map label -> key trong dict kết quả
    LABEL_MAP = {
        "Điện lực:": "dien_luc",
        "Ngày:": "ngay",
        "Thời gian:": "thoi_gian",
        "Khu vực:": "khu_vuc",
        "Lý do:": "ly_do",
        "Trạng thái:": "trang_thai",
    }
    ALL_LABELS = set(LABEL_MAP.keys())
    ORDERED_LABELS = list(LABEL_MAP.keys())

    while i < n:
        if lines[i] == ORDERED_LABELS[0]:  # "Điện lực:"
            cursor = i
            values = {}
            ok = True

            for label in ORDERED_LABELS:
                if cursor >= n or lines[cursor] != label:
                    ok = False
                    break
                cursor += 1
                # Gom các dòng value cho tới khi gặp label tiếp theo hoặc hết
                value_lines = []
                while cursor < n and lines[cursor] not in ALL_LABELS:
                    value_lines.append(lines[cursor])
                    cursor += 1
                values[label] = " ".join(value_lines).strip()
                # Bỏ icon emoji phía đầu (vd: "🔔 Kế hoạch" -> "Kế hoạch")
                values[label] = re.sub(r'^[\U00010000-\U0010ffff\u2600-\u26FF\u2700-\u27BF\s]+', '', values[label]).strip()

            if ok and values.get("Ngày:"):  # phải có ít nhất trường Ngày
                entries.append({
                    "dien_luc":  values.get("Điện lực:", ""),
                    "ngay":      values.get("Ngày:", ""),
                    "thoi_gian": values.get("Thời gian:", ""),
                    "khu_vuc":   values.get("Khu vực:", ""),
                    "ly_do":     values.get("Lý do:", ""),
                    "trang_thai":values.get("Trạng thái:", ""),
                })
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


def parse_entry_datetime(entry: dict):
    """Parse 'Ngày' + 'Thời gian' của 1 mục thành (start_dt, end_dt) theo giờ VN.
    Trả về (None, None) nếu không parse được (định dạng lạ)."""
    date_match = re.search(r"(\d{1,2})\s*tháng\s*(\d{1,2})\s*năm\s*(\d{4})", entry.get("ngay", ""))
    if not date_match:
        return None, None
    day, month, year = map(int, date_match.groups())

    time_match = re.search(r"(\d{1,2}):(\d{2}).*?(\d{1,2}):(\d{2})", entry.get("thoi_gian", ""))
    if not time_match:
        return None, None
    h1, m1, h2, m2 = map(int, time_match.groups())

    try:
        start_dt = datetime(year, month, day, h1, m1, tzinfo=VN_TZ)
        end_dt = datetime(year, month, day, h2, m2, tzinfo=VN_TZ)
        if end_dt <= start_dt:
            from datetime import timedelta

            end_dt += timedelta(days=1)  # trường hợp qua đêm
        return start_dt, end_dt
    except ValueError:
        return None, None


def get_upcoming_reminders():
    """Trả về các mục khớp từ khóa mà giờ cúp điện CHƯA xảy ra (còn cần nhắc)."""
    entries = fetch_all_entries()
    now = datetime.now(VN_TZ) if VN_TZ else datetime.now()
    upcoming = []
    for e in entries:
        kw = matches_keyword(e)
        if not kw:
            continue
        start_dt, _end_dt = parse_entry_datetime(e)
        entry = dict(e)
        entry["matched_keyword"] = kw
        if start_dt is None:
            # Không parse được giờ -> vẫn nhắc để tránh bỏ sót thông tin quan trọng
            entry["hours_left"] = None
            upcoming.append(entry)
            continue
        if start_dt > now:
            entry["hours_left"] = round((start_dt - now).total_seconds() / 3600, 1)
            upcoming.append(entry)
    return upcoming


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
            # Chỉ giữ mục có trạng thái "Đã duyệt" hoặc "Đã thực hiện"
            entries = [
                e for e in entries
                if any(s in e.get("trang_thai", "") for s in ["Đã duyệt", "Đã thực hiện"])
            ]
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
    """Quét, so khớp, và gọi send_push_fn(entry) cho các mục MỚI (chưa từng thông báo).
    (Giữ lại hàm này để tương thích cũ; hàm đang được dùng thực tế là check_and_remind bên dưới.)"""
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


def check_and_remind(send_push_fn):
    """Quét và gửi NHẮC NHỞ cho MỌI mục khớp từ khóa mà giờ cúp điện chưa xảy ra.
    Gọi hàm này mỗi giờ -> người dùng sẽ được nhắc lặp lại liên tục cho tới khi
    tới đúng giờ bắt đầu cúp điện, sau đó tự động ngừng nhắc (vì không còn "upcoming")."""
    upcoming = get_upcoming_reminders()
    for entry in upcoming:
        send_push_fn(entry)

    if upcoming:
        print(f"[scraper] Đã gửi nhắc nhở cho {len(upcoming)} lịch cúp điện sắp tới.")
    else:
        print("[scraper] Không có lịch cúp điện nào sắp tới cần nhắc.")

    return {"total_upcoming": len(upcoming)}
