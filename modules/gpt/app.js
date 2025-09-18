// modules/gpt/app.js
(() => {
  "use strict";

  // --- Telegram WebApp setup ---
  const tg = window.Telegram ? window.Telegram.WebApp : null;
  if (tg) {
    tg.ready();
    tg.expand();
    tg.disableVerticalSwipes?.();
    tg.setHeaderColor?.("#0e1117");
    tg.setBackgroundColor?.("#0e1117");
  }

  // --- Theme & config ---
  const cfg = window.__GPT_APP_CONFIG || {};
  const origin = window.location.origin;
  const API_URL = (cfg.apiUrl || "").trim() || new URL("/api/gpt", origin).toString();
  const MODEL = (cfg.model || "gpt-4o-mini").trim() || "gpt-4o-mini";
  const SYSTEM_PROMPT =
    (cfg.systemPrompt || "You are Vexa GPT-5, a friendly and professional AI assistant that answers clearly and concisely.");

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

  // --- State ---
  const messages = []; // {id, role:'system'|'user'|'assistant', content, loading?, secondary?}
  const nodeMap = new Map(); // id -> DOM node

  // --- UI helpers ---
  function appendMessage(m) {
    const id = m.id || (crypto?.randomUUID?.() || String(Date.now()));
    const rec = { ...m, id };
    messages.push(rec);
    renderMessage(rec);
    return id;
  }

  function updateMessage(id, patch) {
    const idx = messages.findIndex((m) => m.id === id);
    if (idx === -1) return;
    messages[idx] = { ...messages[idx], ...patch };
    renderMessage(messages[idx]);
  }

  function renderMessage(m) {
    let node = nodeMap.get(m.id);
    if (!node) {
      node = document.createElement("div");
      node.className = "message";
      node.innerHTML = `
        <div class="avatar"></div>
        <div class="bubble"></div>
      `;
      nodeMap.set(m.id, node);
      els.chat?.appendChild(node);
    }

    node.className = `message ${m.role}${m.loading ? " loading" : ""}`;
    const avatar = node.querySelector(".avatar");
    const bubble = node.querySelector(".bubble");
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
    p.textContent = m.content || "";
    bubble.appendChild(p);

    if (m.secondary) {
      const s = document.createElement("p");
      s.className = "secondary";
      s.textContent = m.secondary;
      bubble.appendChild(s);
    }

    requestAnimationFrame(scrollToBottom);
  }

  function setLoading(on) {
    if (els.sendBtn) els.sendBtn.disabled = on;
    if (els.textarea) els.textarea.disabled = on;
  }

  function autoResize() {
    if (!els.textarea) return;
    els.textarea.style.height = "auto";
    els.textarea.style.height = `${Math.min(els.textarea.scrollHeight, 180)}px`;
  }
  els.textarea?.addEventListener("input", autoResize);

  function scrollToBottom() {
    try {
      window.scrollTo({ top: document.body.scrollHeight });
    } catch {}
  }

  // --- API call ---
  async function callAssistant(history) {
    if (!API_URL) {
      await new Promise((r) => setTimeout(r, 500));
      return {
        role: "assistant",
        content: "به‌زودی به سرور GPT متصل می‌شوم (demo).",
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

    let data = null;
    try { data = await res.json(); } catch (_) {}

    // سرور ما در خطا هم 200 می‌دهد ولی ok=false
    if (!res.ok || (data && data.ok === false)) {
      const msg = (data && data.error) ? String(data.error) : `Request failed ${res.status}`;
      throw new Error(msg);
    }

    const content =
      data?.data?.choices?.[0]?.message?.content ||
      data?.choices?.[0]?.message?.content ||
      data?.content || "";

    return { role: "assistant", content: content || "پاسخی دریافت نشد، دوباره تلاش کن." };
  }

  // --- Submit handler ---
  async function handleSubmit(e) {
    e.preventDefault();
    const txt = (els.textarea?.value || "").trim();
    if (!txt) return;

    const userId = appendMessage({ role: "user", content: txt });
    els.textarea.value = "";
    autoResize();
    setLoading(true);

    const loadingId = appendMessage({ role: "assistant", content: "", loading: true });

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
        content: "متأسفم! اتصال برقرار نشد.",
        secondary: String(err?.message || err || ""),
      });
    } finally {
      setLoading(false);
      scrollToBottom();
    }
  }

  // --- Events ---
  els.form?.addEventListener("submit", handleSubmit);
  els.textarea?.addEventListener("keydown", (ev) => {
    if (ev.key === "Enter" && !ev.shiftKey) {
      ev.preventDefault();
      els.form?.requestSubmit();
    }
  });
})();
