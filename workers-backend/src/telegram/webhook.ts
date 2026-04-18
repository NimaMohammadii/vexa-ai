import type { UserRepository } from "../storage/contracts";

interface TelegramUpdate {
  message?: {
    text?: string;
    from?: { id: number; username?: string; first_name?: string };
    chat?: { id: number };
  };
}

export async function handleTelegramWebhook(update: TelegramUpdate, deps: { botToken: string; users: UserRepository }) {
  const message = update.message;
  if (!message?.from || !message.chat) return { ok: true };

  const user = await deps.users.upsertTelegramUser({
    userId: message.from.id,
    username: message.from.username,
    firstName: message.from.first_name,
  });

  const text = (message.text ?? "").trim();
  if (text === "/start") {
    await sendTelegramMessage(deps.botToken, message.chat.id, `👋 Welcome ${user.firstName ?? ""}`.trim());
  }

  return { ok: true };
}

async function sendTelegramMessage(botToken: string, chatId: number, text: string) {
  await fetch(`https://api.telegram.org/bot${botToken}/sendMessage`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ chat_id: chatId, text }),
  });
}
