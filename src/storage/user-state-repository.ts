export interface BotConversationState {
  mode:
    | "idle"
    | "awaiting_prompt"
    | "gpt:chat"
    | "tts:wait_text"
    | "image:wait_prompt"
    | "video:wait_image"
    | "clone:wait_audio"
    | "clone:wait_name";
  updatedAt: number;
  ttsVoice?: string;
  ttsOutput?: "mp3" | "voice";
  cloneFileId?: string;
  cloneFileKind?: "voice" | "audio" | "document";
  referralPromptedAt?: number;
  dailyRewardClaimedAt?: number;
  lowCreditPromptedAt?: number;
  lowCreditScheduledAt?: number;
  onboardingPending?: boolean;
  welcomeSentAt?: number;
  welcomeAudioSentAt?: number;
  dailyBonusPromptedAt?: number;
  dailyBonusUnlockedAt?: number;
  pendingReferralCode?: string;
  langSelected?: boolean;
  ttsPage?: number;
  waitingReceipt?: boolean;
  selectedPlanIndex?: number;
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
        mode:
          parsed.mode === "awaiting_prompt" ||
          parsed.mode === "gpt:chat" ||
          parsed.mode === "tts:wait_text" ||
          parsed.mode === "image:wait_prompt" ||
          parsed.mode === "video:wait_image" ||
          parsed.mode === "clone:wait_audio" ||
          parsed.mode === "clone:wait_name"
            ? parsed.mode
            : "idle",
        updatedAt: Number(parsed.updatedAt ?? 0),
        ttsVoice: typeof parsed.ttsVoice === "string" ? parsed.ttsVoice : undefined,
        ttsOutput: parsed.ttsOutput === "voice" ? "voice" : parsed.ttsOutput === "mp3" ? "mp3" : undefined,
        cloneFileId: typeof parsed.cloneFileId === "string" ? parsed.cloneFileId : undefined,
        cloneFileKind:
          parsed.cloneFileKind === "voice" || parsed.cloneFileKind === "audio" || parsed.cloneFileKind === "document"
            ? parsed.cloneFileKind
            : undefined,
        referralPromptedAt: Number(parsed.referralPromptedAt ?? 0) || undefined,
        dailyRewardClaimedAt: Number(parsed.dailyRewardClaimedAt ?? 0) || undefined,
        lowCreditPromptedAt: Number(parsed.lowCreditPromptedAt ?? 0) || undefined,
        lowCreditScheduledAt: Number(parsed.lowCreditScheduledAt ?? 0) || undefined,
        onboardingPending: parsed.onboardingPending === undefined ? undefined : !!parsed.onboardingPending,
        welcomeSentAt: Number(parsed.welcomeSentAt ?? 0) || undefined,
        welcomeAudioSentAt: Number(parsed.welcomeAudioSentAt ?? 0) || undefined,
        dailyBonusPromptedAt: Number(parsed.dailyBonusPromptedAt ?? 0) || undefined,
        dailyBonusUnlockedAt: Number(parsed.dailyBonusUnlockedAt ?? 0) || undefined,
        pendingReferralCode: typeof parsed.pendingReferralCode === "string" ? parsed.pendingReferralCode : undefined,
        langSelected: parsed.langSelected === undefined ? undefined : !!parsed.langSelected,
        ttsPage: Number(parsed.ttsPage ?? 0) || undefined,
        waitingReceipt: parsed.waitingReceipt === undefined ? undefined : !!parsed.waitingReceipt,
        selectedPlanIndex: Number(parsed.selectedPlanIndex ?? -1) >= 0 ? Number(parsed.selectedPlanIndex) : undefined,
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
