(function () {
  "use strict";

  const flashData = document.getElementById("flash-data");
  const toastStack = document.getElementById("toast-stack");
  if (!toastStack) return;

  let messages = [];
  if (flashData && flashData.textContent.trim()) {
    try {
      messages = JSON.parse(flashData.textContent);
    } catch (error) {
      messages = [];
    }
  }

  messages.forEach((entry) => {
    const [category, text] = Array.isArray(entry) ? entry : ["info", String(entry)];
    const toast = document.createElement("div");
    toast.className = `toast ${category === "error" ? "error" : "success"}`;
    toast.innerHTML = `
      <span class="toast-dot"></span>
      <div class="toast-content">
        <strong>${category === "error" ? "Heads up" : "All set"}</strong>
        <span>${escapeHtml(text)}</span>
      </div>
    `;
    toastStack.appendChild(toast);
    window.setTimeout(() => {
      toast.classList.add("out");
      window.setTimeout(() => toast.remove(), 200);
    }, 3200);
  });

  function escapeHtml(value) {
    const div = document.createElement("div");
    div.textContent = value;
    return div.innerHTML;
  }

  document.addEventListener("click", (event) => {
    const toggle = event.target.closest("[data-toggle-password]");
    if (!toggle) return;
    const input = document.getElementById(toggle.dataset.togglePassword);
    if (!input) return;
    if (input.type === "password") {
      input.type = "text";
      toggle.textContent = "Hide";
    } else {
      input.type = "password";
      toggle.textContent = "Show";
    }
  });
})();
