export interface BotConversationState {
  mode: "idle" | "awaiting_prompt";
  updatedAt: number;
}

const DEFAULT_STATE: BotConversationState = {
  mode: "idle",
  updatedAt: 0,
};

export class UserStateRepository {
  constructor(private namespace: DurableObjectNamespace) {}

  private objectStub(userId: number): DurableObjectStub {
    const id = this.namespace.idFromName(`telegram-user-${userId}`);
    return this.namespace.get(id);
  }

  async getBotState(userId: number): Promise<BotConversationState> {
    const response = await this.objectStub(userId).fetch("https://do/state");
    if (!response.ok) return DEFAULT_STATE;

    const payload = (await response.json()) as { state?: string };
    if (!payload.state) return DEFAULT_STATE;

    try {
      const parsed = JSON.parse(payload.state) as Partial<BotConversationState>;
      return {
        mode: parsed.mode === "awaiting_prompt" ? "awaiting_prompt" : "idle",
        updatedAt: Number(parsed.updatedAt ?? 0),
      };
    } catch {
      return DEFAULT_STATE;
    }
  }

  async setBotState(userId: number, state: BotConversationState): Promise<void> {
    await this.objectStub(userId).fetch("https://do/state", {
      method: "PUT",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ state: JSON.stringify(state) }),
    });
  }
}
