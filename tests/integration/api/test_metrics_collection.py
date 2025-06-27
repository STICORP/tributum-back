"""Integration tests for end-to-end metrics collection."""

import asyncio
import importlib
import sys

import pytest
from fastapi import FastAPI, HTTPException
from httpx import ASGITransport, AsyncClient
from pytest_mock import MockerFixture, MockType
from sqlalchemy import text

from src.api.middleware.error_handler import register_exception_handlers
from src.api.middleware.request_context import RequestContextMiddleware
from src.api.middleware.request_logging import RequestLoggingMiddleware
from src.api.middleware.security_headers import SecurityHeadersMiddleware
from src.api.utils.responses import ORJSONResponse
from src.core.config import get_settings
from src.core.exceptions import NotFoundError
from src.infrastructure.database.dependencies import DatabaseSession


@pytest.mark.integration
class TestMetricsCollection:
    """Integration tests for complete metrics collection flow."""

    @pytest.fixture
    def mock_metrics(self, mocker: MockerFixture) -> dict[str, MockType]:
        """Mock all metric instruments for testing."""
        # Mock metrics in the observability module
        mock_request_counter = mocker.Mock()
        mock_request_duration = mocker.Mock()
        mock_error_counter = mocker.Mock()
        mock_db_counter = mocker.Mock()
        mock_db_duration = mocker.Mock()

        # Set them in the observability module
        mocker.patch.object(
            __import__("src.core.observability", fromlist=["request_counter"]),
            "request_counter",
            mock_request_counter,
        )
        mocker.patch.object(
            __import__(
                "src.core.observability", fromlist=["request_duration_histogram"]
            ),
            "request_duration_histogram",
            mock_request_duration,
        )
        mocker.patch.object(
            __import__("src.core.observability", fromlist=["error_counter"]),
            "error_counter",
            mock_error_counter,
        )
        mocker.patch.object(
            __import__("src.core.observability", fromlist=["db_query_counter"]),
            "db_query_counter",
            mock_db_counter,
        )
        mocker.patch.object(
            __import__(
                "src.core.observability", fromlist=["db_query_duration_histogram"]
            ),
            "db_query_duration_histogram",
            mock_db_duration,
        )

        return {
            "request_counter": mock_request_counter,
            "request_duration": mock_request_duration,
            "error_counter": mock_error_counter,
            "db_counter": mock_db_counter,
            "db_duration": mock_db_duration,
        }

    @pytest.fixture
    def app_with_metrics(self) -> FastAPI:
        """Create a test app with all middleware configured."""
        # Force reload of middleware modules to pick up the mocked metrics
        if "src.api.middleware.request_logging" in sys.modules:
            importlib.reload(sys.modules["src.api.middleware.request_logging"])
        if "src.api.middleware.error_handler" in sys.modules:
            importlib.reload(sys.modules["src.api.middleware.error_handler"])

        # Re-import after reload

        # Get current settings and enable SQL logging for metrics
        settings = get_settings()
        settings.log_config.enable_sql_logging = True

        app = FastAPI(
            title="Test App",
            default_response_class=ORJSONResponse,
        )

        # Register exception handlers
        register_exception_handlers(app)

        # Add middleware in correct order
        app.add_middleware(
            RequestLoggingMiddleware,
            log_config=settings.log_config,
        )
        app.add_middleware(RequestContextMiddleware)
        app.add_middleware(SecurityHeadersMiddleware)

        # Add test endpoints
        @app.get("/health")
        async def health() -> dict[str, str]:
            return {"status": "ok"}

        @app.get("/database")
        async def database_endpoint(db: DatabaseSession) -> dict[str, int]:
            # Execute a simple query
            async with db as session:
                result = await session.execute(text("SELECT 1"))
                value = result.scalar()
            return {"result": int(value) if value is not None else 0}

        @app.get("/error")
        async def error_endpoint() -> None:
            raise HTTPException(status_code=404, detail="Not found")

        @app.get("/tributum-error")
        async def tributum_error_endpoint() -> None:
            raise NotFoundError("Resource not found", context={"id": 123})

        @app.get("/slow")
        async def slow_endpoint() -> dict[str, str]:
            await asyncio.sleep(0.01)  # 10ms delay
            return {"status": "slow"}

        # Mark endpoint functions as used by adding them to app
        _ = (
            health,
            database_endpoint,
            error_endpoint,
            tributum_error_endpoint,
            slow_endpoint,
        )

        return app

    async def test_metrics_with_no_instruments(
        self,
        app_with_metrics: FastAPI,
        mocker: MockerFixture,
    ) -> None:
        """Test that application works when metric instruments are None."""
        # Set all metrics to None
        mocker.patch("src.api.middleware.request_logging.request_counter", None)
        mocker.patch(
            "src.api.middleware.request_logging.request_duration_histogram", None
        )
        mocker.patch("src.api.middleware.error_handler.error_counter", None)
        mocker.patch("src.api.middleware.request_logging.db_query_counter", None)
        mocker.patch(
            "src.api.middleware.request_logging.db_query_duration_histogram", None
        )

        # Should still work without metrics
        async with AsyncClient(
            transport=ASGITransport(app=app_with_metrics),
            base_url="http://test",
        ) as client:
            response = await client.get("/health")
            assert response.status_code == 200

            error_response = await client.get("/error")
            assert error_response.status_code == 404
