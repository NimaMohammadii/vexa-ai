import {
  TelegramBotFlowService as LegacyTelegramBotFlowService,
  type TelegramWebhookUpdate,
} from "./telegram-legacy-menu-bot-service";

type TelegramBotFlowDeps = ConstructorParameters<typeof LegacyTelegramBotFlowService>[0];

export class TelegramBotFlowService extends LegacyTelegramBotFlowService {
  private readonly botToken: string;

  constructor(deps: TelegramBotFlowDeps) {
    super(deps);
    this.botToken = deps.botToken;
  }

  override async handleWebhook(update: TelegramWebhookUpdate): Promise<{ handled: string }> {
    const message = update.message;
    const text = (message?.text ?? "").trim();

    if (message?.chat?.id && /^\/start(?:\s|$)/.test(text)) {
      await fetch(`https://api.telegram.org/bot${this.botToken}/sendMessage`, {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({
          chat_id: message.chat.id,
          text: "سلام همینجا بفرست",
        }),
      });

      return { handled: "start_greeting" };
    }

    return super.handleWebhook(update);
  }
}

export type { TelegramWebhookUpdate };
