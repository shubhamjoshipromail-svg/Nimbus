const compactWidget = document.getElementById("compactWidget");
const compactUnreadDot = document.getElementById("compactUnreadDot");
const compactSurfaceBubble = document.getElementById("compactSurfaceBubble");
const expandedWindow = document.getElementById("expandedWindow");
const collapseButton = document.getElementById("collapseButton");
const heroAvatarWrap = document.getElementById("heroAvatarWrap");
const heroStatus = document.getElementById("heroStatus");
const chatMessages = document.getElementById("chatMessages");
const chatForm = document.getElementById("chatForm");
const messageInput = document.getElementById("messageInput");
const micHintButton = document.getElementById("micHintButton");
const sendButton = document.getElementById("sendButton");
const contextPeekButton = document.getElementById("contextPeekButton");
const contextPeekCard = document.getElementById("contextPeekCard");
const contextPeekList = document.getElementById("contextPeekList");
const isAppMode = new URLSearchParams(window.location.search).get("mode") === "app";

if (isAppMode) {
  document.body.classList.add("app-mode");
  document.body.classList.add("app-collapsed");
}

const APP_WINDOW_LAYOUT = {
  collapsed: { width: 130, height: 150, x: 1750, y: 100 },
  expanded: { width: 440, height: 680, x: 1450, y: 100 },
};

const AVATAR_STATES = [
  "avatar-state-idle",
  "avatar-state-listening",
  "avatar-state-thinking",
  "avatar-state-talking",
  "avatar-state-caring",
  "avatar-state-celebrating",
  "avatar-state-sleeping",
];

const PLACEHOLDERS = [
  "tell Nimbus what's up…",
  "what's on your mind?",
  "how's it going?",
];

const QUICK_ACTION_ICONS = {
  calendar: "🗓",
  music: "🎧",
  mail: "✉",
  rest: "☁",
  priorities: "⏳",
  moon: "🌙",
};

let contextSummary = "";
let openingSequencePlayed = false;
let isThinking = false;
let totalMessageCount = 0;
let lastReadMessageCount = 0;
let placeholderIndex = 0;
let placeholderTimer = null;
let blinkTimer = null;
let sleepTimer = null;
let celebrationTimer = null;
let avatarState = "idle";

function setAvatarState(state) {
  avatarState = state;
  [compactWidget, heroAvatarWrap].forEach((node) => {
    AVATAR_STATES.forEach((className) => node.classList.remove(className));
    node.classList.add(`avatar-state-${state}`);
  });
}

function scheduleState(state, duration = 1000, fallback = "idle") {
  window.clearTimeout(celebrationTimer);
  setAvatarState(state);
  celebrationTimer = window.setTimeout(() => {
    if (!isThinking) {
      setAvatarState(fallback);
    }
  }, duration);
}

function resetSleepTimer() {
  window.clearTimeout(sleepTimer);
  if (!expandedWindow.classList.contains("hidden")) {
    sleepTimer = window.setTimeout(() => {
      if (!isThinking) {
        heroStatus.textContent = "resting until you need me";
        setAvatarState("sleeping");
      }
    }, 120000);
  }
}

function scheduleBlink() {
  window.clearTimeout(blinkTimer);
  const delay = 3000 + Math.random() * 2000;
  blinkTimer = window.setTimeout(() => {
    if (avatarState !== "sleeping") {
      [compactWidget, heroAvatarWrap].forEach((node) => {
        node.classList.add("is-blinking");
        window.setTimeout(() => node.classList.remove("is-blinking"), 180);
      });
    }
    scheduleBlink();
  }, delay);
}

function rotatePlaceholder() {
  placeholderTimer = window.setInterval(() => {
    if (document.activeElement !== messageInput && !messageInput.value.trim()) {
      placeholderIndex = (placeholderIndex + 1) % PLACEHOLDERS.length;
      messageInput.placeholder = PLACEHOLDERS[placeholderIndex];
    }
  }, 3200);
}

function autoResizeInput() {
  messageInput.style.height = "34px";
  messageInput.style.height = `${Math.min(messageInput.scrollHeight, 120)}px`;
}

function scrollToBottom() {
  chatMessages.scrollTop = chatMessages.scrollHeight;
}

function escapeHtml(text) {
  return text
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;");
}

function renderMarkdown(text) {
  let html = escapeHtml(text);
  html = html.replace(/\*\*(.+?)\*\*/gs, "<strong>$1</strong>");
  html = html.replace(/\*(.+?)\*/gs, "<em>$1</em>");
  html = html.replace(/\n/g, "<br>");
  return html;
}

function stripMarkdown(text) {
  return text.replace(/\*\*/g, "").replace(/\*/g, "");
}

function extractContextLine(label) {
  const line = contextSummary
    .split("\n")
    .find((entry) => entry.startsWith(`${label}:`));
  return line ? line.replace(`${label}:`, "").trim() : "";
}

function parseContextInsights() {
  const state = extractContextLine("CURRENT STATE");
  const sleep = extractContextLine("LAST 7 DAYS SLEEP");
  const deadlines = extractContextLine("UPCOMING DEADLINES (next 7 days)");

  return [
    state || "Sleep is slipping and late-night screen time is rising.",
    sleep
      ? `Last nights: ${sleep.split(";").slice(-3).join(";").trim()}`
      : "The last few nights have been running late.",
    deadlines === "None in the next 7 days."
      ? "No immediate deadlines, but the week is still heavy."
      : "Three deadlines are clustering Thursday and Friday.",
  ];
}

function parseUpcomingPrioritiesFromContext() {
  const line = extractContextLine("UPCOMING DEADLINES (next 7 days)");
  if (!line || line === "None in the next 7 days.") {
    return [];
  }

  return line
    .split(";")
    .map((entry) => entry.trim())
    .filter(Boolean)
    .slice(0, 3)
    .map((entry, index) => {
      const match = entry.match(/^(\d{4}-\d{2}-\d{2}).*?:\s*(.+)$/);
      const date = match ? match[1] : "2026-04-17";
      const title = match ? match[2] : entry;
      return {
        title,
        start: `${date}T12:00:00`,
        urgency_score: Math.max(8 - index, 6),
      };
    });
}

function updateContextPeek() {
  contextPeekList.innerHTML = "";
  parseContextInsights().forEach((line) => {
    const item = document.createElement("li");
    item.textContent = line;
    contextPeekList.appendChild(item);
  });
}

function buildOpeningMessage() {
  return "Hey Maya. How's it going? Are you managing okay right now, or does the week feel like a lot?";
}

function buildOpeningQuickActions() {
  return [
    { label: "It's a lot", prompt: "it's a lot", icon: "rest", primary: true },
    { label: "I'm okay", prompt: "i'm okay", icon: "priorities" },
  ];
}

function updateUnreadIndicator() {
  if (isAppMode) {
    compactUnreadDot.classList.add("hidden");
    compactSurfaceBubble.classList.add("hidden");
    return;
  }
  const unread = totalMessageCount > lastReadMessageCount && expandedWindow.classList.contains("hidden");
  compactUnreadDot.classList.toggle("hidden", !unread);
  compactSurfaceBubble.classList.toggle("hidden", openingSequencePlayed);
}

function mergeQuickActions(primary = [], secondary = []) {
  const combined = [...primary];
  secondary.forEach((action) => {
    if (!combined.some((item) => item.label === action.label && item.prompt === action.prompt)) {
      combined.push(action);
    }
  });
  return combined.slice(0, 4);
}

function setHeroStatus(text) {
  heroStatus.textContent = text;
}

function markMessagesRead() {
  lastReadMessageCount = totalMessageCount;
  updateUnreadIndicator();
}

function createMessageStack(role) {
  const row = document.createElement("div");
  row.className = `message-row ${role}`;
  const stack = document.createElement("div");
  stack.className = "message-stack";
  row.appendChild(stack);
  chatMessages.appendChild(row);
  totalMessageCount += 1;
  if (!expandedWindow.classList.contains("hidden")) {
    markMessagesRead();
  } else {
    updateUnreadIndicator();
  }
  scrollToBottom();
  return { row, stack };
}

function createMessageRow(role) {
  const { row, stack } = createMessageStack(role);
  const bubble = document.createElement("div");
  bubble.className = "message-bubble";
  stack.appendChild(bubble);
  return { row, stack, bubble };
}

function addUserMessage(text) {
  const { bubble } = createMessageRow("user");
  bubble.textContent = text;
}

function addThinkingMessage() {
  const { row, bubble } = createMessageRow("agent");
  bubble.classList.add("thinking-bubble");
  bubble.textContent = "Nimbus is thinking...";
  return row;
}

async function typeAgentMessage(text, stack = null, options = {}) {
  const messageStack = stack || createMessageStack("agent").stack;
  const bubble = document.createElement("div");
  bubble.className = "message-bubble";
  messageStack.appendChild(bubble);
  const plainText = stripMarkdown(text);
  const caring = options.forceCaring || /sleep|deadline|fumes|burnout|not fine|running on coffee/i.test(text);
  const charDelay = options.charDelay || 20;
  setAvatarState("talking");
  setHeroStatus(caring ? "noticed something — tap to chat" : "here with you");

  for (let index = 0; index <= plainText.length; index += 1) {
    bubble.textContent = plainText.slice(0, index);
    bubble.innerHTML = `${escapeHtml(plainText.slice(0, index))}<span class="typing-cursor">|</span>`;
    scrollToBottom();
    // Character pacing keeps Nimbus feeling alive without dragging.
    // eslint-disable-next-line no-await-in-loop
    await new Promise((resolve) => window.setTimeout(resolve, charDelay));
  }

  bubble.innerHTML = renderMarkdown(text);
  setAvatarState(caring ? "caring" : "idle");
  resetSleepTimer();
  return messageStack;
}

function copyText(text, button) {
  navigator.clipboard.writeText(text).then(() => {
    const previous = button.textContent;
    button.textContent = "Copied";
    window.setTimeout(() => {
      button.textContent = previous;
    }, 1200);
  });
}

function parsePriorityTone(item) {
  const urgency = item.urgency_score || 0;
  if (urgency >= 8) {
    return "urgent";
  }
  if (urgency >= 5) {
    return "medium";
  }
  return "low";
}

function extractContextMetrics() {
  const sleepLine = extractContextLine("LAST 7 DAYS SLEEP");
  const loadLine = extractContextLine("LAST 7 DAYS LOAD CHECK-INS");
  const screenLine = extractContextLine("SCREEN TIME SHIFT");

  const sleepHours = [...sleepLine.matchAll(/(\d+\.\d+)h/g)].map((match) => Number(match[1]));
  const loadValues = [...loadLine.matchAll(/load (\d+)/g)].map((match) => Number(match[1]));
  const totalScreenMatch = screenLine.match(/Last 7 days average (\d+\.\d+)h total vs baseline (\d+\.\d+)h/);
  const lateScreenMatch = screenLine.match(/late-night (\d+\.\d+)h vs (\d+\.\d+)h baseline/);

  const averageSleep = sleepHours.length
    ? sleepHours.reduce((sum, value) => sum + value, 0) / sleepHours.length
    : 5.1;
  const averageLoad = loadValues.length
    ? loadValues.reduce((sum, value) => sum + value, 0) / loadValues.length
    : 3.4;

  return {
    sleepRatio: Math.min((7.4 - averageSleep) / 3, 1),
    loadRatio: Math.min((averageLoad - 2) / 2, 1),
    screenRatio: totalScreenMatch && lateScreenMatch
      ? Math.min((Number(lateScreenMatch[1]) - Number(lateScreenMatch[2])) / 2.5, 1)
      : 0.8,
  };
}

function quickActionIcon(icon) {
  return QUICK_ACTION_ICONS[icon] || icon || "✦";
}

function appendToolCard(toolName, toolResult, stack) {
  const card = document.createElement("div");
  const lowerName = toolName.toLowerCase();
  card.className = "tool-card";

  if (lowerName === "block_calendar_time") {
    card.classList.add("calendar-card");
    const timeMatch = String(toolResult).match(/starting at ([^ ]+)/i);
    const durationMatch = String(toolResult).match(/Blocked (\d+) minutes/i);
    card.innerHTML = `
      <div class="tool-header">
        <div class="tool-icon-badge">🗓</div>
        <div class="tool-title-wrap">
          <p class="tool-label">Calendar block</p>
          <p class="tool-copy">Blocked ${durationMatch ? durationMatch[1] : "25"} min — ${timeMatch ? timeMatch[1] : "now"}</p>
        </div>
        <div class="check-badge">✓</div>
      </div>
    `;
  } else if (lowerName === "open_resource") {
    card.classList.add("resource-card");
    const resourceName = toolResult.resource_type
      ? toolResult.resource_type.replaceAll("_", " ")
      : "resource";
    card.innerHTML = `
      <div class="tool-header">
        <div class="tool-icon-badge">▶</div>
        <div class="tool-title-wrap">
          <p class="tool-label">Resource opened</p>
          <p class="tool-copy">${resourceName}</p>
        </div>
      </div>
      <a class="resource-link" href="${toolResult.url}" target="_blank" rel="noreferrer">Listen ↗</a>
    `;
  } else if (lowerName === "draft_message") {
    card.classList.add("draft-card");
    if (toolResult && typeof toolResult === "object" && toolResult.to && toolResult.subject) {
      const emailBody = String(toolResult.body || "");
      card.innerHTML = `
        <div class="tool-header">
          <div class="tool-icon-badge">✉</div>
          <div class="tool-title-wrap">
            <p class="tool-label">Extension draft</p>
            <p class="tool-copy">Ready to send to Professor Chen.</p>
          </div>
          <div class="sent-badge hidden">Sent ✓</div>
        </div>
        <div class="email-meta">
          <p><strong>To:</strong> ${escapeHtml(toolResult.to)}</p>
          <p><strong>Subject:</strong> ${escapeHtml(toolResult.subject)}</p>
        </div>
        <div class="draft-preview expanded">${renderMarkdown(emailBody)}</div>
        <div class="draft-actions"></div>
      `;
      const actionsWrap = card.querySelector(".draft-actions");
      (toolResult.action_buttons || []).forEach((action) => {
        const button = document.createElement("button");
        button.type = "button";
        button.className = `mini-button ${action.kind === "primary" ? "primary" : ""}`;
        button.textContent = action.label;
        button.addEventListener("click", async () => {
          handleActivity();
          if ((action.label || "").toLowerCase() === "edit") {
            await renderAgentResponse(
              "You can tweak the middle line later if you want, but this version already asks early and clearly.",
              [],
              [],
              [],
              { forceCaring: true, suppressCelebrate: true }
            );
            return;
          }
          if ((action.label || "").toLowerCase() === "send") {
            card.classList.add("sent");
            card.querySelectorAll(".mini-button").forEach((node) => {
              node.disabled = true;
            });
            button.textContent = "Sent ✓";
            card.querySelector(".sent-badge").classList.remove("hidden");
            await new Promise((resolve) => window.setTimeout(resolve, 450));
            await waitForAgentIdle();
            await requestAgent(action.prompt || action.label || "", action.next_stage || null, { skipUserBubble: true });
          }
        });
        actionsWrap.appendChild(button);
      });
    } else {
      const draftText = String(toolResult);
      card.innerHTML = `
        <div class="tool-header">
          <div class="tool-icon-badge">✉</div>
          <div class="tool-title-wrap">
            <p class="tool-label">Message drafted</p>
            <p class="tool-copy">Ready to copy and send.</p>
          </div>
        </div>
        <div class="draft-preview">${escapeHtml(draftText)}</div>
        <div class="draft-actions">
          <button class="mini-button draft-toggle" type="button">Expand</button>
          <button class="mini-button draft-copy" type="button">Copy</button>
        </div>
      `;
      const preview = card.querySelector(".draft-preview");
      card.querySelector(".draft-toggle").addEventListener("click", () => {
        const expanded = preview.classList.toggle("expanded");
        card.querySelector(".draft-toggle").textContent = expanded ? "Collapse" : "Expand";
      });
      card.querySelector(".draft-copy").addEventListener("click", (event) => {
        copyText(draftText, event.currentTarget);
      });
    }
  } else if (lowerName === "analyze_current_state") {
    const metrics = extractContextMetrics();
    card.classList.add("analysis-card");
    card.innerHTML = `
      <div class="tool-header">
        <div class="tool-icon-badge">◫</div>
        <div class="tool-title-wrap">
          <p class="tool-label">State analysis</p>
          <p class="tool-copy">Quick read against Maya's baseline.</p>
        </div>
      </div>
      <div class="analysis-bars">
        <div class="analysis-row">
          <span>Sleep</span>
          <div class="analysis-track"><div class="analysis-fill" style="width:${Math.round(metrics.sleepRatio * 100)}%"></div></div>
          <span>low</span>
        </div>
        <div class="analysis-row">
          <span>Load</span>
          <div class="analysis-track"><div class="analysis-fill" style="width:${Math.round(metrics.loadRatio * 100)}%"></div></div>
          <span>high</span>
        </div>
        <div class="analysis-row">
          <span>Screen</span>
          <div class="analysis-track"><div class="analysis-fill" style="width:${Math.round(metrics.screenRatio * 100)}%"></div></div>
          <span>late</span>
        </div>
      </div>
    `;
  } else if (lowerName === "get_upcoming_priorities") {
    card.classList.add("priority-card");
    const items = Array.isArray(toolResult) ? toolResult.slice(0, 3) : [];
    const today = new Date("2026-04-17T09:00:00");
    const pills = items
      .map((item) => {
        const start = new Date(item.start);
        const daysUntil = Math.max(Math.ceil((start - today) / (1000 * 60 * 60 * 24)), 0);
        return `<span class="priority-pill ${parsePriorityTone(item)}">${daysUntil}d · ${item.title}</span>`;
      })
      .join("");
    card.innerHTML = `
      <div class="tool-header">
        <div class="tool-icon-badge">⏳</div>
        <div class="tool-title-wrap">
          <p class="tool-label">Priorities</p>
          <p class="tool-copy">Top things closing in first.</p>
        </div>
      </div>
      <div class="priority-pills">${pills}</div>
    `;
  } else if (lowerName === "calendar_watcher") {
    card.classList.add("calendar-card", "watcher-card");
    card.innerHTML = `
      <div class="tool-header">
        <div class="tool-icon-badge">📅</div>
        <div class="tool-title-wrap">
          <p class="tool-label">Calendar watcher armed</p>
          <p class="tool-copy">${escapeHtml(toolResult.message || "Will update on reply.")}</p>
        </div>
      </div>
    `;
  } else if (lowerName === "notifications_silenced") {
    card.classList.add("silence-card");
    card.innerHTML = `
      <div class="tool-header">
        <div class="tool-icon-badge">🌙</div>
        <div class="tool-title-wrap">
          <p class="tool-label">Notifications silenced</p>
          <p class="tool-copy">${escapeHtml(toolResult.message || "Notifications silenced until 7am")}</p>
        </div>
      </div>
    `;
  } else if (lowerName === "celebration") {
    card.classList.add("celebration-card");
    card.innerHTML = `
      <div class="tool-header">
        <div class="tool-icon-badge">🎉</div>
        <div class="tool-title-wrap">
          <p class="tool-label">Task complete</p>
          <p class="tool-copy">${escapeHtml(toolResult.message || "One thing is off your plate.")}</p>
        </div>
      </div>
      <div class="celebration-sparkles" aria-hidden="true">
        <span></span><span></span><span></span><span></span>
      </div>
    `;
  } else if (lowerName === "music_player") {
    card.classList.add("resource-card", "music-player-card");
    card.innerHTML = `
      <div class="tool-header">
        <div class="tool-icon-badge">🎶</div>
        <div class="tool-title-wrap">
          <p class="tool-label">${escapeHtml(toolResult.title || "Momentum music")}</p>
          <p class="tool-copy">${escapeHtml(toolResult.message || "Queued for the home stretch.")}</p>
        </div>
      </div>
      <a class="resource-link" href="${toolResult.url}" target="_blank" rel="noreferrer">Play ↗</a>
    `;
  }

  if (!card.innerHTML) {
    card.innerHTML = `
      <div class="tool-header">
        <div class="tool-icon-badge">✦</div>
        <div class="tool-title-wrap">
          <p class="tool-label">${toolName}</p>
          <p class="tool-copy">${escapeHtml(JSON.stringify(toolResult))}</p>
        </div>
      </div>
    `;
  }

  stack.appendChild(card);
  scrollToBottom();
}

function normalizeToolResult(toolName, toolResult) {
  if (toolName === "open_resource" && typeof toolResult === "string") {
    return { resource_type: "resource", url: toolResult, message: toolResult };
  }
  return toolResult;
}

let breathingAudioContext = null;

function getBreathingAudioContext() {
  if (breathingAudioContext) {
    return breathingAudioContext;
  }

  const AudioCtor = window.AudioContext || window.webkitAudioContext;
  if (!AudioCtor) {
    return null;
  }

  try {
    breathingAudioContext = new AudioCtor();
    return breathingAudioContext;
  } catch (error) {
    return null;
  }
}

async function safeResumeAudio(audioCtx) {
  if (!audioCtx || typeof audioCtx.resume !== "function") {
    return;
  }
  try {
    if (audioCtx.state === "suspended") {
      await audioCtx.resume();
    }
  } catch (error) {
    // Audio can be blocked; visuals should keep working.
  }
}

function playPhaseChime(audioCtx, activeNodes) {
  if (!audioCtx) {
    return;
  }
  try {
    const osc = audioCtx.createOscillator();
    const gain = audioCtx.createGain();
    const start = audioCtx.currentTime;
    osc.type = "sine";
    osc.frequency.value = 440;
    gain.gain.setValueAtTime(0, start);
    gain.gain.linearRampToValueAtTime(0.1, start + 0.01);
    gain.gain.exponentialRampToValueAtTime(0.001, start + 0.1);
    osc.connect(gain);
    gain.connect(audioCtx.destination);
    osc.start(start);
    osc.stop(start + 0.1);
    activeNodes.push({ osc, gain });
  } catch (error) {
    // Ignore audio failures and keep the breathing card alive.
  }
}

function playBreathTone(audioCtx, activeNodes, startFreq, endFreq, duration = 4) {
  if (!audioCtx) {
    return;
  }
  try {
    const osc = audioCtx.createOscillator();
    const gain = audioCtx.createGain();
    const start = audioCtx.currentTime;
    osc.type = "sine";
    osc.frequency.setValueAtTime(startFreq, start);
    osc.frequency.linearRampToValueAtTime(endFreq, start + duration);
    gain.gain.setValueAtTime(0.001, start);
    gain.gain.linearRampToValueAtTime(0.15, start + duration / 2);
    gain.gain.linearRampToValueAtTime(0.001, start + duration);
    osc.connect(gain);
    gain.connect(audioCtx.destination);
    osc.start(start);
    osc.stop(start + duration);
    activeNodes.push({ osc, gain });
  } catch (error) {
    // Ignore audio failures and keep the breathing card alive.
  }
}

function stopBreathingAudio(activeNodes) {
  activeNodes.splice(0).forEach(({ osc, gain }) => {
    try {
      gain.disconnect();
    } catch (error) {
      // noop
    }
    try {
      osc.stop();
    } catch (error) {
      // noop
    }
    try {
      osc.disconnect();
    } catch (error) {
      // noop
    }
  });
}

function createBreathingCard(toolResult, stack, onComplete = null) {
  const duration = Number(toolResult.duration_seconds || 60);
  const totalCycles = Math.max(1, Math.ceil(duration / 16));
  const continueAction = toolResult.continue_action || null;
  const phaseCueTimers = [];
  const card = document.createElement("div");
  card.className = "tool-card breathing-card";
  card.innerHTML = `
    <div class="breathing-card-inner">
      <div class="breathing-cycle-counter">Cycle 1 of ${totalCycles}</div>
      <div class="breathing-orb-wrap">
        <div class="breathing-orb"></div>
        <div class="breathing-phase is-active">Breathe in slowly...</div>
      </div>
      <p class="breathing-helper">Follow Nimbus's rhythm</p>
      <div class="breathing-actions">
        <button class="mini-button breathing-done" type="button">I'm done</button>
        <button class="mini-button primary breathing-continue hidden" type="button">I'm ready →</button>
      </div>
    </div>
  `;
  stack.appendChild(card);
  scrollToBottom();
  card.scrollIntoView({ behavior: "smooth", block: "center" });
  setAvatarState("caring");
  setHeroStatus("here with you");

  const phaseNode = card.querySelector(".breathing-phase");
  const counterNode = card.querySelector(".breathing-cycle-counter");
  const phases = [
    { label: "Breathe in slowly...", kind: "inhale" },
    { label: "Hold...", kind: "hold" },
    { label: "Breathe out gently...", kind: "exhale" },
    { label: "Hold...", kind: "hold" },
  ];
  let phaseIndex = 0;
  let currentCycle = 1;
  let finished = false;
  const activeAudioNodes = [];
  const audioCtx = getBreathingAudioContext();
  const doneButton = card.querySelector(".breathing-done");
  const continueButton = card.querySelector(".breathing-continue");

  const applyPhase = async () => {
    const phase = phases[phaseIndex];
    phaseNode.classList.remove("is-active", "is-hold");
    phaseNode.classList.add(phase.kind === "hold" ? "is-hold" : "is-active");
    phaseNode.classList.add("is-fading");
    window.setTimeout(() => {
      phaseNode.textContent = phase.label;
      phaseNode.classList.remove("is-fading");
    }, 150);

    if (counterNode) {
      counterNode.textContent = `Cycle ${currentCycle} of ${totalCycles}`;
    }

    await safeResumeAudio(audioCtx);
    if (audioCtx) {
      playPhaseChime(audioCtx, activeAudioNodes);
      if (phase.kind === "inhale") {
        phaseCueTimers.push(window.setTimeout(() => {
          playBreathTone(audioCtx, activeAudioNodes, 200, 280, 4);
        }, 100));
      } else if (phase.kind === "exhale") {
        phaseCueTimers.push(window.setTimeout(() => {
          playBreathTone(audioCtx, activeAudioNodes, 280, 200, 4);
        }, 100));
      }
    }
  };

  applyPhase();

  const finishExercise = async () => {
    if (finished) {
      return;
    }
    finished = true;
    window.clearInterval(interval);
    window.clearTimeout(stopTimer);
    phaseCueTimers.splice(0).forEach((timer) => window.clearTimeout(timer));
    stopBreathingAudio(activeAudioNodes);
    if (continueAction) {
      phaseNode.classList.remove("is-active", "is-hold", "is-fading");
      phaseNode.textContent = "Nice. Take one more second.";
      doneButton.classList.add("hidden");
      continueButton.classList.remove("hidden");
      card.classList.add("is-complete");
      setHeroStatus("take your time");
      return;
    }
    card.remove();
    if (typeof onComplete === "function") {
      await onComplete();
    }
  };

  const interval = window.setInterval(() => {
    phaseIndex = (phaseIndex + 1) % phases.length;
    if (phaseIndex === 0) {
      currentCycle = Math.min(totalCycles, currentCycle + 1);
    }
    applyPhase();
  }, 4000);

  const stopTimer = window.setTimeout(() => {
    finishExercise();
  }, duration * 1000);

  doneButton.addEventListener("click", async () => {
    await finishExercise();
  });

  continueButton.addEventListener("click", async () => {
    card.remove();
    if (continueAction) {
      await requestAgent(continueAction.prompt || continueAction.label || "", continueAction.next_stage || null, { skipUserBubble: true });
      return;
    }
    if (typeof onComplete === "function") {
      await onComplete();
    }
  });
}

async function appendToolArtifact(toolName, toolResult, stack, deferredFollowup = null, toolDelay = 220) {
  const lowerName = toolName.toLowerCase();
  const normalizedResult = normalizeToolResult(toolName, toolResult);

  if (normalizedResult && Array.isArray(normalizedResult.steps)) {
    let nestedQuickActions = Array.isArray(normalizedResult.quick_actions) ? normalizedResult.quick_actions : [];
    let deferFollowup = false;
    for (const step of normalizedResult.steps) {
      const extras = await appendToolArtifact(step.tool_name, step.result, stack, deferredFollowup, toolDelay);
      nestedQuickActions = mergeQuickActions(nestedQuickActions, extras.quickActions || []);
      deferFollowup = deferFollowup || Boolean(extras.deferFollowup);
      await new Promise((resolve) => window.setTimeout(resolve, toolDelay));
    }
    return { quickActions: nestedQuickActions, deferFollowup };
  }

  if (lowerName === "start_breathing_exercise") {
    createBreathingCard(normalizedResult, stack, deferredFollowup);
    return { quickActions: [], deferFollowup: true };
  }

  appendToolCard(toolName, normalizedResult, stack);
  return { quickActions: [], deferFollowup: false };
}

function appendQuickActions(actions, stack) {
  if (!Array.isArray(actions) || actions.length === 0) {
    return;
  }

  const row = document.createElement("div");
  row.className = "quick-actions-row";
  actions.slice(0, 4).forEach((action) => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = `quick-action-button ${action.primary ? "quick-action-button-primary" : ""}`;
    button.innerHTML = `
      <span class="quick-action-icon">${escapeHtml(quickActionIcon(action.icon))}</span>
      <span>${escapeHtml(action.label || "Next")}</span>
    `;
    button.addEventListener("click", () => {
      handleActivity();
      sendMessage(action.prompt || action.label || "", action.next_stage || null);
    });
    row.appendChild(button);
  });
  stack.appendChild(row);
  scrollToBottom();
}

async function renderAgentResponse(responseText, toolsUsed = [], toolResults = [], quickActions = [], options = {}) {
  const { stack } = createMessageStack("agent");
  let resolvedQuickActions = [...quickActions];
  let shouldDeferFollowup = false;
  const deferredFollowup = async () => {
    await renderAgentResponse(responseText, [], [], resolvedQuickActions, options);
  };
  const toolDelay = options.toolDelay || 220;
  if (toolsUsed.length > 0) {
    for (let index = 0; index < toolsUsed.length; index += 1) {
      const artifactResult = await appendToolArtifact(toolsUsed[index], toolResults[index], stack, deferredFollowup, toolDelay);
      resolvedQuickActions = mergeQuickActions(resolvedQuickActions, artifactResult.quickActions || []);
      shouldDeferFollowup = shouldDeferFollowup || Boolean(artifactResult.deferFollowup);
      await new Promise((resolve) => window.setTimeout(resolve, toolDelay));
    }
  }

  if (shouldDeferFollowup) {
    setHeroStatus("here with you");
    markMessagesRead();
    return;
  }

  if (responseText && responseText.trim()) {
    await typeAgentMessage(responseText, stack, options);
  }

  if (resolvedQuickActions.length > 0) {
    await new Promise((resolve) => window.setTimeout(resolve, options.afterTextDelay || 300));
    appendQuickActions(resolvedQuickActions, stack);
  }

  if (options.celebrateAfterRender) {
    setHeroStatus("done ✓");
    scheduleState("celebrating", 1200, "idle");
  } else if (toolsUsed.length > 0 && !options.suppressCelebrate) {
    setHeroStatus("done ✓");
    scheduleState("celebrating", 1100, "idle");
  } else {
    setHeroStatus("here with you");
  }
  if (expandedWindow.classList.contains("hidden")) {
    updateUnreadIndicator();
  } else {
    markMessagesRead();
  }
}

async function runOpeningSequence() {
  if (openingSequencePlayed) {
    return;
  }

  openingSequencePlayed = true;
  compactSurfaceBubble.classList.add("hidden");
  heroAvatarWrap.classList.add("intro-pop");
  setHeroStatus("noticed something — tap to chat");
  setAvatarState("idle");
  await new Promise((resolve) => window.setTimeout(resolve, 400));
  setAvatarState("thinking");
  await new Promise((resolve) => window.setTimeout(resolve, 1600));
  const { stack } = createMessageStack("agent");
  await typeAgentMessage(buildOpeningMessage(), stack, { charDelay: 12, forceCaring: true });
  await new Promise((resolve) => window.setTimeout(resolve, 500));
  appendQuickActions(buildOpeningQuickActions(), stack);

  setAvatarState("caring");
  setHeroStatus("here with you");
}

function toggleContextPeek() {
  const expanded = contextPeekCard.classList.toggle("hidden");
  contextPeekButton.classList.toggle("expanded", !expanded);
}

function inferListeningState() {
  if (messageInput.value.trim().length > 0 && !isThinking) {
    setAvatarState("listening");
  } else if (!isThinking && avatarState !== "sleeping") {
    setAvatarState("idle");
  }
}

async function loadContext() {
  try {
    const response = await fetch("/context");
    const data = await response.json();
    contextSummary = data.summary || "";
  } catch (error) {
    contextSummary = "";
  }

  updateContextPeek();
}

function expandWidget() {
  if (isAppMode) {
    window.resizeTo(APP_WINDOW_LAYOUT.expanded.width, APP_WINDOW_LAYOUT.expanded.height);
    window.moveTo(APP_WINDOW_LAYOUT.expanded.x, APP_WINDOW_LAYOUT.expanded.y);
    document.body.classList.remove("app-collapsed");
    document.body.classList.add("app-expanded");
  }
  compactWidget.classList.add("hidden");
  expandedWindow.classList.remove("hidden");
  markMessagesRead();
  resetSleepTimer();
  runOpeningSequence();
  window.setTimeout(() => {
    messageInput.focus();
    autoResizeInput();
  }, 180);
}

function collapseWidget() {
  if (isAppMode) {
    expandedWindow.classList.add("hidden");
    compactWidget.classList.remove("hidden");
    document.body.classList.remove("app-expanded");
    document.body.classList.add("app-collapsed");
    window.resizeTo(APP_WINDOW_LAYOUT.collapsed.width, APP_WINDOW_LAYOUT.collapsed.height);
    window.moveTo(APP_WINDOW_LAYOUT.collapsed.x, APP_WINDOW_LAYOUT.collapsed.y);
    updateUnreadIndicator();
    return;
  }
  expandedWindow.classList.add("hidden");
  compactWidget.classList.remove("hidden");
  updateUnreadIndicator();
}

function setThinking(yes) {
  isThinking = yes;
  sendButton.disabled = yes;
  if (yes) {
    setHeroStatus("thinking...");
    setAvatarState("thinking");
  } else if (avatarState === "thinking") {
    setAvatarState("idle");
  }
}

async function fetchAgentResponse(message, nextStage = null) {
  const response = await fetch("/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message, next_stage: nextStage }),
  });

  if (!response.ok) {
    throw new Error(`Request failed with status ${response.status}`);
  }

  return response.json();
}

async function requestAgent(message, nextStage = null, options = {}) {
  if (!message.trim() || isThinking) {
    return;
  }

  if (!options.skipUserBubble) {
    addUserMessage(message.trim());
  }
  messageInput.value = "";
  autoResizeInput();
  sendButton.classList.add("bounce");
  window.setTimeout(() => sendButton.classList.remove("bounce"), 360);

  setThinking(true);
  const thinkingRow = addThinkingMessage();

  try {
    const data = await fetchAgentResponse(message, nextStage);
    thinkingRow.remove();
    await renderAgentResponse(
      data.response || "I had a thought and lost the wording for a second.",
      data.tools_used || [],
      data.tool_results || [],
      data.quick_actions || [],
      data.render_options || {}
    );
  } catch (error) {
    thinkingRow.remove();
    await renderAgentResponse(
      "The connection slipped for a second. Want me to try again, or keep this light for a minute?",
      [],
      [],
      []
    );
  } finally {
    setThinking(false);
    resetSleepTimer();
  }
}

async function sendMessage(message, nextStage = null) {
  await requestAgent(message, nextStage);
}

function handleActivity() {
  if (avatarState === "sleeping" && !isThinking) {
    setAvatarState("idle");
    setHeroStatus("here with you");
  }
  resetSleepTimer();
}

async function waitForAgentIdle(timeoutMs = 4000) {
  const startedAt = Date.now();
  while (isThinking && Date.now() - startedAt < timeoutMs) {
    // Let in-card actions wait for the current render cycle to finish.
    // eslint-disable-next-line no-await-in-loop
    await new Promise((resolve) => window.setTimeout(resolve, 60));
  }
}

compactWidget.addEventListener("click", () => {
  handleActivity();
  expandWidget();
});

heroAvatarWrap.addEventListener("click", () => {
  handleActivity();
  collapseWidget();
});

collapseButton.addEventListener("click", collapseWidget);
contextPeekButton.addEventListener("click", toggleContextPeek);
micHintButton.addEventListener("click", () => {
  handleActivity();
  setHeroStatus("voice coming soon");
  window.setTimeout(() => {
    if (!isThinking) {
      setHeroStatus("here with you");
    }
  }, 1400);
});

chatForm.addEventListener("submit", (event) => {
  event.preventDefault();
  sendMessage(messageInput.value);
});

messageInput.addEventListener("input", () => {
  autoResizeInput();
  handleActivity();
  inferListeningState();
});

messageInput.addEventListener("focus", () => {
  handleActivity();
  inferListeningState();
});

messageInput.addEventListener("blur", () => {
  if (!isThinking && avatarState !== "sleeping") {
    setAvatarState("idle");
  }
});

messageInput.addEventListener("keydown", (event) => {
  if (event.key === "Enter" && !event.shiftKey) {
    event.preventDefault();
    sendMessage(messageInput.value);
  }
});

["mousemove", "keydown", "click"].forEach((eventName) => {
  window.addEventListener(eventName, handleActivity, { passive: true });
});

window.addEventListener("load", async () => {
  await loadContext();
  rotatePlaceholder();
  scheduleBlink();
  updateUnreadIndicator();
  autoResizeInput();
  resetSleepTimer();
  if (isAppMode) {
    expandedWindow.classList.add("hidden");
    compactWidget.classList.remove("hidden");
    document.body.classList.remove("app-expanded");
    document.body.classList.add("app-collapsed");
    updateUnreadIndicator();
    window.resizeTo(APP_WINDOW_LAYOUT.collapsed.width, APP_WINDOW_LAYOUT.collapsed.height);
    window.moveTo(APP_WINDOW_LAYOUT.collapsed.x, APP_WINDOW_LAYOUT.collapsed.y);
  }
});
