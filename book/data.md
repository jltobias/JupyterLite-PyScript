---
title: A tiny dataset with an explicit story
---

[Open the exploration notebook]({{HUB_BASE}}/lite/lab/index.html?path=02-explore-data.ipynb) · [Download the complete GeoJSON]({{HUB_BASE}}/data/nyc-observations.geojson)

The repository creates **24 deterministic synthetic observations**: six approximate NYC neighborhood locations, repeated at 08:00, 12:00, 18:00 and 21:00 with small invented coordinate offsets. The `value` attribute is a formula, in invented teaching units. `scripts/generate_data.py` is the complete reproducible generator.

No observations were collected from people, taxis, health records or a public trip dataset. Place labels and approximate coordinates supply recognizable geographic context. Every feature is labeled `simulated: true`, and collection metadata records purpose, author, coordinate order and provenance.

| Field | Meaning |
| --- | --- |
| `id` | Stable synthetic feature identifier |
| `name` | Approximate neighborhood label |
| `hour` | Invented hour of day; 8, 12, 18 or 21 |
| `value` | Invented magnitude used for column/bar height |
| `simulated` | Always `true` |
| `geometry.coordinates` | `[longitude, latitude]` in WGS 84 / EPSG:4326 |

## Select without changing the source

The shared Python function creates copies of matching features:

```python
from selection import feature_collection
selected = feature_collection(dataset, 8)
assert len(selected["features"]) == 6
assert all(f["properties"]["hour"] == 8 for f in selected["features"])
```

At 00:00 there are no observations. Exporting then produces `{"type": "FeatureCollection", "features": []}` plus metadata. Empty data is a meaningful result; the renderer clears its observation layer.

## A portable export

GeoJSON follows [RFC 7946](https://www.rfc-editor.org/rfc/rfc7946): longitude first, latitude second, in WGS 84. No deprecated `crs` object is needed. This project adds a `metadata` foreign member containing provenance, selected hour and count. GIS readers can ignore that extra member, so `simulated` is also repeated on each feature and survives many transformations.

When exporting new data yourself, check coordinate order, missing values, units and provenance before sharing. Our dataset is intentionally small enough to inspect in full.
