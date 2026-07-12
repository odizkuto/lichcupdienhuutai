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


@app.route("/api/run-check-now", methods=["POST"])
def run_check_now():
    try:
        result = scraper.check_and_notify(push_utils.send_entry_notification)
        return jsonify({"ok": True, **result})
    except Exception as err:
        print("[api/run-check-now] Lỗi:", err)
        return jsonify({"error": "Lỗi khi quét/gửi thông báo"}), 500


def scheduled_job():
    print("[cron] Bắt đầu quét theo lịch...")
    try:
        scraper.check_and_notify(push_utils.send_entry_notification)
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
