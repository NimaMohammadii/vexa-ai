import type { ApiTokenService, CreditService, GptHistoryService, UserService } from "../services/user-services";

interface TelegramUpdate {
  message?: {
    text?: string;
    from?: { id: number; username?: string; first_name?: string };
    chat?: { id: number };
  };
  callback_query?: {
    id: string;
    data?: string;
    from?: { id: number; username?: string; first_name?: string };
    message?: { chat?: { id: number } };
  };
}

interface TelegramDeps {
  botToken: string;
  users: UserService;
  credits: CreditService;
  tokens: ApiTokenService;
  history: GptHistoryService;
}

export async function handleTelegramWebhook(update: TelegramUpdate, deps: TelegramDeps) {
  if (update.callback_query?.id) {
    await answerCallbackQuery(deps.botToken, update.callback_query.id, "✅ Received. More flows coming soon.");
    return { handled: "callback_query" };
  }

  const message = update.message;
  if (!message?.from || !message.chat) return { handled: "ignored" };

  const user = await deps.users.bootstrapTelegramUser({
    userId: message.from.id,
    username: message.from.username,
    firstName: message.from.first_name,
  });

  const text = (message.text ?? "").trim();
  if (!text) return { handled: "empty_message" };

  if (text === "/start") {
    await sendTelegramMessage(
      deps.botToken,
      message.chat.id,
      [
        `👋 Welcome ${user.firstName ?? ""}`.trim(),
        "Commands:",
        "/profile - view your profile",
        "/credits - view your credit balance",
        "/apitoken - show your API token",
        "/rotatetoken - rotate your API token",
        "/history - show GPT history",
        "/resethistory - clear GPT history",
      ].join("\n")
    );
    return { handled: "/start" };
  }

  if (text === "/profile") {
    await sendTelegramMessage(
      deps.botToken,
      message.chat.id,
      `🧾 Profile\nID: ${user.userId}\nUsername: @${user.username ?? "-"}\nName: ${user.firstName ?? "-"}\nLang: ${user.lang}`
    );
    return { handled: "/profile" };
  }

  if (text === "/credits") {
    const credits = await deps.credits.getCredits(user.userId);
    await sendTelegramMessage(deps.botToken, message.chat.id, `💳 Credits: ${credits.credits}`);
    return { handled: "/credits" };
  }

  if (text === "/apitoken") {
    const token = await deps.tokens.getOrCreate(user.userId);
    await sendTelegramMessage(deps.botToken, message.chat.id, `🔑 API token:\n\`${token}\``, "Markdown");
    return { handled: "/apitoken" };
  }

  if (text === "/rotatetoken") {
    const token = await deps.tokens.rotate(user.userId);
    await sendTelegramMessage(deps.botToken, message.chat.id, `♻️ New API token:\n\`${token}\``, "Markdown");
    return { handled: "/rotatetoken" };
  }

  if (text === "/history") {
    const messages = await deps.history.list(user.userId, 10);
    if (messages.length === 0) {
      await sendTelegramMessage(deps.botToken, message.chat.id, "🗂 GPT history is empty.");
      return { handled: "/history_empty" };
    }

    const lines = messages.slice(-10).map((m, i) => `${i + 1}. [${m.role}] ${m.content.slice(0, 120)}`);
    await sendTelegramMessage(deps.botToken, message.chat.id, `🗂 GPT history\n${lines.join("\n")}`);
    return { handled: "/history" };
  }

  if (text === "/resethistory") {
    await deps.history.clear(user.userId);
    await sendTelegramMessage(deps.botToken, message.chat.id, "🧹 GPT history reset.");
    return { handled: "/resethistory" };
  }

  return { handled: "unmapped_text" };
}

async function sendTelegramMessage(botToken: string, chatId: number, text: string, parseMode?: "Markdown" | "HTML") {
  await fetch(`https://api.telegram.org/bot${botToken}/sendMessage`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ chat_id: chatId, text, parse_mode: parseMode }),
  });
}

async function answerCallbackQuery(botToken: string, callbackQueryId: string, text: string) {
  await fetch(`https://api.telegram.org/bot${botToken}/answerCallbackQuery`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ callback_query_id: callbackQueryId, text, show_alert: false }),
  });
}
