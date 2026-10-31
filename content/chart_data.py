"""Deterministic, standard-library preparation shared by notebooks and charts."""
from copy import deepcopy
import json

from selection import select_features


def chart_config(renderer="d3", view="bars", hour="all", metric="total"):
    """Validate URL/control parameters before they reach a renderer."""
    views = {"d3": {"bars", "points"}, "d3plus": {"bars", "treemap"}}
    if renderer not in views or view not in views[renderer]:
        raise ValueError(f"Invalid view {view!r} for {renderer!r}")
    if metric not in {"count", "total"}:
        raise ValueError("Metric must be 'count' or 'total'")
    # Reuse the map lessons' strict type/range validation, including bools.
    select_features({"features": []}, hour)
    return {"renderer": renderer, "view": view,
            "hour": "all" if hour == "all" else int(hour), "metric": metric}


def chart_summary(dataset, group_by="hour", hour="all", metric="total"):
    """Return additive counts/totals and arithmetic coordinate centroids.

    Rows are ordered by hour, neighborhood name, or observation ID. Empty
    selections have no rows. Input GeoJSON and its provenance remain untouched.
    The centroids are teaching summaries of nearby synthetic points, not areas.
    """
    if group_by not in {"hour", "neighborhood", "point"}:
        raise ValueError("Group must be 'hour', 'neighborhood' or 'point'")
    chart_config(hour=hour, metric=metric)
    features = select_features(dataset, hour)
    groups = {}
    for feature in features:
        p = feature["properties"]
        key = {"hour": p["hour"], "neighborhood": p["name"], "point": feature["id"]}[group_by]
        groups.setdefault(key, []).append(feature)
    rows = []
    for key, members in sorted(groups.items()):
        count = len(members)
        total = sum(f["properties"]["value"] for f in members)
        coordinates = members[0]["geometry"]["coordinates"] if group_by == "point" else [
            round(sum(f["geometry"]["coordinates"][axis] for f in members) / count, 6)
            for axis in (0, 1)]
        rows.append({
            "id": str(key),
            "label": f"{key:02d}:00" if group_by == "hour" else
                     members[0]["properties"]["name"] if group_by == "point" else key,
            "count": count, "total": total,
            "value": count if metric == "count" else total,
            "longitude": coordinates[0], "latitude": coordinates[1],
        })
    return {"metadata": {**deepcopy(dataset["metadata"]),
                         "selection_hour": "all" if hour == "all" else int(hour),
                         "feature_count": len(features), "group_by": group_by,
                         "metric": metric, "group_count": len(rows)}, "rows": rows}


def export_summary(dataset, group_by="hour", hour="all", metric="total"):
    """Serialize precisely the summary used by the table and graphics."""
    return json.dumps(chart_summary(dataset, group_by, hour, metric), indent=2, allow_nan=False)
