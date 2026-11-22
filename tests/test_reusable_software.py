"""Structural safety boundaries for the reusable Software Factory workflow."""
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
SOFTWARE = ROOT / ".github/workflows/sfstack-software.yml"
BUILD = ROOT / ".github/workflows/sfstack-build.md"
LOCK = ROOT / ".github/workflows/sfstack-build.lock.yml"


def jobs(source):
    return dict(re.findall(
        r"(?ms)^  ([a-z_]+):\n(.*?)(?=^  [a-z_]+:\n|\Z)",
        source.split("\njobs:\n", 1)[1],
    ))


class ReusableSoftwareBoundaryTests(unittest.TestCase):
    def test_explicit_manual_or_reusable_call_only(self):
        source = SOFTWARE.read_text(encoding="utf-8")
        self.assertIn("  workflow_call:\n", source)
        self.assertIn("  workflow_dispatch:\n", source)
        for key in ("issue-number", "allowed-paths", "acceptance-criteria",
                    "repair-mode", "regression-file"):
            self.assertIn("      " + key + ":\n", source)
        self.assertIn("      COPILOT_GITHUB_TOKEN:\n        required: true", source)
        for unsafe in ("pull_request_target:", "  pull_request:", "  push:", "  schedule:"):
            self.assertNotIn(unsafe, source)
        self.assertIn("run-name: \"sfstack software / issue #$", source)

    def test_controller_checkouts_are_callee_sha_bound_and_candidate_is_caller_bound(self):
        source = SOFTWARE.read_text(encoding="utf-8")
        selected = jobs(source)
        self.assertEqual({"prepare", "build", "verify", "publish"}, set(selected))
        for name in ("prepare", "verify", "publish"):
            job = selected[name]
            self.assertEqual(1, job.count("repository: $" + "{{ job.workflow_repository }}"))
            self.assertEqual(1, job.count("ref: $" + "{{ job.workflow_sha }}"))
            self.assertNotIn("ref: $" + "{{ github.workflow_sha }}\n          path: controller", job)
        self.assertIn("repository: $" + "{{ github.repository }}", selected["prepare"])
        self.assertIn("ref: $" + "{{ github.workflow_sha }}\n          path: candidate", selected["prepare"])
        self.assertIn("--repo candidate --issue-number", selected["prepare"])
        for name in ("verify", "publish"):
            self.assertIn("repository: $" + "{{ github.repository }}", selected[name])
            self.assertIn("ref: $" + "{{ needs.prepare.outputs.base-sha }}", selected[name])
        self.assertIn("--repo candidate --out publication.json", selected["publish"])
        self.assertIn("uses: $/.github/workflows/sfstack-build.lock.yml", selected["build"])
        self.assertNotIn("uses: ./.github/workflows/sfstack-build.lock.yml", source)

    def test_write_permissions_are_isolated_to_trusted_publisher(self):
        selected = jobs(SOFTWARE.read_text(encoding="utf-8"))
        for name in ("prepare", "verify", "build"):
            self.assertNotIn("contents: write", selected[name])
            self.assertNotIn("pull-requests: write", selected[name])
            self.assertNotIn("checks: write", selected[name])
        publication = selected["publish"]
        for key in ("contents: write", "pull-requests: write", "actions: write", "checks: write"):
            self.assertIn(key, publication)
        self.assertIn("group: sfstack-quality-publication-$" + "{{ github.repository }}", publication)
        self.assertIn("persist-credentials: false", publication)
        self.assertNotIn("pull_request_target:", SOFTWARE.read_text())

    def test_compiled_build_has_inlined_prompt_and_callee_owned_controller(self):
        authored, compiled = BUILD.read_text(encoding="utf-8"), LOCK.read_text(encoding="utf-8")
        self.assertIn("inlined-imports: true", authored)
        self.assertNotIn("ref: $" + "{{ github.workflow_sha }}", authored)
        self.assertEqual(2, authored.count("ref: $" + "{{ job.workflow_sha }}"))
        self.assertEqual(2, authored.count("repository: $" + "{{ job.workflow_repository }}"))
        self.assertIn("ref: $" + "{{ inputs.base-sha }}", authored)
        self.assertNotIn('"author_file"', compiled)
        self.assertIn("GH_AW_PROMPT_CONTENT_0004", compiled)
        self.assertIn("Perform the bounded", compiled)
        self.assertIn("repository: $" + "{{ job.workflow_repository }}", compiled)
        self.assertIn("ref: $" + "{{ job.workflow_sha }}", compiled)
        self.assertNotIn("ref: $" + "{{ github.workflow_sha }}", compiled)

    def test_nested_dollar_self_reference_matches_proven_quality_reuse(self):
        # GitHub.com documents $/ for nested reusable workflows, resolved to
        # the repository and immutable commit containing the reference:
        # https://docs.github.com/en/actions/how-tos/reuse-automations/reuse-workflows
        # Factory's nested Quality review used $/ successfully in the real
        # sfstack cross-repository run 44925384278; this is analogous syntax
        # evidence, not proof of a complete Software issue-to-draft run.
        source = SOFTWARE.read_text(encoding="utf-8")
        quality = (ROOT / ".github/workflows/sfstack-quality.yml").read_text(encoding="utf-8")
        self.assertIn("uses: $/.github/workflows/sfstack-build.lock.yml", source)
        self.assertIn("uses: $/.github/workflows/sfstack-review.lock.yml", quality)
        self.assertNotIn("uses: ./.github/workflows/sfstack-build.lock.yml", source)

    def test_publish_cli_explicit_candidate_path_not_trusted_controller(self):
        source = (ROOT / "integrations/github/software.py").read_text(encoding="utf-8")
        self.assertIn('publication.add_argument("--repo", default=str(ROOT)', source)
        self.assertIn("host.publish(args.bundle, args.result, args.repo)", source)
        self.assertNotIn("host.publish(args.bundle, args.result, ROOT)", source)


if __name__ == "__main__":
    unittest.main()
