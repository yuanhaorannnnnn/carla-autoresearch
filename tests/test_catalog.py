import contextlib
import io
import json
import unittest
from unittest.mock import patch

from carla_agent import catalog, cli
from carla_agent.protocol import AgentError


class CatalogTest(unittest.TestCase):
    def test_discovery_is_offline_and_does_not_invoke_worker(self):
        with patch("carla_agent.cli.run_operation", side_effect=AssertionError("worker invoked")), contextlib.redirect_stdout(io.StringIO()) as output:
            code = cli.main(["skills", "list", "--query", "sensor.camera.dvs"])
        result = json.loads(output.getvalue())["result"]
        self.assertEqual(code, 0)
        self.assertEqual([skill["name"] for skill in result["skills"]], ["carla-camera-dvs"])

    def test_filters_separate_conditional_workflow_from_wrapped_operations(self):
        result = catalog.discover(category="sensors", execution="conditional")
        self.assertTrue(result["skills"])
        self.assertTrue(all(skill["execution"] == "conditional" for skill in result["skills"]))
        self.assertNotIn("capture.run", catalog.describe("carla-camera-dvs")["cli_operations"])
        self.assertEqual(catalog.discover("does-not-exist")["count"], 0)

    def test_unknown_name_is_an_explicit_error(self):
        with self.assertRaises(AgentError) as caught:
            catalog.describe("../../missing")
        self.assertEqual(caught.exception.code, "unknown_skill")


if __name__ == "__main__":
    unittest.main()
