from __future__ import annotations

import sys
import tempfile
import unittest
from contextlib import nullcontext
from pathlib import Path
from subprocess import CompletedProcess
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from mvc_app.services.cli_mutation_service import MutationError, run_cli_mutation


class CliMutationSafetyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        root = Path(self.temp_dir.name)

        self.script_root = root / "scripts"
        self.script_root.mkdir(parents=True, exist_ok=True)
        script = self.script_root / "addws"
        script.write_text("#!/bin/sh\necho ok\n", encoding="utf-8")
        script.chmod(0o755)

        self.xray_config_path = root / "config.json"
        self.xray_config_path.write_text("{}\n", encoding="utf-8")

        self.snapshot_dir = root / "snapshots"
        self.audit_log_path = root / "audit.log"
        self.lock_file = root / "mutation.lock"

        self.payload = {
            "username": "demo-vmess",
            "days": 30,
            "quota_gb": 0,
            "ip_limit": 1,
            "sni_profile": "3",
        }

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    @patch("mvc_app.services.cli_mutation_service.subprocess.run")
    @patch("mvc_app.services.cli_mutation_service.append_audit_log")
    @patch("mvc_app.services.cli_mutation_service._attempt_rollback")
    @patch("mvc_app.services.cli_mutation_service._postcheck_xray_runtime")
    @patch("mvc_app.services.cli_mutation_service._create_snapshot")
    @patch("mvc_app.services.cli_mutation_service._run_xray_test")
    @patch("mvc_app.services.cli_mutation_service.mutation_lock")
    def test_success_marks_preflight_and_postcheck(
        self,
        mocked_lock,
        mocked_precheck,
        mocked_snapshot,
        mocked_postcheck,
        mocked_rollback,
        mocked_audit,
        mocked_subprocess,
    ) -> None:
        mocked_lock.return_value = nullcontext()
        mocked_snapshot.return_value = {
            "id": "snap-1",
            "path": str(self.snapshot_dir / "snap-1"),
            "entries": [],
        }
        mocked_subprocess.return_value = CompletedProcess(
            args=["bash"],
            returncode=0,
            stdout="Username: demo-vmess\n",
            stderr="",
        )

        result = run_cli_mutation(
            operation="create",
            protocol="vmess",
            payload=self.payload,
            operator="tester",
            script_root=str(self.script_root),
            lock_file=str(self.lock_file),
            lock_timeout_seconds=1,
            command_timeout_seconds=5,
            audit_log_path=str(self.audit_log_path),
            mutation_safety_enabled=True,
            mutation_snapshot_dir=str(self.snapshot_dir),
            xray_binary_path="/usr/bin/xray",
            xray_config_path=str(self.xray_config_path),
            mutation_postcheck_timeout_seconds=5,
            mutation_precheck_xray=True,
        )

        self.assertEqual(result.returncode, 0)
        safety = result.details["safety"]
        self.assertTrue(safety["enabled"])
        self.assertTrue(safety["preflight_ok"])
        self.assertTrue(safety["postcheck_ok"])
        self.assertEqual(safety["snapshot_id"], "snap-1")
        self.assertEqual(safety["rollback_status"], "not-needed")

        mocked_precheck.assert_called_once()
        mocked_postcheck.assert_called_once()
        mocked_rollback.assert_not_called()
        self.assertGreaterEqual(mocked_audit.call_count, 2)

    @patch("mvc_app.services.cli_mutation_service.subprocess.run")
    @patch("mvc_app.services.cli_mutation_service.append_audit_log")
    @patch("mvc_app.services.cli_mutation_service._attempt_rollback")
    @patch("mvc_app.services.cli_mutation_service._postcheck_xray_runtime")
    @patch("mvc_app.services.cli_mutation_service._create_snapshot")
    @patch("mvc_app.services.cli_mutation_service._run_xray_test")
    @patch("mvc_app.services.cli_mutation_service.mutation_lock")
    def test_postcheck_failure_triggers_rollback(
        self,
        mocked_lock,
        mocked_precheck,
        mocked_snapshot,
        mocked_postcheck,
        mocked_rollback,
        mocked_audit,
        mocked_subprocess,
    ) -> None:
        mocked_lock.return_value = nullcontext()
        mocked_snapshot.return_value = {
            "id": "snap-2",
            "path": str(self.snapshot_dir / "snap-2"),
            "entries": [],
        }
        mocked_subprocess.return_value = CompletedProcess(
            args=["bash"],
            returncode=0,
            stdout="Username: demo-vmess\n",
            stderr="",
        )
        mocked_postcheck.side_effect = MutationError("Restart service xray gagal")
        mocked_rollback.return_value = (True, "rollback selesai")

        with self.assertRaises(MutationError) as raised:
            run_cli_mutation(
                operation="create",
                protocol="vmess",
                payload=self.payload,
                operator="tester",
                script_root=str(self.script_root),
                lock_file=str(self.lock_file),
                lock_timeout_seconds=1,
                command_timeout_seconds=5,
                audit_log_path=str(self.audit_log_path),
                mutation_safety_enabled=True,
                mutation_snapshot_dir=str(self.snapshot_dir),
                xray_binary_path="/usr/bin/xray",
                xray_config_path=str(self.xray_config_path),
                mutation_postcheck_timeout_seconds=5,
                mutation_precheck_xray=True,
            )

        self.assertIn("Rollback otomatis berhasil", str(raised.exception))
        mocked_rollback.assert_called_once()

        final_audit = mocked_audit.call_args_list[-1].args[1]
        self.assertEqual(final_audit["status"], "failed")
        self.assertEqual(final_audit["safety"]["rollback_reason"], "postcheck_failed")
        self.assertEqual(final_audit["safety"]["rollback_status"], "success")

    @patch("mvc_app.services.cli_mutation_service.subprocess.run")
    @patch("mvc_app.services.cli_mutation_service.append_audit_log")
    @patch("mvc_app.services.cli_mutation_service._attempt_rollback")
    @patch("mvc_app.services.cli_mutation_service._postcheck_xray_runtime")
    @patch("mvc_app.services.cli_mutation_service._create_snapshot")
    @patch("mvc_app.services.cli_mutation_service._run_xray_test")
    @patch("mvc_app.services.cli_mutation_service.mutation_lock")
    def test_script_failure_reports_rollback_error(
        self,
        mocked_lock,
        mocked_precheck,
        mocked_snapshot,
        mocked_postcheck,
        mocked_rollback,
        mocked_audit,
        mocked_subprocess,
    ) -> None:
        mocked_lock.return_value = nullcontext()
        mocked_snapshot.return_value = {
            "id": "snap-3",
            "path": str(self.snapshot_dir / "snap-3"),
            "entries": [],
        }
        mocked_subprocess.return_value = CompletedProcess(
            args=["bash"],
            returncode=1,
            stdout="",
            stderr="script gagal",
        )
        mocked_rollback.return_value = (False, "restore gagal")

        with self.assertRaises(MutationError) as raised:
            run_cli_mutation(
                operation="create",
                protocol="vmess",
                payload=self.payload,
                operator="tester",
                script_root=str(self.script_root),
                lock_file=str(self.lock_file),
                lock_timeout_seconds=1,
                command_timeout_seconds=5,
                audit_log_path=str(self.audit_log_path),
                mutation_safety_enabled=True,
                mutation_snapshot_dir=str(self.snapshot_dir),
                xray_binary_path="/usr/bin/xray",
                xray_config_path=str(self.xray_config_path),
                mutation_postcheck_timeout_seconds=5,
                mutation_precheck_xray=True,
            )

        self.assertIn("Rollback gagal: restore gagal", str(raised.exception))
        mocked_rollback.assert_called_once()
        mocked_postcheck.assert_not_called()

        final_audit = mocked_audit.call_args_list[-1].args[1]
        self.assertEqual(final_audit["status"], "failed")
        self.assertEqual(final_audit["returncode"], 1)
        self.assertEqual(final_audit["safety"]["rollback_reason"], "script_failed")
        self.assertEqual(final_audit["safety"]["rollback_status"], "failed")


if __name__ == "__main__":
    unittest.main()
