# Anki Telegram Reminder Bot

A single-user Telegram bot that sends AnkiWeb study reminders based on the selected decks and schedule configured in Telegram.

This repository can be public. Never commit Anki credentials, Telegram bot tokens, API tokens, webhook secrets, or other private values. Store them in GitHub Actions Secrets or Cloudflare Worker secrets.

## Architecture

```text
Telegram
   │ HTTPS webhook
   ▼
Cloudflare Worker + D1
   │ internal API
   ▼
GitHub Actions + Python + official anki package
   │
   ├─ syncs AnkiWeb
   ├─ reads study statistics
   └─ sends Telegram reminders
```

- The Cloudflare Worker handles `/start`, `/settings`, `/status`, `/study`, and inline-keyboard interactions.
- D1 stores user settings, reminder state, Telegram sessions, and the deck list.
- GitHub Actions runs every five minutes. A reminder may be delayed by up to approximately five minutes, plus GitHub Actions scheduling latency.
- GitHub Actions does not commit `runtime/config.json` or `runtime/state.json`; runtime state is stored through the control API.
- GitHub Pages hosts a Mini App that opens AnkiWeb in Telegram's WebView.

## Features

- Single-user access restricted to the configured `TELEGRAM_CHAT_ID`.
- Support for all decks, individual decks, multiple decks, and parent decks including subdecks, selected through a hierarchical deck browser.
- Up to five reminders per day with custom `HH:MM` times.
- Real-time configuration through Telegram inline keyboards.
- Vietnamese/English bilingual messages.
- Sends `✅ Completed today` at most once per day.
- Reports Anki sync and Telegram API errors.
- Commands: `/start`, `/status`, `/study`, `/settings`, `/cancel`, and `/help`.

## 1. Prepare GitHub

Add these values as GitHub Actions Secrets:

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

Add this GitHub Actions Variable:

```text
MINIAPP_URL=https://<username>.github.io/<repository>/
```

The `CLOUDFLARE_API_TOKEN` must have permission to deploy the Worker and manage the D1 database.

## 2. Create the Cloudflare D1 database and Worker

Install Node.js 22 or later, then run:

```bash
cd services/telegram-control
npm ci
npx wrangler login
npx wrangler d1 create anki-reminder
```

Copy the generated `database_id` into `services/telegram-control/wrangler.toml`:

```toml
database_id = "..."
```

Apply the schema and deploy the Worker:

```bash
npm run db:migrations:remote
npm run typecheck
npm run deploy
```

Set the Worker secrets:

```bash
npx wrangler secret put TELEGRAM_BOT_TOKEN
npx wrangler secret put TELEGRAM_CHAT_ID
npx wrangler secret put TELEGRAM_WEBHOOK_SECRET
npx wrangler secret put CONTROL_API_TOKEN
npx wrangler secret put MINIAPP_URL
```

`CONTROL_API_TOKEN` must match the GitHub Actions Secret with the same name. `MINIAPP_URL` is the URL of the GitHub Pages Mini App.

## 3. Register the Telegram webhook

Replace the token, Worker URL, and secret with your actual values before running:

```bash
curl -X POST "https://api.telegram.org/bot<TOKEN>/setWebhook" \
  -d "url=https://<worker-subdomain>.workers.dev/telegram/webhook" \
  -d "secret_token=<WEBHOOK_SECRET>"
```

Check the webhook status:

```bash
curl "https://api.telegram.org/bot<TOKEN>/getWebhookInfo"
```

After enabling the webhook, do not run `getUpdates` or polling for this bot.

## 4. Import the current configuration

The Worker creates default settings when it receives its first request. To import the configuration from `runtime/config.json`, run:

```bash
curl -X PUT "https://<worker-subdomain>.workers.dev/internal/runtime/config" \
  -H "Authorization: Bearer <CONTROL_API_TOKEN>" \
  -H "Content-Type: application/json" \
  --data-binary @runtime/config.json
```

## 5. Sync the deck list

Run the `Refresh Anki decks` workflow manually for the first sync. It temporarily syncs the Anki collection and uploads the deck list to D1.

The decks will then appear in Telegram under `/settings` → `Decks`.

## 6. GitHub Actions reminder

The `Anki reminder` workflow runs every five minutes and uses:

```text
RUNTIME_BACKEND=control_api
CONTROL_API_URL
CONTROL_API_TOKEN
```

The workflow only has `contents: read` permission. Runtime state is stored through the control API.

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

Locally, Python uses `JsonRuntimeRepository` by default. Use `RUNTIME_BACKEND=control_api` only after the Worker/D1 service is deployed and `CONTROL_API_URL` and `CONTROL_API_TOKEN` are configured.

## Security and limitations

- Do not commit Anki credentials, Telegram tokens, API tokens, or webhook secrets.
- The Worker only processes requests from the configured Telegram chat ID.
- Anki credentials are stored only in GitHub Actions Secrets and are never sent to the Worker.
- The Cloudflare Worker does not run Anki sync; `/status` shows the latest sync status reported by GitHub Actions.
- The official Anki library uses an internal API and is pinned to `26.8.1`. Re-evaluate compatibility before upgrading it.
