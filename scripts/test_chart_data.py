"""Focused contracts for shared chart preparation and query validation."""
from copy import deepcopy
import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "content"))
from chart_data import chart_config, chart_summary, export_summary


class ChartDataTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dataset = json.loads((Path(__file__).resolve().parents[1] / "content/data/nyc-observations.geojson").read_text())

    def test_additive_and_deterministic(self):
        original = deepcopy(self.dataset)
        hourly = chart_summary(self.dataset)
        self.assertEqual([r["id"] for r in hourly["rows"]], ["8", "12", "18", "21"])
        for grouping, expected in [("hour", 4), ("neighborhood", 6), ("point", 24)]:
            total = chart_summary(self.dataset, grouping)
            count = chart_summary(self.dataset, grouping, metric="count")
            self.assertEqual(len(total["rows"]), expected)
            self.assertEqual(sum(r["count"] for r in total["rows"]), 24)
            self.assertEqual(sum(r["value"] for r in total["rows"]), sum(f["properties"]["value"] for f in original["features"]))
            self.assertEqual(sum(r["value"] for r in count["rows"]), 24)
            self.assertEqual(total, json.loads(export_summary(self.dataset, grouping)))
        self.assertEqual(original, self.dataset)

    def test_filter_empty_centroid_and_provenance(self):
        for grouping in ["hour", "neighborhood", "point"]:
            selected = chart_summary(self.dataset, grouping, 8)
            self.assertEqual(selected["metadata"]["feature_count"], 6)
            self.assertEqual(sum(r["count"] for r in selected["rows"]), 6)
            self.assertEqual(selected["metadata"]["provenance"], self.dataset["metadata"]["provenance"])
            self.assertEqual(chart_summary(self.dataset, grouping, 0)["rows"], [])
        first = chart_summary(self.dataset, "neighborhood", 8)["rows"][0]
        feature = next(f for f in self.dataset["features"] if f["properties"]["hour"] == 8 and f["properties"]["name"] == first["id"])
        self.assertEqual([first["longitude"], first["latitude"]], feature["geometry"]["coordinates"])
        changed = chart_summary(self.dataset)
        changed["metadata"]["provenance"] = "changed"
        self.assertNotEqual(changed["metadata"], self.dataset["metadata"])

    def test_validated_query_parameters(self):
        self.assertEqual(chart_config(hour="08")["hour"], 8)
        for renderer, view in [("d3", "bars"), ("d3", "points"), ("d3plus", "bars"), ("d3plus", "treemap")]:
            self.assertEqual(chart_config(renderer, view)["view"], view)
        for options in [{"hour": h} for h in [-1, 24, "bad", "8.5", 8.0, True]] + [
                {"metric": "mean"}, {"renderer": "d3", "view": "treemap"}, {"renderer": "other"}]:
            with self.assertRaises(ValueError):
                chart_config(**options)

    def test_original_point_precision_and_multi_member_centroid(self):
        precise = deepcopy(self.dataset)
        original = [-74.008123456789, 40.708987654321]
        precise["features"][0]["geometry"]["coordinates"] = original[:]
        point = next(row for row in chart_summary(precise, "point")["rows"]
                     if row["id"] == precise["features"][0]["id"])
        self.assertEqual([point["longitude"], point["latitude"]], original)
        chelsea = next(row for row in chart_summary(self.dataset, "neighborhood")["rows"]
                       if row["id"] == "Chelsea")
        self.assertEqual(chelsea["count"], 4)
        self.assertEqual(chelsea["total"], 194)
        self.assertEqual(chelsea["value"], 194)
        self.assertEqual([chelsea["longitude"], chelsea["latitude"]], [-74.0005, 40.74805])


if __name__ == "__main__":
    unittest.main()
