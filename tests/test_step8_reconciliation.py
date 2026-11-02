"""Focused T1/T2 checks for bounded Step 8 joint reconciliation."""

from __future__ import annotations

import json
import tempfile
import unittest
from http.server import HTTPServer
from pathlib import Path
from threading import Thread
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from src.annotation.publication_step8.reconciliation_app import make_handler
from src.annotation.publication_step8.reconciliation import ReconciliationError, ReconciliationService
from src.extraction.llm.publications import step8_reconciliation_package as package


class Step8ReconciliationTests(unittest.TestCase):
    """Verify frozen membership, allowed choices, persistence, and final-export gating."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.artifact = package.build()

    def test_frozen_package_has_only_eleven_blinded_disagreements(self) -> None:
        """No initial-review identity or extra pooled item crosses this boundary."""

        value = self.artifact
        self.assertEqual(value["itemCount"], 11)
        self.assertEqual(value["judgmentItemIDs"], sorted(value["judgmentItemIDs"]))
        self.assertEqual(value["allowedFinalDecisions"], list(package.FINAL_DECISIONS))
        self.assertTrue(all(set(item["blindedInitialJudgments"]) == {"initialReviewA", "initialReviewB"} for item in value["items"]))
        self.assertNotIn("reviewer_1", json.dumps(value["items"]))
        self.assertNotIn("reviewer_2", json.dumps(value["items"]))
        for item in value["items"]:
            self.assertIn("reviewGuidance", item["judgmentItem"])
            self.assertIn("paragraphContexts", item["judgmentItem"])

    def test_final_export_requires_all_eleven_and_is_deterministic(self) -> None:
        """Only complete authorized decision maps can create a final export."""

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            package_path = root / "package.json"
            package_path.write_text(json.dumps(self.artifact, sort_keys=True, separators=(",", ":")))
            service = ReconciliationService(package_path, root / "state.json")
            with self.assertRaisesRegex(ReconciliationError, "RECONCILIATION_INCOMPLETE"):
                service.export("runtime")
            for item_id in self.artifact["judgmentItemIDs"]:
                service.decide(service.state()["revision"], item_id, "adjudication_unresolved")
            first = service.export("runtime")
            self.assertEqual(first, service.export("runtime"))
            value = json.loads(first)
            self.assertTrue(value["complete"])
            self.assertEqual(len(value["finalDecisions"]), 11)
            self.assertEqual(set(value["finalDecisions"]), set(self.artifact["judgmentItemIDs"]))

    def test_rejects_unlisted_item_or_unauthorized_category(self) -> None:
        """The local endpoint cannot create a new assertion or a fifth outcome."""

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            package_path = root / "package.json"
            package_path.write_text(json.dumps(self.artifact, sort_keys=True, separators=(",", ":")))
            service = ReconciliationService(package_path, root / "state.json")
            with self.assertRaisesRegex(ReconciliationError, "INVALID_RECONCILIATION_DECISION"):
                service.decide(0, "judgment-item-9999", "supported_as_proposed")
            with self.assertRaisesRegex(ReconciliationError, "INVALID_RECONCILIATION_DECISION"):
                service.decide(0, self.artifact["judgmentItemIDs"][0], "rewrite_assertion")

    def test_ui_serves_only_frozen_items_and_authorized_post_shape(self) -> None:
        """The loopback UI cannot select an undisclosed item or accept assertion fields."""

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            package_path = root / "package.json"
            package_path.write_text(json.dumps(self.artifact, sort_keys=True, separators=(",", ":")))
            service = ReconciliationService(package_path, root / "state.json")
            server = HTTPServer(("127.0.0.1", 0), make_handler(service))
            worker = Thread(target=server.serve_forever, daemon=True); worker.start()
            base = f"http://127.0.0.1:{server.server_port}"
            try:
                state = json.loads(urlopen(base + "/api/state").read())
                self.assertEqual(state["total"], 11)
                item = json.loads(urlopen(base + "/api/item/" + self.artifact["judgmentItemIDs"][0]).read())
                self.assertNotIn("reviewerID", json.dumps(item))
                request = Request(base + "/api/decision", data=json.dumps({"expectedRevision": 0, "judgmentItemID": self.artifact["judgmentItemIDs"][0], "decision": "supported_as_proposed", "assertion": "edited"}).encode(), method="POST", headers={"Content-Type": "application/json", "X-Reconciliation-Token": state["csrfToken"]})
                with self.assertRaises(HTTPError) as error:
                    urlopen(request)
                self.assertEqual(error.exception.code, 409)
            finally:
                server.shutdown(); server.server_close(); worker.join()


if __name__ == "__main__":
    unittest.main()
