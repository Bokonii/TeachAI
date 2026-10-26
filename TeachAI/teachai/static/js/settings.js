(function () {
  "use strict";

  const csrf = document.querySelector('meta[name="csrf-token"]')?.content || "";
  const provider = document.getElementById("provider");
  const baseUrl = document.getElementById("base_url");
  const model = document.getElementById("model");
  const testBtn = document.getElementById("test-ai-btn");
  const testResult = document.getElementById("test-result");

  const presets = {
    openai: { base: "https://api.openai.com/v1", model: "gpt-4o-mini" },
    gemini: { base: "https://generativelanguage.googleapis.com/v1beta/openai", model: "gemini-2.5-flash" },
    groq: { base: "https://api.groq.com/openai/v1", model: "llama-3.3-70b-versatile" },
    openrouter: { base: "https://openrouter.ai/api/v1", model: "openai/gpt-4o-mini" },
    ollama: { base: "http://localhost:11434/v1", model: "llama3.2" },
    custom: { base: "", model: "" }
  };

  function applyPreset() {
    const key = provider.value;
    const preset = presets[key];
    if (!preset) return;
    if (key !== "custom") {
      if (!baseUrl.value || baseUrl.dataset.dirty !== "true") baseUrl.value = preset.base;
      if (!model.value || model.dataset.dirty !== "true") model.value = preset.model;
    }
  }

  provider.addEventListener("change", applyPreset);
  baseUrl.addEventListener("input", () => baseUrl.dataset.dirty = "true");
  model.addEventListener("input", () => model.dataset.dirty = "true");
  applyPreset();

  testBtn.addEventListener("click", async () => {
    testBtn.disabled = true;
    testResult.textContent = "Testing connection…";
    try {
      const response = await fetch("/api/settings/ai/test", {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-CSRF-Token": csrf },
        body: JSON.stringify({})
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.error || "Test failed");
      testResult.textContent = "✓ " + (data.reply || "Connection OK");
      testResult.style.color = "#22d3ee";
    } catch (error) {
      testResult.textContent = "✗ " + error.message;
      testResult.style.color = "#f87171";
    } finally {
      testBtn.disabled = false;
    }
  });
})();
