export interface BotConversationState {
  mode:
    | "idle"
    | "awaiting_prompt"
    | "gpt:chat"
    | "tts:wait_text"
    | "image:wait_prompt"
    | "video:wait_image"
    | "clone:wait_audio"
    | "clone:wait_name"
    | "admin:lookup_user"
    | "admin:add_user"
    | "admin:add_amount"
    | "admin:sub_user"
    | "admin:sub_amount"
    | "admin:reset_user"
    | "admin:dm_user"
    | "admin:dm_content"
    | "admin:cast_content"
    | "admin:formula"
    | "admin:set_setting";
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
  ttsDemoLocks?: Record<string, { messageId: number; expiresAt: number }>;
  adminTargetUserId?: number;
  adminCastLang?: string;
  adminSettingKey?: string;
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
          parsed.mode === "clone:wait_name" ||
          parsed.mode === "admin:lookup_user" ||
          parsed.mode === "admin:add_user" ||
          parsed.mode === "admin:add_amount" ||
          parsed.mode === "admin:sub_user" ||
          parsed.mode === "admin:sub_amount" ||
          parsed.mode === "admin:reset_user" ||
          parsed.mode === "admin:dm_user" ||
          parsed.mode === "admin:dm_content" ||
          parsed.mode === "admin:cast_content" ||
          parsed.mode === "admin:formula" ||
          parsed.mode === "admin:set_setting"
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
        ttsDemoLocks:
          parsed.ttsDemoLocks && typeof parsed.ttsDemoLocks === "object"
            ? Object.fromEntries(
                Object.entries(parsed.ttsDemoLocks)
                  .map(([key, value]) => {
                    if (!value || typeof value !== "object") return null;
                    const messageId = Number((value as { messageId?: number }).messageId ?? 0);
                    const expiresAt = Number((value as { expiresAt?: number }).expiresAt ?? 0);
                    if (messageId <= 0 || expiresAt <= 0) return null;
                    return [key, { messageId, expiresAt }] as const;
                  })
                  .filter((entry): entry is [string, { messageId: number; expiresAt: number }] => !!entry)
              )
            : undefined,
        adminTargetUserId: Number(parsed.adminTargetUserId ?? 0) > 0 ? Number(parsed.adminTargetUserId) : undefined,
        adminCastLang: typeof parsed.adminCastLang === "string" ? parsed.adminCastLang : undefined,
        adminSettingKey: typeof parsed.adminSettingKey === "string" ? parsed.adminSettingKey : undefined,
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
