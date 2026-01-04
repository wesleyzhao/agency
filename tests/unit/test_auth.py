"""Tests for authentication module."""
import json
import pytest
from agentctl.shared.auth import (
    AuthConfig,
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

    def test_valid_api_key_variations(self):
        """Various valid API key formats should pass."""
        assert validate_api_key("sk-ant-api01-short") is True
        assert validate_api_key("sk-ant-api03-" + "a" * 100) is True

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

    def test_valid_oauth_token_variations(self):
        """Various valid OAuth token formats should pass."""
        assert validate_oauth_token("sk-ant-oat01-short") is True
        assert validate_oauth_token("sk-ant-oat01-" + "a" * 100) is True

    def test_invalid_oauth_token_empty(self):
        """Empty OAuth token should fail validation."""
        assert validate_oauth_token("") is False
        assert validate_oauth_token(None) is False

    def test_invalid_oauth_token_wrong_prefix(self):
        """OAuth token with wrong prefix should fail validation."""
        assert validate_oauth_token("wrong-prefix-token") is False
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
        assert creds.expires_at == 1748658860401
        assert creds.scopes == ["user:inference", "user:profile"]

    def test_parse_minimal_credentials(self):
        """Credentials with only access token should parse."""
        json_str = json.dumps({
            "claudeAiOauth": {
                "accessToken": "sk-ant-oat01-minimal"
            }
        })
        creds = parse_oauth_credentials_json(json_str)
        assert creds is not None
        assert creds.access_token == "sk-ant-oat01-minimal"
        assert creds.refresh_token is None

    def test_parse_invalid_json(self):
        """Invalid JSON should return None."""
        assert parse_oauth_credentials_json("not json") is None
        assert parse_oauth_credentials_json("") is None

    def test_parse_missing_oauth_key(self):
        """JSON without claudeAiOauth key should return None."""
        json_str = json.dumps({"other": "data"})
        assert parse_oauth_credentials_json(json_str) is None

    def test_parse_missing_access_token(self):
        """JSON without accessToken should return None."""
        json_str = json.dumps({
            "claudeAiOauth": {
                "refreshToken": "sk-ant-ort01-refresh"
            }
        })
        assert parse_oauth_credentials_json(json_str) is None


class TestGenerateCredentialsJson:
    """Tests for generating credentials JSON."""

    def test_generate_full_credentials(self):
        """Should generate complete credentials JSON."""
        creds = OAuthCredentials(
            access_token="sk-ant-oat01-test",
            refresh_token="sk-ant-ort01-refresh",
            expires_at=1748658860401,
            scopes=["user:inference"]
        )
        json_str = generate_credentials_json(creds)
        parsed = json.loads(json_str)

        assert parsed["claudeAiOauth"]["accessToken"] == "sk-ant-oat01-test"
        assert parsed["claudeAiOauth"]["refreshToken"] == "sk-ant-ort01-refresh"
        assert parsed["claudeAiOauth"]["expiresAt"] == 1748658860401
        assert parsed["claudeAiOauth"]["scopes"] == ["user:inference"]

    def test_generate_minimal_credentials(self):
        """Should generate credentials with only access token."""
        creds = OAuthCredentials(access_token="sk-ant-oat01-minimal")
        json_str = generate_credentials_json(creds)
        parsed = json.loads(json_str)

        assert parsed["claudeAiOauth"]["accessToken"] == "sk-ant-oat01-minimal"
        assert "refreshToken" not in parsed["claudeAiOauth"]

    def test_roundtrip(self):
        """Generate and parse should be reversible."""
        original = OAuthCredentials(
            access_token="sk-ant-oat01-roundtrip",
            refresh_token="sk-ant-ort01-refresh",
            expires_at=1748658860401,
            scopes=["user:inference", "user:profile"]
        )
        json_str = generate_credentials_json(original)
        parsed = parse_oauth_credentials_json(json_str)

        assert parsed.access_token == original.access_token
        assert parsed.refresh_token == original.refresh_token
        assert parsed.expires_at == original.expires_at
        assert parsed.scopes == original.scopes


class TestAuthConfig:
    """Tests for AuthConfig dataclass."""

    def test_default_auth_type(self):
        """Default auth type should be API_KEY."""
        config = AuthConfig()
        assert config.auth_type == AuthType.API_KEY

    def test_api_key_config(self):
        """Should create API key auth config."""
        config = AuthConfig(
            auth_type=AuthType.API_KEY,
            api_key_secret_name="my-api-key"
        )
        assert config.auth_type == AuthType.API_KEY
        assert config.api_key_secret_name == "my-api-key"

    def test_oauth_config(self):
        """Should create OAuth auth config."""
        config = AuthConfig(
            auth_type=AuthType.OAUTH,
            oauth_credentials_secret_name="my-oauth-creds"
        )
        assert config.auth_type == AuthType.OAUTH
        assert config.oauth_credentials_secret_name == "my-oauth-creds"


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
        assert creds.api_key is None

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

        # Verify the JSON is valid
        parsed = json.loads(metadata["oauth-credentials"])
        assert parsed["claudeAiOauth"]["accessToken"] == "sk-ant-oat01-test"
