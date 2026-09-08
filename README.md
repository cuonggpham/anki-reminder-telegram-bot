# Anki Telegram Reminder Bot

Bot Telegram single-user nhắc học AnkiWeb theo deck và lịch cấu hình trong Telegram.

## Kiến trúc

```text
Telegram
   │ HTTPS webhook
   ▼
Cloudflare Worker + D1
   │ internal API
   ▼
GitHub Actions + Python + official anki package
   │
   ├─ sync AnkiWeb
   ├─ đọc thống kê
   └─ gửi reminder Telegram
```

- Cloudflare Worker xử lý `/start`, `/settings`, `/status`, `/study` và inline keyboard.
- D1 lưu cấu hình, trạng thái gửi, session Telegram và danh sách deck.
- GitHub Actions chạy mỗi 5 phút; reminder có thể trễ tối đa khoảng 5 phút cộng với độ trễ cron của GitHub.
- GitHub Actions không còn commit `runtime/config.json` hoặc `runtime/state.json`.
- GitHub Pages host Mini App mở AnkiWeb trong Telegram WebView.

## Tính năng

- Single-user, chỉ chấp nhận `TELEGRAM_CHAT_ID` đã cấu hình.
- `All decks`, một deck, nhiều deck và deck cha bao gồm subdeck.
- Tối đa 5 reminder/ngày, giờ tùy ý theo `HH:MM`.
- Cấu hình realtime bằng inline keyboard Telegram.
- Song ngữ Việt/Anh.
- Gửi `✅ Đã hoàn thành hôm nay` tối đa một lần/ngày.
- Cảnh báo lỗi Anki sync hoặc Telegram API.
- `/start`, `/status`, `/study`, `/settings`, `/cancel`, `/help`.

## 1. Chuẩn bị GitHub

Repository nên để private. Thêm GitHub Secrets:

```text
ANKIWEB_EMAIL
ANKIWEB_PASSWORD
TELEGRAM_BOT_TOKEN
TELEGRAM_CHAT_ID
CONTROL_API_URL
CONTROL_API_TOKEN
CLOUDFLARE_API_TOKEN
CLOUDFLARE_ACCOUNT_ID
```

Thêm GitHub Actions Variable:

```text
MINIAPP_URL=https://<username>.github.io/<repository>/
```

`CLOUDFLARE_API_TOKEN` cần quyền deploy Worker và quản lý D1 database.

## 2. Tạo Cloudflare D1 và Worker

Cài Node.js 22+, sau đó:

```bash
cd services/telegram-control
npm ci
npx wrangler login
npx wrangler d1 create anki-reminder
```

Copy `database_id` vào `services/telegram-control/wrangler.toml`, thay giá trị placeholder:

```toml
database_id = "..."
```

Áp dụng schema và deploy:

```bash
npm run db:migrations:remote
npm run typecheck
npm run deploy
```

Thiết lập Worker secrets:

```bash
npx wrangler secret put TELEGRAM_BOT_TOKEN
npx wrangler secret put TELEGRAM_CHAT_ID
npx wrangler secret put TELEGRAM_WEBHOOK_SECRET
npx wrangler secret put CONTROL_API_TOKEN
npx wrangler secret put MINIAPP_URL
```

`CONTROL_API_TOKEN` phải trùng với GitHub Secret cùng tên. `MINIAPP_URL` là URL GitHub Pages của Mini App.

## 3. Đăng ký Telegram webhook

Thay token, URL Worker và secret thật trước khi chạy:

```bash
curl -X POST "https://api.telegram.org/bot<TOKEN>/setWebhook" \
  -d "url=https://<worker-subdomain>.workers.dev/telegram/webhook" \
  -d "secret_token=<WEBHOOK_SECRET>"
```

Kiểm tra:

```bash
curl "https://api.telegram.org/bot<TOKEN>/getWebhookInfo"
```

Sau khi bật webhook, không chạy `getUpdates`/polling cho bot này.

## 4. Import cấu hình hiện tại

Worker tự tạo cấu hình mặc định khi nhận request đầu tiên. Để giữ cấu hình đang có trong `runtime/config.json`, gọi:

```bash
curl -X PUT "https://<worker-subdomain>.workers.dev/internal/runtime/config" \
  -H "Authorization: Bearer <CONTROL_API_TOKEN>" \
  -H "Content-Type: application/json" \
  --data-binary @runtime/config.json
```

## 5. Đồng bộ danh sách deck

Chạy workflow `Refresh Anki decks` thủ công lần đầu trong GitHub Actions. Workflow này sync collection tạm thời và đưa danh sách deck lên D1.

Sau đó Telegram sẽ hiển thị deck trong `/settings` → `Decks`.

## 6. GitHub Actions reminder

Workflow `Anki reminder` chạy mỗi 5 phút và dùng:

```text
RUNTIME_BACKEND=control_api
CONTROL_API_URL
CONTROL_API_TOKEN
```

Workflow chỉ có quyền `contents: read`; runtime state được lưu qua control API.

## Local development

Python:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
PYTHONPATH=src pytest
```

Worker:

```bash
cd services/telegram-control
npm ci
npm run typecheck
```

Local Python mặc định dùng `JsonRuntimeRepository`. Chỉ dùng `RUNTIME_BACKEND=control_api` khi đã có Worker/D1 và thiết lập `CONTROL_API_URL`, `CONTROL_API_TOKEN`.

## Bảo mật và giới hạn

- Không commit Anki credentials, Telegram token, API token hoặc webhook secret.
- Worker chỉ xử lý đúng chat ID đã cấu hình.
- Anki credentials chỉ nằm ở GitHub Secrets và không đi qua Worker.
- Cloudflare Worker không chạy Anki sync; `/status` hiển thị trạng thái sync gần nhất từ GitHub Actions.
- Official Anki library dùng API nội bộ và đang pin ở `26.8.1`; cần kiểm tra lại khi nâng version.
