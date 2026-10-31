---
title: One selection, three renderers
---

The labs use Python for data and interaction, then pass a **serialized GeoJSON string** to a small JavaScript renderer adapter. Each view uses the same `selection.py` filter/export module. Only the visual representation changes.

| Lab | Representation | What to notice |
| --- | --- | --- |
| [Leaflet 2D]({{HUB_BASE}}/apps/leaflet/) | Geographic circle markers on OpenStreetMap tiles | Location and neighborhood context |
| [deck.gl 3D]({{HUB_BASE}}/apps/deck/) | Geographic columns above a tiled map | Invented `value` controls height; pitch and perspective affect perception |
| [Three.js scene]({{HUB_BASE}}/apps/scene/) | Bars on a local illustrative grid | Scene coordinates differ from geographic coordinates |

## Run the comparison

1. Open each lab. Wait until Python and the renderer report ready. The count starts at 24.
2. Select 08:00. Every view reports **6** and renders those same six IDs.
3. Select 18:00. Compare height patterns with 08:00. Magnitudes are invented; they support a rendering lesson, not a conclusion about NYC.
4. Select 00:00. The observation layer disappears and the count becomes **0**; map tiles or the scene grid remain.
5. Download GeoJSON from each view at the same hour. Compare the feature IDs and metadata: the geographic exports agree.

Open **View selected observations** in any lab to read neighborhood names, hours, values and coordinates in a text table. It shows the same selection as the graphic and GeoJSON download.

## Map versus scene

Leaflet and deck.gl consume longitude/latitude. The scene converts coordinates using:

```javascript
x = (longitude + 73.98) * 350;
z = -(latitude - 40.745) * 460;
height = value / 8;
```

These convenient classroom scale factors are **not a cartographic projection** and the grid has no real-world distance unit. The scene is neither terrain nor buildings. Export always uses original geographic coordinates, not scene coordinates.

## Failure should be visible

The app disables controls until ready. Renderer, Python and CDN failures produce visible retry guidance; startup has a two-minute timeout. If map tiles are blocked, the message describes that partial failure while points and exports can still work. If WebGL 2 is unavailable, use the 2D lab and read the source without waiting indefinitely.

Sources: [Leaflet quick start](https://leafletjs.com/examples/quick-start/), [deck.gl standalone API](https://deck.gl/docs/get-started/using-standalone), [deck.gl tile layer](https://deck.gl/docs/api-reference/geo-layers/tile-layer), [Three.js manual](https://threejs.org/manual/#en/fundamentals), [OpenStreetMap attribution](https://www.openstreetmap.org/copyright).
