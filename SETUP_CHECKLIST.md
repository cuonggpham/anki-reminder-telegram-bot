# Checklist cài đặt Anki Telegram Reminder Bot

Làm lần lượt từ trên xuống. Đừng bỏ qua bước nào. Mỗi mục có `- [ ]` là một việc cần tự tick sau khi hoàn thành.

> Không gửi token, mật khẩu hoặc secret cho bất kỳ ai. Không commit chúng vào GitHub.

## Trước khi bắt đầu

- [ ] Repository đã được push lên GitHub.
- [ ] Bạn có tài khoản GitHub, Cloudflare và Telegram.
- [ ] Bạn đã có bot Telegram từ BotFather.
- [ ] Bạn biết `TELEGRAM_BOT_TOKEN` và `TELEGRAM_CHAT_ID` của mình.
- [ ] Máy tính có Node.js 22+ và Python 3.12+.

Kiểm tra Node.js:

```bash
node -v
```

Kết quả cần bắt đầu bằng `v22`.

Nếu đang dùng `nvm` và chưa có Node 22:

```bash
nvm install 22
nvm use 22
```

## Phần A — Bật GitHub Pages cho nút Study Now

- [ ] Mở repository trên GitHub.
- [ ] Chọn **Settings** → **Pages**.
- [ ] Ở mục **Build and deployment**, chọn **Source: GitHub Actions**.
- [ ] Mở tab **Actions** và chờ workflow `Deploy Mini App` chạy thành công.
- [ ] Mở URL Pages để chắc rằng nó không báo lỗi 404.

Với repository hiện tại, URL thường là:

```text
https://cuonggpham.github.io/anki-reminder-telegram-bot/
```

Ghi lại URL này. Nó sẽ được dùng với tên `MINIAPP_URL` ở các bước sau.

## Phần B — Tạm dừng reminder trong lúc setup

Việc này tránh GitHub Actions báo lỗi khi Cloudflare chưa được cấu hình.

- [ ] Vào GitHub repository → **Actions**.
- [ ] Chọn workflow **Anki reminder**.
- [ ] Bấm nút ba chấm ở góc phải → **Disable workflow**.

Sau khi setup xong, bạn sẽ bật lại workflow này ở Phần K.

## Phần C — Tạo database trên Cloudflare

- [ ] Mở Terminal tại thư mục project.
- [ ] Chạy các lệnh sau:

```bash
cd services/telegram-control
npm ci
npx wrangler login
```

Lệnh `wrangler login` sẽ mở browser. Đăng nhập đúng Cloudflare account của bạn rồi quay lại Terminal.

- [ ] Tạo database:

```bash
npx wrangler d1 create anki-reminder
```

Terminal sẽ hiện một đoạn tương tự:

```text
database_id = "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
```

- [ ] Copy giá trị bên trong dấu ngoặc kép của `database_id`.
- [ ] Mở file [services/telegram-control/wrangler.toml](services/telegram-control/wrangler.toml).
- [ ] Thay dòng này:

```toml
database_id = "REPLACE_WITH_CLOUDFLARE_D1_DATABASE_ID"
```

bằng ID vừa copy.

- [ ] Lưu file.
- [ ] Commit và push thay đổi:

```bash
git add services/telegram-control/wrangler.toml
git commit -m "set d1 database"
git push
```

`database_id` không phải mật khẩu, có thể commit.

## Phần D — Deploy Worker lần đầu

Trong Terminal, vẫn ở thư mục `services/telegram-control`:

```bash
npm run db:migrations:remote
npm run deploy
```

- [ ] Cả hai lệnh hoàn tất không báo lỗi.
- [ ] Copy URL Worker ở kết quả deploy. Nó thường có dạng:

```text
https://anki-telegram-control.<ten-cloudflare-cua-ban>.workers.dev
```

Đây là `CONTROL_API_URL`.

- [ ] Mở URL sau trên browser hoặc chạy Terminal:

```bash
curl https://anki-telegram-control.<ten-cloudflare-cua-ban>.workers.dev/health
```

Kết quả đúng:

```json
{"ok":true,"service":"telegram-control"}
```

## Phần E — Tạo hai secret ngẫu nhiên

Bạn cần hai secret khác nhau:

1. `TELEGRAM_WEBHOOK_SECRET`: bảo vệ request gửi từ Telegram.
2. `CONTROL_API_TOKEN`: cho phép GitHub Actions đọc và ghi cấu hình.

Tạo secret thứ nhất:

```bash
openssl rand -hex 32
```

- [ ] Lưu kết quả ở nơi an toàn, đặt tên `TELEGRAM_WEBHOOK_SECRET`.

Chạy lại lệnh để tạo secret thứ hai:

```bash
openssl rand -hex 32
```

- [ ] Lưu kết quả thứ hai, đặt tên `CONTROL_API_TOKEN`.
- [ ] Không dùng chung hai giá trị này.
- [ ] Không dán hai giá trị này vào source code, GitHub commit hoặc chat.

## Phần F — Thêm secret vào Cloudflare Worker

Trong Terminal, vẫn ở `services/telegram-control`, chạy từng lệnh. Mỗi lệnh sẽ hỏi giá trị; dán đúng giá trị rồi Enter.

```bash
npx wrangler secret put TELEGRAM_BOT_TOKEN
npx wrangler secret put TELEGRAM_CHAT_ID
npx wrangler secret put TELEGRAM_WEBHOOK_SECRET
npx wrangler secret put CONTROL_API_TOKEN
npx wrangler secret put MINIAPP_URL
```

Điền theo bảng:

| Tên secret | Giá trị cần dán |
|---|---|
| `TELEGRAM_BOT_TOKEN` | Token bot từ BotFather |
| `TELEGRAM_CHAT_ID` | Chat ID Telegram của bạn, chỉ là số |
| `TELEGRAM_WEBHOOK_SECRET` | Secret thứ nhất ở Phần E |
| `CONTROL_API_TOKEN` | Secret thứ hai ở Phần E |
| `MINIAPP_URL` | URL GitHub Pages ở Phần A |

- [ ] Đã thêm đủ 5 secret.
- [ ] Chạy deploy thêm một lần:

```bash
npm run deploy
```

## Phần G — Đưa cấu hình cũ vào Cloudflare

File `runtime/config.json` hiện chỉ dùng làm dữ liệu ban đầu. Sau bước này, bạn sẽ cấu hình reminder trực tiếp bằng Telegram.

Quay về root project:

```bash
cd ../..
```

Nhập token an toàn; Terminal sẽ không hiện chữ bạn gõ:

```bash
read -rs CONTROL_TOKEN
```

Dán `CONTROL_API_TOKEN` ở Phần E rồi bấm Enter.

Tạo biến URL Worker:

```bash
CONTROL_ENDPOINT="https://anki-telegram-control.<ten-cloudflare-cua-ban>.workers.dev"
```

Thay URL ví dụ bằng URL Worker thật của bạn, rồi import config:

```bash
curl -X PUT "$CONTROL_ENDPOINT/internal/runtime/config" \
  -H "Authorization: Bearer $CONTROL_TOKEN" \
  -H "Content-Type: application/json" \
  --data-binary @runtime/config.json
```

- [ ] Lệnh trả về `{"ok":true}`.

## Phần H — Cấu hình menu BotFather và Telegram webhook

### H.1. Hiển thị command trong Telegram

Mở Telegram → vào **BotFather**:

- [ ] Gõ `/setcommands`.
- [ ] Chọn bot của bạn.
- [ ] Dán nội dung sau:

```text
start - Mở menu
settings - Cấu hình reminder
status - Xem trạng thái gần nhất
study - Mở AnkiWeb
cancel - Hủy thao tác đang nhập
help - Hướng dẫn
```

### H.2. Kết nối bot với Worker

Trong Terminal:

```bash
read -rs BOT_TOKEN
read -rs WEBHOOK_SECRET
```

- [ ] Dán `TELEGRAM_BOT_TOKEN`, Enter.
- [ ] Dán `TELEGRAM_WEBHOOK_SECRET`, Enter.

Đăng ký webhook:

```bash
curl -X POST "https://api.telegram.org/bot${BOT_TOKEN}/setWebhook" \
  -d "url=${CONTROL_ENDPOINT}/telegram/webhook" \
  -d "secret_token=${WEBHOOK_SECRET}" \
  -d 'allowed_updates=["message","callback_query"]'
```

- [ ] Kết quả có `"ok":true`.

Kiểm tra webhook:

```bash
curl "https://api.telegram.org/bot${BOT_TOKEN}/getWebhookInfo"
```

- [ ] Trường `url` đúng URL Worker cộng `/telegram/webhook`.
- [ ] Không có `last_error_message`.

Mở bot Telegram và gửi:

```text
/start
```

- [ ] Bot trả lời ngay với menu.
- [ ] Bấm `⚙️ Settings` mở được màn hình cấu hình.
- [ ] Bấm `📖 Study now` mở được Mini App/AnkiWeb.

## Phần I — Thêm secrets vào GitHub

Trên GitHub repository:

- [ ] Vào **Settings** → **Secrets and variables** → **Actions**.
- [ ] Trong tab **Secrets**, bấm **New repository secret**.

Thêm các secret sau:

| Tên | Giá trị |
|---|---|
| `ANKIWEB_EMAIL` | Email đăng nhập AnkiWeb |
| `ANKIWEB_PASSWORD` | Mật khẩu AnkiWeb |
| `TELEGRAM_BOT_TOKEN` | Token từ BotFather |
| `TELEGRAM_CHAT_ID` | Chat ID Telegram của bạn |
| `CONTROL_API_URL` | URL Worker, ví dụ `https://...workers.dev` |
| `CONTROL_API_TOKEN` | Phải giống secret ở Cloudflare Worker |
| `CLOUDFLARE_ACCOUNT_ID` | Account ID Cloudflare |
| `CLOUDFLARE_API_TOKEN` | Token dùng để deploy Worker từ GitHub |

Để lấy `CLOUDFLARE_ACCOUNT_ID`:

- [ ] Mở Cloudflare dashboard.
- [ ] Chọn account đang dùng.
- [ ] Copy **Account ID** ở sidebar/dashboard.

Để tạo `CLOUDFLARE_API_TOKEN`:

- [ ] Cloudflare dashboard → **Manage Account** → **Account API Tokens**.
- [ ] Chọn **Create Token**.
- [ ] Tạo Custom Token có quyền **Edit Cloudflare Workers**.
- [ ] Chỉ scope token cho đúng Cloudflare account đang dùng.
- [ ] Nếu workflow migration báo thiếu quyền D1, thêm quyền **D1 Edit**.
- [ ] Copy token và lưu vào GitHub Secret `CLOUDFLARE_API_TOKEN`.

Trong tab **Variables**, thêm:

| Tên variable | Giá trị |
|---|---|
| `MINIAPP_URL` | URL GitHub Pages ở Phần A |

## Phần J — Test workflows

Vào GitHub → **Actions**, chạy thủ công theo đúng thứ tự:

1. `Deploy Telegram control service`
2. `Refresh Anki decks`
3. `Anki reminder`

### J.1. Deploy Telegram control service

- [ ] Chọn workflow `Deploy Telegram control service`.
- [ ] Bấm **Run workflow** → **Run workflow**.
- [ ] Chờ toàn bộ bước màu xanh.

### J.2. Refresh Anki decks

- [ ] Chọn workflow `Refresh Anki decks`.
- [ ] Bấm **Run workflow**.
- [ ] Chờ workflow màu xanh.
- [ ] Mở Telegram → gửi `/settings` → bấm `Decks`.
- [ ] Kiểm tra danh sách deck Anki đã xuất hiện.

### J.3. Test reminder thật

- [ ] Trong Telegram, vào `/settings`.
- [ ] Chọn deck cần test.
- [ ] Đặt một giờ reminder tạm thời cách thời điểm hiện tại khoảng 10 phút và trùng mốc 5 phút, ví dụ `18:25`.
- [ ] Bật reminder nếu đang tắt.
- [ ] Chờ GitHub Actions chạy.
- [ ] Kiểm tra Telegram có nhận reminder hoặc thông báo hoàn thành.
- [ ] Sau khi test xong, đặt lại giờ reminder mong muốn.

## Phần K — Bật reminder tự động

- [ ] GitHub → Actions → `Anki reminder`.
- [ ] Bấm nút ba chấm → **Enable workflow**.
- [ ] Kiểm tra workflow có chạy gần mỗi 5 phút.
- [ ] Theo dõi lần chạy đầu tiên để chắc rằng không có lỗi.

Reminder worker sẽ chỉ sync Anki khi đến giờ đã cấu hình. Thời gian gửi có thể lệch khoảng 5 phút, đôi khi lâu hơn nếu GitHub Actions bị xếp hàng.

## Sau khi setup xong

Từ đây, sử dụng Telegram để thay đổi:

- [ ] `/settings` → bật/tắt reminder.
- [ ] `/settings` → chọn `All decks`, một deck hoặc nhiều deck.
- [ ] `/settings` → chọn giờ hoặc nhập giờ tùy ý.
- [ ] `/settings` → đổi ngôn ngữ.
- [ ] `/status` → xem thời gian sync gần nhất.
- [ ] `/study` → mở AnkiWeb.

Không cần sửa `runtime/config.json` cho cấu hình production nữa.

## Xử lý lỗi thường gặp

| Hiện tượng | Cách kiểm tra |
|---|---|
| Bot không trả lời `/start` | Chạy `getWebhookInfo`; kiểm tra `url`, `last_error_message`, `TELEGRAM_WEBHOOK_SECRET`. |
| GitHub Actions báo `401` | Kiểm tra `CONTROL_API_URL` và `CONTROL_API_TOKEN`; token GitHub phải giống token trong Cloudflare Worker. |
| Không có deck trong Telegram | Chạy lại workflow `Refresh Anki decks`, xem log Anki sync. |
| Deploy Worker lỗi database | Kiểm tra `database_id` trong `services/telegram-control/wrangler.toml`. |
| Study now không mở đúng | Kiểm tra GitHub Pages xanh và `MINIAPP_URL` ở cả Cloudflare Worker lẫn GitHub Variable. |
| Reminder không gửi | Kiểm tra `/settings` có bật reminder, giờ đúng timezone và workflow `Anki reminder` đã enable. |

## Nếu cần quay lại cách cũ

Bạn có thể xóa webhook để dừng Worker:

```bash
curl -X POST "https://api.telegram.org/bot${BOT_TOKEN}/deleteWebhook"
```

Sau đó tạm thời chuyển `RUNTIME_BACKEND` về `json` trong workflow và dùng lại `runtime/config.json`. Chỉ làm việc này khi cần rollback.
