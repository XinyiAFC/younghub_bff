import unittest
from unittest.mock import Mock

from app.util.azure_cosmos_util import AzureCosmosUtil


class FakeContainer:
    def __init__(self, items):
        self.items = items
        self.query = None

    def query_items(self, query, parameters, enable_cross_partition_query):
        self.query = (query, parameters, enable_cross_partition_query)
        if "c.ID >= 0 AND c.ID <= 99" in query:
            items = [row for row in self.items
                     if 0 <= row.get("ID", -1) <= 99
                     and row.get("ID") not in {10, 11, 12}]
        else:
            allowed = {param["value"] for param in parameters}
            items = [row for row in self.items if row.get("ID") in allowed]
        return iter(items)


def item(item_id, category_id, title="item"):
    return {"id": item_id, "ID": category_id, "Title": title}


class ArticleRoutingTests(unittest.TestCase):
    def setUp(self):
        self.util = AzureCosmosUtil.__new__(AzureCosmosUtil)

    def run_query(self, items, channel=None, aliases=None):
        container = FakeContainer(items)
        result = self.util._read_items(container, channel_id=channel,
                                       id_aliases=aliases)
        return container.query, result

    def test_homepage_is_v2_range_only(self):
        query, result = self.run_query([
            item("home", 2), item("future", 99), item("old-channel", 10),
            item("new-channel", 101), item("event", 200), item("service", 300)
        ])
        self.assertIn("c.ID >= 0 AND c.ID <= 99", query[0])
        self.assertEqual({row["ID"] for row in result}, {2, 99})

    def test_channel_101_reads_new_and_legacy_and_prefers_new(self):
        query, result = self.run_query([
            item("same", 10, "legacy"), item("same", 101, "new"),
            item("legacy-only", 10), item("new-only", 101)
        ], channel="101")
        self.assertIn("c.ID IN (@preferredId, @legacyId)", query[0])
        self.assertEqual({p["name"] for p in query[1]}, {"@preferredId", "@legacyId"})
        rows = {row["id"]: row for row in result}
        self.assertEqual(rows["same"]["ID"], 101)
        self.assertEqual(set(rows), {"same", "legacy-only", "new-only"})

    def test_channels_102_and_103_use_expected_aliases(self):
        for channel, preferred, legacy in (("102", 102, 11), ("103", 103, 12)):
            query, _ = self.run_query([], channel=channel)
            params = {p["name"]: p["value"] for p in query[1]}
            self.assertEqual(params["@preferredId"], preferred)
            self.assertEqual(params["@legacyId"], legacy)

    def test_legacy_channel_parameters_remain_compatible(self):
        for channel, preferred, legacy in (("10", 101, 10), ("11", 102, 11), ("12", 103, 12)):
            query, _ = self.run_query([], channel=channel)
            params = {p["name"]: p["value"] for p in query[1]}
            self.assertEqual(params["@preferredId"], preferred)
            self.assertEqual(params["@legacyId"], legacy)

    def test_event_and_service_aliases_prefer_new(self):
        for aliases, preferred in (((200, 111), 200), ((300, 112), 300)):
            query, result = self.run_query([
                item("same", aliases[1]), item("same", aliases[0]),
                item("only-old", aliases[1])
            ], aliases=aliases)
            self.assertIn("c.ID IN (@preferredId, @legacyId)", query[0])
            rows = {row["id"]: row for row in result}
            self.assertEqual(rows["same"]["ID"], preferred)

    def test_migrated_article_projection_is_preserved(self):
        _, result = self.run_query([
            {
                "id": "f4e6d237-5770-408d-b870-d3409a51ff04",
                "ID": 2,
                "SourcePostID": 19187,
                "ContentType": "article",
                "ContentHTML": "<h2>漫画</h2>" * 1,
                "FeaturedImageBlobURL": "https://storage.example/featured.jpg",
                "SyncVersion": 6,
            }
        ])
        article = result[0]
        self.assertEqual(article["ID"], 2)
        self.assertEqual(article["SourcePostID"], 19187)
        self.assertEqual(article["ContentType"], "article")
        self.assertTrue(article["ContentHTML"])
        self.assertEqual(article["SyncVersion"], 6)

    def test_unknown_channel_is_empty(self):
        container = Mock()
        self.assertEqual(self.util._read_items(container, channel_id="999"), [])
        container.query_items.assert_not_called()


if __name__ == "__main__":
    unittest.main()
