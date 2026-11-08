import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi.testclient import TestClient
from api.main import app
from api.config import settings
from api.services.llm_provider import llm_provider

client = TestClient(app)


def test_health_check():
    """Verify /api/health is a simple fast liveness endpoint."""
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == settings.APP_NAME
    assert "version" in data
    assert "timestamp" in data


def test_system_status_minimal_and_non_leaking():
    """Verify /api/system/status returns only minimal service health without leaking internal details."""
    response = client.get("/api/system/status")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "operational"
    assert data["service"] == settings.APP_NAME
    assert data["environment"] == settings.APP_ENV
    assert data["version"] == "1.0.0"
    assert "timestamp" in data

    # STRICT: Verify no internal architecture, metrics, or credentials leaked
    assert "database" not in data
    assert "ai_orchestration" not in data
    assert "payment_gateway" not in data
    assert "counts" not in data
    assert "client_id" not in data
    assert "has_credentials" not in data
    assert "timeout_seconds" not in data
    assert "configured_model" not in data


def test_system_status_avoids_db_queries_and_external_calls():
    """Verify /api/system/status executes zero DB queries, zero PayPal OAuth requests, and zero AI inference."""
    with patch("api.database.engine.connect") as mock_db, \
         patch("api.services.paypal_service.paypal_service.get_access_token", new_callable=AsyncMock) as mock_paypal, \
         patch.object(llm_provider, "_call_gemini", new_callable=AsyncMock) as mock_gemini:

        response = client.get("/api/system/status")
        assert response.status_code == 200

        assert mock_db.call_count == 0
        assert mock_paypal.call_count == 0
        assert mock_gemini.call_count == 0


def test_test_ai_forbidden_in_production_for_get_and_post():
    """Verify public /api/system/test-ai is rejected with HTTP 403 on both GET and POST in production."""
    with patch.object(settings, "APP_ENV", "production"), \
         patch.object(settings, "ENABLE_LIVE_AI_DIAGNOSTICS", False), \
         patch.object(llm_provider, "_call_gemini", new_callable=AsyncMock) as mock_gemini:

        # Test GET
        res_get = client.get("/api/system/test-ai")
        assert res_get.status_code == 403
        assert "disabled" in res_get.json()["detail"].lower()
        assert mock_gemini.call_count == 0

        # Test POST
        res_post = client.post("/api/system/test-ai")
        assert res_post.status_code == 403
        assert "disabled" in res_post.json()["detail"].lower()
        assert mock_gemini.call_count == 0


def test_test_ai_forbidden_in_production_even_if_flag_enabled():
    """Verify live AI diagnostics cannot be forced on in production."""
    with patch.object(settings, "APP_ENV", "production"), \
         patch.object(settings, "ENABLE_LIVE_AI_DIAGNOSTICS", True), \
         patch.object(llm_provider, "_call_gemini", new_callable=AsyncMock) as mock_gemini:

        res = client.get("/api/system/test-ai")
        assert res.status_code == 403
        assert mock_gemini.call_count == 0


def test_test_ai_disabled_by_default_in_development():
    """Verify test-ai is disabled by default in development unless explicitly enabled."""
    with patch.object(settings, "APP_ENV", "development"), \
         patch.object(settings, "ENABLE_LIVE_AI_DIAGNOSTICS", False):

        res = client.get("/api/system/test-ai")
        assert res.status_code == 403


def test_test_ai_enabled_in_development_when_configured():
    """Verify test-ai works in development for both GET and POST when explicitly enabled."""
    mock_diag = {"status": "connected", "provider": "gemini", "model": "gemini-3.5-flash-lite"}
    with patch.object(settings, "APP_ENV", "development"), \
         patch.object(settings, "ENABLE_LIVE_AI_DIAGNOSTICS", True), \
         patch.object(llm_provider, "test_connection", new_callable=AsyncMock, return_value=mock_diag):

        res_get = client.get("/api/system/test-ai")
        assert res_get.status_code == 200
        assert res_get.json()["status"] == "connected"

        res_post = client.post("/api/system/test-ai")
        assert res_post.status_code == 200
        assert res_post.json()["status"] == "connected"


def test_production_environment_detection_fails_closed():
    """Verify is_production property fails closed for empty, missing, or ambiguous environments."""
    # 1. Explicit production
    with patch.object(settings, "APP_ENV", "production"):
        assert settings.is_production is True

    # 2. Empty / whitespace string fails closed
    with patch.object(settings, "APP_ENV", ""):
        assert settings.is_production is True
    with patch.object(settings, "APP_ENV", "   "):
        assert settings.is_production is True

    # 3. None fails closed
    with patch.object(settings, "APP_ENV", None):
        assert settings.is_production is True

    # 4. Unknown/ambiguous string (e.g. staging) fails closed
    with patch.object(settings, "APP_ENV", "staging"):
        assert settings.is_production is True
    with patch.object(settings, "APP_ENV", "preview"):
        assert settings.is_production is True

    # 5. Vercel production system env forces production
    with patch.dict("os.environ", {"VERCEL_ENV": "production"}), \
         patch.object(settings, "APP_ENV", "development"):
        assert settings.is_production is True

    # 6. Only explicit development or test without VERCEL_ENV=production is non-production
    with patch.dict("os.environ", {"VERCEL_ENV": ""}), \
         patch.object(settings, "APP_ENV", "development"):
        assert settings.is_production is False
    with patch.dict("os.environ", {"VERCEL_ENV": ""}), \
         patch.object(settings, "APP_ENV", "test"):
        assert settings.is_production is False


def test_test_ai_fails_closed_when_app_env_is_ambiguous_or_empty():
    """Verify test-ai returns HTTP 403 even if flag is set when environment is ambiguous or empty."""
    with patch.object(settings, "APP_ENV", ""), \
         patch.object(settings, "ENABLE_LIVE_AI_DIAGNOSTICS", True), \
         patch.object(llm_provider, "_call_gemini", new_callable=AsyncMock) as mock_gemini:

        res = client.get("/api/system/test-ai")
        assert res.status_code == 403
        assert mock_gemini.call_count == 0


def test_test_ai_fails_closed_when_vercel_env_is_production():
    """Verify test-ai returns HTTP 403 on Vercel production deployments even if dev flag is forced."""
    with patch.dict("os.environ", {"VERCEL_ENV": "production", "VERCEL": "1"}), \
         patch.object(settings, "APP_ENV", "development"), \
         patch.object(settings, "ENABLE_LIVE_AI_DIAGNOSTICS", True), \
         patch.object(llm_provider, "_call_gemini", new_callable=AsyncMock) as mock_gemini:

        res = client.get("/api/system/test-ai")
        assert res.status_code == 403
        assert mock_gemini.call_count == 0


def test_test_ai_fails_closed_on_vercel_preview():
    """Verify test-ai returns HTTP 403 on Vercel Preview deployments regardless of APP_ENV."""
    # 1. Vercel Preview with APP_ENV="development" and flag=True -> Must be 403
    with patch.dict("os.environ", {"VERCEL_ENV": "preview", "VERCEL": "1"}), \
         patch.object(settings, "APP_ENV", "development"), \
         patch.object(settings, "ENABLE_LIVE_AI_DIAGNOSTICS", True), \
         patch.object(llm_provider, "_call_gemini", new_callable=AsyncMock) as mock_gemini:

        res = client.get("/api/system/test-ai")
        assert res.status_code == 403
        res_post = client.post("/api/system/test-ai")
        assert res_post.status_code == 403
        assert mock_gemini.call_count == 0

    # 2. Vercel Preview with APP_ENV="production" and flag=True -> Must be 403
    with patch.dict("os.environ", {"VERCEL_ENV": "preview", "VERCEL": "1"}), \
         patch.object(settings, "APP_ENV", "production"), \
         patch.object(settings, "ENABLE_LIVE_AI_DIAGNOSTICS", True), \
         patch.object(llm_provider, "_call_gemini", new_callable=AsyncMock) as mock_gemini:

        res = client.get("/api/system/test-ai")
        assert res.status_code == 403
        assert mock_gemini.call_count == 0


@pytest.mark.parametrize("env_name,app_env,flag,expected_status", [
    ("Local", "development", False, 403),
    ("Local", "development", True, 200),
    ("Vercel Production", "production", True, 403),
    ("Vercel Production", "development", True, 403),
    ("Vercel Preview", "development", True, 403),
    ("Vercel Preview", "production", True, 403),
    ("Ambiguous hosted environment", "unknown", True, 403),
    ("Ambiguous hosted environment", "", True, 403),
])
def test_all_hosted_and_local_environment_lockout_combinations(env_name, app_env, flag, expected_status):
    """Parametrized test strictly verifying the exact 7-row hosted environment lockout matrix."""
    mock_env = {}
    if env_name == "Vercel Production":
        mock_env = {"VERCEL": "1", "VERCEL_ENV": "production"}
    elif env_name == "Vercel Preview":
        mock_env = {"VERCEL": "1", "VERCEL_ENV": "preview"}
    elif env_name == "Ambiguous hosted environment":
        mock_env = {"VERCEL": "1", "VERCEL_ENV": ""}
    else:
        # Local
        mock_env = {"VERCEL": "", "VERCEL_ENV": "", "AWS_LAMBDA_FUNCTION_NAME": ""}

    mock_diag = {"status": "connected", "provider": "gemini", "model": "gemini-3.5-flash-lite"}
    with patch.dict("os.environ", mock_env), \
         patch.object(settings, "APP_ENV", app_env), \
         patch.object(settings, "ENABLE_LIVE_AI_DIAGNOSTICS", flag), \
         patch.object(llm_provider, "test_connection", new_callable=AsyncMock, return_value=mock_diag), \
         patch.object(llm_provider, "_call_gemini", new_callable=AsyncMock) as mock_gemini:

        res_get = client.get("/api/system/test-ai")
        assert res_get.status_code == expected_status
        res_post = client.post("/api/system/test-ai")
        assert res_post.status_code == expected_status

        if expected_status == 403:
            assert mock_gemini.call_count == 0


def test_postgres_pool_configuration_hosted_vs_local():
    """Verify that hosted environments use NullPool without QueuePool-specific sizing,
    while local development preserves QueuePool with pool_size=5, max_overflow=10.
    """
    from sqlalchemy import create_engine
    from sqlalchemy.pool import NullPool, QueuePool
    from api.database import get_postgres_pool_kwargs

    # 1. Hosted environment (Vercel / Lambda)
    hosted_kwargs = get_postgres_pool_kwargs(is_hosted=True)
    assert hosted_kwargs["poolclass"] is NullPool
    assert hosted_kwargs.get("pool_recycle") == 300
    assert hosted_kwargs.get("pool_pre_ping") is True
    assert "pool_size" not in hosted_kwargs
    assert "max_overflow" not in hosted_kwargs
    assert "pool_timeout" not in hosted_kwargs

    hosted_engine = create_engine("postgresql+psycopg://user:pass@localhost:5432/db", **hosted_kwargs)
    assert isinstance(hosted_engine.pool, NullPool)
    assert not isinstance(hosted_engine.pool, QueuePool)
    assert hosted_engine.pool._recycle == 300
    assert hosted_engine.pool._pre_ping is True

    # 2. Local development / concurrency test environment
    local_kwargs = get_postgres_pool_kwargs(is_hosted=False)
    assert local_kwargs["poolclass"] is QueuePool
    assert local_kwargs["pool_size"] == 5
    assert local_kwargs["max_overflow"] == 10
    assert local_kwargs["pool_recycle"] == 300
    assert local_kwargs["pool_timeout"] == 15
    assert local_kwargs.get("pool_pre_ping") is True

    local_engine = create_engine("postgresql+psycopg://user:pass@localhost:5432/db", **local_kwargs)
    assert isinstance(local_engine.pool, QueuePool)
    assert local_engine.pool.size() == 5
    assert local_engine.pool._max_overflow == 10
    assert local_engine.pool._recycle == 300
    assert local_engine.pool._timeout == 15
    assert local_engine.pool._pre_ping is True


def test_settings_is_hosted_governs_postgres_pool_kwargs():
    """Verify that setting VERCEL=1 or VERCEL_ENV triggers NullPool hosted pool settings."""
    from sqlalchemy import create_engine
    from sqlalchemy.pool import NullPool, QueuePool
    from api.database import get_postgres_pool_kwargs

    # Test under Vercel hosted environment
    with patch.dict("os.environ", {"VERCEL": "1", "VERCEL_ENV": "production"}):
        assert settings.is_hosted is True
        pool_kwargs = get_postgres_pool_kwargs(settings.is_hosted)
        assert pool_kwargs["poolclass"] is NullPool
        assert "pool_size" not in pool_kwargs
        assert "max_overflow" not in pool_kwargs
        hosted_engine = create_engine("postgresql+psycopg://user:pass@localhost:5432/db", **pool_kwargs)
        assert isinstance(hosted_engine.pool, NullPool)

    # Test under local unhosted environment
    with patch.dict("os.environ", {"VERCEL": "", "VERCEL_ENV": "", "AWS_LAMBDA_FUNCTION_NAME": ""}):
        assert settings.is_hosted is False
        pool_kwargs = get_postgres_pool_kwargs(settings.is_hosted)
        assert pool_kwargs["poolclass"] is QueuePool
        assert pool_kwargs["pool_size"] == 5
        assert pool_kwargs["max_overflow"] == 10
        local_engine = create_engine("postgresql+psycopg://user:pass@localhost:5432/db", **pool_kwargs)
        assert isinstance(local_engine.pool, QueuePool)
        assert local_engine.pool.size() == 5
