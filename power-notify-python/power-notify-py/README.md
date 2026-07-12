# Power Notify (bản Python/Flask) — Lịch Cúp Điện tự động + Push Notification

Bản này viết bằng **Python/Flask**, dùng `requirements.txt` — khớp với cách bạn đã
deploy trên Render trước đó.

Tự động quét trang **lichcupdien.org/lich-cup-dien-phu-tan-an-giang** (Huyện Phú Tân,
An Giang) mỗi giờ, so khớp với từ khóa (Xã Phú An, Xã Tân Trung, Đường Cồn, Quốc lộ 80B),
và gửi **push notification** ra điện thoại khi có lịch mới liên quan.

## 1. Chạy thử ở máy local

```bash
cd power-notify-py
pip install -r requirements.txt
```

### VAPID key (bắt buộc để gửi được push)

Bạn có thể dùng cặp key có sẵn bên dưới (mình đã tạo sẵn), hoặc tự tạo cặp mới bằng:

```bash
python -c "from py_vapid import Vapid02; v = Vapid02(); v.generate_keys(); print(v.public_key, v.private_key)"
```

Set biến môi trường (tạo file `.env` hoặc export trực tiếp):

```
VAPID_PUBLIC_KEY=BMSQOL4YYCqcNNiyRdZz1k0rjg88u2Zs8jU3gHAe5jDH5o-UAHEpkaUzCI4GggYuG5aVXwSOe-grnN7rCa1tkG8
VAPID_PRIVATE_KEY=HlcYghwstlnH1LxN0UydkWYUUGwQgVJtxs5SCzfr3es
VAPID_SUBJECT=mailto:ban@email.com
```

Chạy:
```bash
python app.py
```
Mở `http://localhost:3000`.

## 2. Deploy lên Render

1. Đẩy toàn bộ nội dung thư mục này lên GitHub repo hiện tại của bạn (thay thế các
   file cũ, hoặc merge vào thư mục `PowerNotify/`).
2. Trên Render, service của bạn cần:
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `gunicorn app:app` (đã có sẵn trong file `Procfile`, Render tự
     nhận nếu bạn để `Procfile` ở thư mục gốc)
3. Vào tab **Environment**, thêm các biến:
   - `VAPID_PUBLIC_KEY`
   - `VAPID_PRIVATE_KEY`
   - `VAPID_SUBJECT`
   - (tùy chọn) `KEYWORDS` — cách nhau bởi dấu phẩy
   - (tùy chọn) `TARGET_URLS` — cách nhau bởi dấu phẩy

## 3. Lưu ý về lưu trữ dữ liệu (Render free tier)

App lưu 2 file nhỏ trong `data/`:
- `subscriptions.json` — thiết bị đã đăng ký nhận thông báo
- `seen.json` — các lịch đã từng thông báo (tránh gửi trùng)

Trên gói **Free**, ổ đĩa không giữ được lâu dài — mỗi lần deploy lại, 2 file này
có thể bị mất, nghĩa là người dùng phải bật lại thông báo, và có thể nhận lại
thông báo cũ. Muốn khắc phục triệt để, cần nâng cấp gói + gắn Persistent Disk,
hoặc chuyển sang dùng database. Nhắn mình nếu bạn muốn làm phần này.

## 4. Test gửi thông báo ngay lập tức

```bash
curl -X POST http://localhost:3000/api/run-check-now
```

## 5. Cấu trúc project

```
power-notify-py/
├── app.py           # Flask app + APScheduler chạy mỗi giờ
├── scraper.py       # Quét & parse dữ liệu, so khớp từ khóa
├── push_utils.py    # Gửi web push bằng pywebpush
├── requirements.txt
├── Procfile
├── static/
│   ├── index.html
│   ├── app.js
│   └── sw.js
└── data/            # subscriptions.json & seen.json (tự tạo khi chạy)
```
