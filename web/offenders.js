// The repeat offenders page: which places flood again and again, and what that costs.
//
// `offendersModel` decides the order and every figure, and is pure so it can be checked against
// the Python (tests/test_offenders.py). Everything shown comes from data/<city>-floods.json,
// which holds only what the flood workflow measured. The page says what it does not show.

import { ageWords } from "./glyph.js";

const POLL_MS = 60_000;
export const STALE_AFTER_S = 3 * 3600 + 120;     // the file is refreshed hourly; this is late
export const PEAK_CAP_CM = 60;                   // a mark is full height at this depth
export const NOT_YET_RECORDED = [
  "How much rain it took to flood each time",
  "How long the water took to drain away",
  "How quickly a pump was started once asked",
];

/** "45 min", "1 h 5 min", "12 h". Whole minutes in, plain words out. */
export function duration(minutes) {
  const m = Math.round(minutes);
  if (m < 60) return `${m} min`;
  const h = Math.floor(m / 60), rest = m % 60;
  return rest ? `${h} h ${rest} min` : `${h} h`;
}

export function toneFor(highCm) {
  return highCm < 12 ? "shallow" : highCm <= 30 ? "water" : "deep";
}

/** Sites with a confirmed flood, ranked as history.ranking() does: minutes blocked for cars,
 *  then floods, then name. Unconfirmed floods never move a site up. */
export function offendersModel(doc) {
  const ranked = doc.sites.filter((s) => s.confirmed > 0).sort((a, b) =>
    b.cars_min - a.cars_min || b.confirmed - a.confirmed || (a.name < b.name ? -1 : a.name > b.name ? 1 : 0));
  const unranked = doc.sites.filter((s) => s.confirmed === 0 && s.unconfirmed > 0);
  const quiet = doc.sites.filter((s) => s.confirmed === 0 && s.unconfirmed === 0);
  return {
    sample: Boolean(doc.sample),
    watched: doc.sites.length,
    floodedSites: ranked.length,
    empty: ranked.length === 0 && unranked.length === 0,
    ranked: ranked.map((site, index) => ({ ...site, rank: index + 1 })),
    unranked, quietCount: quiet.length,
    totals: {
      floods: doc.sites.reduce((n, s) => n + s.confirmed, 0),
      carsMin: doc.sites.reduce((n, s) => n + s.cars_min, 0),
    },
  };
}

/** The line of facts under a site's name. */
export function factsLine(site) {
  const floods = `${site.confirmed} flood${site.confirmed === 1 ? "" : "s"}`;
  return `${floods} · ${duration(site.cars_min)} blocked for cars · peak ${Math.round(site.peak_high)} cm`;
}

const escape = (text) => String(text).replace(/[&<>"']/g, (c) => (
  { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

const dayFormat = new Intl.DateTimeFormat("en-IN", { day: "numeric", month: "short", timeZone: "Asia/Kolkata" });
const day = (seconds) => dayFormat.format(new Date(seconds * 1000));

/** One small vertical mark per flood, oldest first, height by peak depth. An unconfirmed flood
 *  is drawn as an outline, so it is told from a confirmed one without colour. */
export function stripSvg(site) {
  const marks = site.floods.slice(-24);
  const width = 12, gap = 5, height = 36;
  const total = marks.length * (width + gap) - gap;
  const bars = marks.map((f, i) => {
    const h = Math.max(3, Math.round((Math.min(f.high, PEAK_CAP_CM) / PEAK_CAP_CM) * height));
    return `<rect class="mark ${f.confirmed ? "" : "is-unconfirmed"}" data-tone="${toneFor(f.high)}" ` +
      `x="${i * (width + gap)}" y="${height - h}" width="${width}" height="${h}" rx="1.5" />`;
  }).join("");
  const label = `${marks.length} flood${marks.length === 1 ? "" : "s"}, peaks ` +
    marks.map((f) => `${Math.round(f.high)}`).join(", ") + " centimetres";
  return `<svg class="strip" viewBox="0 0 ${Math.max(total, 1)} ${height}" width="${Math.max(total, 1)}" ` +
    `height="${height}" role="img" aria-label="${escape(label)}">${bars}</svg>`;
}

export function rowHtml(site) {
  // The line under the figures describes the confirmed floods those figures count.
  const last = site.floods.filter((f) => f.confirmed).at(-1);
  const extra = site.unconfirmed ? `<span class="is-critical">+ ${site.unconfirmed} unconfirmed</span>` : "";
  return `
    <li class="offender">
      <span class="offender-rank display" aria-hidden="true">${site.rank}</span>
      <div class="offender-body">
        <h3 class="display offender-name">${escape(site.name)}</h3>
        <p class="offender-facts">${escape(factsLine(site))}</p>
        <p class="offender-meta muted small">Last flood ${escape(day(last.end))}, peak ${Math.round(last.high)} cm ${extra}</p>
      </div>
      ${stripSvg(site)}
    </li>`;
}

export function pageHtml(model) {
  if (model.empty) {
    return `
      <p class="display title">No floods have been recorded yet.</p>
      <p class="measure">This page fills in as floods end. ${model.watched} places are watched, and each one is
      looked at whenever heavy rain is forecast there. A place appears here once a flood at it has been seen,
      measured and closed.</p>`;
  }
  const rows = model.ranked.map(rowHtml).join("");
  const unranked = model.unranked.length ? `
    <h2 class="label">Not yet ranked</h2>
    <p class="muted small measure">Floods reported by one unconfirmed photo are counted here but never move a place up the list.</p>
    <ul class="plain">${model.unranked.map((s) => `<li>${escape(s.name)} · ${s.unconfirmed} unconfirmed</li>`).join("")}</ul>` : "";
  return `
    <p class="summary">${model.totals.floods} confirmed flood${model.totals.floods === 1 ? "" : "s"} at
      ${model.floodedSites} of ${model.watched} places watched · ${duration(model.totals.carsMin)} blocked for cars</p>
    <ol class="offenders">${rows}</ol>
    ${unranked}
    ${model.quietCount ? `<p class="muted small">${model.quietCount} watched place${model.quietCount === 1 ? "" : "s"} with no flood recorded.</p>` : ""}`;
}

export function startPage({ url, root, notice }) {
  let last = null, generatedAt = null, failed = false;
  const draw = () => {
    root.innerHTML = last ? pageHtml(offendersModel(last)) : "";
    const sample = last && last.sample;
    document.getElementById("sample-banner").hidden = !sample;
    const age = generatedAt ? Date.now() / 1000 - generatedAt : 0;
    const old = generatedAt && age > STALE_AFTER_S;
    notice.hidden = !(failed || old);
    notice.textContent = failed ? `Could not refresh. Last updated ${ageWords(age)} ago` : old ? `Last updated ${ageWords(age)} ago` : "";
  };
  async function poll() {
    try {
      const response = await fetch(url, { headers: { Accept: "application/json" } });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      last = await response.json();
      generatedAt = last.generated_at;
      failed = false;
    } catch (error) {
      failed = true;
      if (!last) root.innerHTML = '<p class="is-critical">The flood history could not be loaded.</p>';
    }
    draw();
  }
  poll();
  setInterval(poll, POLL_MS);
}
