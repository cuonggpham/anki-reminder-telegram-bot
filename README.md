# Anki Telegram Reminder Bot

Bot Telegram single-user nhắc học AnkiWeb theo deck và lịch do người dùng cấu hình.

## Kiến trúc

- Python 3.12+ cho application core.
- Official Anki Python library được cô lập trong `adapters/anki`.
- Telegram Bot API được gọi qua `httpx`.
- GitHub Actions chạy worker mỗi 5 phút; application tự kiểm tra giờ local.
- Cấu hình runtime nằm trong `runtime/*.json` của repository private.
- GitHub Pages host Mini App mở AnkiWeb trong Telegram WebView.

Thiết kế dùng ports/adapters để sau này có thể thay Telegram API, persistence hoặc scheduler mà không viết lại domain logic.

## Chức năng hiện tại

- Single-user.
- `All decks`, một deck, nhiều deck và subdeck.
- Tối đa 5 reminder mỗi ngày.
- Giờ tùy ý theo định dạng `HH:MM`.
- Inline keyboard để cấu hình deck, giờ và bật/tắt reminder.
- `/start`, `/status`, `/study`, `/settings`, `/times`.
- Notification song ngữ Việt/Anh.
- Gửi thông báo hoàn thành một lần mỗi ngày.
- Cảnh báo khi sync hoặc Telegram API lỗi.

## Setup

### 1. Tạo bot Telegram

Tạo bot bằng BotFather và lấy token. Chat ID phải là chat cá nhân duy nhất được phép dùng bot.

### 2. Tạo repository private

Push project vào repository private. GitHub Actions cần quyền `Contents: Read and write` để cập nhật `runtime/config.json` và `runtime/state.json`.

### 3. Thêm GitHub Secrets

```text
ANKIWEB_EMAIL
ANKIWEB_PASSWORD
TELEGRAM_BOT_TOKEN
TELEGRAM_CHAT_ID
```

Thêm GitHub Actions Variable:

```text
MINIAPP_URL=https://<username>.github.io/<repository>/
```

### 4. Bật GitHub Pages

Trong repository settings, chọn Pages → Source: GitHub Actions. Workflow `pages.yml` sẽ deploy `miniapp/`.

### 5. Chạy feasibility test

Trước khi bật lịch tự động, chạy thủ công workflow `Anki reminder`. Đây là bước bắt buộc để kiểm tra phiên bản official Anki library và sync read-only.

### 6. Cấu hình BotFather

- Set commands theo danh sách trong `TelegramBotApi.set_commands()`.
- Configure Main Mini App bằng URL GitHub Pages.

## Local development

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
PYTHONPATH=src pytest
```

Để chạy local, export các biến trong `.env.example` hoặc thiết lập trực tiếp trong shell. Không commit `.env`, credentials, collection Anki hoặc session token.

## Custom reminder time

Trong bot, chọn `Custom time / Giờ tùy ý` rồi gửi:

```text
08:15, 13:30, 21:45
```

Có thể đặt tối đa 5 giờ. Worker chạy theo chu kỳ 5 phút nên thời điểm gửi có thể lệch tối đa khoảng 5 phút.

## Known limitations

- GitHub Actions schedule có thể bị GitHub trì hoãn.
- Telegram configuration polling không realtime; mục tiêu là tối đa khoảng 5 phút.
- Anki Python library có phần API nội bộ; hiện pin ở phiên bản `26.8.1` và cần kiểm tra lại khi nâng version.
- Mini App dùng top-level navigation tới AnkiWeb, không iframe và không lưu credentials.
