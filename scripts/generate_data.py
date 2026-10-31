"""Generate the intentionally invented, deterministic NYC classroom sample."""
import json
from pathlib import Path

PLACES = [
    ("Lower Manhattan", -74.008, 40.708),
    ("SoHo", -73.998, 40.724),
    ("Chelsea", -74.002, 40.747),
    ("Midtown", -73.985, 40.758),
    ("East Village", -73.982, 40.729),
    ("Long Island City", -73.948, 40.747),
]


def make_dataset():
    features = []
    for hour_index, hour in enumerate((8, 12, 18, 21)):
        for place_index, (name, lon, lat) in enumerate(PLACES):
            features.append({
                "type": "Feature", "id": f"demo-{hour:02d}-{place_index + 1:02d}",
                "geometry": {"type": "Point", "coordinates": [
                    round(lon + hour_index * 0.001, 6),
                    round(lat + hour_index * 0.0007, 6)]},
                "properties": {"name": name, "hour": hour,
                    "value": 20 + ((place_index * 17 + hour_index * 23) % 80),
                    "simulated": True},
            })
    return {
        "type": "FeatureCollection", "name": "Synthetic NYC teaching observations",
        "metadata": {
            "provenance": "Invented by scripts/generate_data.py for JupyterLite-PyScript; not collected or sampled from people, taxi trips or health records.",
            "author": "James L. Tobias, MS, GISP",
            "purpose": "Small deterministic classroom dataset; approximate NYC neighborhood coordinates and invented hour/value attributes.",
            "coordinate_reference_system": "EPSG:4326; WGS 84 longitude, latitude (RFC 7946)",
            "value_units": "invented teaching units", "simulated": True,
            "feature_count": 24,
        }, "features": features,
    }


if __name__ == "__main__":
    target = Path(__file__).resolve().parents[1] / "content/data/nyc-observations.geojson"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(make_dataset(), indent=2) + "\n", encoding="utf-8")
    print(f"Generated {target}")
