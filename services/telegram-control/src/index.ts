interface Env {
  DB: D1Database;
  TELEGRAM_BOT_TOKEN: string;
  TELEGRAM_CHAT_ID: string;
  TELEGRAM_WEBHOOK_SECRET: string;
  CONTROL_API_TOKEN: string;
  MINIAPP_URL: string;
}

interface TelegramUser {
  id: number;
}

interface TelegramChat {
  id: number;
}

interface TelegramMessage {
  chat: TelegramChat;
  text?: string;
  message_id: number;
}

interface TelegramCallbackQuery {
  id: string;
  data?: string;
  from: TelegramUser;
  message?: TelegramMessage;
}

interface TelegramUpdate {
  update_id: number;
  message?: TelegramMessage;
  callback_query?: TelegramCallbackQuery;
}

interface Settings {
  chatId: string;
  enabled: boolean;
  selectedDecks: string[];
  reminderTimes: string[];
  timezone: string;
  language: "vi-en" | "en-vi";
  version: number;
  updatedAt: string;
}

interface RuntimeState {
  sentSlots: Record<string, string>;
  completionSentDates: string[];
  lastSyncAt: string | null;
}

const ALL_DECKS = "*";
const DEFAULT_TIMES = ["08:00", "18:00"];
const MAX_DECKS_PER_PAGE = 12;
const MAX_SESSION_SECONDS = 15 * 60;

export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    const url = new URL(request.url);

    try {
      if (request.method === "GET" && url.pathname === "/health") {
        return json({ ok: true, service: "telegram-control" });
      }

      if (url.pathname === "/telegram/webhook") {
        return handleWebhook(request, env);
      }

      if (url.pathname.startsWith("/internal/")) {
        return handleInternal(request, env, url);
      }

      return json({ error: "Not found" }, 404);
    } catch (error) {
      console.error("control service error", error);
      return json({ error: "Internal server error" }, 500);
    }
  },
};

async function handleWebhook(request: Request, env: Env): Promise<Response> {
  if (request.method !== "POST") return json({ error: "Method not allowed" }, 405);
  if (
    request.headers.get("X-Telegram-Bot-Api-Secret-Token") !==
    env.TELEGRAM_WEBHOOK_SECRET
  ) {
    return json({ error: "Unauthorized" }, 401);
  }

  const update = (await request.json()) as TelegramUpdate;
  const inserted = await env.DB.prepare(
    "INSERT OR IGNORE INTO processed_updates (update_id, processed_at) VALUES (?, ?)",
  )
    .bind(update.update_id, new Date().toISOString())
    .run();

  if (!inserted.meta.changes) return json({ ok: true, duplicate: true });

  const chatId = getChatId(update);
  if (chatId !== env.TELEGRAM_CHAT_ID) return json({ ok: true, ignored: true });

  await processUpdate(update, env, chatId);
  return json({ ok: true });
}

async function processUpdate(update: TelegramUpdate, env: Env, chatId: string) {
  const callback = update.callback_query;
  if (callback) {
    if (String(callback.from.id) !== chatId) return;
    await answerCallback(env, callback.id);
    await processCallback(callback, env, chatId);
    return;
  }

  const message = update.message;
  if (!message || String(message.chat.id) !== chatId) return;

  const text = (message.text ?? "").trim();
  const session = await loadSession(env.DB, chatId);
  if (session?.flow === "times" && !text.startsWith("/")) {
    await saveTimesFromText(env, chatId, text);
    return;
  }

  const command = text.split(/\s+/, 1)[0].split("@")[0].toLowerCase();
  switch (command) {
    case "/start":
      await sendMainMenu(env, chatId);
      break;
    case "/settings":
      await sendSettings(env, chatId);
      break;
    case "/status":
      await sendStatus(env, chatId);
      break;
    case "/study":
      await sendStudy(env, chatId);
      break;
    case "/cancel":
      await deleteSession(env.DB, chatId);
      await sendMessage(env, chatId, "Đã hủy thao tác. / Cancelled.");
      break;
    case "/help":
      await sendMessage(
        env,
        chatId,
        "Các lệnh / Commands:\n/start - Menu\n/settings - Cấu hình / Settings\n/status - Trạng thái gần nhất / Latest status\n/study - Học ngay / Study now\n/cancel - Hủy / Cancel",
      );
      break;
    default:
      await sendMainMenu(env, chatId);
  }
}

async function processCallback(
  callback: TelegramCallbackQuery,
  env: Env,
  chatId: string,
) {
  const data = callback.data ?? "";
  const messageId = callback.message?.message_id;

  if (data === "menu:main") {
    await editMessage(env, chatId, messageId, "📚 Anki Reminder", mainKeyboard());
  } else if (data === "menu:settings") {
    await editSettings(env, chatId, messageId);
  } else if (data === "menu:status") {
    await editMessage(env, chatId, messageId, await statusText(env.DB, chatId), studyKeyboard(env));
  } else if (data === "menu:study") {
    await sendStudy(env, chatId);
  } else if (data === "settings:toggle") {
    const settings = await loadSettings(env.DB, chatId);
    settings.enabled = !settings.enabled;
    await saveSettings(env.DB, settings);
    await editSettings(env, chatId, messageId);
  } else if (data === "settings:decks") {
    await editDecks(env, chatId, messageId, 0);
  } else if (data.startsWith("decks:page:")) {
    await editDecks(env, chatId, messageId, Number(data.split(":")[2]) || 0);
  } else if (data === "decks:all") {
    const settings = await loadSettings(env.DB, chatId);
    settings.selectedDecks = [ALL_DECKS];
    await saveSettings(env.DB, settings);
    await editDecks(env, chatId, messageId, 0);
  } else if (data.startsWith("decks:toggle:")) {
    const index = Number(data.split(":")[2]);
    const decks = await listDecks(env.DB);
    const selected = decks[index];
    if (selected) {
      const settings = await loadSettings(env.DB, chatId);
      settings.selectedDecks = toggleDeck(settings.selectedDecks, selected);
      await saveSettings(env.DB, settings);
    }
    await editDecks(env, chatId, messageId, Math.floor(index / MAX_DECKS_PER_PAGE));
  } else if (data === "decks:done") {
    await editSettings(env, chatId, messageId);
  } else if (data === "settings:times") {
    await editTimes(env, chatId, messageId);
  } else if (data.startsWith("times:toggle:")) {
    const value = data.slice("times:toggle:".length);
    const settings = await loadSettings(env.DB, chatId);
    settings.reminderTimes = toggleTime(settings.reminderTimes, value);
    await saveSettings(env.DB, settings);
    await editTimes(env, chatId, messageId);
  } else if (data === "times:custom") {
    await saveSession(env.DB, chatId, "times", {});
    await sendMessage(
      env,
      chatId,
      "✍️ Gửi 1-5 giờ theo định dạng HH:MM, cách nhau bằng dấu phẩy.\nSend 1-5 times as HH:MM, separated by commas.\n\nVí dụ / Example: 08:15, 13:30, 21:45",
    );
  } else if (data === "times:done") {
    await deleteSession(env.DB, chatId);
    await editSettings(env, chatId, messageId);
  } else if (data === "settings:language") {
    await editLanguages(env, chatId, messageId);
  } else if (data.startsWith("language:")) {
    const language = data.slice("language:".length);
    if (language === "vi-en" || language === "en-vi") {
      const settings = await loadSettings(env.DB, chatId);
      settings.language = language;
      await saveSettings(env.DB, settings);
    }
    await editSettings(env, chatId, messageId);
  }
}

async function handleInternal(request: Request, env: Env, url: URL): Promise<Response> {
  if (request.headers.get("Authorization") !== `Bearer ${env.CONTROL_API_TOKEN}`) {
    return json({ error: "Unauthorized" }, 401);
  }

  const chatId = env.TELEGRAM_CHAT_ID;
  if (request.method === "GET" && url.pathname === "/internal/runtime") {
    return json({ config: await loadSettings(env.DB, chatId), state: await loadState(env.DB, chatId) });
  }

  if (request.method === "PUT" && url.pathname === "/internal/runtime/state") {
    const body = (await request.json()) as RuntimeState;
    await saveState(env.DB, chatId, body);
    return json({ ok: true });
  }

  if (request.method === "POST" && url.pathname === "/internal/decks") {
    const body = (await request.json()) as { decks?: string[] };
    const decks = [...new Set((body.decks ?? []).map(String))].sort();
    const batch = env.DB.batch([
      env.DB.prepare("DELETE FROM decks"),
      ...decks.map((deck) =>
        env.DB.prepare("INSERT INTO decks (deck_name, updated_at) VALUES (?, ?)").bind(deck, new Date().toISOString()),
      ),
    ]);
    await batch;
    return json({ ok: true, count: decks.length });
  }

  if (request.method === "GET" && url.pathname === "/internal/health") {
    await env.DB.prepare("SELECT 1").first();
    return json({ ok: true, service: "telegram-control", database: "ok" });
  }

  return json({ error: "Not found" }, 404);
}

async function loadSettings(db: D1Database, chatId: string): Promise<Settings> {
  const row = await db.prepare("SELECT * FROM user_settings WHERE chat_id = ?").bind(chatId).first<{
    chat_id: string;
    enabled: number;
    selected_decks_json: string;
    reminder_times_json: string;
    timezone: string;
    language: "vi-en" | "en-vi";
    version: number;
    updated_at: string;
  }>();
  if (!row) {
    const now = new Date().toISOString();
    await db.prepare(
      "INSERT INTO user_settings (chat_id, updated_at) VALUES (?, ?)",
    ).bind(chatId, now).run();
    return {
      chatId,
      enabled: true,
      selectedDecks: [ALL_DECKS],
      reminderTimes: [...DEFAULT_TIMES],
      timezone: "Asia/Ho_Chi_Minh",
      language: "vi-en",
      version: 1,
      updatedAt: now,
    };
  }
  return {
    chatId: row.chat_id,
    enabled: Boolean(row.enabled),
    selectedDecks: parseJson(row.selected_decks_json, [ALL_DECKS]),
    reminderTimes: parseJson(row.reminder_times_json, [...DEFAULT_TIMES]),
    timezone: row.timezone,
    language: row.language,
    version: row.version,
    updatedAt: row.updated_at,
  };
}

async function saveSettings(db: D1Database, settings: Settings) {
  validateSettings(settings);
  const now = new Date().toISOString();
  await db.prepare(
    `UPDATE user_settings
     SET enabled = ?, selected_decks_json = ?, reminder_times_json = ?, timezone = ?, language = ?, version = version + 1, updated_at = ?
     WHERE chat_id = ?`,
  ).bind(
    settings.enabled ? 1 : 0,
    JSON.stringify(settings.selectedDecks),
    JSON.stringify(settings.reminderTimes),
    settings.timezone,
    settings.language,
    now,
    settings.chatId,
  ).run();
  settings.updatedAt = now;
}

async function loadState(db: D1Database, chatId: string): Promise<RuntimeState> {
  const row = await db.prepare("SELECT * FROM runtime_state WHERE chat_id = ?").bind(chatId).first<{
    sent_slots_json: string;
    completion_sent_dates_json: string;
    last_sync_at: string | null;
  }>();
  if (!row) {
    await saveState(db, chatId, { sentSlots: {}, completionSentDates: [], lastSyncAt: null });
    return { sentSlots: {}, completionSentDates: [], lastSyncAt: null };
  }
  return {
    sentSlots: parseJson(row.sent_slots_json, {}),
    completionSentDates: parseJson(row.completion_sent_dates_json, []),
    lastSyncAt: row.last_sync_at,
  };
}

async function saveState(db: D1Database, chatId: string, state: RuntimeState) {
  const now = new Date().toISOString();
  await db.prepare(
    `INSERT INTO runtime_state (chat_id, sent_slots_json, completion_sent_dates_json, last_sync_at, updated_at)
     VALUES (?, ?, ?, ?, ?)
     ON CONFLICT(chat_id) DO UPDATE SET sent_slots_json = excluded.sent_slots_json,
       completion_sent_dates_json = excluded.completion_sent_dates_json,
       last_sync_at = excluded.last_sync_at, updated_at = excluded.updated_at`,
  ).bind(
    chatId,
    JSON.stringify(state.sentSlots),
    JSON.stringify(state.completionSentDates),
    state.lastSyncAt,
    now,
  ).run();
}

async function listDecks(db: D1Database): Promise<string[]> {
  const result = await db.prepare("SELECT deck_name FROM decks ORDER BY deck_name").all<{ deck_name: string }>();
  return result.results.map((row) => row.deck_name);
}

async function loadSession(db: D1Database, chatId: string): Promise<{ flow: string; payload: Record<string, unknown> } | null> {
  const row = await db.prepare(
    "SELECT flow, payload_json, expires_at FROM telegram_sessions WHERE chat_id = ?",
  ).bind(chatId).first<{ flow: string; payload_json: string; expires_at: string }>();
  if (!row) return null;
  if (row.expires_at < new Date().toISOString()) {
    await deleteSession(db, chatId);
    return null;
  }
  return { flow: row.flow, payload: parseJson(row.payload_json, {}) };
}

async function saveSession(db: D1Database, chatId: string, flow: string, payload: Record<string, unknown>) {
  const expires = new Date(Date.now() + MAX_SESSION_SECONDS * 1000).toISOString();
  await db.prepare(
    `INSERT INTO telegram_sessions (chat_id, flow, payload_json, expires_at) VALUES (?, ?, ?, ?)
     ON CONFLICT(chat_id) DO UPDATE SET flow = excluded.flow, payload_json = excluded.payload_json, expires_at = excluded.expires_at`,
  ).bind(chatId, flow, JSON.stringify(payload), expires).run();
}

async function deleteSession(db: D1Database, chatId: string) {
  await db.prepare("DELETE FROM telegram_sessions WHERE chat_id = ?").bind(chatId).run();
}

async function saveTimesFromText(env: Env, chatId: string, text: string) {
  try {
    const values = [...new Set(text.split(/[;,]/).map((value) => value.trim()).filter(Boolean))].sort();
    if (values.length < 1 || values.length > 5 || values.some((value) => !isClockTime(value))) {
      throw new Error("invalid time list");
    }
    const settings = await loadSettings(env.DB, chatId);
    settings.reminderTimes = values;
    await saveSettings(env.DB, settings);
    await deleteSession(env.DB, chatId);
    await sendMessage(env, chatId, `✅ Đã lưu giờ / Times saved: ${values.join(", ")}`);
    await sendSettings(env, chatId);
  } catch {
    await sendMessage(env, chatId, "❌ Sai định dạng. Vui lòng gửi 1-5 giờ HH:MM. / Invalid format. Send 1-5 times as HH:MM.");
  }
}

async function sendMainMenu(env: Env, chatId: string) {
  await sendMessage(env, chatId, "📚 Anki Reminder\n\nChọn thao tác / Choose an action:", mainKeyboard());
}

async function sendSettings(env: Env, chatId: string) {
  await sendMessage(env, chatId, await settingsText(env.DB, chatId), settingsKeyboard(await loadSettings(env.DB, chatId)));
}

async function editSettings(env: Env, chatId: string, messageId?: number) {
  if (!messageId) return sendSettings(env, chatId);
  await editMessage(env, chatId, messageId, await settingsText(env.DB, chatId), settingsKeyboard(await loadSettings(env.DB, chatId)));
}

async function sendStatus(env: Env, chatId: string) {
  await sendMessage(env, chatId, await statusText(env.DB, chatId), studyKeyboard(env));
}

async function sendStudy(env: Env, chatId: string) {
  await sendMessage(env, chatId, "📖 Học ngay / Study now", studyKeyboard(env));
}

async function settingsText(db: D1Database, chatId: string): Promise<string> {
  const settings = await loadSettings(db, chatId);
  const status = settings.enabled ? "✅ Bật / Enabled" : "⏸ Tắt / Disabled";
  return `⚙️ Cấu hình / Settings\n\n🔔 ${status}\n🗂 Deck: ${settings.selectedDecks.join(", ")}\n⏰ Times: ${settings.reminderTimes.join(", ")}\n🌍 Timezone: ${settings.timezone}\n🌐 Language: ${settings.language}`;
}

async function statusText(db: D1Database, chatId: string): Promise<string> {
  const state = await loadState(db, chatId);
  return `📊 Trạng thái gần nhất / Latest status\n\nLast sync: ${state.lastSyncAt ?? "Chưa có / Not yet"}\n\nDữ liệu được cập nhật bởi GitHub Actions. / Data is updated by GitHub Actions.`;
}

async function editDecks(env: Env, chatId: string, messageId: number | undefined, page: number) {
  const decks = await listDecks(env.DB);
  const settings = await loadSettings(env.DB, chatId);
  const totalPages = Math.max(1, Math.ceil(decks.length / MAX_DECKS_PER_PAGE));
  const safePage = Math.min(Math.max(page, 0), totalPages - 1);
  const start = safePage * MAX_DECKS_PER_PAGE;
  const visible = decks.slice(start, start + MAX_DECKS_PER_PAGE);
  const rows = visible.map((deck, offset) => {
    const index = start + offset;
    const marker = settings.selectedDecks.includes(deck) ? "✅" : "⬜";
    return [{ text: `${marker} ${deck}`, callback_data: `decks:toggle:${index}` }];
  });
  rows.unshift([{ text: settings.selectedDecks.includes(ALL_DECKS) ? "✅ All decks" : "⬜ All decks", callback_data: "decks:all" }]);
  const navigation: { text: string; callback_data: string }[] = [];
  if (safePage > 0) navigation.push({ text: "◀️", callback_data: `decks:page:${safePage - 1}` });
  navigation.push({ text: `${safePage + 1}/${totalPages}`, callback_data: `decks:page:${safePage}` });
  if (safePage + 1 < totalPages) navigation.push({ text: "▶️", callback_data: `decks:page:${safePage + 1}` });
  rows.push(navigation);
  rows.push([{ text: "✅ Done / Xong", callback_data: "decks:done" }]);
  const text = decks.length ? "🗂 Chọn deck / Select decks" : "🗂 Chưa có danh sách deck. Chạy deck sync trước. / No decks yet. Run deck sync first.";
  await editMessage(env, chatId, messageId, text, { inline_keyboard: rows });
}

async function editTimes(env: Env, chatId: string, messageId: number | undefined) {
  const settings = await loadSettings(env.DB, chatId);
  const presets = ["07:30", "08:00", "12:00", "18:00", "21:00"];
  const rows = presets.map((time) => [{ text: `${settings.reminderTimes.includes(time) ? "✅" : "⬜"} ${time}`, callback_data: `times:toggle:${time}` }]);
  rows.push([{ text: "✍️ Custom / Tùy ý", callback_data: "times:custom" }]);
  rows.push([{ text: "✅ Done / Xong", callback_data: "times:done" }]);
  await editMessage(env, chatId, messageId, "⏰ Chọn giờ / Select times", { inline_keyboard: rows });
}

async function editLanguages(env: Env, chatId: string, messageId: number | undefined) {
  const settings = await loadSettings(env.DB, chatId);
  const keyboard = {
    inline_keyboard: [
      [{ text: `${settings.language === "vi-en" ? "✅" : "⬜"} Việt / English`, callback_data: "language:vi-en" }],
      [{ text: `${settings.language === "en-vi" ? "✅" : "⬜"} English / Việt`, callback_data: "language:en-vi" }],
    ],
  };
  await editMessage(env, chatId, messageId, "🌐 Ngôn ngữ / Language", keyboard);
}

function mainKeyboard() {
  return {
    inline_keyboard: [
      [{ text: "⚙️ Cấu hình / Settings", callback_data: "menu:settings" }],
      [{ text: "📊 Trạng thái / Status", callback_data: "menu:status" }, { text: "📖 Học ngay / Study", callback_data: "menu:study" }],
    ],
  };
}

function settingsKeyboard(settings: Settings) {
  return {
    inline_keyboard: [
      [{ text: settings.enabled ? "🔔 ON / Đang bật" : "🔕 OFF / Đang tắt", callback_data: "settings:toggle" }],
      [{ text: "🗂 Decks / Deck", callback_data: "settings:decks" }],
      [{ text: "⏰ Times / Giờ", callback_data: "settings:times" }],
      [{ text: "🌐 Language / Ngôn ngữ", callback_data: "settings:language" }],
      [{ text: "🏠 Main menu / Menu", callback_data: "menu:main" }],
    ],
  };
}

function studyKeyboard(env: Env) {
  return { inline_keyboard: [[{ text: "📖 Học ngay / Study now", web_app: { url: env.MINIAPP_URL } }]] };
}

function toggleDeck(selected: string[], deck: string): string[] {
  const values = selected.filter((value) => value !== ALL_DECKS);
  if (values.includes(deck)) values.splice(values.indexOf(deck), 1);
  else values.push(deck);
  return values.length ? values.sort() : [ALL_DECKS];
}

function toggleTime(selected: string[], value: string): string[] {
  const values = selected.includes(value) ? selected.filter((item) => item !== value) : [...selected, value];
  return values.sort();
}

function validateSettings(settings: Settings) {
  if (!settings.selectedDecks.length) throw new Error("At least one deck selection is required");
  if (settings.selectedDecks.includes(ALL_DECKS) && settings.selectedDecks.length > 1) throw new Error("Invalid deck selection");
  if (settings.reminderTimes.length > 5 || settings.reminderTimes.some((value) => !isClockTime(value))) throw new Error("Invalid reminder times");
  if (!["vi-en", "en-vi"].includes(settings.language)) throw new Error("Invalid language");
}

function isClockTime(value: string): boolean {
  const match = /^(?:[01]\d|2[0-3]):[0-5]\d$/.test(value);
  return match;
}

function getChatId(update: TelegramUpdate): string | null {
  return String(update.message?.chat.id ?? update.callback_query?.message?.chat.id ?? "");
}

function parseJson<T>(value: string, fallback: T): T {
  try {
    return JSON.parse(value) as T;
  } catch {
    return fallback;
  }
}

async function sendMessage(env: Env, chatId: string, text: string, replyMarkup?: object) {
  await telegramCall(env, "sendMessage", { chat_id: chatId, text, disable_web_page_preview: true, ...(replyMarkup ? { reply_markup: replyMarkup } : {}) });
}

async function editMessage(env: Env, chatId: string, messageId: number | undefined, text: string, replyMarkup?: object) {
  if (!messageId) return sendMessage(env, chatId, text, replyMarkup);
  await telegramCall(env, "editMessageText", { chat_id: chatId, message_id: messageId, text, ...(replyMarkup ? { reply_markup: replyMarkup } : {}) });
}

async function answerCallback(env: Env, callbackId: string) {
  await telegramCall(env, "answerCallbackQuery", { callback_query_id: callbackId });
}

async function telegramCall(env: Env, method: string, payload: object) {
  const response = await fetch(`https://api.telegram.org/bot${env.TELEGRAM_BOT_TOKEN}/${method}`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(payload),
  });
  const data = (await response.json()) as { ok: boolean; description?: string };
  if (!response.ok || !data.ok) throw new Error(data.description ?? `Telegram ${method} failed`);
}

function json(value: unknown, status = 200): Response {
  return new Response(JSON.stringify(value), { status, headers: { "content-type": "application/json; charset=utf-8" } });
}
