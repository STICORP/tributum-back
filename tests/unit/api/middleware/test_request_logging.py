"""Tests for simplified request logging middleware."""

import asyncio
from collections.abc import Iterator
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from loguru import logger

from src.api.middleware.request_context import RequestContextMiddleware
from src.api.middleware.request_logging import RequestLoggingMiddleware
from src.core.config import LogConfig
from src.core.context import RequestContext


# Simple test data collector that avoids type checking issues
class LogCollector:
    """Collects log records for testing."""

    def __init__(self) -> None:
        """Initialize the collector."""
        self.logs: list[dict[str, Any]] = []

    def __call__(self, message: object) -> None:
        """Called by loguru to write log messages."""
        # We know message has a record attribute from loguru's API
        # but typing it precisely is complex, so we use object and
        # access it dynamically
        record = getattr(message, "record", {})
        self.logs.append(record)


@pytest.fixture
def capture_logs() -> Iterator[list[dict[str, Any]]]:
    """Fixture to capture Loguru logs."""
    collector = LogCollector()

    handler_id = logger.add(collector, level="DEBUG")
    yield collector.logs
    logger.remove(handler_id)


@pytest.fixture
def test_app() -> FastAPI:
    """Create test FastAPI app with middleware."""
    app = FastAPI()

    # Add test endpoint
    @app.get("/test")
    async def test_endpoint() -> dict[str, str]:
        # Log something to verify context
        logger.info("Inside endpoint")
        return {"status": "ok"}

    @app.get("/slow")
    async def slow_endpoint() -> dict[str, str]:
        await asyncio.sleep(0.1)
        return {"status": "slow"}

    @app.get("/error")
    async def error_endpoint() -> dict[str, str]:
        raise ValueError("Test error")

    # Add middleware in correct order
    log_config = LogConfig(
        excluded_paths=["/health"],
        slow_request_threshold_ms=50,
    )
    app.add_middleware(RequestLoggingMiddleware, log_config=log_config)
    app.add_middleware(RequestContextMiddleware)

    return app


class TestRequestLoggingMiddleware:
    """Test request logging middleware."""

    def test_basic_request_logging(
        self, test_app: FastAPI, capture_logs: list[dict[str, Any]]
    ) -> None:
        """Test basic request is logged."""
        client = TestClient(test_app)

        response = client.get("/test")

        assert response.status_code == 200

        # Check logs
        log_messages = [log["message"] for log in capture_logs]
        assert "Request started" in log_messages
        assert "Request completed" in log_messages
        assert "Inside endpoint" in log_messages

        # Check context propagation
        for log in capture_logs:
            if log["message"] in [
                "Request started",
                "Request completed",
                "Inside endpoint",
            ]:
                assert "correlation_id" in log["extra"]
                assert "request_id" in log["extra"]
                assert "method" in log["extra"]
                assert log["extra"]["method"] == "GET"
                assert log["extra"]["path"] == "/test"

    def test_excluded_paths(
        self, test_app: FastAPI, capture_logs: list[dict[str, Any]]
    ) -> None:
        """Test excluded paths are not logged."""

        # Add health endpoint
        @test_app.get("/health")
        async def health() -> dict[str, str]:
            return {"status": "ok"}

        client = TestClient(test_app)
        response = client.get("/health")

        assert response.status_code == 200

        # Should not have request logs
        log_messages = [log["message"] for log in capture_logs]
        assert "Request started" not in log_messages
        assert "Request completed" not in log_messages

    def test_correlation_id_propagation(
        self, test_app: FastAPI, capture_logs: list[dict[str, Any]]
    ) -> None:
        """Test correlation ID propagates correctly."""
        client = TestClient(test_app)

        # Send request with correlation ID
        headers = {"X-Correlation-ID": "test-correlation-123"}
        response = client.get("/test", headers=headers)

        assert response.status_code == 200
        assert response.headers["X-Correlation-ID"] == "test-correlation-123"

        # All logs should have the same correlation ID
        for log in capture_logs:
            if "correlation_id" in log["extra"]:
                assert log["extra"]["correlation_id"] == "test-correlation-123"

    def test_request_id_generation(
        self, test_app: FastAPI, capture_logs: list[dict[str, Any]]
    ) -> None:
        """Test request ID is generated and returned."""
        client = TestClient(test_app)

        response = client.get("/test")

        assert response.status_code == 200
        assert "X-Request-ID" in response.headers

        request_id = response.headers["X-Request-ID"]

        # Check logs have request ID
        for log in capture_logs:
            if log["message"] in ["Request started", "Request completed"]:
                assert log["extra"]["request_id"] == request_id

    def test_slow_request_warning(
        self, test_app: FastAPI, capture_logs: list[dict[str, Any]]
    ) -> None:
        """Test slow requests generate warnings."""
        client = TestClient(test_app)

        response = client.get("/slow")

        assert response.status_code == 200

        # Check for slow request warning
        warning_logs = [
            log for log in capture_logs if log["message"] == "Slow request detected"
        ]
        assert len(warning_logs) == 1
        assert warning_logs[0]["level"].name == "WARNING"
        assert warning_logs[0]["extra"]["duration_ms"] > 50

    def test_error_logging(
        self, test_app: FastAPI, capture_logs: list[dict[str, Any]]
    ) -> None:
        """Test errors are logged correctly."""
        client = TestClient(test_app, raise_server_exceptions=False)

        response = client.get("/error")

        assert response.status_code == 500

        # Check error was logged
        error_logs = [log for log in capture_logs if log["message"] == "Request failed"]
        assert len(error_logs) == 1
        assert error_logs[0]["level"].name == "ERROR"
        assert error_logs[0]["extra"]["error_type"] == "ValueError"
        assert error_logs[0]["extra"]["error_message"] == "Test error"

    def test_performance_metrics(
        self, test_app: FastAPI, capture_logs: list[dict[str, Any]]
    ) -> None:
        """Test performance metrics are tracked."""
        client = TestClient(test_app)

        response = client.get("/test")

        assert response.status_code == 200

        # Find completion log
        completion_logs = [
            log for log in capture_logs if log["message"] == "Request completed"
        ]
        assert len(completion_logs) == 1

        # Check duration is tracked
        assert "duration_ms" in completion_logs[0]["extra"]
        assert completion_logs[0]["extra"]["duration_ms"] > 0
        assert completion_logs[0]["extra"]["status_code"] == 200


class TestContextPropagation:
    """Test context propagation through async calls."""

    @pytest.mark.asyncio
    async def test_async_context_propagation(self) -> None:
        """Test correlation ID propagates through async operations."""
        correlation_id = "async-test-123"

        async def nested_operation() -> None:
            logger.info("Nested operation")
            # Context should be available here
            assert RequestContext.get_correlation_id() == correlation_id

        # Set context
        RequestContext.set_correlation_id(correlation_id)

        # Use contextualize for proper async propagation
        with logger.contextualize(correlation_id=correlation_id):
            logger.info("Main operation")
            await nested_operation()

            # Verify context still set
            assert RequestContext.get_correlation_id() == correlation_id
