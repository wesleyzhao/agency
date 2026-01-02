"""Tests for provider interface."""
import pytest
from pathlib import Path
from agentctl.providers.base import CloudProvider, VMConfig
from agentctl.providers.local import LocalProvider


def test_local_provider_secrets(tmp_path):
    """LocalProvider should store and retrieve secrets."""
    provider = LocalProvider(data_dir=tmp_path)

    provider.set_secret("test-key", "test-value")
    assert provider.get_secret("test-key") == "test-value"
    assert provider.get_secret("nonexistent") is None


def test_local_provider_files(tmp_path):
    """LocalProvider should store and retrieve files."""
    provider = LocalProvider(data_dir=tmp_path)

    # Create a test file
    local_file = tmp_path / "test.txt"
    local_file.write_text("hello")

    # Upload
    url = provider.upload_file(local_file, "bucket/test.txt")
    assert "local://" in url

    # Download
    download_path = tmp_path / "downloaded.txt"
    provider.download_file("bucket/test.txt", download_path)
    assert download_path.read_text() == "hello"

    # List
    files = provider.list_files("bucket/")
    assert "bucket/test.txt" in files
