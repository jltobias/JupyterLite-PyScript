---
title: NYC Taxi — study an external inspiration
---

Explore [NYC Taxi Panel/deck.gl, hosted on PyScript.com under @ambv](https://pyscript.com/@ambv/nyc-taxi-panel-deckgl-copy/latest?files=README.md), an independently maintained inspiration for browser geospatial interaction. Its runtime versions and availability may differ from the local labs.

For related implementation material, read the [HoloViz Panel NYC deck.gl gallery example](https://panel.holoviz.org/gallery/nyc_deckgl.html). Attribute that example to **HoloViz/Panel and its contributors**; retain upstream licensing and attribution if you reuse its code or data.

## Compare the ideas

Our hub demonstrates a small version of a common geospatial interaction: choose an hour, select observations and render geographic magnitudes. The local labs use 24 invented observations rather than a taxi trip dataset. They do not reproduce the external app or validate traffic patterns.

Open the gallery source and consider:

1. Where is the data loaded and what is its provenance?
2. Which control changes the hour, and where is filtering performed?
3. How does the deck.gl layer receive updated data?
4. Which parts depend on Panel, Python packages or a server, and which could work in a static browser runtime?

A familiar Python visualization API does not by itself guarantee that all its dependencies work in Pyodide. Check the actual dependency versions and build/runtime architecture before attempting a browser port. The local PyScript labs intentionally use standard-library Python plus direct JavaScript renderer adapters.

## A useful extension

After completing the shared-data notebook, add a summary count by hour and compare it with the six-per-hour design. When working with a real taxi dataset later, describe licensing, sampling, timestamps, geography and privacy implications. Keep simulated and measured observations clearly distinguished throughout the analysis.
