"""Tests for authentication module."""
import json
import pytest
from agency_quickdeploy.auth import (
    AuthType,
    Credentials,
    OAuthCredentials,
    validate_api_key,
    validate_oauth_token,
    parse_oauth_credentials_json,
    generate_credentials_json,
)


class TestAuthType:
    """Tests for AuthType enum."""

    def test_auth_type_values(self):
        """AuthType should have api_key and oauth values."""
        assert AuthType.API_KEY.value == "api_key"
        assert AuthType.OAUTH.value == "oauth"

    def test_auth_type_from_string(self):
        """AuthType should be creatable from string."""
        assert AuthType("api_key") == AuthType.API_KEY
        assert AuthType("oauth") == AuthType.OAUTH


class TestValidateApiKey:
    """Tests for API key validation."""

    def test_valid_api_key(self):
        """Valid API keys should pass validation."""
        assert validate_api_key("sk-ant-api03-abcdef123456") is True

    def test_invalid_api_key_empty(self):
        """Empty API key should fail validation."""
        assert validate_api_key("") is False
        assert validate_api_key(None) is False

    def test_invalid_api_key_wrong_prefix(self):
        """API key with wrong prefix should fail validation."""
        assert validate_api_key("wrong-prefix-key") is False
        assert validate_api_key("sk-ant-oat01-this-is-oauth") is False


class TestValidateOAuthToken:
    """Tests for OAuth token validation."""

    def test_valid_oauth_token(self):
        """Valid OAuth tokens should pass validation."""
        assert validate_oauth_token("sk-ant-oat01-abcdef123456") is True

    def test_invalid_oauth_token_empty(self):
        """Empty OAuth token should fail validation."""
        assert validate_oauth_token("") is False
        assert validate_oauth_token(None) is False

    def test_invalid_oauth_token_wrong_prefix(self):
        """OAuth token with wrong prefix should fail validation."""
        assert validate_oauth_token("sk-ant-api03-this-is-api-key") is False


class TestParseOAuthCredentialsJson:
    """Tests for parsing OAuth credentials JSON."""

    def test_parse_valid_credentials(self):
        """Valid credentials JSON should parse correctly."""
        json_str = json.dumps({
            "claudeAiOauth": {
                "accessToken": "sk-ant-oat01-test-token",
                "refreshToken": "sk-ant-ort01-refresh-token",
                "expiresAt": 1748658860401,
                "scopes": ["user:inference", "user:profile"]
            }
        })
        creds = parse_oauth_credentials_json(json_str)
        assert creds is not None
        assert creds.access_token == "sk-ant-oat01-test-token"
        assert creds.refresh_token == "sk-ant-ort01-refresh-token"

    def test_parse_invalid_json(self):
        """Invalid JSON should return None."""
        assert parse_oauth_credentials_json("not json") is None
        assert parse_oauth_credentials_json("") is None

    def test_parse_missing_oauth_key(self):
        """JSON without claudeAiOauth key should return None."""
        json_str = json.dumps({"other": "data"})
        assert parse_oauth_credentials_json(json_str) is None


class TestCredentials:
    """Tests for Credentials container."""

    def test_api_key_credentials(self):
        """Should create API key credentials."""
        creds = Credentials.from_api_key("sk-ant-api03-test")
        assert creds.auth_type == AuthType.API_KEY
        assert creds.api_key == "sk-ant-api03-test"
        assert creds.oauth is None

    def test_oauth_credentials(self):
        """Should create OAuth credentials."""
        oauth = OAuthCredentials(access_token="sk-ant-oat01-test")
        creds = Credentials.from_oauth(oauth)
        assert creds.auth_type == AuthType.OAUTH
        assert creds.oauth.access_token == "sk-ant-oat01-test"

    def test_get_metadata_api_key(self):
        """Should generate correct metadata for API key."""
        creds = Credentials.from_api_key("sk-ant-api03-test")
        metadata = creds.get_vm_metadata()

        assert metadata["auth-type"] == "api_key"
        assert metadata["anthropic-api-key"] == "sk-ant-api03-test"
        assert "oauth-credentials" not in metadata

    def test_get_metadata_oauth(self):
        """Should generate correct metadata for OAuth."""
        oauth = OAuthCredentials(
            access_token="sk-ant-oat01-test",
            refresh_token="sk-ant-ort01-refresh"
        )
        creds = Credentials.from_oauth(oauth)
        metadata = creds.get_vm_metadata()

        assert metadata["auth-type"] == "oauth"
        assert "anthropic-api-key" not in metadata
        assert "oauth-credentials" in metadata

    def test_from_oauth_json(self):
        """Should create credentials from OAuth JSON."""
        json_str = json.dumps({
            "claudeAiOauth": {
                "accessToken": "sk-ant-oat01-from-json"
            }
        })
        creds = Credentials.from_oauth_json(json_str)
        assert creds is not None
        assert creds.auth_type == AuthType.OAUTH
        assert creds.oauth.access_token == "sk-ant-oat01-from-json"

    def test_from_oauth_json_invalid(self):
        """Should return None for invalid JSON."""
        assert Credentials.from_oauth_json("invalid") is None
