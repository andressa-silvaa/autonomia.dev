"use strict";

const THEME_STORAGE_KEY = "formacao-theme";
const THEME_SEQUENCE = ["auto", "light", "dark"];
const THEME_LABELS = { auto: "tema: automático", light: "tema: claro", dark: "tema: escuro" };
const STATUS_MARKERS = { completed: "✔", in_progress: "▶", available: "○", locked: "·" };
const WEEKDAY_FORMAT = new Intl.DateTimeFormat("pt-BR", { weekday: "short", day: "2-digit" });
const LONG_DATE_FORMAT = new Intl.DateTimeFormat("pt-BR", { weekday: "long", day: "numeric", month: "long" });
const API_UNREACHABLE = {
  problem: "a API não respondeu.",
  next_step: "confira se o terminal com formacao serve ainda está rodando.",
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
  return `#/trilhas/${module.track_slug}/${module.slug}`;
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
        el("a", { href: `#/trilhas/${track.slug}`, text: track.name }),
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
    chips.push(el("span", { className: "chip chip-pending" }, ["check-in pendente — ", el("code", { text: "formacao checkin" })]));
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
    content.push(renderChallenge({ problem: "nenhuma trilha carregada ainda.", next_step: "rode formacao content sync no terminal." }));
    return content;
  }
  if (overview.next_modules.length) {
    content.push(el("section", { className: "section" }, [el("h2", { text: "Continue daqui" }), moduleList(overview.next_modules, { showTrack: true })]));
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
    el("section", { className: "section" }, tracks.length ? trackProgressList(tracks) : el("p", { className: "muted", text: "Nenhuma trilha carregada. Rode formacao content sync." })),
  ];
}

async function renderTrack(trackSlug) {
  const track = await fetchJson(`/api/tracks/${encodeURIComponent(trackSlug)}`);
  return [
    el("div", { className: "breadcrumb" }, el("a", { href: "#/trilhas", text: "Trilhas" })),
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
    el("code", { text: `formacao session start ${module.slug}` }),
    ". Respondeu a recuperação ativa sem olhar? ",
    el("code", { text: `formacao done ${module.key}` }),
  ]);
}

async function renderModule(trackSlug, moduleSlug) {
  const module = await fetchJson(`/api/tracks/${encodeURIComponent(trackSlug)}/modules/${encodeURIComponent(moduleSlug)}`);
  const header = [
    el("div", { className: "breadcrumb" }, [el("a", { href: "#/trilhas", text: "Trilhas" }), " / ", el("a", { href: `#/trilhas/${module.track_slug}`, text: module.track_name })]),
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

function currentRoute() {
  const parts = location.hash.replace(/^#\/?/, "").split("/").filter(Boolean).map(decodeURIComponent);
  if (parts[0] === "trilhas" && parts.length === 3) return { nav: "tracks", render: () => renderModule(parts[1], parts[2]) };
  if (parts[0] === "trilhas" && parts.length === 2) return { nav: "tracks", render: () => renderTrack(parts[1]) };
  if (parts[0] === "trilhas") return { nav: "tracks", render: renderTracks };
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
