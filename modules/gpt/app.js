// modules/gpt/app.js
(() => {
  "use strict";

  // Telegram WebApp polish (اختیاری، اگر در وب‌ویو تلگرام هستی)
  const tg = window.Telegram?.WebApp;
  if (tg) {
    tg.ready();
    tg.expand();
    tg.disableVerticalSwipes?.();
    tg.setHeaderColor?.("#0b0f14");
    tg.setBackgroundColor?.("#0b0f14");
  }

  // --- Config ---
  const cfg = window.__GPT_APP_CONFIG || {};
  const origin = window.location.origin;
  const API_URL = (cfg.apiUrl || "").trim() || new URL("/api/gpt", origin).toString();
  const MODEL = (cfg.model || "gpt-4o-mini").trim() || "gpt-4o-mini";
  const SYSTEM_PROMPT =
    (cfg.systemPrompt ||
      "You are Vexa GPT-5, a friendly and professional AI assistant that answers clearly and concisely.");

  // --- DOM refs ---
  const els = {
    chat: document.getElementById("chat"),
    form: document.getElementById("composer"),
    textarea: document.getElementById("prompt-input"),
    sendBtn: document.getElementById("send-btn"),
    suggestions: Array.from(document.querySelectorAll(".suggestion")),
    newChat: document.getElementById("new-chat"),
  };

  // Online/Offline indicator (اختیاری: می‌تونی اضافه‌اش کنی به هدر)
  window.addEventListener("online", () => console.log("online"));
  window.addEventListener("offline", () => console.log("offline"));

  // --- State ---
  const messages = [];   // {id, role:'user'|'ai', content, loading?, secondary?, ts}
  const nodeMap = new Map();

  // Helpers
  const rAF = (fn) => requestAnimationFrame(fn);
  const scrollToBottom = () => {
    try {
      window.scrollTo({ top: document.body.scrollHeight, behavior: "smooth" });
    } catch {}
  };
  const now = () => new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  const newId = () => (crypto?.randomUUID?.() || `${Date.now()}_${Math.random().toString(36).slice(2)}`);
  const isRTL = (t = "") => /[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF]/.test(t);

  function setLoading(on) {
    if (els.sendBtn) els.sendBtn.disabled = on;
    if (els.textarea) els.textarea.disabled = on;
  }

  // Auto-resize textarea
  function autoResize() {
    if (!els.textarea) return;
    els.textarea.style.height = "auto";
    els.textarea.style.height = `${Math.min(els.textarea.scrollHeight, 180)}px`;
  }
  els.textarea?.addEventListener("input", autoResize);

  // Append & render
  function appendMessage(m) {
    const id = m.id || newId();
    const record = { ...m, id, ts: m.ts || Date.now() };
    messages.push(record);
    renderMessage(record);
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
    const user = m.role === "user";
    if (!node) {
      node = document.createElement("div");
      node.className = `message ${user ? "user" : "ai"} animate-in`;
      node.innerHTML = `
        <div class="avatar">${user ? "🙂" : "🤖"}</div>
        <div class="bubble ${user ? "user" : "ai"}">
          <p class="primary"></p>
          <div class="meta">
            <time></time>
            <div class="actions-row">
              <button class="act" data-act="copy">کپی</button>
              <button class="act" data-act="like">👍</button>
              <button class="act" data-act="dislike">👎</button>
              <button class="act" data-act="regen">⟲</button>
              <button class="act" data-act="share">↗︎</button>
            </div>
          </div>
        </div>
      `;
      nodeMap.set(m.id, node);
      els.chat?.appendChild(node);

      // actions
      node.querySelector('[data-act="copy"]')?.addEventListener("click", () => copyText(m.content));
      node.querySelector('[data-act="like"]')?.addEventListener("click", () => toast("👍"));
      node.querySelector('[data-act="dislike"]')?.addEventListener("click", () => toast("👎"));
      node.querySelector('[data-act="regen"]')?.addEventListener("click", () => regenerateLast());
      node.querySelector('[data-act="share"]')?.addEventListener("click", () => shareText(m.content));
    }

    // content
    const bubble = node.querySelector(".bubble");
    const p = node.querySelector(".primary");
    const time = node.querySelector("time");

    // loading state
    if (m.loading) {
      bubble.classList.add("loading");
      p.innerHTML =
        'در حال فکر کردن<span class="dots"><span></span><span></span><span></span></span>';
    } else {
      bubble.classList.remove("loading");
      p.textContent = m.content || "";
    }

    // dir
    if (p) p.setAttribute("dir", isRTL(m.content) ? "rtl" : "auto");
    if (time) time.textContent = new Date(m.ts).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });

    // secondary line (error text)
    let sec = bubble.querySelector(".secondary");
    if (m.secondary) {
      if (!sec) {
        sec = document.createElement("p");
        sec.className = "secondary";
        bubble.appendChild(sec);
      }
      sec.textContent = m.secondary;
    } else if (sec) {
      sec.remove();
    }

    rAF(scrollToBottom);
  }

  // Suggestions → paste into input
  els.suggestions.forEach((btn) => {
    btn.addEventListener("click", () => {
      if (!els.textarea) return;
      els.textarea.value = btn.textContent.trim();
      autoResize();
      els.textarea.focus();
    });
  });

  // New chat
  els.newChat?.addEventListener("click", () => {
    messages.splice(0, messages.length);
    nodeMap.forEach((n) => n.remove());
    nodeMap.clear();

    appendMessage({ role: "ai", content: "چت جدید شروع شد. بنویس ✨" });
    els.textarea.value = "";
    autoResize();
    els.textarea.focus();
  });

  // Submit handlers
  els.form?.addEventListener("submit", (e) => {
    e.preventDefault();
    send();
  });

  els.textarea?.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      send();
    }
  });

  // Main send
  async function send() {
    const txt = (els.textarea?.value || "").trim();
    if (!txt) return;

    const userId = appendMessage({ role: "user", content: txt });
    els.textarea.value = "";
    autoResize();

    setLoading(true);
    const loaderId = appendMessage({ role: "ai", content: "", loading: true });

    try {
      const history = messages
        .filter((m) => !m.loading)
        .map(({ role, content }) => ({ role: role === "ai" ? "assistant" : "user", content }));

      const data = await callGPT([
        { role: "system", content: SYSTEM_PROMPT },
        ...history,
      ]);

      const content =
        data?.data?.choices?.[0]?.message?.content ||
        data?.choices?.[0]?.message?.content ||
        data?.content ||
        "";

      updateMessage(loaderId, { role: "ai", loading: false, content: content || "پاسخی دریافت نشد." });
    } catch (err) {
      console.error(err);
      updateMessage(loaderId, {
        role: "ai",
        loading: false,
        content: "متأسفم! اتصال برقرار نشد.",
        secondary: String(err?.message || err || ""),
      });
    } finally {
      setLoading(false);
    }
  }

  // Backend call
  async function callGPT(messages) {
    if (!API_URL) throw new Error("API URL تنظیم نشده");
    const res = await fetch(API_URL, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ model: MODEL, messages }),
    });

    let data = null;
    try { data = await res.json(); } catch {}
    if (!res.ok || (data && data.ok === false)) {
      const msg = (data && data.error) ? String(data.error) : `HTTP ${res.status}`;
      throw new Error(msg);
    }
    return data;
  }

  // Utils
  async function copyText(text) {
    try { await navigator.clipboard.writeText(text); toast("کپی شد ✅"); }
    catch { toast("کپی نشد!"); }
  }
  function shareText(text) {
    if (navigator.share) navigator.share({ text }).catch(()=>{});
    else copyText(text);
  }
  function toast(msg) { console.log(msg); }
  function regenerateLast() {
    // دمو: آخرین پاسخ AI را کمی تغییر می‌دهیم
    const last = [...messages].reverse().find(m => m.role === "ai" && !m.loading);
    if (!last) return;
    updateMessage(last.id, { content: (last.content || "") + " 🔄" });
  }
})();
