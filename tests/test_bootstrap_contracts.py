"""Installation fails before pip when the reviewed distribution pin changes."""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools import bootstrap_contracts


class BootstrapPinTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.wheel = self.root / "vendor/sfstack_contracts-1.1.0-py3-none-any.whl"
        self.wheel.parent.mkdir()
        with zipfile.ZipFile(self.wheel, "w") as archive:
            archive.writestr("sfstack_contracts-1.1.0.dist-info/METADATA", "Name: sfstack-contracts\nVersion: 1.1.0\n")
        self.dependencies = self.root / "requirements-runtime.txt"
        self.dependencies.write_text("example==1.0 --hash=sha256:" + "1" * 64 + "\n")
        self.lock_path = self.root / "sfstack.lock.json"
        self.lock = {
            "schema_version": 1, "interface_version": "1.1", "distribution_version": "1.1.0",
            "source": {"repository": "https://github.com/grove/sfstack", "commit": "a" * 40},
            "artifact": {"path": str(self.wheel.relative_to(self.root)),
                         "sha256": hashlib.sha256(self.wheel.read_bytes()).hexdigest()},
            "dependencies_sha256": hashlib.sha256(self.dependencies.read_bytes()).hexdigest(),
        }
        self.write_lock(self.lock)
        for patcher in (patch.object(bootstrap_contracts, "ROOT", self.root),
                        patch.object(bootstrap_contracts, "LOCK", self.lock_path)):
            patcher.start()
            self.addCleanup(patcher.stop)

    def write_lock(self, lock):
        self.lock_path.write_text(json.dumps(lock))

    def test_exact_distribution_and_dependency_hashes_are_accepted_without_installing(self):
        with patch.object(bootstrap_contracts.subprocess, "run") as run:
            lock, wheel, dependencies = bootstrap_contracts.verified_inputs()
            run.assert_not_called()
        self.assertEqual(self.lock, lock)
        self.assertEqual(self.wheel, wheel)
        self.assertEqual(self.dependencies, dependencies)

    def test_changed_wheel_is_rejected_before_any_install(self):
        self.wheel.write_bytes(self.wheel.read_bytes() + b"tampered")
        with patch.object(bootstrap_contracts.subprocess, "run") as run:
            with self.assertRaisesRegex(ValueError, "SHA-256"):
                bootstrap_contracts.verified_inputs()
            run.assert_not_called()

    def test_changed_dependency_lock_is_rejected(self):
        self.dependencies.write_text("example==2.0\n")
        with self.assertRaisesRegex(ValueError, "dependency lock"):
            bootstrap_contracts.verified_inputs()

    def test_unpinned_source_or_wrong_distribution_is_rejected(self):
        for field, value in (("commit", "main"), ("repository", "https://example.invalid/replacement")):
            with self.subTest(field=field):
                lock = deepcopy(self.lock)
                lock["source"][field] = value
                self.write_lock(lock)
                with self.assertRaises(ValueError):
                    bootstrap_contracts.verified_inputs()

    def test_symlink_distribution_cannot_substitute_for_locked_file(self):
        original = self.root / "original.whl"
        self.wheel.rename(original)
        self.wheel.symlink_to(original)
        with self.assertRaisesRegex(ValueError, "symlinks"):
            bootstrap_contracts.verified_inputs()


if __name__ == "__main__":
    unittest.main()
