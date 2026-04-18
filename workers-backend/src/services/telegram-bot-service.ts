import type { BotConversationState, UserStateRepository } from "../storage/user-state-repository";
import type { ApiTokenService, CreditService, GptHistoryService, UserService } from "./user-services";

interface TelegramUser {
  id: number;
  username?: string;
  first_name?: string;
}

export interface TelegramWebhookUpdate {
  message?: {
    text?: string;
    from?: TelegramUser;
    chat?: { id: number };
  };
  callback_query?: {
    id: string;
    data?: string;
    from?: TelegramUser;
    message?: { chat?: { id: number } };
  };
}

interface TelegramBotFlowDeps {
  botToken: string;
  users: UserService;
  credits: CreditService;
  tokens: ApiTokenService;
  history: GptHistoryService;
  userState: UserStateRepository;
}

const nowTs = () => Math.floor(Date.now() / 1000);

export class TelegramBotFlowService {
  constructor(private deps: TelegramBotFlowDeps) {}

  async handleWebhook(update: TelegramWebhookUpdate): Promise<{ handled: string }> {
    if (update.callback_query?.id) {
      await this.answerCallback(update.callback_query.id, "Action received ✅");
      return { handled: "callback_query" };
    }

    const msg = update.message;
    if (!msg?.chat?.id || !msg.from?.id) return { handled: "ignored" };

    const user = await this.deps.users.bootstrapTelegramUser({
      userId: msg.from.id,
      username: msg.from.username,
      firstName: msg.from.first_name,
    });

    const state = await this.deps.userState.getBotState(user.userId);
    const text = (msg.text ?? "").trim();

    if (text.startsWith("/")) {
      return this.handleCommand(user.userId, msg.chat.id, text);
    }

    if (state.mode === "awaiting_prompt" && text) {
      await this.deps.history.append(user.userId, "user", text);
      await this.deps.history.append(user.userId, "assistant", `Received your prompt: ${text.slice(0, 400)}`);
      await this.deps.credits.consume(user.userId, 1, "bot_prompt", "telegram_bot");

      await this.deps.userState.setBotState(user.userId, { mode: "idle", updatedAt: nowTs() });
      await this.sendMessage(msg.chat.id, "✅ Prompt stored in GPT history and 1 credit consumed.");
      return { handled: "prompt_captured" };
    }

    if (text) {
      await this.sendMessage(
        msg.chat.id,
        "I only process commands right now. Use /ask to submit a prompt, or /start to see all commands."
      );
      return { handled: "text_unmapped" };
    }

    return { handled: "empty_message" };
  }

  private async handleCommand(userId: number, chatId: number, text: string): Promise<{ handled: string }> {
    switch (text) {
      case "/start":
      case "/help":
        await this.sendMessage(
          chatId,
          [
            "👋 Welcome to Vexa.",
            "Commands:",
            "/profile - view your profile",
            "/credits - view credits",
            "/apitoken - get API token",
            "/rotatetoken - rotate API token",
            "/history - list GPT history",
            "/resethistory - clear GPT history",
            "/ask - enter prompt mode",
            "/cancel - cancel prompt mode",
          ].join("\n")
        );
        return { handled: "start" };
      case "/profile": {
        const profile = await this.deps.users.getProfile(userId);
        await this.sendMessage(
          chatId,
          `🧾 Profile\nID: ${profile.userId}\nUsername: @${profile.username ?? "-"}\nName: ${profile.firstName ?? "-"}\nCredits: ${profile.credits}`
        );
        return { handled: "profile" };
      }
      case "/credits": {
        const credits = await this.deps.credits.getCredits(userId);
        await this.sendMessage(chatId, `💳 Credits: ${credits.credits}`);
        return { handled: "credits" };
      }
      case "/apitoken": {
        const token = await this.deps.tokens.getOrCreate(userId);
        await this.sendMessage(chatId, `🔑 API token:\n\`${token}\``, "Markdown");
        return { handled: "api_token" };
      }
      case "/rotatetoken": {
        const token = await this.deps.tokens.rotate(userId);
        await this.sendMessage(chatId, `♻️ New API token:\n\`${token}\``, "Markdown");
        return { handled: "api_token_rotate" };
      }
      case "/history": {
        const messages = await this.deps.history.list(userId, 10);
        if (!messages.length) {
          await this.sendMessage(chatId, "🗂 GPT history is empty.");
          return { handled: "history_empty" };
        }
        const lines = messages.map((item, idx) => `${idx + 1}. [${item.role}] ${item.content.slice(0, 80)}`);
        await this.sendMessage(chatId, `🗂 GPT history\n${lines.join("\n")}`);
        return { handled: "history" };
      }
      case "/resethistory":
        await this.deps.history.clear(userId);
        await this.sendMessage(chatId, "🧹 GPT history reset.");
        return { handled: "history_reset" };
      case "/ask": {
        const state: BotConversationState = { mode: "awaiting_prompt", updatedAt: nowTs() };
        await this.deps.userState.setBotState(userId, state);
        await this.sendMessage(chatId, "Send your next message as the prompt. Use /cancel to exit prompt mode.");
        return { handled: "ask_start" };
      }
      case "/cancel":
        await this.deps.userState.setBotState(userId, { mode: "idle", updatedAt: nowTs() });
        await this.sendMessage(chatId, "Prompt mode canceled.");
        return { handled: "ask_cancel" };
      default:
        await this.sendMessage(chatId, "Unknown command. Use /help.");
        return { handled: "unknown_command" };
    }
  }

  private async sendMessage(chatId: number, text: string, parse_mode?: "Markdown" | "HTML") {
    await fetch(`https://api.telegram.org/bot${this.deps.botToken}/sendMessage`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ chat_id: chatId, text, parse_mode }),
    });
  }

  private async answerCallback(callbackQueryId: string, text: string) {
    await fetch(`https://api.telegram.org/bot${this.deps.botToken}/answerCallbackQuery`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ callback_query_id: callbackQueryId, text, show_alert: false }),
    });
  }
}
