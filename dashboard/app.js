"use strict";

const THEME_STORAGE_KEY = "hone-theme";
const THEMES = ["light", "dark", "system"];
const DEFAULT_THEME = "light";
const STATUS_ICONS = { completed: "done", in_progress: "current", available: "open", locked: "locked" };
const EXERCISE_STATUS_MAP = { passed: "completed", started: "in_progress", not_started: "available" };
const MAX_DIFFICULTY = 5;
const DRAFT_SAVE_DELAY_MS = 900;
const TAB_SPACES = "    ";
const CLIENT_HEADER = { "X-Hone-Client": "dashboard" };
const WEEKDAY_FORMAT = new Intl.DateTimeFormat("pt-BR", { weekday: "short", day: "2-digit" });
const LONG_DATE_FORMAT = new Intl.DateTimeFormat("pt-BR", { weekday: "long", day: "numeric", month: "long" });
const SHORT_DATE_FORMAT = new Intl.DateTimeFormat("pt-BR", { day: "2-digit", month: "2-digit" });
const DATE_TIME_FORMAT = new Intl.DateTimeFormat("pt-BR", { day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit" });
const LIKELY_KNOWN_NOTE = "o diagnóstico diz que você já aplica isto";
const API_UNREACHABLE = {
  problem: "o sistema não respondeu.",
  next_step: "confira se a janela do hone ainda está aberta. Se fechou, abra o hone de novo.",
};

const view = document.getElementById("view");
let activeChart = null;
let pendingFlash = null;
let pendingSubmission = null;
let pendingDiagnosticFeedback = null;

function el(tag, attributes = {}, children = []) {
  const node = document.createElement(tag);
  for (const [name, value] of Object.entries(attributes)) {
    if (value === null || value === undefined || value === false) continue;
    if (name === "text") node.textContent = value;
    else if (name === "className") node.className = value;
    else if (name.startsWith("on")) node.addEventListener(name.slice(2), value);
    else if (value === true) node.setAttribute(name, "");
    else node.setAttribute(name, value);
  }
  for (const child of [].concat(children)) {
    if (child === null || child === undefined || child === false) continue;
    node.append(child instanceof Node ? child : document.createTextNode(String(child)));
  }
  return node;
}

function icon(name, { className = "icon", label = null } = {}) {
  const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  svg.setAttribute("class", className);
  if (label) svg.setAttribute("aria-label", label);
  else svg.setAttribute("aria-hidden", "true");
  const use = document.createElementNS("http://www.w3.org/2000/svg", "use");
  use.setAttribute("href", `#icon-${name}`);
  svg.append(use);
  return svg;
}

function readStoredTheme() {
  try {
    const stored = localStorage.getItem(THEME_STORAGE_KEY);
    return THEMES.includes(stored) ? stored : DEFAULT_THEME;
  } catch {
    return DEFAULT_THEME;
  }
}

function applyTheme(theme) {
  document.documentElement.setAttribute("data-theme", theme);
  for (const button of document.querySelectorAll("[data-theme-choice]")) {
    button.setAttribute("aria-pressed", String(button.dataset.themeChoice === theme));
  }
}

function setupThemeSwitch() {
  applyTheme(readStoredTheme());
  for (const button of document.querySelectorAll("[data-theme-choice]")) {
    button.addEventListener("click", () => {
      const theme = button.dataset.themeChoice;
      try {
        localStorage.setItem(THEME_STORAGE_KEY, theme);
      } catch {
        void theme;
      }
      applyTheme(theme);
      route();
    });
  }
}

class ChallengeError extends Error {
  constructor(challenge) {
    super(challenge.problem);
    this.challenge = challenge;
  }
}

async function requestJson(path, { method = "GET", body } = {}) {
  const headers = { Accept: "application/json", ...CLIENT_HEADER };
  if (body !== undefined) headers["Content-Type"] = "application/json";
  let response;
  try {
    response = await fetch(path, { method, headers, body: body === undefined ? undefined : JSON.stringify(body) });
  } catch {
    throw new ChallengeError(API_UNREACHABLE);
  }
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new ChallengeError(
      payload.challenge || {
        problem: typeof payload.detail === "string" ? payload.detail : "algo não saiu como esperado.",
        next_step: "recarregue a página e tente de novo.",
      },
    );
  }
  return payload;
}

function fetchJson(path) {
  return requestJson(path);
}

function sendJson(path, method, body) {
  return requestJson(path, { method, body });
}

function cssToken(name) {
  return getComputedStyle(document.documentElement).getPropertyValue(`--${name}`).trim();
}

function capitalize(text) {
  return text.charAt(0).toUpperCase() + text.slice(1);
}

function renderChallenge(challenge) {
  return el("div", { className: "challenge", role: "alert" }, [
    el("p", { className: "challenge-title", text: "Desafio" }),
    el("p", { text: capitalize(challenge.problem) }),
    el("p", { className: "muted", text: `Próximo passo: ${challenge.next_step}` }),
  ]);
}

function flash(message, tone = "ok") {
  pendingFlash = { message, tone };
}

function renderFlash() {
  if (!pendingFlash) return null;
  const { message, tone } = pendingFlash;
  pendingFlash = null;
  return el("div", { className: `flash flash-${tone}`, role: "status" }, [
    tone === "ok" ? icon("done") : icon("hint"),
    el("span", { text: message }),
  ]);
}

function button(label, onClick, { variant = "default", disabled = false, iconName = null } = {}) {
  return el("button", { type: "button", className: `button button-${variant}`, disabled, onclick: onClick }, [
    iconName ? icon(iconName) : null,
    label,
  ]);
}

function actionButton(label, action, options = {}) {
  const slot = el("div", { className: "action-error" });
  const control = button(
    label,
    async () => {
      control.disabled = true;
      slot.replaceChildren();
      try {
        await action();
      } catch (error) {
        control.disabled = false;
        if (!(error instanceof ChallengeError)) throw error;
        slot.replaceChildren(renderChallenge(error.challenge));
      }
    },
    options,
  );
  return { control, slot };
}

function pageHead(title, subtitle, aside = null) {
  return el("header", { className: "page-head" }, [
    el("div", {}, [el("h1", { text: title }), subtitle ? el("p", { text: subtitle }) : null]),
    aside,
  ]);
}

function card(title, children, { className = "" } = {}) {
  return el("section", { className: `card ${className}`.trim() }, [
    title ? el("h2", { text: title }) : null,
    ...[].concat(children),
  ]);
}

function moduleHref(module) {
  return `#/tracks/${module.track_slug}/${module.slug}`;
}

function moduleKeyHref(key) {
  return `#/tracks/${key}`;
}

function exerciseHref(slug) {
  return `#/exercises/${encodeURIComponent(slug)}`;
}

function progressBar(done, total, label) {
  const percent = total ? Math.round((100 * done) / total) : 0;
  return el(
    "div",
    { className: "progress-bar", role: "progressbar", "aria-valuenow": percent, "aria-valuemin": 0, "aria-valuemax": 100, "aria-label": label },
    el("div", { className: "progress-bar-fill", style: `width: ${percent}%` }),
  );
}

function difficultyDots(difficulty) {
  return el("span", { className: "difficulty", "aria-label": `dificuldade ${difficulty} de ${MAX_DIFFICULTY}` }, [
    el("span", { className: "difficulty-filled", text: "●".repeat(difficulty) }),
    el("span", { className: "difficulty-empty", text: "●".repeat(MAX_DIFFICULTY - difficulty) }),
  ]);
}

function trackProgressList(tracks) {
  return el(
    "div",
    {},
    tracks.map((track) =>
      el("div", { className: "progress-row" }, [
        el("a", { href: `#/tracks/${track.slug}`, text: track.name }),
        progressBar(track.completed, track.total, `Progresso em ${track.name}`),
        el("span", { className: "progress-count", text: `${track.completed}/${track.total}` }),
      ]),
    ),
  );
}

function moduleList(modules, { showTrack = false, notes = {} } = {}) {
  return el(
    "ul",
    { className: "list" },
    modules.map((module) => {
      const note = notes[module.key];
      const detail = note || (module.missing_prerequisites.length ? `precisa de: ${module.missing_prerequisites.map((link) => link.title).join(", ")}` : module.summary);
      return el("li", { className: "list-item", "data-status": module.status }, [
        icon(STATUS_ICONS[module.status], { className: "icon marker" }),
        el("span", {}, [
          el("span", { className: "list-item-title" }, el("a", { href: moduleHref(module), text: showTrack ? module.title : `${module.position}. ${module.title}` })),
          detail ? el("span", { className: note ? "list-item-detail note-known" : "list-item-detail", text: detail }) : null,
        ]),
        el("span", { className: "status-tag", text: module.status_label }),
      ]);
    }),
  );
}

function studyChart(days) {
  const canvas = el("canvas", { "aria-label": "Minutos de estudo por dia nos últimos 14 dias", role: "img" });
  const box = el("div", { className: "chart-box" }, canvas);
  requestAnimationFrame(() => {
    if (typeof Chart === "undefined") return;
    const muted = cssToken("text-muted");
    activeChart = new Chart(canvas, {
      type: "bar",
      data: {
        labels: days.map((entry) => WEEKDAY_FORMAT.format(new Date(`${entry.day}T12:00:00`))),
        datasets: [{ data: days.map((entry) => entry.minutes), backgroundColor: cssToken("accent"), borderRadius: 2, maxBarThickness: 18 }],
      },
      options: {
        maintainAspectRatio: false,
        animation: window.matchMedia("(prefers-reduced-motion: reduce)").matches ? false : undefined,
        plugins: { legend: { display: false }, tooltip: { callbacks: { label: (item) => `${item.parsed.y} min` } } },
        scales: {
          x: { grid: { display: false }, ticks: { color: muted, font: { size: 10 } } },
          y: { beginAtZero: true, grid: { color: cssToken("border") }, border: { display: false }, ticks: { color: muted, precision: 0, font: { size: 10 } } },
        },
      },
    });
  });
  return box;
}

function checkinCard(overview) {
  if (overview.todays_checkin) {
    return card("Check-in de hoje", [
      el("p", { className: "list-item-title", text: overview.todays_checkin.intention }),
      el("p", { className: "muted", text: "Feito. Agora é estudar." }),
    ]);
  }
  const input = el("input", { type: "text", className: "input", placeholder: "Hoje eu vou estudar…", "aria-label": "O que você vai estudar hoje?", maxlength: "200" });
  const { control, slot } = actionButton(
    "Registrar",
    async () => {
      const result = await sendJson("/api/checkin", "POST", { intention: input.value });
      flash(result.message);
      route();
    },
    { variant: "primary" },
  );
  input.addEventListener("keydown", (event) => {
    if (event.key === "Enter") control.click();
  });
  return card("Check-in de hoje", [
    el("label", { className: "field-label", text: "O que você vai estudar hoje?" }),
    el("div", { className: "inline-form" }, [input, control]),
    slot,
  ]);
}

function sessionCard(overview) {
  const session = overview.active_session;
  if (!session) {
    const { control, slot } = actionButton(
      "Começar sessão livre",
      async () => {
        await sendJson("/api/sessions", "POST", {});
        flash("Sessão começou. Celular longe, foco perto.");
        route();
      },
      { iconName: "play" },
    );
    return card("Sessão de estudo", [
      el("p", { className: "muted", text: "Nenhuma rolando. Comece aqui ou pela página de um módulo." }),
      el("div", { className: "actions" }, [control]),
      slot,
    ]);
  }
  const notes = el("textarea", { className: "input", rows: "2", placeholder: "O que você fez ou descobriu? (opcional)", "aria-label": "Notas da sessão" });
  const { control, slot } = actionButton(
    "Encerrar sessão",
    async () => {
      const result = await sendJson("/api/sessions/stop", "POST", { notes: notes.value });
      flash(result.message);
      route();
    },
    { variant: "primary", iconName: "stop" },
  );
  return card("Sessão de estudo", [
    el("p", {}, [el("strong", { text: `${session.minutes} min` }), ` · ${session.module_title || "estudo livre"}`]),
    notes,
    el("div", { className: "actions" }, [control]),
    slot,
  ]);
}

async function renderToday() {
  const overview = await fetchJson("/api/overview");
  const streak = overview.streak;
  const content = [
    pageHead(
      capitalize(LONG_DATE_FORMAT.format(new Date(`${overview.today}T12:00:00`))),
      null,
      el("div", { className: "stat-strip" }, [
        el("div", {}, [
          el("div", { className: "streak-line" }, [
            el("span", { className: "streak-count", "data-alive": String(streak.current > 0), text: streak.current }),
            el("span", { className: "muted", text: streak.current === 1 ? "dia seguido" : "dias seguidos" }),
          ]),
          el("span", { className: "stat-label", text: "streak" }),
        ]),
        el("div", {}, [
          el("span", { className: "stat-value", "data-accent": "true", text: overview.xp.competency }),
          el("span", { className: "stat-label", text: "XP de competência" }),
        ]),
      ]),
    ),
    el("p", { className: "streak-message", text: streak.message }),
  ];

  if (overview.tracks.length === 0) {
    content.push(renderChallenge({ problem: "nenhuma trilha carregada ainda.", next_step: "confira a pasta data/ e abra o hone de novo." }));
    return content;
  }

  const nextHeading = overview.goal ? `Continue daqui, rumo a ${overview.goal.title}` : "Continue daqui";
  content.push(
    el("div", { className: "section grid grid-main" }, [
      el("div", {}, [
        overview.next_modules.length ? card(nextHeading, moduleList(overview.next_modules, { showTrack: true })) : null,
        card("Trilhas", trackProgressList(overview.tracks), { className: "section" }),
      ]),
      el("div", {}, [
        checkinCard(overview),
        el("div", { className: "section" }, sessionCard(overview)),
        el("div", { className: "section" }, card("Últimos 14 dias", studyChart(overview.study_minutes))),
      ]),
    ]),
  );
  return content;
}

function trackCard(track) {
  return card(track.name, [
    el("p", { className: "muted", text: track.description }),
    el("div", { className: "progress-row" }, [
      el("a", { href: `#/tracks/${track.slug}`, text: "Abrir trilha" }),
      progressBar(track.completed, track.total, `Progresso em ${track.name}`),
      el("span", { className: "progress-count", text: `${track.completed}/${track.total}` }),
    ]),
  ]);
}

async function renderTracks() {
  const tracks = await fetchJson("/api/tracks");
  return [
    pageHead("Trilhas", "Cada uma é um caminho, não uma lista de tarefas."),
    el(
      "div",
      { className: "section grid grid-two" },
      tracks.length ? tracks.map(trackCard) : el("p", { className: "muted", text: "Nenhuma trilha carregada." }),
    ),
  ];
}

async function renderTrack(trackSlug) {
  const track = await fetchJson(`/api/tracks/${encodeURIComponent(trackSlug)}`);
  return [
    el("div", { className: "breadcrumb" }, el("a", { href: "#/tracks", text: "Trilhas" })),
    pageHead(
      track.name,
      track.description,
      el("div", {}, [
        el("span", { className: "stat-value", text: `${track.completed}/${track.total}` }),
        el("span", { className: "stat-label", text: "módulos concluídos" }),
      ]),
    ),
    el("div", { className: "section" }, card(null, moduleList(track.modules))),
  ];
}

function exerciseList(exercises) {
  return el(
    "ul",
    { className: "list" },
    exercises.map((exercise) =>
      el("li", { className: "list-item", "data-status": EXERCISE_STATUS_MAP[exercise.status] }, [
        icon(STATUS_ICONS[EXERCISE_STATUS_MAP[exercise.status]], { className: "icon marker" }),
        el("span", {}, [
          el("span", { className: "list-item-title" }, [el("a", { href: exerciseHref(exercise.slug), text: exercise.title }), exercise.required ? el("span", { className: "tag", text: "obrigatório" }) : null]),
          el("span", { className: "list-item-detail" }, [difficultyDots(exercise.difficulty), ` ${exercise.kind_label} · ${exercise.base_xp} XP`]),
        ]),
        el("span", { className: "status-tag", text: exercise.status_label }),
      ]),
    ),
  );
}

function moduleSessionCard(module, overview) {
  const session = overview.active_session;
  if (session && session.module_key === module.key) {
    return card("Sessão", el("p", {}, [el("strong", { text: `${session.minutes} min` }), " neste módulo"]));
  }
  if (session) {
    return card("Sessão", el("p", { className: "muted" }, ["Rolando em outro assunto. ", el("a", { href: "#/", text: "Encerrar em Hoje" }), "."]));
  }
  const { control, slot } = actionButton(
    "Começar sessão",
    async () => {
      await sendJson("/api/sessions", "POST", { module_key: module.key });
      flash("Sessão começou. Celular longe, foco perto.");
      route();
    },
    { iconName: "play" },
  );
  return card("Sessão", [el("p", { className: "muted", text: "Cronometre o tempo que passar neste módulo." }), el("div", { className: "actions" }, [control]), slot]);
}

function completionCard(module) {
  if (module.status === "completed") {
    return card("Concluído", el("p", { className: "muted", text: "Reler é revisão, não retrocesso." }));
  }
  if (module.pending_required.length) {
    return card("Concluir módulo", [
      el("p", { className: "muted", text: `Antes, passe em: ${module.pending_required.join(", ")}.` }),
      el("div", { className: "actions" }, [button("Concluir módulo", null, { disabled: true })]),
    ]);
  }
  const { control, slot } = actionButton(
    "Concluir módulo",
    async () => {
      const result = await sendJson(`/api/tracks/${encodeURIComponent(module.track_slug)}/modules/${encodeURIComponent(module.slug)}/complete`, "POST");
      const unlocked = result.unlocked.map((item) => item.title).join(", ");
      flash([result.message, unlocked ? `Destravou: ${unlocked}.` : "", result.track_message || ""].filter(Boolean).join(" "));
      route();
    },
    { variant: "primary", iconName: "done" },
  );
  return card("Concluir módulo", [el("p", { className: "muted", text: "Respondeu a recuperação ativa sem olhar? Então este é seu." }), el("div", { className: "actions" }, [control]), slot]);
}

async function renderModule(trackSlug, moduleSlug) {
  const [module, overview] = await Promise.all([
    fetchJson(`/api/tracks/${encodeURIComponent(trackSlug)}/modules/${encodeURIComponent(moduleSlug)}`),
    fetchJson("/api/overview"),
  ]);
  const header = [
    el("div", { className: "breadcrumb" }, [el("a", { href: "#/tracks", text: "Trilhas" }), " / ", el("a", { href: `#/tracks/${module.track_slug}`, text: module.track_name })]),
    pageHead(module.title, module.summary, el("span", { className: "status-tag", text: module.status_label })),
  ];
  if (module.status === "locked") {
    return [...header, renderChallenge({ problem: "este módulo ainda está trancado.", next_step: `conclua antes: ${module.missing_prerequisites.map((link) => link.title).join(", ")}.` })];
  }
  const article = el("article", { className: "prose" });
  article.innerHTML = module.content_html;
  return [
    ...header,
    el("div", { className: "section grid grid-main" }, [
      article,
      el("div", { className: "sticky-pane" }, [
        module.exercises.length ? card("Exercícios", exerciseList(module.exercises)) : null,
        el("div", { className: module.exercises.length ? "section" : "" }, moduleSessionCard(module, overview)),
        el("div", { className: "section" }, completionCard(module)),
      ]),
    ]),
  ];
}

function scheduleDraftSave(slug, textarea, status) {
  let timer = null;
  let dirty = false;
  async function save() {
    clearTimeout(timer);
    if (!dirty) return;
    dirty = false;
    try {
      await sendJson(`/api/exercises/${encodeURIComponent(slug)}/draft`, "PUT", { content: textarea.value });
      status.textContent = "salvo";
    } catch (error) {
      dirty = true;
      status.textContent = error instanceof ChallengeError ? `não salvou: ${error.challenge.problem}` : "não salvou";
    }
  }
  textarea.addEventListener("input", () => {
    dirty = true;
    status.textContent = "editando…";
    clearTimeout(timer);
    timer = setTimeout(save, DRAFT_SAVE_DELAY_MS);
  });
  return save;
}

function handleEditorKeys(textarea, submit) {
  textarea.addEventListener("keydown", (event) => {
    if (event.key === "Tab" && !event.shiftKey) {
      event.preventDefault();
      textarea.setRangeText(TAB_SPACES, textarea.selectionStart, textarea.selectionEnd, "end");
      textarea.dispatchEvent(new Event("input"));
    }
    if (event.key === "Enter" && (event.ctrlKey || event.metaKey)) {
      event.preventDefault();
      submit();
    }
  });
}

function answerInput(exercise) {
  const noDraft = async () => {};
  if (exercise.answer_format === "choice") {
    const name = `answer-${exercise.slug}`;
    const list = el(
      "div",
      { className: "option-list", role: "radiogroup" },
      exercise.options.map((option) => el("label", { className: "option" }, [el("input", { type: "radio", name, value: option }), el("span", { text: option })])),
    );
    return { node: list, read: () => list.querySelector("input:checked")?.value || "", flushDraft: noDraft };
  }
  if (exercise.answer_format === "typed") {
    const input = el("input", { type: "text", className: "input", "aria-label": "Sua resposta", autocomplete: "off" });
    return { node: input, read: () => input.value, flushDraft: noDraft };
  }
  const isCode = exercise.answer_format === "code";
  const textarea = el("textarea", {
    className: isCode ? "input code-editor" : "input text-editor",
    spellcheck: isCode ? "false" : "true",
    "aria-label": isCode ? "Seu código" : "Sua resposta",
  });
  textarea.value = exercise.draft;
  const status = el("span", { className: "save-status", "aria-live": "polite" });
  const flushDraft = scheduleDraftSave(exercise.slug, textarea, status);
  return { node: textarea, status, read: () => textarea.value, textarea, flushDraft };
}

function testRunView(testRun) {
  if (testRun.timed_out) return [el("p", { text: "Tempo esgotado: o código demorou demais. Laço infinito ou algoritmo lento?" })];
  if (testRun.total === 0) return [el("p", { text: "Os testes nem chegaram a rodar:" }), el("pre", { className: "output", text: testRun.output })];
  const items = [el("p", { className: "result-message", text: `${testRun.passed}/${testRun.total} testes passaram` })];
  if (testRun.failures.length) {
    items.push(el("ul", { className: "failure-list" }, testRun.failures.map((failure) => el("li", {}, [el("code", { text: failure.name }), failure.message ? el("span", { className: "muted", text: ` ${failure.message}` }) : null]))));
  }
  return items;
}

function rubricView(rubric) {
  const items = [
    el(
      "ul",
      { className: "criteria-list" },
      rubric.criteria.map((item) => el("li", { "data-met": String(item.met) }, [icon(item.met ? "done" : "hint", { className: "icon criterion-mark" }), el("span", {}, [item.criterion, item.comment ? el("span", { className: "list-item-detail", text: item.comment }) : null])])),
    ),
  ];
  if (rubric.feedback) items.push(el("p", { text: rubric.feedback }));
  items.push(el("p", { className: "muted", text: `Correção: ${rubric.graded_by_label}` }));
  return items;
}

function submissionView(result, exercise) {
  const panel = el("div", { className: `result ${result.passed ? "result-ok" : ""}`.trim(), role: "status" });
  panel.append(el("p", { className: "result-message", text: result.message }));
  if (result.xp_message) panel.append(el("p", { className: "xp-earned", text: result.xp_message }));
  for (const promotion of result.promotions) {
    panel.append(el("p", { text: `${promotion.competency_name}: ${promotion.before_label} → ${promotion.after_label}` }));
  }
  if (result.test_run) panel.append(...testRunView(result.test_run));
  if (result.rubric) panel.append(...rubricView(result.rubric));
  if (result.answer_correct === false) panel.append(el("p", { className: "muted", text: "Releia o enunciado com calma e tente de novo." }));
  if (result.module_ready_message) {
    const [trackSlug, moduleSlug] = exercise.module_key.split("/");
    panel.append(el("p", {}, [result.module_ready_message, " ", el("a", { href: `#/tracks/${trackSlug}/${moduleSlug}`, text: "Ir para o módulo" })]));
  }
  return panel;
}

function selfAssessmentForm(exercise, assessment, usedAi, container) {
  const reference = el("div", { className: "prose" });
  reference.innerHTML = assessment.reference_html;
  const questions = assessment.rubric.map((criterion, index) =>
    el("fieldset", { className: "criterion-question" }, [
      el("legend", { text: criterion }),
      el("label", {}, [el("input", { type: "radio", name: `criterion-${index}`, value: "yes" }), " sim"]),
      el("label", {}, [el("input", { type: "radio", name: `criterion-${index}`, value: "no" }), " não"]),
    ]),
  );
  const { control, slot } = actionButton(
    "Registrar autoavaliação",
    async () => {
      const answers = questions.map((fieldset) => fieldset.querySelector("input:checked")?.value);
      if (answers.some((value) => value === undefined)) throw new ChallengeError({ problem: "falta marcar algum critério.", next_step: "responda sim ou não em todos." });
      const result = await sendJson(`/api/exercises/${encodeURIComponent(exercise.slug)}/self-assessments`, "POST", { met: answers.map((value) => value === "yes"), used_ai: usedAi });
      pendingSubmission = { slug: exercise.slug, result };
      route();
    },
    { variant: "primary" },
  );
  container.replaceChildren(
    card("Autoavaliação", [
      el("p", { text: assessment.message }),
      assessment.reference_html ? el("p", { className: "field-label", text: "Resposta de referência (uma boa, não a única):" }) : null,
      assessment.reference_html ? reference : null,
      el("p", { className: "field-label", text: "Agora seja honesta: a sua resposta…" }),
      ...questions,
      el("div", { className: "actions" }, [control]),
      slot,
    ]),
  );
}

function hintsCard(exercise, flushDraft) {
  if (exercise.hints_total === 0) return null;
  const children = [];
  if (exercise.hints_revealed.length) {
    children.push(el("ol", { className: "hint-list" }, exercise.hints_revealed.map((hint) => el("li", { text: hint }))));
  }
  const left = exercise.hints_total - exercise.hints_revealed.length;
  if (left > 0) {
    const { control, slot } = actionButton(
      `Pedir uma dica (${left})`,
      async () => {
        await flushDraft();
        const hint = await sendJson(`/api/exercises/${encodeURIComponent(exercise.slug)}/hints`, "POST");
        flash(`Dica ${hint.number} de ${hint.total}. Ela custa um pouco de XP, mas só um pouco.`, "info");
        route();
      },
      { iconName: "hint" },
    );
    children.push(el("p", { className: "muted", text: "Cada dica reduz um pouco o XP da primeira aprovação." }), el("div", { className: "actions" }, [control]), slot);
  } else {
    children.push(el("p", { className: "muted", text: "As dicas acabaram. Agora é com você, e você tem mais do que imagina." }));
  }
  return card("Dicas", children);
}

function historyCard(attempts) {
  if (!attempts.length) return null;
  const rows = attempts
    .slice()
    .reverse()
    .map((attempt) =>
      el("tr", {}, [
        el("td", { text: DATE_TIME_FORMAT.format(new Date(attempt.submitted_at)) }),
        el("td", { className: attempt.passed ? "cell-ok" : "cell-fail", text: attempt.passed ? "passou" : "não passou" }),
        el("td", { className: "numeric", text: attempt.score === null ? "-" : `${Math.round(attempt.score * 100)}%` }),
        el("td", { text: attempt.graded_by_label }),
        el("td", { className: "numeric", text: String(attempt.hints_used) }),
        el("td", { text: attempt.used_ai ? "sim" : "não" }),
      ]),
    );
  return card(
    "Suas tentativas",
    el("div", { className: "table-scroll" }, el("table", { className: "data-table" }, [
      el("thead", {}, el("tr", {}, [
        el("th", { text: "Quando" }),
        el("th", { text: "Resultado" }),
        el("th", { className: "numeric", text: "Nota" }),
        el("th", { text: "Correção" }),
        el("th", { className: "numeric", text: "Dicas" }),
        el("th", { text: "IA" }),
      ])),
      el("tbody", {}, rows),
    ])),
  );
}

async function renderExercise(slug) {
  const exercise = await fetchJson(`/api/exercises/${encodeURIComponent(slug)}`);
  const [trackSlug, moduleSlug] = exercise.module_key.split("/");
  const header = [
    el("div", { className: "breadcrumb" }, [el("a", { href: "#/tracks", text: "Trilhas" }), " / ", el("a", { href: `#/tracks/${trackSlug}/${moduleSlug}`, text: exercise.module_title })]),
    pageHead(
      exercise.title,
      null,
      el("div", { className: "meta-row" }, [
        difficultyDots(exercise.difficulty),
        el("span", { text: exercise.kind_label }),
        el("span", {}, [el("strong", { text: exercise.base_xp }), " XP"]),
        el("span", { text: exercise.status_label }),
        exercise.required ? el("span", { className: "tag", text: "obrigatório" }) : null,
      ]),
    ),
  ];
  if (!exercise.module_open) {
    return [...header, renderChallenge({ problem: "o módulo deste exercício ainda está trancado.", next_step: "conclua os pré-requisitos do módulo antes." })];
  }

  const statement = el("article", { className: "prose" });
  statement.innerHTML = exercise.statement_html;
  const input = answerInput(exercise);
  const usedAi = el("input", { type: "checkbox", id: "used-ai" });
  const resultSlot = el("div", { className: "result-slot" });
  const isCode = exercise.answer_format === "code";
  const { control, slot } = actionButton(
    isCode ? "Rodar testes" : "Enviar resposta",
    async () => {
      const answer = input.read();
      if (!answer.trim()) throw new ChallengeError({ problem: "a resposta está em branco.", next_step: "responda antes de enviar." });
      const body = isCode || exercise.answer_format === "text" ? { content: answer, used_ai: usedAi.checked } : { answer, used_ai: usedAi.checked };
      resultSlot.replaceChildren(el("p", { className: "muted", text: isCode ? "Rodando os testes…" : exercise.grading === "ollama" ? "Corrigindo com o Ollama, pode levar um minuto…" : "Corrigindo…" }));
      const result = await sendJson(`/api/exercises/${encodeURIComponent(exercise.slug)}/submissions`, "POST", body);
      if (result.self_assessment) {
        control.disabled = false;
        selfAssessmentForm(exercise, result.self_assessment, usedAi.checked, resultSlot);
        return;
      }
      pendingSubmission = { slug: exercise.slug, result };
      route();
    },
    { variant: "primary" },
  );
  if (input.textarea) handleEditorKeys(input.textarea, () => control.click());
  if (pendingSubmission && pendingSubmission.slug === exercise.slug) {
    resultSlot.append(submissionView(pendingSubmission.result, exercise));
    pendingSubmission = null;
  }

  return [
    ...header,
    el("div", { className: "split" }, [
      el("div", { className: "split-pane" }, [
        statement,
        el("div", { className: "section" }, hintsCard(exercise, input.flushDraft)),
        el("div", { className: "section" }, historyCard(exercise.attempts)),
      ]),
      el("div", { className: "split-pane sticky-pane" }, [
        card(isCode ? "Seu código" : "Sua resposta", [
          input.node,
          el("div", { className: "editor-foot" }, [
            input.status || el("span", {}),
            el("label", { className: "checkbox", for: "used-ai" }, [usedAi, " Usei IA nesta tentativa"]),
          ]),
          el("div", { className: "actions" }, [control, input.textarea ? el("span", { className: "muted", text: "Ctrl+Enter envia" }) : null]),
          slot,
          resultSlot,
        ]),
      ]),
    ]),
  ];
}

function masteryMeter(name, label, rank, maxRank) {
  return el(
    "div",
    { className: "mastery-meter", role: "img", "aria-label": `${name}: ${label}` },
    Array.from({ length: maxRank }, (_, index) => el("span", { className: "mastery-segment", "data-filled": String(index < rank) })),
  );
}

function competencyRows(competencies, maxRank) {
  return el(
    "div",
    {},
    competencies.map((competency) =>
      el("div", { className: "mastery-row", "data-solid": String(competency.is_solid) }, [
        el("span", { className: "mastery-name", text: competency.name }),
        masteryMeter(competency.name, competency.mastery_label, competency.mastery_rank, maxRank),
        el("span", { className: "mastery-label", "data-mastery": competency.mastery, text: competency.mastery_label }),
      ]),
    ),
  );
}

async function startDiagnostic() {
  await sendJson("/api/diagnostic", "POST");
  location.hash = "#/diagnostic";
}

function diagnosticCard(map) {
  if (map.open_diagnostic) {
    return card("Diagnóstico", [
      el("p", { text: `Pausado: ${map.open_diagnostic.answered} de ${map.open_diagnostic.total} respondidas. As respostas estão guardadas.` }),
      el("div", { className: "actions" }, [el("a", { className: "button button-primary", href: "#/diagnostic", text: "Continuar" })]),
    ]);
  }
  if (!map.last_diagnostic_at) {
    const { control, slot } = actionButton("Começar diagnóstico", startDiagnostic, { variant: "primary" });
    return card("Diagnóstico", [
      el("p", { text: "O mapa ainda está em branco. Descubra o que você já sabe: sem consulta, sem nota, só um retrato honesto." }),
      el("div", { className: "actions" }, [control]),
      slot,
    ]);
  }
  const { control, slot } = actionButton("Refazer", startDiagnostic);
  return card("Diagnóstico", [
    el("p", { className: "muted", text: `Último feito em ${SHORT_DATE_FORMAT.format(new Date(map.last_diagnostic_at))}.` }),
    el("div", { className: "actions" }, [el("a", { className: "button", href: "#/diagnostic", text: "Ver resultado" }), control]),
    slot,
  ]);
}

function goalPicker(levels, currentKey) {
  const select = el("select", { className: "input", "aria-label": "Módulo que você quer alcançar" }, [
    el("option", { value: "", text: "Escolha um módulo…" }),
    ...levels.flat().map((module) => el("option", { value: module.key, selected: module.key === currentKey, text: module.title })),
  ]);
  const { control, slot } = actionButton(
    "Definir",
    async () => {
      if (!select.value) throw new ChallengeError({ problem: "nenhum módulo escolhido.", next_step: "escolha um módulo na lista." });
      const result = await sendJson("/api/goal", "PUT", { module_key: select.value });
      flash(result.message);
      route();
    },
    { variant: "primary" },
  );
  return el("div", {}, [el("div", { className: "inline-form" }, [select, control]), slot]);
}

function goalCard(path, levels) {
  if (!path.goal) {
    return card("Objetivo", [
      el("p", { className: "muted", text: "Escolha aonde quer chegar e o sistema monta o caminho, com os pré-requisitos na ordem certa." }),
      goalPicker(levels, null),
    ]);
  }
  const children = [el("p", { className: "goal-title" }, el("a", { href: moduleHref(path.goal), text: path.goal.title }))];
  if (path.reached) {
    children.push(el("p", { text: "Você já chegou aqui. Hora de escolher o próximo topo." }));
  } else {
    const notes = Object.fromEntries(path.steps.filter((step) => step.likely_known).map((step) => [step.module.key, LIKELY_KNOWN_NOTE]));
    children.push(moduleList(path.steps.map((step) => step.module), { showTrack: true, notes }));
  }
  const { control, slot } = actionButton(
    "Remover objetivo",
    async () => {
      await sendJson("/api/goal", "DELETE");
      flash("Objetivo removido. A tela Hoje volta a sugerir pela ordem das trilhas.", "info");
      route();
    },
    { variant: "quiet" },
  );
  children.push(el("details", { className: "goal-change" }, [el("summary", { text: "Trocar objetivo" }), goalPicker(levels, path.goal.key), el("div", { className: "actions" }, [control]), slot]));
  return card("Objetivo", children);
}

function gapsCard(path, titlesByKey) {
  const title = path.goal ? "Lacunas no caminho" : "Lacunas apontadas pelo diagnóstico";
  if (!path.gaps.length) return card(title, el("p", { className: "muted", text: "Nenhuma lacuna à vista." }));
  return card(
    title,
    el(
      "ul",
      { className: "list" },
      path.gaps.map((gap) =>
        el("li", { className: "list-item" }, [
          el("span", {}),
          el("span", {}, [
            el("span", { className: "list-item-title", text: gap.name }),
            el("span", { className: "list-item-detail" }, gap.module_keys.length ? ["estude: ", ...gap.module_keys.flatMap((key, index) => [index ? ", " : "", el("a", { href: moduleKeyHref(key), text: titlesByKey.get(key) || key })])] : []),
          ]),
          el("span", { className: "mastery-label", "data-mastery": gap.mastery, text: gap.mastery_label }),
        ]),
      ),
    ),
  );
}

function graphCard(levels) {
  return card(
    "Pré-requisitos",
    el(
      "div",
      { className: "graph-levels" },
      levels.map((level, index) =>
        el("div", {}, [
          el("p", { className: "graph-level-label", text: `nível ${index + 1}` }),
          ...level.map((module) =>
            el("a", {
              className: "graph-node",
              href: moduleHref(module),
              "data-status": module.status,
              title: module.prerequisites.length ? `precisa de: ${module.prerequisites.map((link) => link.title).join(", ")}` : "sem pré-requisitos",
              text: module.title,
            }),
          ),
        ]),
      ),
    ),
  );
}

async function renderMap() {
  const [map, path, levels] = await Promise.all([fetchJson("/api/knowledge-map"), fetchJson("/api/learning-path"), fetchJson("/api/module-levels")]);
  const content = [pageHead("Mapa de conhecimento", "Domínio se prova com evidência, não com horas.")];
  if (!map.areas.length) {
    content.push(renderChallenge({ problem: "nenhuma competência carregada ainda.", next_step: "confira a pasta data/ e abra o hone de novo." }));
    return content;
  }
  const titlesByKey = new Map(levels.flat().map((module) => [module.key, module.title]));
  content.push(
    el("div", { className: "section grid grid-main" }, [
      el("div", {}, [
        card("Competências", map.areas.map((area) => el("div", { className: "area-block" }, [el("h3", { className: "area-name", text: area.name }), competencyRows(area.competencies, map.max_mastery_rank)]))),
        el("div", { className: "section" }, graphCard(levels)),
      ]),
      el("div", {}, [
        diagnosticCard(map),
        el("div", { className: "section" }, goalCard(path, levels)),
        el("div", { className: "section" }, gapsCard(path, titlesByKey)),
      ]),
    ]),
  );
  return content;
}

function diagnosticReportView(report) {
  return [
    pageHead("Resultado do diagnóstico", `Feito em ${SHORT_DATE_FORMAT.format(new Date(report.finished_at))}.`),
    el("p", { className: "streak-message", text: report.message }),
    el(
      "div",
      { className: "section" },
      card(
        null,
        report.results.map((result) =>
          el("div", { className: "mastery-row", "data-solid": String(result.is_solid) }, [
            el("span", {}, [el("span", { className: "mastery-name", text: result.competency_name }), el("span", { className: "list-item-detail", text: `${result.correct}/${result.answered} certas${result.guessed ? ` · ${result.guessed} no chute` : ""}` })]),
            masteryMeter(result.competency_name, result.assessed_label, result.assessed_rank, report.max_mastery_rank),
            el("span", { className: "mastery-label", "data-mastery": result.assessed, text: result.assessed_label }),
          ]),
        ),
      ),
    ),
    el("div", { className: "actions" }, [el("a", { className: "button button-primary", href: "#/map", text: "Ver o mapa e escolher um objetivo" })]),
  ];
}

function diagnosticFeedbackView(feedback) {
  const panel = el("div", { className: `result ${feedback.is_correct ? "result-ok" : ""}`.trim(), role: "status" }, [el("p", { className: "result-message", text: feedback.message })]);
  if (feedback.correct_answer) panel.append(el("p", {}, ["Resposta: ", el("strong", { text: feedback.correct_answer })]));
  if (feedback.explanation) panel.append(el("p", { className: "muted", text: feedback.explanation }));
  panel.append(el("div", { className: "actions" }, [button(feedback.report ? "Ver resultado" : "Próxima pergunta", () => route(), { variant: "primary" })]));
  return panel;
}

function diagnosticQuestionView(state) {
  const question = state.question;
  const startedAt = performance.now();
  const prompt = el("article", { className: "prose" });
  prompt.innerHTML = question.prompt_html;
  let readAnswer;
  let answerNode;
  if (question.is_choice) {
    answerNode = el(
      "div",
      { className: "option-list", role: "radiogroup" },
      question.options.map((option) => el("label", { className: "option" }, [el("input", { type: "radio", name: `question-${question.id}`, value: option }), el("span", { text: option })])),
    );
    readAnswer = () => answerNode.querySelector("input:checked")?.value || "";
  } else {
    answerNode = el("input", { type: "text", className: "input", "aria-label": "Sua resposta", autocomplete: "off" });
    readAnswer = () => answerNode.value;
  }
  const feedbackSlot = el("div", { className: "action-error" });

  async function send(confidence) {
    const answer = confidence === "dont_know" ? "" : readAnswer();
    if (confidence !== "dont_know" && !answer.trim()) {
      feedbackSlot.replaceChildren(renderChallenge({ problem: "falta escolher uma resposta.", next_step: "responda, ou use “Não sei”: é resposta válida." }));
      return;
    }
    for (const control of buttons) control.disabled = true;
    try {
      const feedback = await sendJson("/api/diagnostic/answers", "POST", {
        question_id: question.id,
        answer,
        confidence,
        duration_seconds: Math.round((performance.now() - startedAt) / 1000),
      });
      pendingDiagnosticFeedback = feedback;
      route();
    } catch (error) {
      for (const control of buttons) control.disabled = false;
      if (!(error instanceof ChallengeError)) throw error;
      feedbackSlot.replaceChildren(renderChallenge(error.challenge));
    }
  }

  const buttons = [
    button("Eu sabia", () => send("sure"), { variant: "primary" }),
    button("Chutei", () => send("guess")),
    button("Não sei", () => send("dont_know"), { variant: "quiet" }),
  ];
  return [
    pageHead(
      "Diagnóstico",
      "Sem consulta e sem pressa. Aqui não tem nota: tem um mapa do que você já sabe.",
      el("div", {}, [el("span", { className: "stat-value", text: `${state.answered + 1}/${state.total}` }), el("span", { className: "stat-label", text: "perguntas" })]),
    ),
    el("div", { className: "section" }, progressBar(state.answered, state.total, "Progresso do diagnóstico")),
    el("div", { className: "section" }, card(null, [
      el("p", { className: "question-meta", text: `${question.competency_name} · ${question.kind_label}` }),
      prompt,
      answerNode,
      el("p", { className: "muted", text: "Depois de responder, diga se você sabia ou chutou. Pode parar quando quiser: as respostas ficam salvas." }),
      el("div", { className: "actions" }, buttons),
      feedbackSlot,
    ])),
  ];
}

async function renderDiagnostic() {
  if (pendingDiagnosticFeedback) {
    const feedback = pendingDiagnosticFeedback;
    pendingDiagnosticFeedback = null;
    return [pageHead("Diagnóstico", null), diagnosticFeedbackView(feedback)];
  }
  const state = await fetchJson("/api/diagnostic");
  if (state && state.question) return diagnosticQuestionView(state);
  try {
    return diagnosticReportView(await fetchJson("/api/diagnostic/report"));
  } catch (error) {
    if (!(error instanceof ChallengeError)) throw error;
    const { control, slot } = actionButton("Começar diagnóstico", startDiagnostic, { variant: "primary" });
    return [
      pageHead("Diagnóstico", "Você ainda não fez nenhum. São perguntas curtas, e dá para parar no meio."),
      el("div", { className: "actions" }, [control]),
      slot,
    ];
  }
}

function percent(value) {
  return value === null ? "-" : `${Math.round(value * 100)}%`;
}

async function renderStats() {
  const stats = await fetchJson("/api/stats");
  const content = [
    pageHead(
      "Métricas",
      "Competência vem de exercício aprovado; atividade, de tentar. O primeiro é o que importa.",
      el("div", { className: "stat-strip" }, [
        el("div", {}, [el("span", { className: "stat-value", "data-accent": "true", text: stats.xp.competency }), el("span", { className: "stat-label", text: "XP de competência" })]),
        el("div", {}, [el("span", { className: "stat-value", text: stats.xp.activity }), el("span", { className: "stat-label", text: "XP de atividade" })]),
        el("div", {}, [el("span", { className: "stat-value", text: stats.exercises_passed }), el("span", { className: "stat-label", text: "exercícios aprovados" })]),
      ]),
    ),
  ];
  if (!stats.competencies.length) {
    content.push(el("p", { className: "muted section", text: "Nenhum exercício carregado ainda." }));
    return content;
  }
  const rows = stats.competencies.map((item) =>
    el("tr", {}, [
      el("td", { text: item.name }),
      el("td", {}, [progressBar(item.exercises_passed, item.exercises_total, `Exercícios aprovados em ${item.name}`), el("span", { className: "muted", text: `${item.exercises_passed}/${item.exercises_total}` })]),
      el("td", { className: "numeric", text: percent(item.first_try_rate) }),
      el("td", { className: "numeric", text: String(item.attempts) }),
      el("td", { className: "numeric", text: String(item.hints_used) }),
      el("td", { className: "numeric", text: String(item.ai_attempts) }),
    ]),
  );
  content.push(
    el("div", { className: "section" }, card("Prática por competência", el("div", { className: "table-scroll" }, el("table", { className: "data-table" }, [
      el("thead", {}, el("tr", {}, [
        el("th", { text: "Competência" }),
        el("th", { text: "Aprovados" }),
        el("th", { className: "numeric", text: "De primeira" }),
        el("th", { className: "numeric", text: "Tentativas" }),
        el("th", { className: "numeric", text: "Dicas" }),
        el("th", { className: "numeric", text: "Com IA" }),
      ])),
      el("tbody", {}, rows),
    ])))),
  );
  return content;
}

function currentRoute() {
  const parts = location.hash.replace(/^#\/?/, "").split("/").filter(Boolean).map(decodeURIComponent);
  if (parts[0] === "tracks" && parts.length === 3) return { nav: "tracks", render: () => renderModule(parts[1], parts[2]) };
  if (parts[0] === "tracks" && parts.length === 2) return { nav: "tracks", render: () => renderTrack(parts[1]) };
  if (parts[0] === "tracks") return { nav: "tracks", render: renderTracks };
  if (parts[0] === "exercises" && parts.length === 2) return { nav: "tracks", render: () => renderExercise(parts[1]) };
  if (parts[0] === "map") return { nav: "map", render: renderMap };
  if (parts[0] === "diagnostic") return { nav: "map", render: renderDiagnostic };
  if (parts[0] === "stats") return { nav: "stats", render: renderStats };
  return { nav: "today", render: renderToday };
}

function highlightNav(nav) {
  for (const link of document.querySelectorAll("[data-nav]")) {
    if (link.dataset.nav === nav) link.setAttribute("aria-current", "page");
    else link.removeAttribute("aria-current");
  }
}

async function route() {
  const { nav, render } = currentRoute();
  highlightNav(nav);
  if (activeChart) {
    activeChart.destroy();
    activeChart = null;
  }
  const flashNode = renderFlash();
  try {
    view.replaceChildren(...[flashNode, ...(await render())].filter(Boolean));
  } catch (error) {
    const challenge = error instanceof ChallengeError ? error.challenge : { problem: error.message, next_step: "recarregue a página." };
    view.replaceChildren(renderChallenge(challenge));
  }
  window.scrollTo(0, 0);
}

setupThemeSwitch();
window.addEventListener("hashchange", route);
route();
