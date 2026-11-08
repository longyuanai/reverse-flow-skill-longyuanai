"""Tests for generate_license module."""
from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "generate_license",
    ROOT / "scripts" / "generate_license.py"
)
assert SPEC is not None and SPEC.loader is not None
generate_license = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(generate_license)


class GenerateLicenseTests(unittest.TestCase):
    def test_issue_consultant_license_in_memory(self):
        res = generate_license.issue_license(
            client_name="张三独立安全顾问工作室",
            tier="consultant",
            contact_email="zhangsan@sec.com",
            years_valid=1,
        )
        self.assertTrue(res["license_id"].startswith("RF-COMM-"))
        self.assertIn("张三独立安全顾问工作室", res["cert_text"])
        self.assertIn("独立顾问版", res["cert_text"])

        token_obj = json.loads(res["token_json"])
        self.assertEqual(token_obj["licensee"], "张三独立安全顾问工作室")
        self.assertEqual(token_obj["tier"], "consultant")

    def test_issue_and_verify_enterprise_buyout_license(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            out_dir = Path(temp_dir)
            res = generate_license.issue_license(
                client_name="某某大型网络安全攻防实验室",
                tier="enterprise-buyout",
                contact_email="soc@corp.com",
                out_dir=out_dir,
            )

            token_file = Path(res["token_path"])
            cert_file = Path(res["cert_path"])

            self.assertTrue(token_file.exists())
            self.assertTrue(cert_file.exists())

            # Verification should pass
            self.assertTrue(generate_license.verify_license(token_file))

            # Tampering test: modify licensee name
            data = json.loads(token_file.read_text(encoding="utf-8"))
            data["licensee"] = "恶意篡改的公司名称"
            token_file.write_text(json.dumps(data), encoding="utf-8")

            # Verification must fail on tampered token
            self.assertFalse(generate_license.verify_license(token_file))

    def test_invalid_tier_rejected(self):
        with self.assertRaises(ValueError):
            generate_license.issue_license(
                client_name="Test",
                tier="invalid_tier",
                contact_email="test@test.com",
            )


if __name__ == "__main__":
    unittest.main()
