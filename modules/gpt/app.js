// modules/gpt/app.js
(() => {
  "use strict";

  const cfg = window.__GPT_APP_CONFIG || {};
  const origin = window.location.origin;
  const API_URL = (cfg.apiUrl || "").trim() || new URL("/api/gpt", origin).toString();
  const MODEL = (cfg.model || "gpt-4o-mini").trim() || "gpt-4o-mini";
  const SYSTEM_PROMPT =
    cfg.systemPrompt || "You are Vexa GPT-5, a friendly and professional AI assistant.";

  const els = {
    chat: document.getElementById("chat"),
    form: document.getElementById("composer"),
    textarea: document.getElementById("prompt-input"),
    sendBtn: document.getElementById("send-btn"),
    newChat: document.getElementById("new-chat"),
  };

  const messages = []; // {id, role:'user'|'ai', content, loading?, ts}
  const nodeMap = new Map();

  const newId = () => (crypto?.randomUUID?.() || `${Date.now()}_${Math.random().toString(36).slice(2)}`);
  const isRTL = (t="") => /[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF]/.test(t);
  const scrollToBottom = () => { try { window.scrollTo({ top: document.body.scrollHeight, behavior: "smooth" }); } catch {} };
  const autoResize = () => {
    if (!els.textarea) return;
    els.textarea.style.height = "auto";
    els.textarea.style.height = `${Math.min(els.textarea.scrollHeight, 180)}px`;
  };
  const setLoading = (on) => {
    if (els.textarea) els.textarea.disabled = on;
    if (els.sendBtn) els.sendBtn.disabled = on;
  };

  // Init
  els.textarea?.addEventListener("input", autoResize);
  els.newChat?.addEventListener("click", resetChat);
  els.form?.addEventListener("submit", (e) => { e.preventDefault(); send(); });
  els.textarea?.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(); }
  });

  function resetChat(){
    messages.splice(0, messages.length);
    nodeMap.forEach(n => n.remove());
    nodeMap.clear();
    appendMessage({ role: "ai", content: "چت جدید شروع شد. بنویس." });
    els.textarea.value = ""; autoResize(); els.textarea.focus();
  }

  function appendMessage(m){
    const id = m.id || newId();
    const rec = { ...m, id, ts: m.ts || Date.now() };
    messages.push(rec);
    renderMessage(rec);
    return id;
  }

  function updateMessage(id, patch){
    const i = messages.findIndex(m => m.id === id);
    if (i === -1) return;
    messages[i] = { ...messages[i], ...patch };
    renderMessage(messages[i]);
  }

  function renderMessage(m){
    let node = nodeMap.get(m.id);
    const user = m.role === "user";
    if (!node){
      node = document.createElement("div");
      node.className = `msg ${user ? "user" : "ai"} fade-in`;
      node.innerHTML = `<div class="block"></div>`;
      nodeMap.set(m.id, node);
      els.chat?.appendChild(node);
    }
    const block = node.querySelector(".block");

    if (m.loading){
      node.classList.add("loading");
      block.innerHTML = `در حال فکر کردن<span class="dots"><i></i><i></i><i></i></span>`;
    } else {
      node.classList.remove("loading");
      block.textContent = m.content || "";
    }

    block.setAttribute("dir", isRTL(m.content) ? "rtl" : "auto");
    requestAnimationFrame(scrollToBottom);
  }

  async function send(){
    const txt = (els.textarea?.value || "").trim();
    if (!txt) return;

    appendMessage({ role: "user", content: txt });
    els.textarea.value = ""; autoResize();

    setLoading(true);
    const loaderId = appendMessage({ role: "ai", content: "", loading: true });

    try {
      const history = messages
        .filter(m => !m.loading)
        .map(({ role, content }) => ({ role: role === "ai" ? "assistant" : "user", content }));

      const data = await callGPT([{ role: "system", content: SYSTEM_PROMPT }, ...history]);

      const content =
        data?.data?.choices?.[0]?.message?.content ||
        data?.choices?.[0]?.message?.content ||
        data?.content || "";

      updateMessage(loaderId, { role:"ai", loading:false, content: content || "پاسخی دریافت نشد." });
    } catch (err) {
      updateMessage(loaderId, {
        role: "ai", loading: false, content: "متأسفم! اتصال برقرار نشد.", secondary: String(err?.message || err || "")
      });
    } finally {
      setLoading(false);
    }
  }

  async function callGPT(messages){
    if (!API_URL) throw new Error("API URL تنظیم نشده");
    const res = await fetch(API_URL, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ model: MODEL, messages }),
    });
    let data = null; try { data = await res.json(); } catch {}
    if (!res.ok || (data && data.ok === false)) {
      const msg = (data && data.error) ? String(data.error) : `HTTP ${res.status}`;
      throw new Error(msg);
    }
    return data;
  }
})();
