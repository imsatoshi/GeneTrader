"""Static safety checks for adaptive docker-compose runtime defaults."""

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
COMPOSE = ROOT / "docker-compose.adaptive.yml"


class TestAdaptiveComposeStaticSafety(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.compose_text = COMPOSE.read_text(encoding="utf-8")

    def test_agent_api_key_has_no_default(self):
        self.assertNotIn("default-key", self.compose_text)
        self.assertIn("AGENT_API_KEY=${AGENT_API_KEY:?AGENT_API_KEY is required}", self.compose_text)

    def test_agent_api_port_is_localhost_only(self):
        self.assertIn('"127.0.0.1:8090:8090"', self.compose_text)
        self.assertNotIn('"8090:8090"', self.compose_text)

    def test_referenced_dockerfile_exists(self):
        self.assertIn("dockerfile: Dockerfile", self.compose_text)
        self.assertTrue((ROOT / "Dockerfile").is_file())
        self.assertNotIn("Dockerfile.adaptive", self.compose_text)

    def test_agent_api_command_starts_api_server(self):
        self.assertIn("--api-port 8090", self.compose_text)
        self.assertIn("--api-host 0.0.0.0", self.compose_text)
        self.assertNotIn("--check-only", self.compose_text)

    def test_healthcheck_uses_public_health_endpoint(self):
        self.assertIn("http://localhost:8090/api/v1/health", self.compose_text)


if __name__ == "__main__":
    unittest.main()
