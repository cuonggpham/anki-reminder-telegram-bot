# Telegram control service

Cloudflare Worker nhận Telegram webhook và lưu cấu hình/runtime vào D1.

## Local setup

```bash
npm install
npm run typecheck
```

Tạo D1 database và điền `database_id` trong `wrangler.toml` trước khi migrate/deploy.

## Secrets

```bash
npx wrangler secret put TELEGRAM_BOT_TOKEN
npx wrangler secret put TELEGRAM_CHAT_ID
npx wrangler secret put TELEGRAM_WEBHOOK_SECRET
npx wrangler secret put CONTROL_API_TOKEN
npx wrangler secret put MINIAPP_URL
```

## Deployment order

```bash
npx wrangler d1 create anki-reminder
npm run db:migrations:remote
npm run deploy
```

Sau khi deploy, gọi Telegram `setWebhook` với URL `/telegram/webhook` và header secret token.
