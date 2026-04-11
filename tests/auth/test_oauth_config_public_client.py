import pytest

from auth.oauth_config import OAuthConfig


def test_oauth_config_public_client_oauth21_requires_jwt_signing_key(monkeypatch):
    monkeypatch.setenv("MCP_ENABLE_OAUTH21", "true")
    monkeypatch.setenv("GOOGLE_OAUTH_CLIENT_ID", "public-client-id")
    monkeypatch.delenv("GOOGLE_OAUTH_CLIENT_SECRET", raising=False)
    monkeypatch.delenv("FASTMCP_SERVER_AUTH_GOOGLE_JWT_SIGNING_KEY", raising=False)

    with pytest.raises(
        ValueError,
        match="Public client OAuth 2.1 mode requires FASTMCP_SERVER_AUTH_GOOGLE_JWT_SIGNING_KEY",
    ):
        OAuthConfig()


def test_oauth_config_public_client_oauth21_with_jwt_signing_key_is_configured(
    monkeypatch,
):
    monkeypatch.setenv("MCP_ENABLE_OAUTH21", "true")
    monkeypatch.setenv("GOOGLE_OAUTH_CLIENT_ID", "public-client-id")
    monkeypatch.delenv("GOOGLE_OAUTH_CLIENT_SECRET", raising=False)
    monkeypatch.setenv(
        "FASTMCP_SERVER_AUTH_GOOGLE_JWT_SIGNING_KEY",
        "this-is-a-long-enough-jwt-signing-key",
    )

    cfg = OAuthConfig()
    assert cfg.is_public_client() is True
    assert cfg.is_configured() is True
