"""The review list and the agent's settings. No model, no SDK and no database."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import tomllib
from types import SimpleNamespace

import pytest

from triage_agent.__main__ import positive
from triage_agent.config import ENV_FILE, MODEL_SLOTS, REVIEW_FILE, TOML_FILE, bare_environment, cli_environment, load_config
from triage_agent.review import ReviewError, ReviewList, changed, printable

ROW = {"ticket_id": "T00727", "subject": "Invite link expired", "status": "open", "category": "account access",
       "priority": "P2", "team": "Technical support"}
RESULT = {"category": "account access", "priority": "P3", "team": "Customer care", "reason": "Invitation trouble.",
          "record_ids": ["KB004"], "model": "x/y:free", "dropped_ids": 0}
SECRETS = "OPENROUTER_API_KEY=sk-file\nPG_HOST=db\nPG_USER=reader\nPG_PASSWORD=pw\nPG_DATABASE=orion_desk\n"


@pytest.fixture
def review(tmp_path):
    review = ReviewList(tmp_path / "deep" / "review.jsonl")
    review.propose("run1", ROW, SimpleNamespace(result=RESULT, turns=3, tool_calls=2, estimated_usd=0.05))
    return review


@pytest.fixture
def secrets(tmp_path):
    path = tmp_path / ".env.triage-agent"
    path.write_text(SECRETS)
    return path


def test_a_new_proposal_is_pending_and_keeps_stored_and_proposed_apart(review):
    proposal = review.proposals()["T00727"]
    assert proposal["status"] == "pending"
    assert proposal["current"] == {"category": "account access", "priority": "P2", "team": "Technical support"}
    assert proposal["proposed"] == {"category": "account access", "priority": "P3", "team": "Customer care"}
    assert changed(proposal) == ["priority", "team"]


@pytest.mark.parametrize("decision", ["approved", "rejected"])
def test_a_decision_names_the_person(review, decision):
    review.decide("T00727", decision, " Arun ", "Looks right")
    proposal = review.proposals()["T00727"]
    assert proposal["status"] == decision
    assert proposal["decision"]["by"] == "Arun"
    assert proposal["decision"]["note"] == "Looks right"


@pytest.mark.parametrize("by", ["", "   ", None])
def test_a_decision_with_no_name_is_refused(review, by):
    with pytest.raises(ReviewError):
        review.decide("T00727", "approved", by)
    assert review.proposals()["T00727"]["status"] == "pending"


def test_a_decision_is_final(review):
    review.decide("T00727", "rejected", "Arun")
    with pytest.raises(ReviewError, match="already rejected by Arun"):
        review.decide("T00727", "approved", "Leena")
    assert review.proposals()["T00727"]["status"] == "rejected"


def test_a_ticket_with_no_proposal_cannot_be_decided(review):
    with pytest.raises(ReviewError, match="T99999"):
        review.decide("T99999", "approved", "Arun")


def test_the_list_is_only_ever_added_to(review):
    before = review.path.read_text()
    review.decide("T00727", "approved", "Arun")
    assert review.path.read_text().startswith(before)
    assert [json.loads(line)["type"] for line in review.path.read_text().splitlines()] == ["proposal", "decision"]


def test_only_its_owner_can_read_the_list(review):
    assert review.path.stat().st_mode & 0o077 == 0
    assert review.path.parent.stat().st_mode & 0o077 == 0


def test_a_missing_list_is_empty(tmp_path):
    assert ReviewList(tmp_path / "none.jsonl").proposals() == {}


@pytest.mark.parametrize("character", ["\u2028", "\u2029", "\u0085", "\x0b", "\x0c", "\x1c"])
def test_a_character_in_a_subject_can_t_break_the_list(tmp_path, character):
    review = ReviewList(tmp_path / "review.jsonl")
    subject = f"Invite{character}link"
    review.propose("run1", {**ROW, "subject": subject}, SimpleNamespace(result=RESULT, turns=3, tool_calls=2, estimated_usd=0.05))
    review.decide("T00727", "approved", "Arun")
    assert review.proposals()["T00727"]["subject"] == subject
    assert review.proposals()["T00727"]["status"] == "approved"


def test_control_characters_never_reach_a_reviewer_s_terminal():
    assert printable("Fine\x1b[2J\nnext") == "Fine [2J next"


def test_the_shipped_settings_load(secrets):
    config = load_config(TOML_FILE, secrets)
    assert config.model.endswith(":free")
    assert config.base_url == "https://openrouter.ai/api"
    assert config.limits.real_usd_per_run == 0


def test_a_model_that_is_not_free_is_refused(tmp_path, secrets):
    paid = tmp_path / "agent.toml"
    paid.write_text(TOML_FILE.read_text().replace('name = "nvidia/nemotron-3-ultra-550b-a55b:free"', 'name = "openai/gpt-6-luna"'))
    with pytest.raises(SystemExit, match="free model"):
        load_config(paid, secrets)


def test_the_key_goes_only_to_openrouter(tmp_path, secrets):
    moved = tmp_path / "agent.toml"
    moved.write_text(TOML_FILE.read_text().replace("https://openrouter.ai/api", "https://example.com/api"))
    with pytest.raises(SystemExit, match="goes only to"):
        load_config(moved, secrets)


@pytest.mark.parametrize("tickets", ["0", "-5"])
def test_a_ticket_count_below_one_is_refused(tickets):
    assert positive("1") == 1
    with pytest.raises(argparse.ArgumentTypeError):
        positive(tickets)


def test_a_missing_secret_is_named_and_its_value_is_not(tmp_path):
    path = tmp_path / ".env.triage-agent"
    path.write_text("OPENROUTER_API_KEY=sk-file\n")
    with pytest.raises(SystemExit, match="PG_HOST, PG_USER, PG_PASSWORD, PG_DATABASE") as stopped:
        load_config(TOML_FILE, path)
    assert "sk-file" not in str(stopped.value)


def test_the_environment_changes_nothing(monkeypatch, secrets):
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-shell")
    monkeypatch.setenv("PG_USER", "owner")
    config = load_config(TOML_FILE, secrets)
    assert config.openrouter_key == "sk-file"
    assert config.database.pg_user == "reader"


def test_settings_never_print_their_secrets(secrets):
    assert "sk-file" not in repr(load_config(TOML_FILE, secrets))


def test_every_model_name_the_cli_knows_is_the_free_model(secrets):
    config = load_config(TOML_FILE, secrets)
    env = cli_environment(config, "/empty")
    assert {env[name] for name in MODEL_SLOTS} == {config.model}
    assert env["ANTHROPIC_API_KEY"] == ""
    assert env["HOME"] == env["CLAUDE_CONFIG_DIR"] == "/empty"


def test_the_agent_s_environment_is_bare_and_comes_back(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-mine")
    monkeypatch.setenv("CLAUDE_CODE_OAUTH_TOKEN", "mine")
    monkeypatch.setenv("PG_PASSWORD", "owner-password")
    with bare_environment():
        assert not {"ANTHROPIC_API_KEY", "CLAUDE_CODE_OAUTH_TOKEN", "PG_PASSWORD"} & set(os.environ)
        assert "PATH" in os.environ
    assert os.environ["ANTHROPIC_API_KEY"] == "sk-mine"


def test_git_ignores_the_secrets_and_the_list():
    root = Path(__file__).resolve().parents[2]
    for path in (ENV_FILE, REVIEW_FILE):
        assert subprocess.run(["git", "check-ignore", "-q", str(path)], cwd=root).returncode == 0


def test_the_deployed_api_neither_needs_nor_loads_the_agent():
    project = tomllib.loads((Path(__file__).resolve().parents[1] / "pyproject.toml").read_text())["project"]
    assert not [name for name in project["dependencies"] if "claude" in name]
    loaded = subprocess.run([sys.executable, "-c", "import sys, orion_api.main; print(sorted(sys.modules))"],
                            capture_output=True, text=True, check=True, cwd=Path(__file__).resolve().parents[1]).stdout
    assert "claude_agent_sdk" not in loaded
    assert "triage_agent" not in loaded
