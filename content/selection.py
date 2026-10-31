"""Runtime-independent selection and RFC 7946 GeoJSON export for every lesson."""
from copy import deepcopy
import json


def select_features(dataset, hour="all"):
    """Select a teaching hour; preserve input data and support empty selections."""
    if hour != "all":
        if isinstance(hour, bool) or not isinstance(hour, (int, str)):
            raise ValueError("Hour must be 'all' or an integer from 0 to 23")
        hour = int(hour)
        if not 0 <= hour <= 23:
            raise ValueError("Hour must be 'all' or an integer from 0 to 23")
    return [deepcopy(feature) for feature in dataset["features"]
            if hour == "all" or feature["properties"]["hour"] == hour]


def feature_collection(dataset, hour="all"):
    """Return a portable selection with provenance as GeoJSON foreign members.

    RFC 7946 uses longitude, latitude in WGS 84 (EPSG:4326). No deprecated
    `crs` member is added; GIS importers can ignore the extra `metadata` member.
    """
    features = select_features(dataset, hour)
    return {
        "type": "FeatureCollection",
        "name": "Synthetic NYC teaching observations",
        "metadata": {
            **deepcopy(dataset["metadata"]),
            "selection_hour": "all" if hour == "all" else int(hour),
            "feature_count": len(features),
        },
        "features": features,
    }


def export_geojson(dataset, hour="all"):
    """Serialize the same selection sent to all renderers."""
    return json.dumps(feature_collection(dataset, hour), indent=2, allow_nan=False)
