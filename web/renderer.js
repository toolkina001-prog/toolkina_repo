const TEXT = {
  EN: {
    play: "Continue playing", levels: "Choose a level", settings: "Settings", exit: "Exit",
    completed: "Levels completed", campaign: "The campaign", pickLevel: "Pick up where you left off",
    back: "Back", level: "Level {number}", colors: "{count} colors", moves: "Moves",
    time: "Time", collected: "Sorted bottles", undo: "Undo", restart: "Restart",
    hint: "Hint", check: "Check solution", menu: "Main menu", previous: "Previous",
    next: "Next", solved: "Puzzle solved — beautifully done!", dead: "No legal moves left. Restart this level to try again.",
    hintMove: "Try pouring bottle {source} into bottle {target}.", noHint: "No solution was found for this position.",
    hintLimit: "You have used all three hints for this level.", solutionFound: "A solution exists in {count} moves.",
    solutionMissing: "No solution found within the search time limit.", tutorial: "Level guide",
    settingsTitle: "Make it yours", sound: "Sound effects", soundInfo: "Soft feedback for moves and wins",
    music: "Ambient music", musicInfo: "A cheerful, gentle melody while you play", patterns: "Color patterns",
    patternsInfo: "Add texture so liquids are easier to tell apart", language: "Language",
    save: "Save settings", reset: "Reset progress", resetConfirm: "Reset completed levels? Your caps will be kept.",
    progressError: "Could not load saved progress: {error}", progressSaved: "Settings saved.",
    progressReset: "Progress cleared. Caps were kept.", openLevel: "Open level {number}", bottles: "bottles",
    caps: "Caps", capsEarned: "Earned {count} caps!",
    mechanic_decoy_bottle: "Decoy bottle", mechanic_capacity_5: "Capacity 5", mechanic_giant_bottle_3x: "Giant bottle",
    mechanic_hidden_colors: "Hidden colors", mechanic_stone_layer: "Stone layer", mechanic_frozen_layer: "Frozen layer",
    mechanic_decoy: "Decoy bottle", mechanic_ice: "Frozen layer", mechanic_stone: "Stone layer",
    exitTitle: "Close Bottle Sort", appName: "Bottle Sort",
    bottleLabel: "Bottle {number}",
  },
  RU: {
    play: "Продолжить игру", levels: "Выбор уровня", settings: "Настройки", exit: "Выход",
    completed: "Пройдено уровней", campaign: "Кампания", pickLevel: "Выберите уровень",
    back: "Назад", level: "Уровень {number}", colors: "цветов: {count}", moves: "Ходы",
    time: "Время", collected: "Собрано бутылок", undo: "Отменить", restart: "Заново",
    hint: "Подсказка", check: "Проверить решение", menu: "Главное меню", previous: "Предыдущий",
    next: "Следующий", solved: "Уровень пройден — отлично!", dead: "Ходов больше нет. Начните уровень заново.",
    hintMove: "Попробуйте перелить из бутылки {source} в бутылку {target}.", noHint: "Решение для этой позиции не найдено.",
    hintLimit: "Все три подсказки для этого уровня использованы.", solutionFound: "Решение найдено: {count} ходов.",
    solutionMissing: "Решение не найдено за отведённое время.", tutorial: "Подсказка уровня",
    settingsTitle: "Настройки игры", sound: "Звуковые эффекты", soundInfo: "Звуки ходов и победы",
    music: "Фоновая музыка", musicInfo: "Весёлая, но спокойная мелодия во время игры", patterns: "Узоры для цветов",
    patternsInfo: "Текстуры помогают различать цвета", language: "Язык",
    save: "Сохранить настройки", reset: "Сбросить прогресс", resetConfirm: "Сбросить пройденные уровни? Крышки сохранятся.",
    progressError: "Не удалось загрузить сохранение: {error}", progressSaved: "Настройки сохранены.",
    progressReset: "Прогресс очищен, крышки сохранены.", openLevel: "Открыть уровень {number}", bottles: "бутылок",
    caps: "Крышки", capsEarned: "Получено крышек: {count}",
    mechanic_decoy_bottle: "Бутылка-обманка", mechanic_capacity_5: "Ёмкость 5", mechanic_giant_bottle_3x: "Большая бутылка",
    mechanic_hidden_colors: "Скрытые цвета", mechanic_stone_layer: "Каменный слой", mechanic_frozen_layer: "Замороженный слой",
    mechanic_decoy: "Обманка", mechanic_ice: "Лёд", mechanic_stone: "Камень",
    exitTitle: "Закрыть Bottle Sort", appName: "Bottle Sort",
    bottleLabel: "Бутылка {number}",
  },
};

const PALETTE = [
  "#D61E11", "#00F5F5", "#5A00F5", "#49F500", "#F5D236", "#F536BC",
  "#006BB2", "#00F56E", "#B28900", "#B20077", "#00B21E", "#369FF5",
  "#ABF500", "#BC00F5", "#0025F5", "#F56C36", "#2FD6B2", "#6FB227",
  "#7F27B2", "#2E27B2", "#27B264", "#F5366F", "#00F500", "#3656F5",
  "#F5A300", "#8F36F5", "#7CF536", "#36F543", "#F50045", "#B25327",
  "#00B6D6", "#F50097",
];
const STORAGE_KEY = "bottle-sort-progress";
const root = document.getElementById("app");
const toast = document.getElementById("toast");

let campaign = [];
let progress = { completed: [], caps: 0, settings: {} };
let progressLoadError = "";
let progressNeedsSave = false;
let screen = "home";
let levelIndex = 0;
let levelState = [];
let initialState = [];
let layerIds = [];
let initialLayerIds = [];
let secretLayerIds = new Set();
let revealedLayerIds = new Set();
let history = [];
let moveCount = 0;
let solutionPath = [];
let legalMoves = [];
let selectedBottle = null;
let hintsRemaining = 3;
let movePending = false;
let elapsedSeconds = 0;
let startedAt = null;
let timerHandle = null;
let toastHandle = null;
let homeAnimationTimer = null;
let homeAnimationTimeout = null;
let statusMessage = "";
let statusIsError = false;
let activePour = null;
let audioContext;
let musicGain;
let musicTimer = null;
let musicNoteIndex = 0;
let audioUnlocked = false;
const POUR_ANIMATION_MS = 340;

const settings = {
  language: "EN",
  sound_enabled: true,
  music_enabled: true,
  patterns_enabled: true,
};

function t(key, values = {}) {
  const text = TEXT[settings.language]?.[key] ?? TEXT.EN[key] ?? key;
  return text.replace(/\{(\w+)\}/g, (_match, name) => String(values[name] ?? ""));
}

function escapeHtml(value) {
  return String(value).replace(/[&<>"']/g, (character) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  })[character]);
}

function loadProgress() {
  try {
    const saved = localStorage.getItem(STORAGE_KEY);
    if (!saved) return;
    const parsed = JSON.parse(saved);
    if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) {
      throw new Error("Save file must contain an object.");
    }
    progress = parsed;
    const savedSettings = parsed.settings || {};
    for (const key of Object.keys(settings)) {
      if (key in savedSettings) settings[key] = savedSettings[key];
    }
    if (!Object.hasOwn(TEXT, settings.language)) settings.language = "EN";
    progress.completed = Array.isArray(progress.completed) ? progress.completed : [];
    if (Object.hasOwn(parsed, "caps")) {
      progress.caps = Number.isSafeInteger(parsed.caps) && parsed.caps >= 0 ? parsed.caps : 0;
    } else {
      progress.caps = capsForCompletedLevels(progress.completed);
      progressNeedsSave = true;
    }
  } catch (error) {
    progress = { completed: [], caps: 0, settings: {} };
    progressLoadError = error.message;
  }
}

function persistProgress() {
  progress.settings = { ...settings };
  if (levelState.length && campaign[levelIndex]) {
    progress.current_level = levelIndex;
    progress.current_state = levelState;
    progress.current_layer_tokens = layerIds;
    progress.revealed_layer_tokens = [...revealedLayerIds];
    progress.move_count = moveCount;
    progress.elapsed_seconds = elapsedSeconds + (startedAt ? (Date.now() - startedAt) / 1000 : 0);
    progress.solution_path = solutionPath;
  }
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(progress));
  } catch (error) {
    showToast(t("progressError", { error: error.message }));
  }
}

function applySettings() {
  document.body.classList.toggle("patterns-off", !settings.patterns_enabled);
  if (settings.music_enabled && audioUnlocked) startMusic();
  else stopMusic();
}

function showToast(message) {
  toast.textContent = message;
  toast.classList.add("visible");
  clearTimeout(toastHandle);
  toastHandle = setTimeout(() => toast.classList.remove("visible"), 2600);
}

function setStatus(message = "", error = false) {
  statusMessage = message;
  statusIsError = error;
  const element = document.querySelector(".status");
  if (element) {
    element.textContent = message;
    element.classList.toggle("error", error);
  }
}

async function backend(command, payload = {}) {
  if (!window.gameBridge?.request) throw new Error("Desktop game bridge is unavailable.");
  return window.gameBridge.request(command, payload);
}

function ensureAudio() {
  if (!audioContext) {
    const Context = window.AudioContext || window.webkitAudioContext;
    if (!Context) return null;
    audioContext = new Context();
  }
  return audioContext;
}

function unlockAudio() {
  const context = ensureAudio();
  if (!context || audioUnlocked) return;
  context.resume().then(() => {
    audioUnlocked = context.state === "running";
    if (settings.music_enabled) startMusic();
  }).catch((error) => showToast(`Audio could not start: ${error.message}`));
}

function playTone(frequency, duration = 0.07, type = "sine", volume = 0.035) {
  if (!settings.sound_enabled) return;
  const context = ensureAudio();
  if (!context) return;
  if (context.state === "suspended") {
    context.resume().catch((error) => showToast(`Audio could not start: ${error.message}`));
  }
  const oscillator = context.createOscillator();
  const gain = context.createGain();
  oscillator.type = type;
  oscillator.frequency.value = frequency;
  gain.gain.setValueAtTime(volume, context.currentTime);
  gain.gain.exponentialRampToValueAtTime(0.001, context.currentTime + duration);
  oscillator.connect(gain);
  gain.connect(context.destination);
  oscillator.start();
  oscillator.stop(context.currentTime + duration);
}

const MUSIC_NOTES = [
  523.25, 659.25, 783.99, 659.25,
  440, 523.25, 659.25, 523.25,
  349.23, 440, 523.25, 440,
  392, 493.88, 587.33, 493.88,
];
const MUSIC_CHORDS = [
  [130.81, 164.81, 196],
  [110, 130.81, 164.81],
  [87.31, 110, 130.81],
  [98, 123.47, 146.83],
];

function playMusicTone(frequency, start, duration, volume, type = "sine") {
  if (!audioContext || !musicGain) return;
  const oscillator = audioContext.createOscillator();
  const envelope = audioContext.createGain();
  oscillator.type = type;
  oscillator.frequency.value = frequency;
  envelope.gain.setValueAtTime(0.0001, start);
  envelope.gain.exponentialRampToValueAtTime(volume, start + 0.035);
  envelope.gain.exponentialRampToValueAtTime(0.0001, start + duration);
  oscillator.connect(envelope);
  envelope.connect(musicGain);
  oscillator.addEventListener("ended", () => {
    oscillator.disconnect();
    envelope.disconnect();
  }, { once: true });
  oscillator.start(start);
  oscillator.stop(start + duration + 0.01);
}

function playMusicStep() {
  if (!settings.music_enabled || !audioUnlocked || !audioContext || audioContext.state !== "running") return;
  const step = musicNoteIndex % MUSIC_NOTES.length;
  const chord = MUSIC_CHORDS[Math.floor(step / 4)];
  const start = audioContext.currentTime + 0.015;
  playMusicTone(MUSIC_NOTES[step], start, 0.34, 0.38, "triangle");
  if (step % 4 === 0) {
    playMusicTone(chord[0], start, 1.65, 0.12);
    playMusicTone(chord[2], start + 0.02, 1.3, 0.07);
  } else if (step % 4 === 2) {
    playMusicTone(chord[1], start, 0.5, 0.08);
  }
  musicNoteIndex += 1;
}

function startMusic() {
  if (!settings.music_enabled || !audioUnlocked || musicTimer !== null) return;
  const context = ensureAudio();
  if (!context || context.state !== "running") return;
  musicGain = context.createGain();
  musicGain.gain.value = 0.13;
  musicGain.connect(context.destination);
  playMusicStep();
  musicTimer = setInterval(playMusicStep, 500);
}

function stopMusic() {
  clearInterval(musicTimer);
  musicTimer = null;
  const fadingGain = musicGain;
  musicGain = null;
  if (fadingGain && audioContext) {
    fadingGain.gain.setTargetAtTime(0, audioContext.currentTime, 0.04);
    setTimeout(() => fadingGain.disconnect(), 300);
  }
}

function playVictoryMusic() {
  if (!settings.music_enabled || !audioUnlocked || !audioContext || audioContext.state !== "running") return;
  startMusic();
  const start = audioContext.currentTime + 0.03;
  [659.25, 783.99, 1046.5, 1318.51, 1046.5, 1318.51].forEach((frequency, index) => {
    playMusicTone(frequency, start + index * 0.16, 0.24, 0.4, "triangle");
  });
}

function playCoinShower() {
  if (!settings.sound_enabled) return;
  const context = ensureAudio();
  if (!context) return;
  if (context.state === "suspended") {
    context.resume().catch((error) => showToast(`Audio could not start: ${error.message}`));
  }
  const notes = [1567.98, 2093, 1760, 2349.32, 1975.53, 2637.02, 2093, 3135.96, 2349.32, 2793.83, 2093, 2637.02];
  notes.forEach((frequency, index) => {
    setTimeout(() => {
      if (!settings.sound_enabled) return;
      const start = context.currentTime;
      for (const [partial, volume] of [[frequency, 0.032], [frequency * 2.4, 0.009]]) {
        const oscillator = context.createOscillator();
        const envelope = context.createGain();
        oscillator.type = "sine";
        oscillator.frequency.setValueAtTime(partial, start);
        oscillator.frequency.exponentialRampToValueAtTime(partial * 0.78, start + 0.13);
        envelope.gain.setValueAtTime(0.0001, start);
        envelope.gain.exponentialRampToValueAtTime(volume, start + 0.006);
        envelope.gain.exponentialRampToValueAtTime(0.0001, start + 0.17);
        oscillator.connect(envelope);
        envelope.connect(context.destination);
        oscillator.addEventListener("ended", () => {
          oscillator.disconnect();
          envelope.disconnect();
        }, { once: true });
        oscillator.start(start);
        oscillator.stop(start + 0.18);
      }
    }, index * 55);
  });
}

function launchCapFireworks(anchor) {
  const layer = document.createElement("div");
  layer.className = "cap-firework-layer";
  layer.setAttribute("aria-hidden", "true");
  const rect = anchor?.getBoundingClientRect();
  layer.style.left = `${rect ? rect.left + rect.width / 2 : window.innerWidth / 2}px`;
  layer.style.top = `${rect ? rect.top + rect.height * 0.2 : window.innerHeight / 2}px`;
  for (let index = 0; index < 32; index += 1) {
    const angle = (Math.PI * 2 * index) / 32 + (Math.random() - 0.5) * 0.24;
    const distance = 80 + Math.random() * 210;
    const cap = document.createElement("span");
    cap.className = "firework-cap";
    cap.style.setProperty("--x", `${Math.cos(angle) * distance}px`);
    cap.style.setProperty("--y", `${Math.sin(angle) * distance - 55}px`);
    cap.style.setProperty("--delay", `${Math.random() * 100}ms`);
    cap.style.setProperty("--spin", `${(Math.random() - 0.5) * 900}deg`);
    cap.style.setProperty("--cap-color", ["#d9aa48", "#e7c56e", "#8db7bb", "#ef8354"][index % 4]);
    layer.append(cap);
  }
  document.body.append(layer);
  setTimeout(() => layer.remove(), 1900);
}

function celebrateLevel(target) {
  playVictoryMusic();
  playCoinShower();
  launchCapFireworks(root.querySelector(`[data-bottle="${target}"]`));
}

document.addEventListener("pointerdown", unlockAudio, { once: true });
document.addEventListener("keydown", unlockAudio, { once: true });

function makeLayerTokens(id, state) {
  return state.map((bottle, bottleIndex) =>
    bottle.map((_color, layerIndex) => `${id}:${bottleIndex}:${layerIndex}`)
  );
}

function revealTopRuns(state = levelState, tokens = layerIds) {
  const mechanics = campaign[levelIndex]?.mechanics_config || {};
  const concealed = new Set([
    ...(mechanics.hidden_bottles || []),
    ...(mechanics.decoy_bottles || []),
  ]);
  for (const index of concealed) {
    if (!state[index]?.length) continue;
    const bottle = state[index];
    let runLength = 1;
    while (runLength < bottle.length && bottle[bottle.length - runLength - 1] === bottle.at(-1)) {
      runLength += 1;
    }
    for (const token of tokens[index].slice(-runLength)) revealedLayerIds.add(token);
  }
}

function currentElapsed() {
  return elapsedSeconds + (startedAt ? (Date.now() - startedAt) / 1000 : 0);
}

function formatTime(seconds) {
  const whole = Math.floor(seconds);
  return `${String(Math.floor(whole / 60)).padStart(2, "0")}:${String(whole % 60).padStart(2, "0")}`;
}

function colorIndexOf(color) {
  const colorId = /^C(\d+)$/.exec(color);
  return colorId
    ? Number(colorId[1]) % PALETTE.length
    : Math.abs([...color].reduce((hash, character) => (hash * 31 + character.charCodeAt(0)) | 0, 0)) % PALETTE.length;
}

function layerColor(color) {
  return PALETTE[colorIndexOf(color)] || "#56b9a2";
}

function startTimer() {
  clearInterval(timerHandle);
  timerHandle = setInterval(() => {
    const element = document.querySelector("[data-timer]");
    if (element) element.textContent = formatTime(currentElapsed());
  }, 500);
}

function renderBottle(index, bottle, capacities, options = {}) {
  const selected = options.selected === index;
  const isTarget = options.targets?.has(index);
  const isPouring = options.pouring === index;
  const isReceiving = options.receiving === index;
  const capacity = capacities[index];
  const complete = bottle.length === capacity && bottle.length > 0 &&
    bottle.every((color) => color === bottle[0]);
  const baseCapacity = options.baseCapacity || 4;
  const scale = options.scale ?? Math.min(1.8, Math.max(1, Math.sqrt(capacity / baseCapacity)));
  const classes = [
    "bottle", options.className || "", selected ? "selected" : "",
    isTarget ? "valid-target" : "", isPouring ? "pouring" : "",
    isPouring ? `pouring-${options.pourDirection || "right"}` : "",
    isReceiving ? "receiving" : "", complete ? "complete" : "",
  ]
    .filter(Boolean).join(" ");
  const layers = bottle.map((color, layerIndex) => {
    const token = options.tokens?.[index]?.[layerIndex];
    const concealed = options.secrets?.has(token) && !options.revealed?.has(token);
    const colorIndex = colorIndexOf(color);
    const fill = concealed ? "#080b0f" : layerColor(color);
    const texture = concealed ? "texture-secret" : ["texture-snow", "texture-lava", "texture-glitter"][colorIndex % 3];
    const bottom = (layerIndex / capacities[index]) * 100;
    const height = 100 / capacities[index];
    return `<span class="liquid pattern-${colorIndex % 6} ${texture}" aria-hidden="true"
      style="bottom:${bottom}%;height:${height}%;background-color:${fill}">${concealed ? '<span class="secret-mark">?</span>' : ""}</span>`;
  }).join("");
  const emptyHint = bottle.length === 0 ? '<span class="empty-hint">+</span>' : "";
  const shell = `<span class="bottle-shell">
    <span class="bottle-neck-outline"></span><span class="bottle-neck"></span>
    <span class="bottle-shoulders-outline"></span><span class="bottle-shoulders"></span>
    <span class="bottle-body-outline"></span>
    <span class="bottle-body"><span class="bottle-liquid-area">${layers}${emptyHint}</span>
      <span class="bottle-glint"></span></span>
    <span class="bottle-mouth"></span>${complete ? '<span class="bottle-cap"></span>' : ""}
  </span>`;
  const liquidLevel = (bottle.length / capacity) * 100;
  const pourColor = options.pourColor ? `;--pour-color:${options.pourColor}` : "";
  const sizing = `--bottle-height:${Math.round(218 * scale)}px;--shell-height:${Math.round(176 * scale)}px;--liquid-level:${liquidLevel}%${pourColor}`;
  if (options.decorative) {
    const homeIndex = Number.isInteger(options.homeIndex) ? `data-home-bottle="${options.homeIndex}"` : "";
    return `<div class="${classes}" style="${sizing}" ${homeIndex} aria-hidden="true">${shell}</div>`;
  }
  const label = `${t("bottleLabel", { number: index + 1 })}, ${bottle.length}`;
  return `<button type="button" class="${classes}" style="${sizing}" data-bottle="${index}"
      aria-label="${escapeHtml(label)}" aria-pressed="${selected}" ${movePending ? "disabled" : ""}>
    ${options.showLabel === false ? "" : `<span class="bottle-label">${String(index + 1).padStart(2, "0")}</span>`}${shell}
  </button>`;
}

function brand() {
  return `<button class="brand" data-action="home" aria-label="${escapeHtml(t("appName"))}">
    <span class="brand-mark">BS</span><span>${escapeHtml(t("appName"))}</span>
  </button>`;
}

function capBalance() {
  return Number.isSafeInteger(progress.caps) && progress.caps >= 0 ? progress.caps : 0;
}

function capRewardForLevel(levelId) {
  const levelNumber = Number(levelId);
  return 50 + (Math.max(1, Number.isSafeInteger(levelNumber) ? levelNumber : 1) - 1) * 10;
}

function capsForCompletedLevels(completed) {
  return [...new Set(completed.map(Number).filter((levelId) =>
    Number.isSafeInteger(levelId) && levelId >= 1
  ))].reduce((total, levelId) => total + capRewardForLevel(levelId), 0);
}

function topbar(right = "") {
  const balance = capBalance();
  return `<header class="topbar">${brand()}
    <div class="top-actions">
      <span class="caps-wallet" aria-label="${escapeHtml(t("caps"))}: ${balance}">
        <span class="cap-wallet-icon" aria-hidden="true"></span><strong>${balance}</strong>
        <span class="caps-wallet-label">${escapeHtml(t("caps"))}</span>
      </span>${right}
    </div>
  </header>`;
}

function renderHome() {
  screen = "home";
  stopHomeAnimation();
  const completed = progress.completed.length;
  const level = Math.min(Number(progress.current_level) || 0, campaign.length - 1);
  const sample = [
    ["C0", "C1"],
    ["C2", "C1"],
    ["C3", "C1"],
    ["C0", "C1"],
    [],
  ];
  const demo = sample.map((layers, index) =>
    `<span class="home-floater" style="--float-delay:${index * -0.7}s">
      ${renderBottle(index, layers, sample.map(() => 4), {
        decorative: true, homeIndex: index, className: "home-bottle",
        scale: 0.78, showLabel: false,
      })}
    </span>`
  ).join("");
  root.innerHTML = `<section class="page home-page">
    ${topbar(`<button class="btn btn-quiet" data-action="settings">${escapeHtml(t("settings"))}</button>
      <button class="btn btn-quiet" data-action="exit">${escapeHtml(t("exit"))}</button>`)}
    <div class="home-layout">
      <section class="hero-card">
        <h1>${escapeHtml(t("appName"))}</h1>
        <div class="hero-actions">
          <button class="btn btn-primary" data-action="continue">${escapeHtml(t("play"))}</button>
          <button class="btn" data-action="levels">${escapeHtml(t("levels"))}</button>
        </div>
      </section>
      <aside class="scene-card" aria-hidden="true">
        <div class="demo-stage"><div class="demo-row">${demo}</div>
          <svg class="home-pour-stream" aria-hidden="true" preserveAspectRatio="none"></svg>
        </div>
      </aside>
    </div>
    <footer class="home-footer">
      <span>${escapeHtml(t("completed"))}: <strong>${completed} / ${campaign.length}</strong></span>
      <span>${progressLoadError ? escapeHtml(t("progressError", { error: progressLoadError })) : `${escapeHtml(t("pickLevel"))}: ${escapeHtml(t("level", { number: (campaign[level]?.id ?? 1) }))}`}</span>
    </footer>
  </section>`;
  startHomeAnimation();
}

function stopHomeAnimation() {
  clearInterval(homeAnimationTimer);
  clearTimeout(homeAnimationTimeout);
  homeAnimationTimer = null;
  homeAnimationTimeout = null;
}

function layoutDemoBottle(bottle) {
  const area = bottle.querySelector(".bottle-liquid-area");
  const layers = [...area.querySelectorAll(".liquid")];
  layers.forEach((layer, index) => {
    layer.style.bottom = `${(index / 4) * 100}%`;
    layer.style.height = "25%";
  });
  let emptyHint = area.querySelector(".empty-hint");
  if (!layers.length && !emptyHint) {
    emptyHint = document.createElement("span");
    emptyHint.className = "empty-hint";
    emptyHint.textContent = "+";
    area.append(emptyHint);
  } else if (layers.length && emptyHint) {
    emptyHint.remove();
  }
  bottle.style.setProperty("--liquid-level", `${(layers.length / 4) * 100}%`);
}

function transferDemoLayer(source, target) {
  const sourceArea = source.querySelector(".bottle-liquid-area");
  const targetArea = target.querySelector(".bottle-liquid-area");
  const sourceLayers = sourceArea.querySelectorAll(".liquid");
  const targetLayers = targetArea.querySelectorAll(".liquid");
  const layer = sourceLayers[sourceLayers.length - 1];
  const targetTop = targetLayers[targetLayers.length - 1];
  if (!layer || targetLayers.length >= 4 ||
      (targetTop && targetTop.style.backgroundColor !== layer.style.backgroundColor)) return false;
  layer.remove();
  targetArea.append(layer);
  layoutDemoBottle(source);
  layoutDemoBottle(target);
  return true;
}

function positionPourStream(stream, source, target, container, color) {
  if (!stream || !source || !target || !container) return;
  const sourceRect = (source.querySelector(".bottle-mouth") || source).getBoundingClientRect();
  const targetRect = (target.querySelector(".bottle-mouth") || target).getBoundingClientRect();
  const containerRect = container.getBoundingClientRect();
  const startX = sourceRect.left + sourceRect.width / 2 - containerRect.left;
  const startY = sourceRect.top + sourceRect.height / 2 - containerRect.top;
  const endX = targetRect.left + targetRect.width / 2 - containerRect.left;
  const endY = targetRect.top + targetRect.height / 2 - containerRect.top;
  const controlX = (startX + endX) / 2;
  const controlY = (startY + endY) / 2 + Math.min(64, Math.max(22, Math.abs(endX - startX) * 0.2));
  const path = `M ${startX} ${startY} Q ${controlX} ${controlY} ${endX} ${endY}`;
  stream.setAttribute("viewBox", `0 0 ${containerRect.width} ${containerRect.height}`);
  stream.innerHTML = `<path class="pour-body" d="${path}"/>
    <path class="pour-highlight" d="${path}"/>
    <circle class="pour-drop" r="3" cx="${startX}" cy="${startY}">
      <animateMotion dur=".48s" repeatCount="indefinite" path="${path}"/>
    </circle>
    <circle class="pour-drop pour-drop-small" r="2" cx="${startX}" cy="${startY}">
      <animateMotion begin=".22s" dur=".48s" repeatCount="indefinite" path="${path}"/>
    </circle>`;
  stream.style.setProperty("--pour-color", color);
}

function startHomeAnimation() {
  const bottles = [...root.querySelectorAll(".home-bottle")];
  const stream = root.querySelector(".home-pour-stream");
  const stage = root.querySelector(".demo-stage");
  const row = root.querySelector(".demo-row");
  if (bottles.length < 2 || !stream || !stage || !row) return;

  const initialContents = bottles.map((bottle) => bottle.querySelector(".bottle-liquid-area").innerHTML);
  let pair = 0;
  const pour = () => {
    bottles.forEach((bottle) => bottle.classList.remove("home-pouring", "home-receiving"));
    stream.classList.remove("active");
    const sourceIndex = pair % (bottles.length - 1);
    const targetIndex = sourceIndex + 1;
    const source = bottles[sourceIndex];
    const target = bottles[targetIndex];
    const layers = source.querySelectorAll(".liquid");
    const color = layers.length ? getComputedStyle(layers[layers.length - 1]).backgroundColor : "#5dd8b1";
    source.style.setProperty("--pour-color", color);
    target.style.setProperty("--pour-color", color);
    target.style.setProperty("--liquid-level", `${(target.querySelectorAll(".liquid").length / 4) * 100}%`);
    source.classList.add("home-pouring");
    target.classList.add("home-receiving");
    requestAnimationFrame(() => {
      if (!source.isConnected || !target.isConnected) return;
      positionPourStream(stream, source, target, stage, color);
      stream.classList.add("active");
      homeAnimationTimeout = setTimeout(() => {
        source.classList.remove("home-pouring");
        target.classList.remove("home-receiving");
        stream.classList.remove("active");
        transferDemoLayer(source, target);
        pair += 1;
        if (pair >= bottles.length - 1) {
          pair = 0;
          row.classList.add("demo-resetting");
          homeAnimationTimeout = setTimeout(() => {
            bottles.forEach((bottle, index) => {
              const area = bottle.querySelector(".bottle-liquid-area");
              area.innerHTML = initialContents[index];
              layoutDemoBottle(bottle);
            });
            row.classList.remove("demo-resetting");
          }, 240);
        }
      }, 1000);
    });
  };

  pour();
  homeAnimationTimer = setInterval(pour, 3400);
}

function renderLevels() {
  screen = "levels";
  stopHomeAnimation();
  const completed = new Set(progress.completed);
  root.innerHTML = `<section class="page">
    ${topbar(`<button class="btn btn-quiet" data-action="home">${escapeHtml(t("back"))}</button>`)}
    <div class="page-heading"><div><p class="eyebrow">${escapeHtml(t("campaign"))}</p>
      <h2>${escapeHtml(t("levels"))}</h2><p>${escapeHtml(t("pickLevel"))}</p></div>
      <span class="muted">${completed.size} / ${campaign.length} ${escapeHtml(t("completed").toLowerCase())}</span>
    </div>
    <section class="panel levels-scroll"><div class="level-grid">${campaign.map((level, index) => `
      <button class="level-card ${completed.has(level.id) ? "completed" : ""}" data-level="${index}"
        aria-label="${escapeHtml(t("openLevel", { number: level.id }))}">
        <span class="level-number"><span>${completed.has(level.id) ? "✓" : String(level.id).padStart(2, "0")}</span><span>›</span></span>
        <small>${escapeHtml(t("colors", { count: level.color_count }))}</small>
      </button>`).join("")}</div></section>
  </section>`;
}

function renderSettings() {
  screen = "settings";
  stopHomeAnimation();
  const row = (key, title, detail, checked) => `<label class="setting-row">
    <span class="setting-label"><strong>${escapeHtml(t(title))}</strong><small>${escapeHtml(t(detail))}</small></span>
    <input class="toggle" type="checkbox" data-setting="${key}" ${checked ? "checked" : ""}>
  </label>`;
  root.innerHTML = `<section class="page">
    ${topbar(`<button class="btn btn-quiet" data-action="home">${escapeHtml(t("back"))}</button>`)}
    <div class="settings-layout"><section class="settings-card">
      <p class="eyebrow">${escapeHtml(t("settings"))}</p><h2>${escapeHtml(t("settingsTitle"))}</h2>
      ${row("sound_enabled", "sound", "soundInfo", settings.sound_enabled)}
      ${row("music_enabled", "music", "musicInfo", settings.music_enabled)}
      ${row("patterns_enabled", "patterns", "patternsInfo", settings.patterns_enabled)}
      <label class="setting-row"><span class="setting-label"><strong>${escapeHtml(t("language"))}</strong></span>
        <select class="language-select" data-language aria-label="${escapeHtml(t("language"))}">
          <option value="EN" ${settings.language === "EN" ? "selected" : ""}>English</option>
          <option value="RU" ${settings.language === "RU" ? "selected" : ""}>Русский</option>
        </select>
      </label>
      <div class="settings-buttons">
        <button class="btn btn-primary" data-action="save-settings">${escapeHtml(t("save"))}</button>
        <button class="btn btn-danger" data-action="reset-progress">${escapeHtml(t("reset"))}</button>
      </div>
    </section></div>
  </section>`;
}

function getMechanicLabels(level) {
  const config = level.mechanics_config || {};
  const mechanics = new Set(level.mechanics || []);
  if (config.decoy_bottles?.length) mechanics.add("decoy_bottle");
  if (config.hidden_bottles?.length) mechanics.add("hidden_colors");
  return [...mechanics].map((mechanic) => {
    const key = `mechanic_${mechanic}`;
    return t(key) === key ? mechanic.replaceAll("_", " ") : t(key);
  });
}

function completeBottleCount() {
  const level = campaign[levelIndex];
  return levelState.filter((bottle, index) =>
    bottle.length === level.capacities[index] && bottle.length > 0 &&
    bottle.every((color) => color === bottle[0])
  ).length;
}

function renderGame() {
  screen = "game";
  stopHomeAnimation();
  const level = campaign[levelIndex];
  const pourColor = activePour ? layerColor(levelState[activePour.source].at(-1)) : undefined;
  const targets = selectedBottle === null ? new Set() : new Set(
    legalMoves.filter(([source]) => source === selectedBottle).map(([, target]) => target)
  );
  const isSolved = levelState.every((bottle, index) => !bottle.length ||
    (bottle.length === level.capacities[index] && bottle.every((color) => color === bottle[0])));
  const mechanicLabels = getMechanicLabels(level);
  const statusClass = statusIsError ? "status error" : "status";
  root.innerHTML = `<section class="page game-page">
    ${topbar(`<div class="stats">
      <div class="stat"><small>${escapeHtml(t("moves"))}</small><strong>${moveCount}</strong></div>
      <div class="stat"><small>${escapeHtml(t("time"))}</small><strong data-timer>${formatTime(currentElapsed())}</strong></div>
      <div class="stat"><small>${escapeHtml(t("collected"))}</small><strong>${completeBottleCount()} / ${level.color_count}</strong></div>
    </div>`)}
    <div class="game-topbar">
      <div class="game-heading"><span class="brand-mark">BS</span><h2>${escapeHtml(t("level", { number: level.id }))}</h2></div>
    </div>
    ${mechanicLabels.length ? `<div class="mechanics">${mechanicLabels.map((label) => `<span class="mechanic-badge">${escapeHtml(label)}</span>`).join("")}</div>` : ""}
    <nav class="game-toolbar" aria-label="Game controls">
      <button class="btn" data-action="undo" ${history.length ? "" : "disabled"}>${escapeHtml(t("undo"))}</button>
      <button class="btn" data-action="restart">${escapeHtml(t("restart"))}</button>
      <button class="btn" data-action="hint" ${isSolved ? "disabled" : ""}>${escapeHtml(t("hint"))} · ${hintsRemaining}</button>
      <button class="btn" data-action="check">${escapeHtml(t("check"))}</button>
      <span class="spacer"></span>
      <button class="btn btn-quiet" data-action="previous" ${levelIndex === 0 ? "disabled" : ""}>‹ ${escapeHtml(t("previous"))}</button>
      <button class="btn btn-quiet" data-action="next" ${levelIndex + 1 >= campaign.length ? "disabled" : ""}>${escapeHtml(t("next"))} ›</button>
      <button class="btn btn-quiet" data-action="home">${escapeHtml(t("menu"))}</button>
    </nav>
    <p class="${statusClass}">${escapeHtml(statusMessage)}</p>
    <section class="board-wrap" aria-label="${escapeHtml(t("level", { number: level.id }))}">
      ${activePour ? '<svg class="pour-stream active" aria-hidden="true" preserveAspectRatio="none"></svg>' : ""}
      <div class="board">${levelState.map((bottle, index) => renderBottle(index, bottle, level.capacities, {
        selected: selectedBottle, targets, tokens: layerIds,
        secrets: secretLayerIds, revealed: revealedLayerIds, baseCapacity: level.capacity,
        pouring: activePour?.source, receiving: activePour?.target,
        pourColor,
        pourDirection: activePour && (activePour.target < activePour.source ? "left" : "right"),
      })).join("")}</div>
    </section>
    <footer class="game-bottom"><span>${levelState.length} ${escapeHtml(t("bottles"))}</span></footer>
  </section>`;
  if (activePour) {
    const pour = activePour;
    requestAnimationFrame(() => {
      const source = root.querySelector(`[data-bottle="${pour.source}"]`);
      const target = root.querySelector(`[data-bottle="${pour.target}"]`);
      positionPourStream(
        root.querySelector(".pour-stream"),
        source,
        target,
        root.querySelector(".board-wrap"),
        source?.querySelector(".liquid:last-of-type")?.style.backgroundColor || "#52d8b2",
      );
    });
  }
  startTimer();
}

function render() {
  applySettings();
  if (screen === "levels") renderLevels();
  else if (screen === "settings") renderSettings();
  else if (screen === "game") renderGame();
  else renderHome();
}

async function startLevel(index, resume = true) {
  if (!Number.isInteger(index) || index < 0 || index >= campaign.length) index = 0;
  levelIndex = index;
  const level = campaign[levelIndex];
  initialState = level.state.map((bottle) => [...bottle]);
  const shouldResume = resume && progress.current_level === levelIndex &&
    Array.isArray(progress.current_state) && progress.current_state.length === initialState.length;
  levelState = shouldResume
    ? progress.current_state.map((bottle) => [...bottle])
    : initialState.map((bottle) => [...bottle]);
  initialLayerIds = makeLayerTokens(level.id, initialState);
  const savedIds = shouldResume ? progress.current_layer_tokens : null;
  const tokenSet = Array.isArray(savedIds) && savedIds.length === levelState.length &&
    savedIds.every((tokens, bottle) => Array.isArray(tokens) && tokens.length === levelState[bottle].length &&
      tokens.every((token) => typeof token === "string"));
  layerIds = tokenSet ? savedIds.map((tokens) => [...tokens]) : makeLayerTokens(level.id, levelState);
  const allTokens = layerIds.flat();
  const expectedTokens = initialLayerIds.flat().sort();
  if (new Set(allTokens).size !== allTokens.length ||
      allTokens.slice().sort().some((token, tokenIndex) => token !== expectedTokens[tokenIndex])) {
    layerIds = makeLayerTokens(level.id, levelState);
  }
  const hidden = new Set([
    ...(level.mechanics_config?.hidden_bottles || []),
    ...(level.mechanics_config?.decoy_bottles || []),
  ]);
  secretLayerIds = new Set(initialLayerIds.flatMap((tokens, bottle) => hidden.has(bottle) ? tokens : []));
  const savedRevealed = shouldResume && Array.isArray(progress.revealed_layer_tokens)
    ? progress.revealed_layer_tokens : [];
  revealedLayerIds = new Set(savedRevealed.filter((token) => secretLayerIds.has(token)));
  revealTopRuns();
  history = [];
  moveCount = shouldResume ? Number(progress.move_count) || 0 : 0;
  elapsedSeconds = shouldResume ? Number(progress.elapsed_seconds) || 0 : 0;
  startedAt = Date.now();
  hintsRemaining = 3;
  selectedBottle = null;
  statusMessage = "";
  statusIsError = false;
  const savedSolution = shouldResume ? progress.solution_path : null;
  solutionPath = Array.isArray(savedSolution)
    ? savedSolution.map((move) => [...move])
    : (level.solution || []).map((move) => [...move]);
  legalMoves = await backend("legal_moves", { level_index: levelIndex, state: levelState });
  screen = "game";
  persistProgress();
  render();
}

function leaveGame() {
  if (startedAt) {
    elapsedSeconds = currentElapsed();
    startedAt = null;
  }
  persistProgress();
  screen = "home";
  renderHome();
}

async function selectBottle(index) {
  if (movePending) return;
  if (selectedBottle === null) {
    if (!legalMoves.some(([source]) => source === index)) return;
    selectedBottle = index;
    playTone(420);
    renderGame();
    return;
  }
  if (index === selectedBottle) {
    selectedBottle = null;
    renderGame();
    return;
  }
  const isLegal = legalMoves.some(([source, target]) => source === selectedBottle && target === index);
  if (!isLegal) {
    if (legalMoves.some(([source]) => source === index)) {
      selectedBottle = index;
      renderGame();
    } else {
      selectedBottle = null;
      renderGame();
    }
    return;
  }
  const source = selectedBottle;
  const target = index;
  selectedBottle = null;
  const before = {
    state: levelState.map((bottle) => [...bottle]),
    tokens: layerIds.map((tokens) => [...tokens]),
    moves: moveCount,
    solution: solutionPath.map((move) => [...move]),
    revealed: [...revealedLayerIds],
  };
  movePending = true;
  activePour = { source, target };
  renderGame();
  let result;
  try {
    const request = backend("move", {
      level_index: levelIndex, state: levelState, source, target,
    });
    [result] = await Promise.all([
      request,
      new Promise((resolve) => setTimeout(resolve, POUR_ANIMATION_MS)),
    ]);
  } finally {
    activePour = null;
    movePending = false;
  }
  history.push(before);
  const movedCount = levelState[source].length - result.state[source].length;
  const movedTokens = layerIds[source].splice(-movedCount);
  layerIds[target].push(...movedTokens);
  levelState = result.state;
  if (solutionPath[0]?.[0] === source && solutionPath[0]?.[1] === target) solutionPath.shift();
  else solutionPath = [];
  moveCount += 1;
  legalMoves = result.legal_moves;
  revealTopRuns();
  persistProgress();
  setStatus("");
  playTone(530, 0.12, "triangle", 0.04);
  let levelWon = false;
  if (result.solved) {
    levelWon = true;
    elapsedSeconds = currentElapsed();
    startedAt = null;
    if (!progress.completed.includes(campaign[levelIndex].id)) {
      progress.completed.push(campaign[levelIndex].id);
      const reward = capRewardForLevel(campaign[levelIndex].id || levelIndex + 1);
      progress.caps = capBalance() + reward;
      showToast(t("capsEarned", { count: reward }));
    }
    solutionPath = [];
    setStatus(t("solved"));
  } else if (legalMoves.length === 0) {
    setStatus(t("dead"), true);
  } else if (solutionPath.length === 0) {
    const search = await backend("solve", { level_index: levelIndex, state: levelState });
    if (search.solution) solutionPath = search.solution;
    else if (!search.timed_out) setStatus(t("noHint"), true);
  }
  persistProgress();
  renderGame();
  if (levelWon) celebrateLevel(target);
}

async function requestSolution() {
  if (solutionPath.length) return { solution: solutionPath, timed_out: false };
  return backend("solve", { level_index: levelIndex, state: levelState });
}

async function showHint() {
  if (hintsRemaining <= 0) {
    setStatus(t("hintLimit"));
    return;
  }
  const result = await requestSolution();
  if (!result.solution?.length) {
    setStatus(result.timed_out ? t("solutionMissing") : t("noHint"), true);
    return;
  }
  solutionPath = result.solution;
  hintsRemaining -= 1;
  const [source, target] = result.solution[0];
  setStatus(t("hintMove", { source: source + 1, target: target + 1 }));
  persistProgress();
  renderGame();
}

async function checkSolution() {
  const result = await requestSolution();
  if (result.solution) {
    solutionPath = result.solution;
    setStatus(t("solutionFound", { count: result.solution.length }));
    persistProgress();
  } else {
    setStatus(t("solutionMissing"), true);
  }
  renderGame();
}

function undoMove() {
  const previous = history.pop();
  if (!previous) return;
  levelState = previous.state;
  layerIds = previous.tokens;
  moveCount = previous.moves;
  solutionPath = previous.solution;
  revealedLayerIds = new Set(previous.revealed);
  revealTopRuns();
  setStatus("");
  startedAt = Date.now();
  persistProgress();
  backend("legal_moves", { level_index: levelIndex, state: levelState })
    .then((moves) => { legalMoves = moves; renderGame(); })
    .catch((error) => { setStatus(error.message, true); renderGame(); });
}

async function restartLevel() {
  history = [];
  levelState = initialState.map((bottle) => [...bottle]);
  layerIds = initialLayerIds.map((tokens) => [...tokens]);
  revealedLayerIds = new Set();
  revealTopRuns();
  moveCount = 0;
  elapsedSeconds = 0;
  startedAt = Date.now();
  hintsRemaining = 3;
  solutionPath = (campaign[levelIndex].solution || []).map((move) => [...move]);
  selectedBottle = null;
  statusMessage = "";
  legalMoves = await backend("legal_moves", { level_index: levelIndex, state: levelState });
  persistProgress();
  renderGame();
}

function setSetting(name, value) {
  settings[name] = value;
  if (name === "language") {
    render();
    return;
  }
  applySettings();
}

function saveSettings() {
  persistProgress();
  showToast(t("progressSaved"));
  renderSettings();
}

function resetProgress() {
  if (!window.confirm(t("resetConfirm"))) return;
  progress = { completed: [], caps: capBalance(), settings: { ...settings } };
  persistProgress();
  showToast(t("progressReset"));
  renderSettings();
}

root.addEventListener("click", async (event) => {
  const bottle = event.target.closest("[data-bottle]");
  if (bottle && screen === "game") {
    try { await selectBottle(Number(bottle.dataset.bottle)); }
    catch (error) { setStatus(error.message, true); renderGame(); }
    return;
  }
  const level = event.target.closest("[data-level]");
  if (level) {
    try { await startLevel(Number(level.dataset.level)); }
    catch (error) { showToast(error.message); }
    return;
  }
  const control = event.target.closest("[data-action]");
  if (!control) return;
  if (movePending) return;
  try {
    switch (control.dataset.action) {
      case "home": leaveGame(); break;
      case "continue": await startLevel(Number(progress.current_level) || 0); break;
      case "levels": renderLevels(); break;
      case "settings": renderSettings(); break;
      case "undo": undoMove(); break;
      case "restart": await restartLevel(); break;
      case "hint": await showHint(); break;
      case "check": await checkSolution(); break;
      case "previous": await startLevel(levelIndex - 1, false); break;
      case "next": await startLevel(levelIndex + 1, false); break;
      case "save-settings": saveSettings(); break;
      case "reset-progress": resetProgress(); break;
      case "exit": window.close(); break;
      default: break;
    }
  } catch (error) {
    if (screen === "game") {
      setStatus(error.message, true);
      renderGame();
    } else showToast(error.message);
  }
});

root.addEventListener("change", (event) => {
  if (event.target.matches("[data-setting]")) {
    setSetting(event.target.dataset.setting, event.target.checked);
  } else if (event.target.matches("[data-language]")) {
    setSetting("language", event.target.value);
  }
});

window.addEventListener("beforeunload", () => {
  if (screen === "game") persistProgress();
  clearInterval(timerHandle);
});

async function initialize() {
  loadProgress();
  try {
    campaign = await backend("get_campaign");
    if (!Array.isArray(campaign) || campaign.length === 0) {
      throw new Error("Campaign is empty.");
    }
    if (progressNeedsSave) {
      persistProgress();
      progressNeedsSave = false;
    }
    applySettings();
    renderHome();
  } catch (error) {
    root.innerHTML = `<section class="loading-card"><div class="brand-mark">BS</div>
      <h1>${escapeHtml(t("appName"))}</h1><p>${escapeHtml(error.message)}</p>
      <p class="muted">Install Python and run <code>pip install -r requirements.txt</code>, then start the app again.</p>
    </section>`;
  }
}

initialize();
