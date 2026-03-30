from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from mvc_app import create_app
from mvc_app.services import MutationResult


class ApiEndpointTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        root = Path(self.temp_dir.name)

        user_file = root / "user"
        pass_file = root / "password"
        xray_config = root / "config.json"

        user_file.write_text("admin\n", encoding="utf-8")
        pass_file.write_text("secret\n", encoding="utf-8")
        xray_config.write_text("{}\n", encoding="utf-8")

        script_root = root / "scripts"
        script_root.mkdir(parents=True, exist_ok=True)

        app = create_app()
        app.config.update(
            TESTING=True,
            SECRET_KEY="test-secret",
            PANEL_USER_FILE=str(user_file),
            PANEL_PASS_FILE=str(pass_file),
            XRAY_CONFIG_PATH=str(xray_config),
            CLI_SCRIPT_ROOT=str(script_root),
            MUTATION_LOCK_FILE=str(root / "mutation.lock"),
            MUTATION_LOCK_TIMEOUT_SEC=1,
            CLI_MUTATION_TIMEOUT_SEC=5,
            AUDIT_LOG_PATH=str(root / "audit.log"),
            MUTATION_SAFETY_ENABLED=True,
            MUTATION_PRECHECK_XRAY=True,
            MUTATION_POSTCHECK_TIMEOUT_SEC=5,
            MUTATION_SNAPSHOT_DIR=str(root / "snapshots"),
            XRAY_BINARY_PATH="/usr/bin/xray",
        )

        self.client = app.test_client()

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def _login(self) -> None:
        with self.client.session_transaction() as session:
            session["authenticated"] = True
            session["operator"] = "tester"

    def test_requires_login_for_service_action(self) -> None:
        response = self.client.post(
            "/api/services/vmess/actions/create",
            json={},
        )

        self.assertEqual(response.status_code, 401)
        payload = response.get_json()
        self.assertFalse(payload["ok"])
        self.assertIn("Sesi login habis", payload["message"])

    def test_rejects_non_object_json_payload(self) -> None:
        self._login()
        response = self.client.post(
            "/api/services/vmess/actions/create",
            json=["bad", "payload"],
        )

        self.assertEqual(response.status_code, 400)
        payload = response.get_json()
        self.assertFalse(payload["ok"])
        self.assertIn("Payload JSON harus berbentuk object", payload["message"])

    def test_rejects_invalid_username_pattern(self) -> None:
        self._login()
        response = self.client.post(
            "/api/services/vmess/actions/create",
            json={
                "username": "bad user",
                "days": 30,
                "quota_gb": 0,
                "ip_limit": 1,
                "sni_profile": "3",
            },
        )

        self.assertEqual(response.status_code, 400)
        payload = response.get_json()
        self.assertFalse(payload["ok"])
        self.assertIn("Username hanya boleh", payload["message"])

    def test_rejects_missing_required_field(self) -> None:
        self._login()
        response = self.client.post(
            "/api/services/vmess/actions/create",
            json={
                "days": 30,
                "quota_gb": 0,
                "ip_limit": 1,
                "sni_profile": "3",
            },
        )

        self.assertEqual(response.status_code, 400)
        payload = response.get_json()
        self.assertFalse(payload["ok"])
        self.assertIn("Field Username wajib diisi", payload["message"])

    @patch("mvc_app.controllers.api_controller.run_cli_mutation")
    def test_service_action_sanitizes_payload_and_returns_result(
        self,
        mocked_run_cli_mutation,
    ) -> None:
        self._login()
        mocked_run_cli_mutation.return_value = MutationResult(
            operation="create",
            protocol="vmess",
            script_name="addws",
            username="vm-test",
            returncode=0,
            stdout_tail="ok",
            stderr_tail="",
            details={
                "fields": [
                    {
                        "key": "username",
                        "label": "Username",
                        "value": "vm-test",
                    }
                ],
                "links": [],
                "safety": {
                    "enabled": True,
                    "preflight_ok": True,
                    "postcheck_ok": True,
                    "snapshot_id": "snap-1",
                    "rollback_status": "not-needed",
                },
            },
        )

        response = self.client.post(
            "/api/services/vmess/actions/create",
            json={
                "username": "vm-test",
                "days": "30",
                "quota_gb": "0",
                "ip_limit": "1",
                "sni_profile": "3",
                "ignored": "should-not-pass",
            },
        )

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertTrue(payload["ok"])

        called_payload = mocked_run_cli_mutation.call_args.kwargs["payload"]
        self.assertEqual(called_payload["username"], "vm-test")
        self.assertEqual(called_payload["days"], 30)
        self.assertEqual(called_payload["quota_gb"], 0)
        self.assertEqual(called_payload["ip_limit"], 1)
        self.assertNotIn("ignored", called_payload)
        self.assertEqual(called_payload["protocol"], "vmess")
        self.assertEqual(called_payload["operation"], "create")

        safety = payload["result"]["details"]["safety"]
        self.assertTrue(safety["enabled"])
        self.assertEqual(safety["snapshot_id"], "snap-1")

    @patch("mvc_app.controllers.api_controller.run_cli_mutation")
    def test_mutations_endpoint_uses_operation_schema(self, mocked_run_cli_mutation) -> None:
        self._login()
        mocked_run_cli_mutation.return_value = MutationResult(
            operation="renew",
            protocol="vless",
            script_name="renewvless",
            username="vless-01",
            returncode=0,
            stdout_tail="ok",
            stderr_tail="",
            details={"fields": [], "links": [], "safety": {"enabled": True}},
        )

        response = self.client.post(
            "/api/mutations",
            json={
                "protocol": "vless",
                "operation": "renew",
                "username": "vless-01",
                "days": "10",
                "quota_gb": "5",
                "ip_limit": "2",
                "extra_field": "drop-me",
            },
        )

        self.assertEqual(response.status_code, 200)
        called_payload = mocked_run_cli_mutation.call_args.kwargs["payload"]
        self.assertEqual(called_payload["protocol"], "vless")
        self.assertEqual(called_payload["operation"], "renew")
        self.assertEqual(called_payload["username"], "vless-01")
        self.assertEqual(called_payload["days"], 10)
        self.assertEqual(called_payload["quota_gb"], 5)
        self.assertEqual(called_payload["ip_limit"], 2)
        self.assertNotIn("extra_field", called_payload)


if __name__ == "__main__":
    unittest.main()
