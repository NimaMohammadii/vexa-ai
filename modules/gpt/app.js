(function () {
  const tg = window.Telegram ? window.Telegram.WebApp : null;
  if (tg) {
    tg.ready();
    tg.expand();
    if (typeof tg.disableVerticalSwipes === "function") {
      tg.disableVerticalSwipes();
    }
    if (typeof tg.setHeaderColor === "function") {
      tg.setHeaderColor("#0e1117");
    }
    if (typeof tg.setBackgroundColor === "function") {
      tg.setBackgroundColor("#0e1117");
    }
  }

  const userLang = tg?.initDataUnsafe?.user?.language_code || navigator.language || "en";
  const rtlLanguages = new Set(["fa", "ar", "he", "ur"]);
  const normalizedLang = (userLang || "en").slice(0, 2).toLowerCase();
  document.documentElement.lang = normalizedLang;
  document.documentElement.dir = rtlLanguages.has(normalizedLang) ? "rtl" : "ltr";

  const prefersLight = window.matchMedia("(prefers-color-scheme: light)").matches;
  const initialTheme = prefersLight ? "light" : "dark";
  const body = document.body;
  if (initialTheme === "light") {
    body.classList.add("light");
  }

  const config = window.__GPT_APP_CONFIG || {};
  const API_URL = (config.apiUrl || "").trim();
  const model = config.model || "gpt-4o-mini";
  const systemPrompt =
    config.systemPrompt ||
    "You are Vexa GPT-5, a friendly and professional AI assistant that answers clearly and concisely.";

  const brandTitleEl = document.querySelector(".brand__title");
  if (config.title && brandTitleEl) {
    brandTitleEl.textContent = config.title;
  }

  const chatEl = document.getElementById("chat");
  const form = document.getElementById("composer");
  const textarea = document.getElementById("prompt-input");
  const sendBtn = document.getElementById("send-btn");
  const suggestionEls = Array.from(document.querySelectorAll(".suggestion"));
  const themeToggle = document.getElementById("theme-toggle");
  if (themeToggle && body.classList.contains("light")) {
    const iconEl = themeToggle.querySelector(".icon");
    if (iconEl) {
      iconEl.textContent = "☀️";
    }
  }

  const messages = [];
  const messageElements = new Map();

  function scrollToBottom() {
    requestAnimationFrame(() => {
      chatEl.scrollTo({ top: chatEl.scrollHeight, behavior: "smooth" });
    });
  }

  function createMessageElement(message) {
    const wrapper = document.createElement("div");
    wrapper.className = `message ${message.role}${message.loading ? " loading" : ""}`;

    const avatar = document.createElement("div");
    avatar.className = "avatar";
    avatar.textContent = message.role === "user" ? "🙂" : "🤖";

    const bubble = document.createElement("div");
    bubble.className = "bubble";

    const primary = document.createElement("p");
    primary.className = "primary";
    primary.textContent = message.content;
    bubble.appendChild(primary);

    if (message.secondary) {
      const secondary = document.createElement("p");
      secondary.className = "secondary";
      secondary.textContent = message.secondary;
      bubble.appendChild(secondary);
    }

    if (message.loading) {
      bubble.innerHTML = "<span>در حال فکر کردن</span><span class=\"dots\"><span></span><span></span><span></span></span>";
    }

    wrapper.appendChild(avatar);
    wrapper.appendChild(bubble);
    return wrapper;
  }

  function renderMessage(message) {
    const el = createMessageElement(message);
    chatEl.appendChild(el);
    messageElements.set(message.id, el);
    scrollToBottom();
  }

  function updateMessage(id, updates) {
    const message = messages.find((m) => m.id === id);
    if (!message) return;
    Object.assign(message, updates);
    const el = messageElements.get(id);
    if (!el) return;
    const bubble = el.querySelector(".bubble");
    const avatar = el.querySelector(".avatar");
    el.className = `message ${message.role}${message.loading ? " loading" : ""}`;
    if (avatar) {
      avatar.textContent = message.role === "user" ? "🙂" : "🤖";
    }
    if (message.loading) {
      bubble.innerHTML = "<span>در حال فکر کردن</span><span class=\"dots\"><span></span><span></span><span></span></span>";
    } else {
      bubble.innerHTML = "";
      const primary = document.createElement("p");
      primary.className = "primary";
      primary.textContent = message.content;
      bubble.appendChild(primary);
      if (message.secondary) {
        const secondary = document.createElement("p");
        secondary.className = "secondary";
        secondary.textContent = message.secondary;
        bubble.appendChild(secondary);
      }
    }
  }

  function appendMessage(message) {
    const record = { ...message, id: message.id || (crypto.randomUUID ? crypto.randomUUID() : Date.now().toString()) };
    messages.push(record);
    renderMessage(record);
    return record.id;
  }

  function setLoadingState(isLoading) {
    sendBtn.disabled = isLoading;
    textarea.disabled = isLoading;
  }

  function autoResizeTextarea() {
    textarea.style.height = "auto";
    textarea.style.height = `${Math.min(textarea.scrollHeight, 180)}px`;
  }

  textarea.addEventListener("input", autoResizeTextarea);
  autoResizeTextarea();

  suggestionEls.forEach((btn) => {
    btn.addEventListener("click", () => {
      const prompt = btn.dataset.prompt || "";
      textarea.value = prompt;
      autoResizeTextarea();
      textarea.focus();
      if (tg?.HapticFeedback) {
        tg.HapticFeedback.impactOccurred("light");
      }
    });
  });

  if (themeToggle) {
    themeToggle.addEventListener("click", () => {
      const isLight = body.classList.toggle("light");
      if (tg?.HapticFeedback) {
        tg.HapticFeedback.impactOccurred("medium");
      }
      themeToggle.querySelector(".icon").textContent = isLight ? "☀️" : "🌙";
    });
  }

  async function callAssistant(history) {
    if (!API_URL) {
      await new Promise((resolve) => setTimeout(resolve, 900));
      return {
        role: "assistant",
        content: "به زودی به سرور GPT متصل می‌شوم. فعلاً این یک پیش‌نمایش از رابط کاربری است.",
      };
    }

    const payload = {
      model,
      messages: [
        { role: "system", content: systemPrompt },
        ...history.map(({ role, content }) => ({ role, content })),
      ],
    };

    const response = await fetch(API_URL, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(payload),
    });

    if (!response.ok) {
      throw new Error(`Request failed with status ${response.status}`);
    }

    const data = await response.json();
    const assistantMessage = data?.choices?.[0]?.message?.content || data?.content || "";
    return {
      role: "assistant",
      content: assistantMessage || "پاسخی دریافت نشد، لطفاً دوباره تلاش کن.",
    };
  }

  async function handleSubmit(event) {
    event.preventDefault();
    const raw = textarea.value.trim();
    if (!raw) return;

    const userMessage = { id: crypto.randomUUID?.() || Date.now().toString(), role: "user", content: raw };
    appendMessage(userMessage);
    textarea.value = "";
    autoResizeTextarea();
    setLoadingState(true);

    const loadingId = appendMessage({ role: "assistant", content: "", loading: true });

    try {
      const history = messages
        .filter((m) => !m.loading && m.role !== "system")
        .map(({ role, content }) => ({ role, content }));
      const assistant = await callAssistant(history);
      updateMessage(loadingId, { ...assistant, loading: false });
    } catch (error) {
      console.error(error);
      updateMessage(loadingId, {
        role: "assistant",
        loading: false,
        content: "متاسفم! اتصال برقرار نشد. تنظیمات سرور GPT را بررسی کن.",
      });
    } finally {
      setLoadingState(false);
      scrollToBottom();
    }
  }

  form.addEventListener("submit", handleSubmit);

  textarea.addEventListener("keydown", (event) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      form.requestSubmit();
    }
  });
})();
