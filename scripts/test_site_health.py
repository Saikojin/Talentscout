import unittest
import asyncio
import os
import json
import tempfile
from unittest.mock import patch
from scripts.verify_site_health import (
    probe_domain_health,
    audit_sources,
    quarantine_dead_domains,
)

class TestSiteHealth(unittest.TestCase):
    def test_probe_domain_health_reachable(self):
        async def run_test():
            with patch("socket.getaddrinfo", return_value=[(2, 1, 0, '', ('127.0.0.1', 80))]):
                is_alive, reason = await probe_domain_health("example.com")
                self.assertTrue(is_alive)
                self.assertEqual(reason, "OK")
        asyncio.run(run_test())

    def test_probe_domain_health_unreachable(self):
        async def run_test():
            import socket
            with patch("socket.getaddrinfo", side_effect=socket.gaierror("Name or service not known")):
                is_alive, reason = await probe_domain_health("nonexistent-fake-domain-12345.xyz")
                self.assertFalse(is_alive)
                self.assertIn("DNS_UNREACHABLE", reason)
        asyncio.run(run_test())

    def test_audit_sources(self):
        async def run_test():
            sources = [
                {"name": "ValidSite", "url": "https://example.com/careers"},
                {"name": "DeadSite", "url": "https://defunct-domain-404.org/jobs"}
            ]

            def mock_dns(host, port):
                if "defunct" in host:
                    import socket
                    raise socket.gaierror("NXDOMAIN")
                return [(2, 1, 0, '', ('127.0.0.1', 80))]

            with patch("socket.getaddrinfo", side_effect=mock_dns):
                healthy, dead = await audit_sources(sources, timeout=2.0)
                self.assertEqual(len(healthy), 1)
                self.assertEqual(healthy[0]["name"], "ValidSite")
                self.assertEqual(len(dead), 1)
                self.assertEqual(dead[0]["name"], "DeadSite")

        asyncio.run(run_test())

    def test_quarantine_dead_domains(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            out_file = os.path.join(tmpdir, "quarantine.json")
            dead = [
                {"name": "OldCo", "url": "https://oldco-dead.com", "domain": "oldco-dead.com", "reason": "DNS_UNREACHABLE"}
            ]

            quarantine_dead_domains(dead, out_file)
            self.assertTrue(os.path.exists(out_file))

            with open(out_file, "r", encoding="utf-8") as f:
                saved = json.load(f)

            self.assertEqual(len(saved), 1)
            self.assertEqual(saved[0]["domain"], "oldco-dead.com")

if __name__ == "__main__":
    unittest.main()
