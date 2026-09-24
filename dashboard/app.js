"use strict";

const THEME_STORAGE_KEY = "hone-theme";
const THEME_SEQUENCE = ["auto", "light", "dark"];
const THEME_LABELS = { auto: "tema: automático", light: "tema: claro", dark: "tema: escuro" };
const STATUS_MARKERS = { completed: "✔", in_progress: "▶", available: "○", locked: "·" };
const WEEKDAY_FORMAT = new Intl.DateTimeFormat("pt-BR", { weekday: "short", day: "2-digit" });
const SHORT_DATE_FORMAT = new Intl.DateTimeFormat("pt-BR", { day: "2-digit", month: "2-digit" });
const LIKELY_KNOWN_NOTE = "o diagnóstico diz que você já aplica isto";
const LONG_DATE_FORMAT = new Intl.DateTimeFormat("pt-BR", { weekday: "long", day: "numeric", month: "long" });
const API_UNREACHABLE = {
  problem: "a API não respondeu.",
  next_step: "confira se o terminal com hone serve ainda está rodando.",
};

const view = document.getElementById("view");
let activeChart = null;

function el(tag, attributes = {}, children = []) {
  const node = document.createElement(tag);
  for (const [name, value] of Object.entries(attributes)) {
    if (value === null || value === undefined) continue;
    if (name === "text") node.textContent = value;
    else if (name === "className") node.className = value;
    else node.setAttribute(name, value);
  }
  for (const child of [].concat(children)) {
    if (child === null || child === undefined || child === false) continue;
    node.append(child instanceof Node ? child : document.createTextNode(String(child)));
  }
  return node;
}

function readStoredTheme() {
  try {
    return localStorage.getItem(THEME_STORAGE_KEY) || "auto";
  } catch {
    return "auto";
  }
}

function storeTheme(theme) {
  try {
    localStorage.setItem(THEME_STORAGE_KEY, theme);
  } catch {
    return;
  }
}

function applyTheme(theme) {
  if (theme === "auto") document.documentElement.removeAttribute("data-theme");
  else document.documentElement.setAttribute("data-theme", theme);
  document.getElementById("theme-toggle").textContent = THEME_LABELS[theme];
}

function setupThemeToggle() {
  let theme = readStoredTheme();
  applyTheme(theme);
  document.getElementById("theme-toggle").addEventListener("click", () => {
    theme = THEME_SEQUENCE[(THEME_SEQUENCE.indexOf(theme) + 1) % THEME_SEQUENCE.length];
    storeTheme(theme);
    applyTheme(theme);
    route();
  });
}

class ChallengeError extends Error {
  constructor(challenge) {
    super(challenge.problem);
    this.challenge = challenge;
  }
}

async function fetchJson(path) {
  let response;
  try {
    response = await fetch(path, { headers: { Accept: "application/json" } });
  } catch {
    throw new ChallengeError(API_UNREACHABLE);
  }
  const body = await response.json().catch(() => ({}));
  if (!response.ok) {
    const challenge = body.challenge || {
      problem: typeof body.detail === "string" ? body.detail : "algo não saiu como esperado.",
      next_step: "volte para o início e tente de novo.",
    };
    throw new ChallengeError(challenge);
  }
  return body;
}

function cssToken(name) {
  return getComputedStyle(document.documentElement).getPropertyValue(`--${name}`).trim();
}

function renderChallenge(challenge) {
  return el("div", { className: "challenge", role: "alert" }, [
    el("p", { className: "challenge-title", text: "Desafio" }),
    el("p", { text: capitalize(challenge.problem) }),
    el("p", { className: "muted", text: `Próximo passo: ${challenge.next_step}` }),
  ]);
}

function capitalize(text) {
  return text.charAt(0).toUpperCase() + text.slice(1);
}

function moduleHref(module) {
  return `#/tracks/${module.track_slug}/${module.slug}`;
}

function progressBar(done, total, label) {
  const percent = total ? Math.round((100 * done) / total) : 0;
  return el(
    "div",
    { className: "progress-bar", role: "progressbar", "aria-valuenow": percent, "aria-valuemin": 0, "aria-valuemax": 100, "aria-label": label },
    el("div", { className: "progress-bar-fill", style: `width: ${percent}%` }),
  );
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

function moduleList(modules, { showTrack = false } = {}) {
  return el(
    "ul",
    { className: "list" },
    modules.map((module) => {
      const detail = module.missing_prerequisites.length
        ? `precisa de: ${module.missing_prerequisites.map((link) => link.title).join(", ")}`
        : module.summary;
      return el("li", { className: "list-item", "data-status": module.status }, [
        el("span", { className: "marker", "data-status": module.status, "aria-hidden": "true", text: STATUS_MARKERS[module.status] }),
        el("span", {}, [
          el("span", { className: "list-item-title" }, el("a", { href: moduleHref(module), text: showTrack ? module.title : `${module.position}. ${module.title}` })),
          el("span", { className: "list-item-detail", text: detail }),
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
        datasets: [{ data: days.map((entry) => entry.minutes), backgroundColor: cssToken("accent"), borderRadius: 4, maxBarThickness: 28 }],
      },
      options: {
        maintainAspectRatio: false,
        animation: window.matchMedia("(prefers-reduced-motion: reduce)").matches ? false : undefined,
        plugins: { legend: { display: false }, tooltip: { callbacks: { label: (item) => `${item.parsed.y} min` } } },
        scales: {
          x: { grid: { display: false }, ticks: { color: muted } },
          y: { beginAtZero: true, grid: { color: cssToken("border") }, border: { display: false }, ticks: { color: muted, precision: 0 } },
        },
      },
    });
  });
  return box;
}

function statusChips(overview) {
  const chips = [];
  if (overview.todays_checkin) {
    chips.push(el("span", { className: "chip chip-ok", text: `check-in feito: ${overview.todays_checkin.intention}` }));
  } else {
    chips.push(el("span", { className: "chip chip-pending" }, ["check-in pendente — ", el("code", { text: "hone checkin" })]));
  }
  if (overview.active_session) {
    const topic = overview.active_session.module_title || "estudo livre";
    chips.push(el("span", { className: "chip chip-live", text: `sessão rolando há ${overview.active_session.minutes} min · ${topic}` }));
  }
  return el("div", { className: "status-line" }, chips);
}

async function renderToday() {
  const overview = await fetchJson("/api/overview");
  const streak = overview.streak;
  const dayWord = streak.current === 1 ? "dia seguido" : "dias seguidos";
  const content = [
    el("h1", { text: `Oi, ${overview.user_name}.` }),
    el("p", { className: "lead", text: capitalize(LONG_DATE_FORMAT.format(new Date(`${overview.today}T12:00:00`))) }),
    el("div", { className: "streak" }, [
      el("span", { className: "streak-number", "data-alive": String(streak.current > 0), text: streak.current }),
      el("span", { className: "streak-label", text: dayWord }),
    ]),
    el("p", { className: "streak-message", text: streak.message }),
    statusChips(overview),
  ];

  if (overview.tracks.length === 0) {
    content.push(renderChallenge({ problem: "nenhuma trilha carregada ainda.", next_step: "rode hone content sync no terminal." }));
    return content;
  }
  if (overview.next_modules.length) {
    const heading = overview.goal ? `Continue daqui · rumo a ${overview.goal.title}` : "Continue daqui";
    content.push(el("section", { className: "section" }, [el("h2", { text: heading }), moduleList(overview.next_modules, { showTrack: true })]));
  }
  content.push(el("section", { className: "section" }, [el("h2", { text: "Últimos 14 dias" }), studyChart(overview.study_minutes)]));
  content.push(el("section", { className: "section" }, [el("h2", { text: "Trilhas" }), trackProgressList(overview.tracks)]));
  return content;
}

async function renderTracks() {
  const tracks = await fetchJson("/api/tracks");
  return [
    el("h1", { text: "Trilhas" }),
    el("p", { className: "lead", text: "Cada uma é um caminho, não uma lista de tarefas." }),
    el("section", { className: "section" }, tracks.length ? trackProgressList(tracks) : el("p", { className: "muted", text: "Nenhuma trilha carregada. Rode hone content sync." })),
  ];
}

async function renderTrack(trackSlug) {
  const track = await fetchJson(`/api/tracks/${encodeURIComponent(trackSlug)}`);
  return [
    el("div", { className: "breadcrumb" }, el("a", { href: "#/tracks", text: "Trilhas" })),
    el("h1", { text: track.name }),
    el("p", { className: "lead", text: track.description }),
    el("section", { className: "section" }, [
      el("h2", { text: `${track.completed} de ${track.total} concluídos` }),
      progressBar(track.completed, track.total, `Progresso em ${track.name}`),
    ]),
    el("section", { className: "section" }, moduleList(track.modules)),
  ];
}

function moduleCallout(module) {
  if (module.status === "completed") {
    return el("div", { className: "callout", text: "Você já concluiu este módulo. Reler é revisão, não retrocesso." });
  }
  return el("div", { className: "callout" }, [
    "Estude pelo terminal para registrar a sessão: ",
    el("code", { text: `hone session start ${module.slug}` }),
    ". Respondeu a recuperação ativa sem olhar? ",
    el("code", { text: `hone done ${module.key}` }),
  ]);
}

async function renderModule(trackSlug, moduleSlug) {
  const module = await fetchJson(`/api/tracks/${encodeURIComponent(trackSlug)}/modules/${encodeURIComponent(moduleSlug)}`);
  const header = [
    el("div", { className: "breadcrumb" }, [el("a", { href: "#/tracks", text: "Trilhas" }), " / ", el("a", { href: `#/tracks/${module.track_slug}`, text: module.track_name })]),
    el("h1", { text: module.title }),
    el("p", { className: "lead", text: `${module.status_label} · ${module.summary}` }),
  ];
  if (module.status === "locked") {
    const missing = module.missing_prerequisites.map((link) => link.title).join(", ");
    return [...header, renderChallenge({ problem: "este módulo ainda está trancado.", next_step: `conclua antes: ${missing}.` })];
  }
  const article = el("article", { className: "prose" });
  article.innerHTML = module.content_html;
  return [...header, article, moduleCallout(module)];
}

function moduleKeyHref(key) {
  return `#/tracks/${key}`;
}

function masteryMeter(competency, maxRank) {
  return el(
    "div",
    { className: "mastery-meter", role: "img", "aria-label": `${competency.name}: ${competency.mastery_label}` },
    Array.from({ length: maxRank }, (_, index) => el("span", { className: "mastery-segment", "data-filled": String(index < competency.mastery_rank) })),
  );
}

function competencyRows(competencies, maxRank) {
  return el(
    "div",
    {},
    competencies.map((competency) =>
      el("div", { className: "mastery-row", "data-solid": String(competency.is_solid) }, [
        el("span", { className: "mastery-name", text: competency.name }),
        masteryMeter(competency, maxRank),
        el("span", { className: "mastery-label", "data-mastery": competency.mastery, text: competency.mastery_label }),
      ]),
    ),
  );
}

function diagnosticNotice(map) {
  if (map.open_diagnostic) {
    return el("div", { className: "callout" }, [
      `Diagnóstico pausado: ${map.open_diagnostic.answered} de ${map.open_diagnostic.total} respondidas. Continue com `,
      el("code", { text: "hone diagnostic start" }),
      ".",
    ]);
  }
  if (!map.last_diagnostic_at) {
    return el("div", { className: "callout" }, [
      "O mapa ainda está em branco. Descubra o que você já sabe com ",
      el("code", { text: "hone diagnostic start" }),
      ": sem consulta, sem nota, só um retrato honesto.",
    ]);
  }
  return null;
}

function pathStepList(steps) {
  return el(
    "ol",
    { className: "list" },
    steps.map((step) => {
      const module = step.module;
      const detail = step.likely_known ? LIKELY_KNOWN_NOTE : module.summary;
      return el("li", { className: "list-item", "data-status": module.status }, [
        el("span", { className: "marker", "data-status": module.status, "aria-hidden": "true", text: STATUS_MARKERS[module.status] }),
        el("span", {}, [
          el("span", { className: "list-item-title" }, el("a", { href: moduleHref(module), text: module.title })),
          el("span", { className: step.likely_known ? "list-item-detail note-known" : "list-item-detail", text: detail }),
        ]),
        el("span", { className: "status-tag", text: module.status_label }),
      ]);
    }),
  );
}

function goalSection(path) {
  const children = [el("h2", { text: "Objetivo" })];
  if (!path.goal) {
    children.push(el("div", { className: "callout" }, ["Escolha aonde quer chegar e o sistema monta o caminho: ", el("code", { text: "hone goal <módulo>" }), "."]));
  } else if (path.reached) {
    children.push(el("p", { text: `Você já chegou em “${path.goal.title}”. Hora de escolher o próximo topo.` }));
  } else {
    children.push(el("p", { className: "goal-title" }, el("a", { href: moduleHref(path.goal), text: path.goal.title })));
    children.push(pathStepList(path.steps));
  }
  return el("section", { className: "section" }, children);
}

function gapsSection(path, titlesByKey) {
  const title = path.goal ? "Lacunas no caminho" : "Lacunas apontadas pelo diagnóstico";
  if (!path.gaps.length) {
    return el("section", { className: "section" }, [el("h2", { text: title }), el("p", { className: "muted", text: "Nenhuma lacuna à vista." })]);
  }
  return el("section", { className: "section" }, [
    el("h2", { text: title }),
    el(
      "ul",
      { className: "list" },
      path.gaps.map((gap) =>
        el("li", { className: "gap-item" }, [
          el("span", { className: "list-item-title", text: gap.name }),
          el("span", { className: "mastery-label", "data-mastery": gap.mastery, text: gap.mastery_label }),
          el(
            "span",
            { className: "list-item-detail" },
            gap.module_keys.length ? ["estude: ", ...gap.module_keys.flatMap((key, index) => [index ? ", " : "", el("a", { href: moduleKeyHref(key), text: titlesByKey.get(key) || key })])] : [],
          ),
        ]),
      ),
    ),
  ]);
}

function graphSection(levels) {
  return el("section", { className: "section" }, [
    el("h2", { text: "Pré-requisitos" }),
    el(
      "div",
      { className: "graph-levels" },
      levels.map((level, index) =>
        el("div", { className: "graph-level" }, [
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
  ]);
}

async function renderMap() {
  const [map, path, levels] = await Promise.all([fetchJson("/api/knowledge-map"), fetchJson("/api/learning-path"), fetchJson("/api/module-levels")]);
  const lead = map.last_diagnostic_at
    ? `Último diagnóstico em ${SHORT_DATE_FORMAT.format(new Date(map.last_diagnostic_at))}. Domínio se prova com evidência, não com horas.`
    : "Domínio se prova com evidência, não com horas.";
  const content = [el("h1", { text: "Mapa de conhecimento" }), el("p", { className: "lead", text: lead }), diagnosticNotice(map)];
  if (!map.areas.length) {
    content.push(renderChallenge({ problem: "nenhuma competência carregada ainda.", next_step: "rode hone content sync no terminal." }));
    return content.filter(Boolean);
  }
  const titlesByKey = new Map(levels.flat().map((module) => [module.key, module.title]));
  content.push(goalSection(path), gapsSection(path, titlesByKey));
  content.push(
    el("section", { className: "section" }, [
      el("h2", { text: "Competências" }),
      ...map.areas.map((area) => el("div", { className: "area-block" }, [el("h3", { className: "area-name", text: area.name }), competencyRows(area.competencies, map.max_mastery_rank)])),
    ]),
  );
  content.push(graphSection(levels));
  return content.filter(Boolean);
}

function currentRoute() {
  const parts = location.hash.replace(/^#\/?/, "").split("/").filter(Boolean).map(decodeURIComponent);
  if (parts[0] === "tracks" && parts.length === 3) return { nav: "tracks", render: () => renderModule(parts[1], parts[2]) };
  if (parts[0] === "tracks" && parts.length === 2) return { nav: "tracks", render: () => renderTrack(parts[1]) };
  if (parts[0] === "tracks") return { nav: "tracks", render: renderTracks };
  if (parts[0] === "map") return { nav: "map", render: renderMap };
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
  try {
    view.replaceChildren(...(await render()));
  } catch (error) {
    const challenge = error instanceof ChallengeError ? error.challenge : { problem: error.message, next_step: "recarregue a página." };
    view.replaceChildren(renderChallenge(challenge));
  }
  window.scrollTo(0, 0);
}

setupThemeToggle();
window.addEventListener("hashchange", route);
route();
