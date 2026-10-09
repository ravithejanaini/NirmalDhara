// The sites on the map: one glyph marker per site, created once and updated in place.

import { createGlyph, updateGlyph } from "./glyph.js";

const AGE_REFRESH_MS = 60_000;      // a reading grows old with no new data: redraw the glyphs' age

export class SiteLayer {
  constructor(map) {
    this.map = map;
    this.markers = new Map();       // id -> { marker, button, glyph, site }
    this.timer = null;
  }

  /** Apply one load of the file. Only sites that were added, changed or removed are touched. */
  apply({ data, diff, now }) {
    for (const id of [...diff.added, ...diff.changed]) this.set(data.sites.get(id), now);
    for (const id of diff.removed) this.remove(id);
  }

  set(site, now) {
    const entry = this.markers.get(site.id);
    if (entry) {
      entry.site = site;
      updateGlyph(entry.glyph, site, now);
      entry.button.setAttribute("aria-label", entry.glyph.getAttribute("aria-label"));
      entry.marker.setLngLat([site.lon, site.lat]);
      return;
    }
    const glyph = createGlyph(site, now);
    const button = document.createElement("button");
    button.type = "button";
    button.className = "site-marker";
    button.dataset.siteId = site.id;
    button.setAttribute("aria-label", glyph.getAttribute("aria-label"));
    glyph.removeAttribute("role");              // the button carries the name
    glyph.setAttribute("aria-hidden", "true");
    button.append(glyph);
    // The sheet (WEB-06) listens for this. It is announced on the document, not on the map.
    button.addEventListener("click", () => {
      document.dispatchEvent(new CustomEvent("site-selected", {
        detail: { site: this.markers.get(site.id).site },
      }));
    });
    const marker = new maplibregl.Marker({ element: button, anchor: "center" })
      .setLngLat([site.lon, site.lat]).addTo(this.map);
    // MapLibre names every marker "Map marker" when it is attached; the site's own name goes after.
    button.setAttribute("aria-label", glyph.getAttribute("aria-label"));
    this.markers.set(site.id, { marker, button, glyph, site });
  }

  remove(id) {
    const entry = this.markers.get(id);
    if (!entry) return;
    entry.marker.remove();
    this.markers.delete(id);
  }

  /** Keep ages honest between loads of the file. `now` returns the current time in seconds. */
  keepAges(now) {
    clearInterval(this.timer);
    this.timer = setInterval(() => {
      for (const entry of this.markers.values()) {
        updateGlyph(entry.glyph, entry.site, now());
        entry.button.setAttribute("aria-label", entry.glyph.getAttribute("aria-label"));
      }
    }, AGE_REFRESH_MS);
  }
}
