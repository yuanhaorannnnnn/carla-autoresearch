"""Exercise public read-only research commands against synthetic run evidence."""

import contextlib
import io
import json
import unittest
from unittest.mock import patch

from carla_agent import cli, research
from carla_agent.protocol import atomic_json
from tests import test_research as fixtures


class ResearchCliTest(unittest.TestCase):
    def setUp(self):
        self.fixture = fixtures.ResearchTest()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)

    def invoke(self, *args):
        with contextlib.redirect_stdout(io.StringIO()) as output:
            code = cli.main(list(args))
        return code, json.loads(output.getvalue())

    def test_validate_public_cli_has_no_simulator_or_run_side_effects(self):
        fixture = self.fixture
        atomic_json(fixture.plan_path, fixture.plan)
        before = {str(p): p.read_bytes() for p in fixture.root.rglob("*") if p.is_file()}
        with patch.object(research.bridge, "invoke", side_effect=AssertionError("connected")), \
             patch.object(research.bridge, "server_identity", side_effect=AssertionError("inspected server")):
            code, envelope = self.invoke("research", "validate", "--plan", str(fixture.plan_path))
        self.assertEqual(code, 0)
        self.assertFalse(envelope["result"]["simulator_checked"])
        self.assertEqual(envelope["result"]["worst_case_trials"], 8)
        self.assertEqual(before, {str(p): p.read_bytes() for p in fixture.root.rglob("*") if p.is_file()})

    def test_compare_public_cli_rechecks_evidence_and_returns_structured_failure(self):
        run, _ = self.fixture.execute()
        before = {str(p): p.read_bytes() for p in run.rglob("*") if p.is_file()}
        with patch.object(research.bridge, "invoke", side_effect=AssertionError("connected")), \
             patch.object(research.bridge, "server_identity", side_effect=AssertionError("inspected server")):
            code, envelope = self.invoke("research", "compare", "--run", str(run))
            self.assertEqual(code, 0)
            self.assertTrue(envelope["result"]["read_only"])
            self.assertEqual(envelope["result"]["verdict"], "keep")
            self.assertEqual(before, {str(p): p.read_bytes() for p in run.rglob("*") if p.is_file()})
            next((run / "trials").glob("*/capture/*.f32")).write_bytes(b"changed")
            code, envelope = self.invoke("research", "compare", "--run", str(run))
        self.assertEqual(code, 5)
        self.assertFalse(envelope["ok"])
        self.assertEqual(envelope["error"]["code"], "recovery_conflict")


if __name__ == "__main__":
    unittest.main()
