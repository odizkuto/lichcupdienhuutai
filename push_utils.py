import os
import json

from pywebpush import webpush, WebPushException

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
SUBS_FILE = os.path.join(DATA_DIR, "subscriptions.json")

VAPID_PUBLIC_KEY = os.environ.get("VAPID_PUBLIC_KEY")
VAPID_PRIVATE_KEY = os.environ.get("VAPID_PRIVATE_KEY")
VAPID_SUBJECT = os.environ.get("VAPID_SUBJECT", "mailto:admin@example.com")

if not VAPID_PUBLIC_KEY or not VAPID_PRIVATE_KEY:
    print(
        "[push] CHƯA cấu hình VAPID_PUBLIC_KEY / VAPID_PRIVATE_KEY. "
        "Set 2 biến môi trường này để có thể gửi thông báo."
    )


def load_subs():
    try:
        with open(SUBS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def save_subs(subs):
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(SUBS_FILE, "w", encoding="utf-8") as f:
        json.dump(subs, f, ensure_ascii=False, indent=2)


def add_subscription(sub: dict) -> int:
    subs = load_subs()
    if not any(s.get("endpoint") == sub.get("endpoint") for s in subs):
        subs.append(sub)
        save_subs(subs)
    return len(subs)


def send_to_all(title: str, body: str):
    subs = load_subs()
    if not subs:
        print("[push] Chưa có thiết bị nào đăng ký nhận thông báo.")
        return

    payload = json.dumps({"title": title, "body": body})
    still_valid = []

    for sub in subs:
        try:
            webpush(
                subscription_info=sub,
                data=payload,
                vapid_private_key=VAPID_PRIVATE_KEY,
                vapid_claims={"sub": VAPID_SUBJECT},
            )
            still_valid.append(sub)
        except WebPushException as err:
            status = getattr(err.response, "status_code", None)
            if status in (404, 410):
                print("[push] Subscription hết hạn, đã xóa.")
            else:
                print(f"[push] Lỗi gửi push: {err}")
                still_valid.append(sub)  # có thể lỗi tạm thời, giữ lại

    save_subs(still_valid)


def send_entry_notification(entry: dict):
    send_to_all(
        title="⚡ Cảnh báo lịch cúp điện",
        body=f"{entry['ngay']} ({entry['thoi_gian']}): {entry['khu_vuc']}",
    )
