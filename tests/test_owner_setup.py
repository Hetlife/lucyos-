from unittest import mock

from aion_core import owner_setup
from tests.base import AionTest


def _caps(**overrides):
    base = dict(
        ollama=False, cloud_worker=False, cloud_worker_cmd="not configured",
        model_credential_present=False,
        github_remote_ok=False, github_remote_detail="no git remote configured",
        github_write_ok=False, github_write_detail="no git remote configured",
        github_probe_performed=True, github_credential_present=False,
        openclaw_present=False, openclaw_evidence="home contents: none",
        openclaw_gateway_detail="openclaw_port not configured",
        legacy_bridge_credential_present=False,
        razorpay_keys=False,
    )
    base.update(overrides)
    return base


class TestOwnerSetupMeasuredState(AionTest):
    def test_nothing_working_asks_for_everything_required(self):
        with mock.patch.object(owner_setup, "_capabilities", return_value=_caps()):
            text = owner_setup.render()
        self.assertIn("WhatsApp bridge (OpenClaw)  ·  not set", text)
        self.assertIn("GitHub (repo scope)  ·  not set", text)
        self.assertNotIn("Already satisfied", text)

    def test_read_only_remote_keeps_github_pat_ask(self):
        caps = _caps(github_remote_ok=True,
                      github_remote_detail="remote 'origin' reachable (read access verified, no PAT required)",
                      github_write_ok=False,
                      github_write_detail="remote 'origin' write access not proven: dry-run push failed")
        with mock.patch.object(owner_setup, "_capabilities", return_value=caps):
            text = owner_setup.render()
        self.assertIn("GitHub (repo scope)  ·  not set", text)
        self.assertNotIn("Already satisfied", text)


    def test_unprobed_bootstrap_defers_github_credential_ask(self):
        caps = _caps(github_probe_performed=False,
                     github_remote_detail="not probed during local bootstrap",
                     github_write_detail="not probed during local bootstrap")
        with mock.patch.object(owner_setup, "_capabilities", return_value=caps):
            text = owner_setup.render()
        self.assertNotIn("GitHub (repo scope)  ·  not set", text)
        self.assertIn("VERIFY EXISTING CAPABILITY", text)
        self.assertIn("aion owner-setup", text)
        self.assertIn("no new credential yet", text)

    def test_proven_write_access_removes_github_pat_ask(self):
        caps = _caps(github_remote_ok=True,
                      github_remote_detail="remote 'origin' reachable (read access verified, no PAT required)",
                      github_write_ok=True,
                      github_write_detail="remote 'origin' write access verified (dry-run push, no mutation)")
        with mock.patch.object(owner_setup, "_capabilities", return_value=caps):
            text = owner_setup.render()
        self.assertNotIn("GitHub (repo scope)  ·  not set", text)
        self.assertIn("Already satisfied", text)
        self.assertIn("Existing git remote already has proven write access", text)

    def test_local_or_cloud_model_removes_cheap_key_ask(self):
        caps = _caps(cloud_worker=True, cloud_worker_cmd="scripts/aion_codex_worker.sh")
        with mock.patch.object(owner_setup, "_capabilities", return_value=caps):
            text = owner_setup.render()
        self.assertNotIn("Model provider API key (cheap class B)  ·  not set", text)
        self.assertIn("A configured cloud worker already provides class B routing", text)

    def test_ollama_present_removes_ollama_ask(self):
        caps = _caps(ollama=True)
        with mock.patch.object(owner_setup, "_capabilities", return_value=caps):
            text = owner_setup.render()
        self.assertNotIn("Ollama (local models)  ·  not set", text)
        self.assertIn("Ollama already installed with local models available", text)

    def test_openclaw_present_removes_bridge_token_ask_without_demanding_it(self):
        caps = _caps(openclaw_present=True, openclaw_evidence="executable at /usr/local/bin/openclaw",
                      openclaw_gateway_detail="openclaw_port not configured")
        with mock.patch.object(owner_setup, "_capabilities", return_value=caps):
            text = owner_setup.render()
        self.assertNotIn("WhatsApp bridge (OpenClaw)  ·  not set", text)
        self.assertIn("OpenClaw installation detected on this machine", text)
        self.assertIn("openclaw_port not configured", text)

    def test_openclaw_present_never_claims_whatsapp_is_live(self):
        caps = _caps(openclaw_present=True, openclaw_evidence="executable at /usr/local/bin/openclaw",
                      openclaw_gateway_detail="openclaw_port not configured")
        with mock.patch.object(owner_setup, "_capabilities", return_value=caps):
            text = owner_setup.render()
        self.assertIn("NOT YET PROVEN", text)
        self.assertIn("R-05", text)
        satisfied_section = text.split("## Already satisfied", 1)[1]
        self.assertNotIn("WhatsApp becomes the live command surface", satisfied_section)

    def test_never_prints_a_secret_value(self):
        with mock.patch("aion_core.bootstrap.has_secret", return_value=True):
            with mock.patch.object(owner_setup, "_capabilities",
                                    return_value=_caps(model_credential_present=True,
                                                        github_credential_present=True,
                                                        legacy_bridge_credential_present=True,
                                                        razorpay_keys=True)):
                text = owner_setup.render()
        self.assertNotIn("=", text.split("Current machine facts")[0].replace("aion secrets set", ""))

    def test_all_capabilities_present_yields_no_required_sections(self):
        caps = _caps(ollama=True, cloud_worker=True, model_credential_present=True,
                      github_remote_ok=True, github_write_ok=True, github_credential_present=True,
                      openclaw_present=True, legacy_bridge_credential_present=True)
        with mock.patch.object(owner_setup, "_capabilities", return_value=caps):
            text = owner_setup.render()
        self.assertNotIn("REQUIRED NOW", text)
        self.assertNotIn("REQUIRED SOON", text)


class TestGithubRemoteHealthCheck(AionTest):
    def test_no_remote_configured_reports_not_required(self):
        from aion_core import health
        with mock.patch.object(health, "_run", return_value=(0, "")):
            result = health.check_github_remote()
        self.assertFalse(result["ok"])
        self.assertFalse(result["required"])
        self.assertIn("no git remote configured", result["detail"])

    def test_reachable_remote_reports_ok_without_pat_language(self):
        from aion_core import health
        calls = [(0, "origin"), (0, "abc123\tHEAD")]
        with mock.patch.object(health, "_run", side_effect=calls):
            result = health.check_github_remote()
        self.assertTrue(result["ok"])
        self.assertIn("no PAT required", result["detail"])

    def test_unreachable_remote_reports_optional_not_ok(self):
        from aion_core import health
        calls = [(0, "origin"), (128, "Could not resolve host")]
        with mock.patch.object(health, "_run", side_effect=calls):
            result = health.check_github_remote()
        self.assertFalse(result["ok"])
        self.assertFalse(result["required"])


class TestGithubWriteCapabilityProbe(AionTest):
    def test_no_remote_configured_reports_not_ok(self):
        from aion_core import health
        with mock.patch.object(health, "_run", return_value=(0, "")):
            result = health.check_github_write()
        self.assertFalse(result["ok"])
        self.assertFalse(result["required"])
        self.assertIn("no git remote configured", result["detail"])

    def test_dry_run_push_success_reports_write_ok(self):
        from aion_core import health
        calls = [(0, "origin"), (0, "Everything up-to-date")]
        with mock.patch.object(health, "_run", side_effect=calls) as mocked:
            result = health.check_github_write()
        self.assertTrue(result["ok"])
        self.assertIn("no mutation", result["detail"])
        # The push invocation must include --dry-run: proof no mutation occurs.
        push_call_args = mocked.call_args_list[1][0][0]
        self.assertIn("--dry-run", push_call_args)

    def test_dry_run_push_failure_reports_write_not_proven(self):
        from aion_core import health
        calls = [(0, "origin"), (128, "remote: Permission denied")]
        with mock.patch.object(health, "_run", side_effect=calls):
            result = health.check_github_write()
        self.assertFalse(result["ok"])
        self.assertFalse(result["required"])
        self.assertIn("not proven", result["detail"])

class TestOwnerSetupProbePolicy(AionTest):
    def test_local_bootstrap_does_not_run_github_network_probes(self):
        local_caps = {"ollama": False, "cloud_worker": False, "cloud_worker_cmd": ""}
        oc = {"present": False, "executable_on_path": None, "home_contents": []}
        gateway = {"detail": "openclaw_port not configured"}
        with mock.patch("aion_core.owner_setup.worker.capability_report", return_value=local_caps), \
             mock.patch("aion_core.owner_setup.health.openclaw", return_value=oc), \
             mock.patch("aion_core.owner_setup.health.check_openclaw", return_value=gateway), \
             mock.patch("aion_core.owner_setup.bootstrap.has_secret", return_value=False), \
             mock.patch("aion_core.owner_setup.health.check_github_remote") as read_probe, \
             mock.patch("aion_core.owner_setup.health.check_github_write") as write_probe:
            caps = owner_setup._capabilities(probe_external=False)
        read_probe.assert_not_called()
        write_probe.assert_not_called()
        self.assertFalse(caps["github_probe_performed"])
