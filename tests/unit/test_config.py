"""Tests for configuration module."""
import os
import pytest
from pathlib import Path
from agentctl.shared.config import Config, parse_duration


def test_config_defaults():
    """Config should have sensible defaults."""
    config = Config()
    assert config.gcp_region == "us-central1"
    assert config.default_timeout == "4h"


def test_config_load_from_file(tmp_path):
    """Config should load from YAML file."""
    config_file = tmp_path / "config.yaml"
    config_file.write_text("gcp_project: my-project\ngcp_region: us-west1\n")

    config = Config.load(config_file)
    assert config.gcp_project == "my-project"
    assert config.gcp_region == "us-west1"


def test_config_env_override(tmp_path, monkeypatch):
    """Environment variables should override file values."""
    config_file = tmp_path / "config.yaml"
    config_file.write_text("gcp_project: file-project\n")

    monkeypatch.setenv("AGENTCTL_GCP_PROJECT", "env-project")
    config = Config.load(config_file)
    assert config.gcp_project == "env-project"


def test_config_save(tmp_path):
    """Config should save to YAML file."""
    config_file = tmp_path / "config.yaml"
    config = Config(gcp_project="test-project")
    config.save(config_file)

    loaded = Config.load(config_file)
    assert loaded.gcp_project == "test-project"


def test_parse_duration():
    """parse_duration should handle various formats."""
    assert parse_duration("4h") == 14400
    assert parse_duration("30m") == 1800
    assert parse_duration("60s") == 60
    assert parse_duration("3600") == 3600
