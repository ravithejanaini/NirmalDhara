// The map ground: Hyderabad as a quiet night print.
//
// Tiles and fonts come from OpenFreeMap's public instance (no key; see CREDITS.md). The
// style in style.json keeps only ground, water, main roads, railways and a few names, so
// that flood water is the only thing on the map with colour.

export const HYDERABAD = {
  center: [78.4747, 17.3850],
  // West, south, east, north. A little wider than the city so the edge is never in view.
  bounds: [[78.05, 17.08], [78.90, 17.72]],
  zoom: 10.6,
};

/** Create the map in `container` and resolve once its style has loaded. */
export function createMap(container) {
  const map = new maplibregl.Map({
    container,
    style: "style.json",
    center: HYDERABAD.center,
    zoom: HYDERABAD.zoom,
    minZoom: 9.2,
    maxZoom: 16.5,
    maxBounds: HYDERABAD.bounds,
    dragRotate: false,
    pitchWithRotate: false,
    touchPitch: false,
    attributionControl: false,
  });
  map.touchZoomRotate.disableRotation();
  map.keyboard.disableRotation();
  // Attribution is required by the map data's licence. Compact, so it folds to an "i".
  map.addControl(new maplibregl.AttributionControl({ compact: true }), "bottom-right");
  return new Promise((resolve, reject) => {
    map.once("load", () => resolve(map));
    // A tile that cannot be fetched (no signal) is not a failed map: the sites still draw on
    // the blank ground. Only a failure to load the style itself stops the map.
    const onError = (event) => {
      if (event.tile || event.sourceId) return;
      map.off("error", onError);
      reject(event.error);
    };
    map.on("error", onError);
  });
}
