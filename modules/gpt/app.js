// modules/gpt/app.js
(() => {
  "use strict";

  // --- Telegram WebApp setup ---
  const telegram = window.Telegram ? window.Telegram.WebApp : null;

  function configureTelegramUI() {
    if (!telegram) return;
    telegram.ready();
    telegram.expand();
    telegram.disableVerticalSwipes?.();
    telegram.setHeaderColor?.("#0e1117");
    telegram.setBackgroundColor?.("#0e1117");
  }

  function deriveLanguage() {
    const langCode =
      telegram?.initDataUnsafe?.user?.language_code ||
      navigator.language ||
      "en";
    const normalized = langCode.slice(0, 2).toLowerCase();
    const rtl = new Set(["fa", "ar", "he", "ur"]);
    document.documentElement.lang = normalized;
    document.documentElement.dir = rtl.has(normalized) ? "rtl" : "ltr";
  }

  function initTheme() {
    const prefersLight = window.matchMedia("(prefers-color-scheme: light)").matches;
    if (prefersLight) document.body.classList.add("light");
  }

  configureTelegramUI();
  deriveLanguage();
  initTheme();

  // --- Config & constants ---
  const cfg = window.__GPT_APP_CONFIG || {};
  const origin =
    (window.location.origin && window.location.origin !== "null")
      ? window.location.origin
      : window.location.href;

  // اگر apiUrl در تنظیمات ست نشده بود، به /api/gpt روی همین دامنه می‌افتد
  const API_URL = (cfg.apiUrl || "").trim() || new URL("/api/gpt", origin).toString();
  const MODEL = cfg.model || "gpt-4o-mini";
  const SYSTEM_PROMPT =
    cfg.systemPrompt ||
    "You are Vexa GPT-5, a friendly and professional AI assistant that answers clearly and concisely.";

  // --- DOM refs ---
  const els = {
    chat: document.getElementById("chat"),
    form: document.getElementById("composer"),
    textarea: document.getElementById("prompt-input"),
    sendBtn: document.getElementById("send-btn"),
    suggestions: Array.from(document.querySelectorAll(".suggestion")),
    themeToggle: document.getElementById("theme-toggle"),
    title: document.querySelector(".brand__title"),
  };

  if (cfg.title && els.title) els.title.textContent = cfg.title;
  if (els.themeToggle && document.body.classList.contains("light")) {
    els.themeToggle.querySelector(".icon")?.append("☀️");
  }

  // --- Chat state ---
  const messages = [];
  const nodeMap = new Map();

  function scrollToBottom() {
    requestAnimationFrame(() => {
      els.chat?.scrollTo({ top: els.chat.scrollHeight, behavior: "smooth" });
    });
  }

  function createMessageNode(m) {
    const wrap = document.createElement("div");
    wrap.className = `message ${m.role}${m.loading ? " loading" : ""}`;

    const avatar = document.createElement("div");
    avatar.className = "avatar";
    avatar.textContent = m.role === "user" ? "🙂" : "🤖";

    const bubble = document.createElement("div");
    bubble.className = "bubble";

    if (m.loading) {
      bubble.innerHTML =
        '<span>در حال فکر کردن</span><span class="dots"><span></span><span></span><span></span></span>';
    } else {
      const p = document.createElement("p");
      p.className = "primary";
      p.textContent = m.content;
      bubble.appendChild(p);

      if (m.secondary) {
        const s = document.createElement("p");
        s.className = "secondary";
        s.textContent = m.secondary;
        bubble.appendChild(s);
      }
    }

    wrap.appendChild(avatar);
    wrap.appendChild(bubble);
    return wrap;
  }

  function renderMessage(m) {
    const node = createMessageNode(m);
    els.chat.appendChild(node);
    nodeMap.set(m.id, node);
    scrollToBottom();
  }

  function updateMessage(id, patch) {
    const idx = messages.findIndex((x) => x.id === id);
    if (idx === -1) return;
    Object.assign(messages[idx], patch);

    const node = nodeMap.get(id);
    if (!node) return;

    const bubble = node.querySelector(".bubble");
    const avatar = node.querySelector(".avatar");
    const m = messages[idx];

    node.className = `message ${m.role}${m.loading ? " loading" : ""}`;
    if (avatar) avatar.textContent = m.role === "user" ? "🙂" : "🤖";
    if (!bubble) return;

    if (m.loading) {
      bubble.innerHTML =
        '<span>در حال فکر کردن</span><span class="dots"><span></span><span></span><span></span></span>';
      return;
    }

    bubble.innerHTML = "";
    const p = document.createElement("p");
    p.className = "primary";
    p.textContent = m.content;
    bubble.appendChild(p);

    if (m.secondary) {
      const s = document.createElement("p");
      s.className = "secondary";
      s.textContent = m.secondary;
      bubble.appendChild(s);
    }
  }

  function appendMessage(m) {
    const id =
      m.id || (window.crypto?.randomUUID?.() || String(Date.now()));
    const record = { ...m, id };
    messages.push(record);
    renderMessage(record);
    return id;
  }

  function setLoading(on) {
    if (!els.sendBtn || !els.textarea) return;
    els.sendBtn.disabled = on;
    els.textarea.disabled = on;
  }

  function autoResize() {
    if (!els.textarea) return;
    els.textarea.style.height = "auto";
    els.textarea.style.height = `${Math.min(els.textarea.scrollHeight, 180)}px`;
  }

  els.textarea?.addEventListener("input", autoResize);
  autoResize();

  els.suggestions.forEach((btn) => {
    btn.addEventListener("click", () => {
      const prompt = btn.dataset.prompt || "";
      if (!els.textarea) return;
      els.textarea.value = prompt;
      autoResize();
      els.textarea.focus();
      telegram?.HapticFeedback?.impactOccurred("light");
    });
  });

  els.themeToggle?.addEventListener("click", () => {
    const isLight = document.body.classList.toggle("light");
    telegram?.HapticFeedback?.impactOccurred("medium");
    const icon = els.themeToggle.querySelector(".icon");
    if (icon) icon.textContent = isLight ? "☀️" : "🌙";
  });

  async function callAssistant(history) {
    // اگر هنوز API آماده نیست، پیام نمایشی بده
    if (!API_URL) {
      await new Promise((r) => setTimeout(r, 800));
      return {
        role: "assistant",
        content:
          "به زودی به سرور GPT متصل می‌شوم. فعلاً این یک پیش‌نمایش از رابط کاربری است.",
      };
    }

    const payload = {
      model: MODEL,
      messages: [
        { role: "system", content: SYSTEM_PROMPT },
        ...history.map(({ role, content }) => ({ role, content })),
      ],
    };

    const res = await fetch(API_URL, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    if (!res.ok) throw new Error(`Request failed ${res.status}`);
    const data = await res.json();

    const content =
      data?.choices?.[0]?.message?.content || data?.content || "";
    return {
      role: "assistant",
      content: content || "پاسخی دریافت نشد، لطفاً دوباره تلاش کن.",
    };
  }

  async function handleSubmit(e) {
    e.preventDefault();
    const txt = (els.textarea?.value || "").trim();
    if (!txt) return;

    const userMsg = {
      id: window.crypto?.randomUUID?.() || String(Date.now()),
      role: "user",
      content: txt,
    };
    appendMessage(userMsg);

    els.textarea.value = "";
    autoResize();
    setLoading(true);

    const loadingId = appendMessage({
      role: "assistant",
      content: "",
      loading: true,
    });

    try {
      const history = messages
        .filter((m) => !m.loading && m.role !== "system")
        .map(({ role, content }) => ({ role, content }));
      const assistant = await callAssistant(history);
      updateMessage(loadingId, { ...assistant, loading: false });
    } catch (err) {
      console.error(err);
      updateMessage(loadingId, {
        role: "assistant",
        loading: false,
        content: "متأسفم! اتصال برقرار نشد. تنظیمات سرور GPT را بررسی کن.",
      });
    } finally {
      setLoading(false);
      scrollToBottom();
    }
  }

  els.form?.addEventListener("submit", handleSubmit);

  els.textarea?.addEventListener("keydown", (ev) => {
    if (ev.key === "Enter" && !ev.shiftKey) {
      ev.preventDefault();
      els.form?.requestSubmit();
    }
  });
})();
