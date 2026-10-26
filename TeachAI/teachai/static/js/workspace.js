(function () {
  "use strict";

  const csrf = document.querySelector('meta[name="csrf-token"]')?.content || "";
  const api = {
    bootstrap: "/api/bootstrap",
    conversations: "/api/conversations",
    chat: (id) => `/api/conversations/${id}/chat`,
    groups: "/api/groups",
    group: (id) => `/api/groups/${id}`,
    reminders: "/api/reminders",
    reminder: (id) => `/api/reminders/${id}`,
  };

  const state = {
    user: null,
    ai: null,
    groups: [],
    conversations: [],
    reminders: [],
    activeConversationId: null,
    activeGroupId: null,
    calendarDate: new Date(),
    selectedDateKey: dateKey(new Date()),
    pendingReminderId: null,
  };

  const sidebar = document.getElementById("sidebar");
  const sidebarToggle = document.getElementById("sidebar-toggle");
  const sidebarClose = document.getElementById("sidebar-close");
  const sidebarScrim = document.getElementById("sidebar-scrim");
  const newChatBtn = document.getElementById("new-chat-btn");
  const groupTabs = document.getElementById("group-tabs");
  const manageGroupsBtn = document.getElementById("manage-groups-btn");
  const conversationList = document.getElementById("conversation-list");
  const conversationCount = document.getElementById("conversation-count");
  const conversationSearch = document.getElementById("conversation-search");
  const headerGroup = document.getElementById("header-group");
  const headerGroupDot = document.getElementById("header-group-dot");
  const headerTitle = document.getElementById("header-title");
  const emptyState = document.getElementById("empty-state");
  const messageList = document.getElementById("message-list");
  const chatScroll = document.getElementById("chat-scroll");
  const typingIndicator = document.getElementById("typing-indicator");
  const composer = document.getElementById("composer");
  const messageInput = document.getElementById("message-input");
  const sendBtn = document.getElementById("send-btn");
  const micBtn = document.getElementById("mic-btn");
  const voiceStatus = document.getElementById("voice-status");
  const voiceStatusText = document.getElementById("voice-status-text");
  const voiceCancel = document.getElementById("voice-cancel");
  const aiStatus = document.getElementById("ai-status");
  const aiStatusLabel = document.getElementById("ai-status-label");
  const composerMode = document.getElementById("composer-mode");
  const renameChatBtn = document.getElementById("rename-chat-btn");
  const chatMenuBtn = document.getElementById("chat-menu-btn");
  const chatMenu = document.getElementById("chat-menu");
  const menuRename = document.getElementById("menu-rename");
  const menuGroupSelect = document.getElementById("menu-group-select");
  const menuDelete = document.getElementById("menu-delete");
  const agendaToggle = document.getElementById("agenda-toggle");
  const agendaPanel = document.getElementById("agenda-panel");
  const agendaClose = document.getElementById("agenda-close");
  const agendaScrim = document.getElementById("agenda-scrim");
  const calPrev = document.getElementById("cal-prev");
  const calNext = document.getElementById("cal-next");
  const calToday = document.getElementById("cal-today");
  const calMonthLabel = document.getElementById("cal-month-label");
  const calendarGrid = document.getElementById("calendar-grid");
  const addReminderBtn = document.getElementById("add-reminder-btn");
  const nextReminderTitle = document.getElementById("next-reminder-title");
  const nextReminderMeta = document.getElementById("next-reminder-meta");
  const reminderListTitle = document.getElementById("reminder-list-title");
  const reminderCount = document.getElementById("reminder-count");
  const reminderList = document.getElementById("reminder-list");
  const notifyBtn = document.getElementById("notify-btn");
  const notifyStatus = document.getElementById("notify-status");

  const reminderModal = document.getElementById("reminder-modal");
  const reminderForm = document.getElementById("reminder-form");
  const reminderIdInput = document.getElementById("reminder-id");
  const reminderTitleInput = document.getElementById("reminder-title");
  const reminderDateInput = document.getElementById("reminder-date");
  const reminderTimeInput = document.getElementById("reminder-time");
  const reminderNotesInput = document.getElementById("reminder-notes");
  const deleteReminderBtn = document.getElementById("delete-reminder-btn");
  const reminderModalTitle = document.getElementById("reminder-modal-title");

  const groupModal = document.getElementById("group-modal");
  const groupForm = document.getElementById("group-form");
  const groupIdInput = document.getElementById("group-id");
  const groupNameInput = document.getElementById("group-name");
  const colorPalette = document.getElementById("color-palette");
  const groupModalTitle = document.getElementById("group-modal-title");
  const saveGroupBtn = document.getElementById("save-group-btn");

  const manageGroupsModal = document.getElementById("manage-groups-modal");
  const manageGroupsList = document.getElementById("manage-groups-list");
  const manageAddGroupBtn = document.getElementById("manage-add-group-btn");

  let recognition = null;
  let recognizing = false;
  let voiceStarting = false;
  let voiceStartTimer = null;
  let selectedColor = "#5B5BD6";

  function dateKey(d) { return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,"0")}-${String(d.getDate()).padStart(2,"0")}`; }
  function selectedDateLabel() {
    const selected = new Date(`${state.selectedDateKey}T00:00:00`);
    const today = dateKey(new Date());
    const tomorrowDate = new Date();
    tomorrowDate.setDate(tomorrowDate.getDate() + 1);
    if (state.selectedDateKey === today) return "Today";
    if (state.selectedDateKey === dateKey(tomorrowDate)) return "Tomorrow";
    return selected.toLocaleDateString(undefined, {
      weekday: "short",
      month: "short",
      day: "numeric",
      year: selected.getFullYear() === new Date().getFullYear() ? undefined : "numeric"
    });
  }
  function toTimeInput(d) { return `${String(d.getHours()).padStart(2,"0")}:${String(d.getMinutes()).padStart(2,"0")}`; }
  function monthLabel(d) { return d.toLocaleDateString(undefined, { month: "long", year: "numeric" }); }
  function humanDue(reminder) {
    const date = new Date(reminder.due_at.replace("T"," ") + ":00");
    const now = new Date();
    const sameDay = date.getDate()===now.getDate() && date.getMonth()===now.getMonth() && date.getFullYear()===now.getFullYear();
    const tomorrow = new Date(now); tomorrow.setDate(now.getDate()+1);
    const isTomorrow = date.getDate()===tomorrow.getDate() && date.getMonth()===tomorrow.getMonth() && date.getFullYear()===tomorrow.getFullYear();
    const time = date.toLocaleTimeString(undefined, { hour: "numeric", minute: "2-digit" });
    if (sameDay) return `Today · ${time}`;
    if (isTomorrow) return `Tomorrow · ${time}`;
    return `${date.toLocaleDateString(undefined, { month: "short", day: "numeric" })} · ${time}`;
  }

  async function request(method, url, body) {
    const headers = { "X-CSRF-Token": csrf, "Accept": "application/json" };
    const options = { method, headers, credentials: "same-origin" };
    if (body !== undefined) {
      headers["Content-Type"] = "application/json";
      options.body = JSON.stringify(body);
    }
    const response = await fetch(url, options);
    const data = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(data.error || "Something went wrong.");
    return data;
  }

  function showToast(message, type="success") {
    const toast = document.createElement("div");
    toast.className = `toast ${type === "error" ? "error" : "success"}`;
    toast.innerHTML = `<span class="toast-dot"></span><div class="toast-content"><strong>${type==="error"?"Heads up":"All set"}</strong><span>${escapeHtml(message)}</span></div>`;
    document.getElementById("toast-stack").appendChild(toast);
    window.setTimeout(()=>{ toast.classList.add("out"); window.setTimeout(()=>toast.remove(),180); }, 2800);
  }
  function escapeHtml(s){ const d=document.createElement("div"); d.textContent=s; return d.innerHTML; }

  function initVoice() {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) { micBtn.disabled = true; micBtn.title = "Voice input not supported in this browser"; return; }
    recognition = new SpeechRecognition();
    recognition.lang = "en-US";
    recognition.interimResults = false;
    recognition.continuous = false;
    recognition.onstart = () => {
      window.clearTimeout(voiceStartTimer);
      voiceStartTimer = null;
      voiceStarting = false;
      recognizing = true;
      micBtn.classList.add("active");
      voiceStatus.hidden = false;
      voiceStatusText.textContent = "Listening… speak your question";
    };
    recognition.onend = () => {
      window.clearTimeout(voiceStartTimer);
      voiceStartTimer = null;
      voiceStarting = false;
      recognizing = false;
      micBtn.classList.remove("active");
      voiceStatus.hidden = true;
    };
    recognition.onerror = (event) => {
      window.clearTimeout(voiceStartTimer);
      voiceStartTimer = null;
      voiceStarting = false;
      recognizing = false;
      micBtn.classList.remove("active");
      voiceStatus.hidden = true;

      const messages = {
        "not-allowed": "Microphone access is blocked. Allow it for this site/browser in its permissions, and in Windows Settings > Privacy & security > Microphone, then reload the page.",
        "service-not-allowed": "This browser is not allowing its speech-recognition service. Check microphone permissions or try Chrome or Edge.",
        "audio-capture": "No microphone is available. Connect a microphone and check that Windows has the correct input selected.",
        "no-speech": "No speech was detected. Check your microphone input, then press the microphone and try again.",
        network: "The browser's online speech-recognition service could not be reached. Check your internet connection and try opening TeachAI in Chrome or Edge instead of the embedded VS Code browser.",
        "language-not-supported": "Speech recognition does not support the selected language in this browser.",
        aborted: "Voice recognition was stopped."
      };
      const message = messages[event.error] || `Voice recognition failed (${event.error || "unknown error"}). Check your microphone and browser permissions.`;
      if (event.error !== "aborted") showToast(message, "error");
    };
    recognition.onresult = async (event) => {
      const transcript = event.results[0][0].transcript.trim();
      if (!transcript) {
        showToast("No speech was detected. Check your microphone and try again.", "error");
        return;
      }
      messageInput.value = transcript;
      autoResize();
      updateSend();
      if (!state.activeConversationId) await startNewConversation();
      if (!state.activeConversationId) return;
      composer.requestSubmit();
    };
  }

  micBtn.addEventListener("click", () => {
    if (!recognition) return;
    if (recognizing || voiceStarting) { recognition.stop(); return; }
    voiceStarting = true;
    voiceStatus.hidden = false;
    voiceStatusText.textContent = "Starting microphone…";
    voiceStartTimer = window.setTimeout(() => {
      if (!voiceStarting) return;
      voiceStarting = false;
      voiceStatus.hidden = true;
      showToast(
        "Voice recognition did not start. Allow microphone access for this site/browser and in Windows microphone privacy settings, then reload.",
        "error"
      );
    }, 10000);
    try {
      recognition.start();
    } catch (error) {
      window.clearTimeout(voiceStartTimer);
      voiceStartTimer = null;
      voiceStarting = false;
      voiceStatus.hidden = true;
      showToast(`Could not start voice recognition: ${error.message}`, "error");
    }
  });
  voiceCancel.addEventListener("click", () => { if (recognition && recognizing) recognition.stop(); });

  sidebarToggle.addEventListener("click", () => { sidebar.classList.add("open"); sidebarScrim.hidden=false; });
  sidebarClose.addEventListener("click", closeSidebar);
  sidebarScrim.addEventListener("click", closeSidebar);
  function closeSidebar(){ sidebar.classList.remove("open"); sidebarScrim.hidden=true; }

  agendaToggle.addEventListener("click", () => { agendaPanel.classList.add("open"); agendaScrim.hidden=false; });
  agendaClose.addEventListener("click", closeAgenda);
  agendaScrim.addEventListener("click", closeAgenda);
  function closeAgenda(){ agendaPanel.classList.remove("open"); agendaScrim.hidden=true; }

  newChatBtn.addEventListener("click", () => startNewConversation());
  manageGroupsBtn.addEventListener("click", openManageGroups);

  function autoResize() {
    messageInput.style.height = "auto";
    messageInput.style.height = Math.min(messageInput.scrollHeight, 160) + "px";
  }
  messageInput.addEventListener("input", () => { autoResize(); updateSend(); });
  messageInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); if (!sendBtn.disabled) composer.requestSubmit(); }
  });
  function updateSend(){ sendBtn.disabled = messageInput.value.trim().length === 0; }
  function updateAIStatus(configured, model, unavailable=false) {
    aiStatus.classList.toggle("is-online", configured && !unavailable);
    if (unavailable) {
      aiStatusLabel.textContent = "AI unavailable";
      aiStatus.title = "The configured AI provider did not respond";
      composerMode.textContent = "AI unavailable — check Settings";
    } else if (configured) {
      aiStatusLabel.textContent = "AI connected";
      aiStatus.title = "Cloud AI connected";
      composerMode.textContent = `Powered by ${model}`;
    } else {
      aiStatusLabel.textContent = "Demo mode";
      aiStatus.title = "Built-in demo mode";
      composerMode.textContent = "Demo mode — add an AI key in Settings";
    }
  }

  composer.addEventListener("submit", async (e) => {
    e.preventDefault();
    const text = messageInput.value.trim();
    if (!text) return;
    if (!state.activeConversationId) await startNewConversation();
    const id = state.activeConversationId;
    appendUserMessage(text);
    messageInput.value = "";
    autoResize();
    updateSend();
    setTyping(true);
    let result;
    try {
      result = await request("POST", api.chat(id), { message: text });
    } catch (error) {
      setTyping(false);
      appendAssistantMessage("I ran into a problem sending that message. " + error.message);
      scrollToBottom();
      showToast(error.message, "error");
      return;
    }
    setTyping(false);
    appendAssistantMessage(result.assistant_message.content);
    if (result.source === "cloud") updateAIStatus(true, state.ai?.model || "");
    else if (result.source === "error") updateAIStatus(false, "", true);
    if (Array.isArray(result.reminders)) {
      state.reminders = result.reminders;
      renderReminders();
      renderCalendar();
    } else if (result.reminder) {
      const index = state.reminders.findIndex((reminder) => reminder.id === result.reminder.id);
      if (index >= 0) state.reminders[index] = result.reminder;
      else state.reminders.push(result.reminder);
      renderReminders();
      renderCalendar();
    }
    if (result.conversation) updateConversationInState(result.conversation);
    renderConversations();
    scrollToBottom();
    if (result.warning) showToast(result.warning, "error");
  });

  function setTyping(show){ typingIndicator.hidden = !show; if (show) scrollToBottom(); }
  function scrollToBottom(){ chatScroll.scrollTo({ top: chatScroll.scrollHeight, behavior: "smooth" }); }

  function appendUserMessage(text){
    const row = document.createElement("div");
    row.className = "message-row user";
    row.innerHTML = `<div class="message-content"><div class="message-bubble">${renderMarkdown(text)}</div></div>`;
    messageList.appendChild(row);
    emptyState.hidden = true;
    scrollToBottom();
  }
  function appendAssistantMessage(text){
    const row = document.createElement("div");
    row.className = "message-row assistant";
    row.innerHTML = `<span class="assistant-avatar"><span class="mini-brand">T</span></span><div class="message-content"><div class="message-bubble">${renderMarkdown(text)}</div><div class="message-actions"><button class="action-pill" type="button" data-copy><svg class="icon"><use href="#i-copy"></use></svg> Copy</button></div></div>`;
    row.querySelector("[data-copy]").addEventListener("click", () => copyText(text));
    messageList.appendChild(row);
    emptyState.hidden = true;
    scrollToBottom();
  }
  function renderMarkdown(text){
    let html = escapeHtml(text);
    html = html.replace(/```([\s\S]+?)```/g, "<pre><code>$1</code></pre>");
    html = html.replace(/`([^`]+)`/g, "<code>$1</code>");
    html = html.replace(/^### (.+)$/gm, "<h3>$1</h3>");
    html = html.replace(/^## (.+)$/gm, "<h2>$1</h2>");
    html = html.replace(/^# (.+)$/gm, "<h1>$1</h1>");
    html = html.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");
    html = html.replace(/\*(.+?)\*/g, "<em>$1</em>");
    html = html.replace(/^\> (.+)$/gm, "<blockquote>$1</blockquote>");
    html = html.replace(/^\- (.+)$/gm, "<li>$1</li>");
    html = html.replace(/^\d+\. (.+)$/gm, "<li>$1</li>");
    html = html.replace(/(<li>.+<\/li>)/gs, "<ul>$1</ul>");
    html = html.replace(/\n\n/g, "</p><p>");
    return `<p>${html}</p>`.replace(/<p><\/p>/g,"").replace(/<p><ul>/g,"<ul>").replace(/<\/ul><\/p>/g,"</ul>");
  }
  function copyText(text){ navigator.clipboard.writeText(text).then(()=>showToast("Copied to clipboard")); }

  async function startNewConversation(){
    try {
      const groupId = state.activeGroupId && state.activeGroupId !== "all" ? state.activeGroupId : null;
      const result = await request("POST", api.conversations, { title: "New conversation", group_id: groupId });
      state.activeConversationId = result.conversation.id;
      state.conversations.unshift({
        id: result.conversation.id,
        group_id: result.conversation.group_id,
        title: result.conversation.title,
        preview: "",
        updated_at: result.conversation.updated_at,
        created_at: result.conversation.created_at
      });
      messageList.innerHTML = "";
      emptyState.hidden = false;
      headerTitle.textContent = "What are we learning?";
      renderHeaderGroup(result.conversation.group_id);
      updateConversationControls(true);
      renderConversations();
      closeSidebar();
      messageInput.focus();
    } catch (error) { showToast(error.message, "error"); }
  }

  function updateConversationControls(hasActive){
    renameChatBtn.disabled = !hasActive;
    chatMenuBtn.disabled = !hasActive;
  }

  groupTabs.addEventListener("click", (e) => {
    const tab = e.target.closest(".group-tab");
    if (!tab) return;
    document.querySelectorAll(".group-tab").forEach((t)=>t.classList.remove("active"));
    tab.classList.add("active");
    state.activeGroupId = tab.dataset.groupId;
    renderConversations();
  });

  conversationList.addEventListener("click", async (e) => {
    const item = e.target.closest(".conversation-item");
    if (!item) return;
    const id = Number(item.dataset.id);
    await loadConversation(id);
    closeSidebar();
  });
  conversationSearch.addEventListener("input", renderConversations);

  async function loadConversation(id){
    try {
      const result = await request("GET", api.conversations + "/" + id);
      state.activeConversationId = id;
      messageList.innerHTML = "";
      emptyState.hidden = true;
      result.messages.forEach((m) => {
        if (m.role === "user") appendUserMessage(m.content);
        else appendAssistantMessage(m.content);
      });
      headerTitle.textContent = result.conversation.title;
      renderHeaderGroup(result.conversation.group_id);
      updateConversationInState(result.conversation);
      updateConversationControls(true);
      renderConversations();
      scrollToBottom();
      messageInput.focus();
    } catch (error) { showToast(error.message, "error"); }
  }

  function updateConversationInState(convo){
    const idx = state.conversations.findIndex((c)=>c.id === convo.id);
    if (idx >= 0) { state.conversations[idx] = {...state.conversations[idx], ...convo}; }
    else state.conversations.unshift(convo);
  }

  function renderConversations(){
    const query = conversationSearch.value.toLowerCase().trim();
    const filtered = state.conversations.filter((c) => {
      if (state.activeGroupId && state.activeGroupId !== "all") {
        if (String(c.group_id) !== String(state.activeGroupId)) return false;
      }
      if (!query) return true;
      return c.title.toLowerCase().includes(query) || (c.preview||"").toLowerCase().includes(query);
    });
    conversationList.innerHTML = "";
    conversationCount.textContent = filtered.length;
    filtered.forEach((c) => {
      const item = document.createElement("button");
      item.className = "conversation-item" + (state.activeConversationId === c.id ? " active" : "");
      item.dataset.id = c.id;
      const group = state.groups.find((g)=>g.id === c.group_id);
      item.innerHTML = `<span class="group-dot" style="background:${group?group.color:"#5B5BD6"}"></span><div class="conversation-copy"><span class="conversation-title">${escapeHtml(c.title)}</span><span class="conversation-preview">${escapeHtml(c.preview||"")}</span></div>`;
      conversationList.appendChild(item);
    });
  }

  function renderHeaderGroup(groupId){
    const group = state.groups.find((g)=>g.id === groupId);
    if (group) { headerGroup.textContent = group.name; headerGroupDot.style.background = group.color; headerGroupDot.hidden=false; }
    else { headerGroup.textContent = "Workspace"; headerGroupDot.hidden=true; }
  }

  renameChatBtn.addEventListener("click", renameActiveChat);
  menuRename.addEventListener("click", renameActiveChat);
  function renameActiveChat(){
    if (!state.activeConversationId) return;
    chatMenu.hidden = true;
    const current = state.conversations.find((c)=>c.id === state.activeConversationId);
    const name = prompt("Rename this conversation", current?.title || "New conversation");
    if (!name || name.trim() === current?.title) return;
    request("PATCH", api.conversations + "/" + state.activeConversationId, { title: name.trim() })
      .then((result) => { updateConversationInState(result.conversation); headerTitle.textContent = result.conversation.title; renderConversations(); })
      .catch((err) => showToast(err.message, "error"));
  }

  chatMenuBtn.addEventListener("click", (e) => { e.stopPropagation(); chatMenu.hidden = !chatMenu.hidden; populateGroupSelect(); });
  document.addEventListener("click", (e) => { if (!chatMenu.contains(e.target) && e.target !== chatMenuBtn) chatMenu.hidden = true; });
  menuGroupSelect.addEventListener("change", () => {
    const groupId = menuGroupSelect.value === "none" ? null : Number(menuGroupSelect.value);
    request("PATCH", api.conversations + "/" + state.activeConversationId, { group_id: groupId })
      .then((result) => { updateConversationInState(result.conversation); renderHeaderGroup(result.conversation.group_id); renderConversations(); chatMenu.hidden=true; })
      .catch((err) => showToast(err.message, "error"));
  });
  function populateGroupSelect(){
    menuGroupSelect.innerHTML = '<option value="none">Unassigned</option>';
    state.groups.forEach((g) => { const opt = document.createElement("option"); opt.value = g.id; opt.textContent = g.name; menuGroupSelect.appendChild(opt); });
    const current = state.conversations.find((c)=>c.id === state.activeConversationId);
    menuGroupSelect.value = current?.group_id ? current.group_id : "none";
  }
  menuDelete.addEventListener("click", async () => {
    if (!state.activeConversationId) return;
    if (!confirm("Delete this conversation and all messages?")) return;
    try {
      await request("DELETE", api.conversations + "/" + state.activeConversationId);
      state.conversations = state.conversations.filter((c)=>c.id !== state.activeConversationId);
      state.activeConversationId = null;
      messageList.innerHTML = "";
      emptyState.hidden = false;
      headerTitle.textContent = "What are we learning?";
      renderHeaderGroup(null);
      updateConversationControls(false);
      renderConversations();
      chatMenu.hidden = true;
      showToast("Conversation deleted");
    } catch (error) { showToast(error.message, "error"); }
  });

  calPrev.addEventListener("click", () => changeCalendarMonth(-1));
  calNext.addEventListener("click", () => changeCalendarMonth(1));
  calToday.addEventListener("click", () => { state.calendarDate = new Date(); state.selectedDateKey = dateKey(state.calendarDate); renderCalendar(); renderReminderListForDate(); });
  function changeCalendarMonth(offset) {
    const selectedDay = new Date(`${state.selectedDateKey}T00:00:00`).getDate();
    const targetMonth = new Date(
      state.calendarDate.getFullYear(),
      state.calendarDate.getMonth() + offset,
      1
    );
    const lastDay = new Date(
      targetMonth.getFullYear(),
      targetMonth.getMonth() + 1,
      0
    ).getDate();
    state.calendarDate = targetMonth;
    state.selectedDateKey = dateKey(new Date(
      targetMonth.getFullYear(),
      targetMonth.getMonth(),
      Math.min(selectedDay, lastDay)
    ));
    renderCalendar();
    renderReminderListForDate();
  }
  function renderCalendar(){
    calMonthLabel.textContent = monthLabel(state.calendarDate);
    calendarGrid.innerHTML = "";
    const year = state.calendarDate.getFullYear();
    const month = state.calendarDate.getMonth();
    const first = new Date(year, month, 1);
    const start = first.getDay();
    const daysInMonth = new Date(year, month+1, 0).getDate();
    const daysInPrev = new Date(year, month, 0).getDate();
    for (let i = start-1; i >= 0; i--) {
      const day = daysInPrev - i;
      appendCalendarDay(new Date(year, month - 1, day), true);
    }
    for (let day=1; day<=daysInMonth; day++) {
      appendCalendarDay(new Date(year, month, day), false);
    }
    const total = start + daysInMonth;
    const remaining = total % 7 === 0 ? 0 : 7 - (total % 7);
    for (let day=1; day<=remaining; day++) {
      appendCalendarDay(new Date(year, month + 1, day), true);
    }
  }
  function appendCalendarDay(date, otherMonth) {
    const key = dateKey(date);
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "calendar-day" +
      (otherMonth ? " other" : "") +
      (key === dateKey(new Date()) ? " today" : "") +
      (hasReminderOn(key) ? " has-event" : "") +
      (key === state.selectedDateKey ? " active" : "");
    btn.textContent = date.getDate();
    btn.setAttribute("aria-label", date.toLocaleDateString(undefined, {
      weekday: "long", month: "long", day: "numeric", year: "numeric"
    }));
    btn.setAttribute("aria-pressed", String(key === state.selectedDateKey));
    btn.addEventListener("click", () => {
      state.selectedDateKey = key;
      if (otherMonth) state.calendarDate = new Date(date.getFullYear(), date.getMonth(), 1);
      renderCalendar();
      renderReminderListForDate();
    });
    calendarGrid.appendChild(btn);
  }
  function hasReminderOn(key){
    return state.reminders.some((r) => r.due_at.startsWith(key) && !r.completed);
  }
  function renderReminderListForDate(){
    renderReminders();
  }

  addReminderBtn.addEventListener("click", () => openReminderModal());
  function openReminderModal(reminder=null){
    reminderModal.classList.add("open");
    reminderModal.setAttribute("aria-hidden","false");
    if (reminder) {
      reminderModalTitle.textContent = "Edit reminder";
      reminderIdInput.value = reminder.id;
      reminderTitleInput.value = reminder.title;
      const dt = new Date(reminder.due_at.replace("T"," ") + ":00");
      reminderDateInput.value = dateKey(dt);
      reminderTimeInput.value = toTimeInput(dt);
      reminderNotesInput.value = reminder.notes || "";
      deleteReminderBtn.hidden = false;
    } else {
      reminderModalTitle.textContent = "New reminder";
      reminderIdInput.value = "";
      reminderTitleInput.value = "";
      reminderDateInput.value = state.selectedDateKey;
      reminderTimeInput.value = "09:00";
      reminderNotesInput.value = "";
      deleteReminderBtn.hidden = true;
    }
    reminderTitleInput.focus();
  }
  document.querySelectorAll("[data-close-modal]").forEach((btn) => btn.addEventListener("click", () => closeModals()));
  function closeModals(){
    reminderModal.classList.remove("open");
    reminderModal.setAttribute("aria-hidden","true");
    groupModal.classList.remove("open");
    groupModal.setAttribute("aria-hidden","true");
    manageGroupsModal.classList.remove("open");
    manageGroupsModal.setAttribute("aria-hidden","true");
  }

  reminderForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const id = reminderIdInput.value;
    const body = {
      title: reminderTitleInput.value.trim(),
      notes: reminderNotesInput.value.trim(),
      due_at: reminderDateInput.value + "T" + reminderTimeInput.value
    };
    try {
      if (id) {
        const result = await request("PATCH", api.reminder(id), body);
        const idx = state.reminders.findIndex((r)=>r.id===Number(id));
        if (idx>=0) state.reminders[idx] = result.reminder;
        showToast("Reminder updated");
      } else {
        const result = await request("POST", api.reminders, body);
        state.reminders.push(result.reminder);
        showToast("Reminder added");
      }
      closeModals();
      renderReminders();
      renderCalendar();
      renderNextReminder();
    } catch (error) { showToast(error.message, "error"); }
  });
  deleteReminderBtn.addEventListener("click", async () => {
    const id = reminderIdInput.value;
    if (!id) return;
    if (!confirm("Delete this reminder?")) return;
    try {
      await request("DELETE", api.reminder(id));
      state.reminders = state.reminders.filter((r)=>r.id!==Number(id));
      closeModals();
      renderReminders();
      renderCalendar();
      renderNextReminder();
      showToast("Reminder deleted");
    } catch (error) { showToast(error.message, "error"); }
  });

  function renderReminders(){
    const list = state.reminders
      .filter((reminder) => reminder.due_at.startsWith(state.selectedDateKey))
      .sort((a,b)=>a.due_at.localeCompare(b.due_at));
    reminderList.innerHTML = "";
    reminderListTitle.textContent = `Tasks for ${selectedDateLabel()}`;
    reminderCount.textContent = list.length;
    if (list.length === 0) {
      const empty = document.createElement("p");
      empty.className = "reminder-empty";
      empty.textContent = "No tasks scheduled for this day.";
      reminderList.appendChild(empty);
    }
    list.forEach((r) => {
      const card = document.createElement("div");
      card.className = "reminder-card" + (r.completed?" completed":"");
      card.innerHTML = `<button class="reminder-check" data-complete data-id="${r.id}">${r.completed?'<svg class="icon"><use href="#i-check"></use></svg>':""}</button><div class="reminder-copy"><strong>${escapeHtml(r.title)}</strong><div class="reminder-meta"><svg class="icon"><use href="#i-clock"></use></svg><span>${humanDue(r)}</span></div>${r.notes?`<span class="reminder-meta">${escapeHtml(r.notes)}</span>`:""}</div><button class="icon-btn" data-edit data-reminder='${escapeHtml(JSON.stringify(r))}'><svg class="icon"><use href="#i-edit"></use></svg></button>`;
      card.querySelector("[data-complete]").addEventListener("click", () => toggleComplete(r));
      card.querySelector("[data-edit]").addEventListener("click", () => openReminderModal(r));
      reminderList.appendChild(card);
    });
    renderNextReminder();
  }
  async function toggleComplete(r){
    try {
      const result = await request("PATCH", api.reminder(r.id), { completed: !r.completed });
      const idx = state.reminders.findIndex((x)=>x.id===r.id);
      if (idx>=0) state.reminders[idx] = result.reminder;
      renderReminders();
      renderCalendar();
    } catch (error) { showToast(error.message, "error"); }
  }
  function renderNextReminder(){
    const pending = state.reminders.filter((r)=>!r.completed).sort((a,b)=>a.due_at.localeCompare(b.due_at));
    if (pending.length === 0) { nextReminderTitle.textContent = "No reminders yet"; nextReminderMeta.textContent = "Create one with your voice or the + button"; return; }
    const r = pending[0];
    nextReminderTitle.textContent = r.title;
    nextReminderMeta.textContent = humanDue(r);
  }

  colorPalette.addEventListener("click", (e) => {
    const swatch = e.target.closest(".color-swatch");
    if (!swatch) return;
    colorPalette.querySelectorAll(".color-swatch").forEach((s)=>s.classList.remove("active"));
    swatch.classList.add("active");
    selectedColor = swatch.dataset.color;
  });
  function openGroupModal(group=null){
    groupModal.classList.add("open");
    groupModal.setAttribute("aria-hidden","false");
    if (group) {
      groupModalTitle.textContent = "Edit study group";
      groupIdInput.value = group.id;
      groupNameInput.value = group.name;
      selectedColor = group.color || "#5B5BD6";
      colorPalette.querySelectorAll(".color-swatch").forEach((s)=>s.classList.toggle("active", s.dataset.color===selectedColor));
      saveGroupBtn.textContent = "Save changes";
    } else {
      groupModalTitle.textContent = "New study group";
      groupIdInput.value = "";
      groupNameInput.value = "";
      selectedColor = "#5B5BD6";
      colorPalette.querySelectorAll(".color-swatch").forEach((s,i)=>s.classList.toggle("active", i===0));
      saveGroupBtn.textContent = "Create group";
    }
    groupNameInput.focus();
  }
  groupForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const id = groupIdInput.value;
    const body = { name: groupNameInput.value.trim(), color: selectedColor };
    try {
      if (id) {
        const result = await request("PATCH", api.group(id), body);
        const idx = state.groups.findIndex((g)=>g.id===Number(id));
        if (idx>=0) state.groups[idx] = result.group;
        showToast("Group updated");
      } else {
        const result = await request("POST", api.groups, body);
        state.groups.push(result.group);
        showToast("Group created");
      }
      closeModals();
      renderGroupTabs();
      renderConversations();
    } catch (error) { showToast(error.message, "error"); }
  });
  function openManageGroups(){
    manageGroupsModal.classList.add("open");
    manageGroupsModal.setAttribute("aria-hidden","false");
    renderManageGroups();
  }
  manageAddGroupBtn.addEventListener("click", () => { closeModals(); openGroupModal(); });
  function renderManageGroups(){
    manageGroupsList.innerHTML = "";
    state.groups.forEach((g) => {
      const item = document.createElement("div");
      item.className = "manage-group-item";
      item.innerHTML = `<span class="manage-group-dot" style="background:${g.color}"></span><span style="flex:1">${escapeHtml(g.name)}</span><button class="icon-btn" data-edit><svg class="icon"><use href="#i-edit"></use></svg></button><button class="icon-btn" data-delete><svg class="icon"><use href="#i-trash"></use></svg></button>`;
      item.querySelector("[data-edit]").addEventListener("click", () => { closeModals(); openGroupModal(g); });
      item.querySelector("[data-delete]").addEventListener("click", async () => {
        if (!confirm(`Delete "${g.name}"? Conversations in this group will become unassigned.`)) return;
        try {
          await request("DELETE", api.group(g.id));
          state.groups = state.groups.filter((x)=>x.id!==g.id);
          state.conversations.forEach((c)=>{ if (c.group_id===g.id) c.group_id=null; });
          closeModals();
          renderGroupTabs();
          renderConversations();
          showToast("Group deleted");
        } catch (error) { showToast(error.message, "error"); }
      });
      manageGroupsList.appendChild(item);
    });
  }
  function renderGroupTabs(){
    groupTabs.innerHTML = "";
    const all = document.createElement("button");
    all.className = "group-tab" + (!state.activeGroupId || state.activeGroupId==="all" ? " active" : "");
    all.dataset.groupId = "all";
    all.innerHTML = `<span class="group-dot" style="background:rgba(148,163,255,0.8)"></span><span>All</span>`;
    groupTabs.appendChild(all);
    state.groups.forEach((g) => {
      const tab = document.createElement("button");
      tab.className = "group-tab" + (String(state.activeGroupId)===String(g.id)?" active":"");
      tab.dataset.groupId = g.id;
      tab.innerHTML = `<span class="group-dot" style="background:${g.color}"></span><span>${escapeHtml(g.name)}</span>`;
      groupTabs.appendChild(tab);
    });
    renderConversations();
  }

  notifyBtn.addEventListener("click", async () => {
    if (!("Notification" in window)) { showToast("Notifications not supported in this browser.", "error"); return; }
    let permission = Notification.permission;
    if (permission !== "granted") permission = await Notification.requestPermission();
    if (permission === "granted") { notifyStatus.textContent = "Alerts enabled"; showToast("Desktop alerts enabled"); scheduleAlerts(); }
    else { notifyStatus.textContent = "Permission denied"; showToast("Enable notifications in your browser settings.", "error"); }
  });
  function scheduleAlerts(){
    if (!("Notification" in window) || Notification.permission !== "granted") return;
    state.reminders.forEach((r) => {
      if (r.completed) return;
      const due = new Date(r.due_at.replace("T"," ") + ":00").getTime();
      const now = Date.now();
      if (due > now && due - now < 3600000) {
        window.setTimeout(() => new Notification("TeachAI reminder", { body: r.title, tag: "teachai-" + r.id }), due - now);
      }
    });
  }

  document.getElementById("new-chat-btn").addEventListener("keydown", (e) => { if (e.key === "n" || e.key === "N") { e.preventDefault(); startNewConversation(); } });

  async function bootstrap(){
    try {
      const data = await request("GET", api.bootstrap);
      state.user = data.user;
      state.ai = data.ai;
      updateAIStatus(data.ai.configured, data.ai.model);
      state.groups = data.groups;
      state.conversations = data.conversations.map((c)=>({...c}));
      state.reminders = data.reminders.map((r)=>({...r}));
      document.getElementById("sidebar-user-name").textContent = state.user.name;
      document.getElementById("sidebar-user-email").textContent = state.user.email;
      document.getElementById("sidebar-user-avatar").textContent = state.user.name[0].toUpperCase();
      renderGroupTabs();
      renderConversations();
      renderReminders();
      renderCalendar();
      renderNextReminder();
      initVoice();
    } catch (error) {
      if (error.message.includes("log in")) window.location.href = "/login";
      else showToast(error.message, "error");
    }
  }

  bootstrap();
})();
