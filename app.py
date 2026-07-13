import os

from flask import Flask, jsonify, request, send_from_directory
from apscheduler.schedulers.background import BackgroundScheduler

import scraper
import push_utils

app = Flask(__name__, static_folder="static", static_url_path="")


@app.route("/")
def index():
    return send_from_directory(app.static_folder, "index.html")


@app.route("/api/vapid-public-key")
def vapid_public_key():
    if not push_utils.VAPID_PUBLIC_KEY:
        return jsonify({"error": "Server chưa cấu hình VAPID key"}), 500
    return jsonify({"publicKey": push_utils.VAPID_PUBLIC_KEY})


@app.route("/api/subscribe", methods=["POST"])
def subscribe():
    sub = request.get_json(silent=True)
    if not sub or not sub.get("endpoint"):
        return jsonify({"error": "Subscription không hợp lệ"}), 400
    total = push_utils.add_subscription(sub)
    return jsonify({"ok": True, "totalSubscriptions": total})


@app.route("/api/check")
def check():
    try:
        matched = scraper.check_now()
        return jsonify({"ok": True, "count": len(matched), "entries": matched, "keywords": scraper.KEYWORDS})
    except Exception as err:
        print("[api/check] Lỗi:", err)
        return jsonify({"error": "Lỗi khi quét dữ liệu"}), 500


@app.route("/api/check-all")
def check_all():
    """Trả về TOÀN BỘ lịch cúp điện huyện Phú Tân, không lọc từ khóa."""
    try:
        entries = scraper.fetch_all_entries()
        return jsonify({"ok": True, "count": len(entries), "entries": entries})
    except Exception as err:
        print("[api/check-all] Lỗi:", err)
        return jsonify({"error": "Lỗi khi quét dữ liệu"}), 500


@app.route("/api/run-check-now", methods=["POST"])
def run_check_now():
    try:
        result = scraper.check_and_remind(push_utils.send_entry_notification)
        return jsonify({"ok": True, **result})
    except Exception as err:
        print("[api/run-check-now] Lỗi:", err)
        return jsonify({"error": "Lỗi khi quét/gửi thông báo"}), 500


@app.route("/api/test-notification", methods=["POST"])
def test_notification():
    try:
        subs_count = len(push_utils.load_subs())
        # Gửi thông báo giả giống y như thật (có ngày, giờ, khu vực, đếm ngược)
        fake_entry = {
            "ngay": "15 tháng 7 năm 2026",
            "thoi_gian": "Từ 08:00 đến 16:30",
            "khu_vuc": "Một phần xã Phú An (đường Cồn Tân Trung) - tỉnh An Giang",
            "dien_luc": "Điện lực Huyện Phú Tân",
            "trang_thai": "Đã duyệt",
            "hours_left": 2.5,
        }
        push_utils.send_entry_notification(fake_entry)
        return jsonify({"ok": True, "subscribersOnServer": subs_count})
    except Exception as err:
        print("[api/test-notification] Lỗi:", err)
        return jsonify({"error": str(err)}), 500


@app.route("/api/debug-subs")
def debug_subs():
    """Xem nhanh server hiện đang lưu bao nhiêu thiết bị đăng ký."""
    subs = push_utils.load_subs()
    return jsonify({"count": len(subs)})


def scheduled_job():
    print("[cron] Bắt đầu quét theo lịch...")
    try:
        scraper.check_and_remind(push_utils.send_entry_notification)
    except Exception as err:
        print("[cron] Lỗi:", err)


scheduler = BackgroundScheduler()
scheduler.add_job(scheduled_job, "cron", minute=0)  # chạy đúng đầu mỗi giờ
scheduler.start()

# Quét ngay 1 lần khi app khởi động (không cần đợi tới đầu giờ)
scheduled_job()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 3000))
    app.run(host="0.0.0.0", port=port)
