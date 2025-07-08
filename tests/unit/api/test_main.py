"""Unit tests for src/api/main.py.

This module contains comprehensive unit tests for the FastAPI application
initialization, lifecycle management, middleware registration, and route handlers.
All tests follow the best practices outlined in the project guidelines.
"""

import asyncio
import importlib
import sys
import types

import pytest
from fastapi import FastAPI
from pytest_mock import MockerFixture, MockType

from src.core.config import Settings


def get_main_module() -> types.ModuleType:
    """Get the main module after ensuring mocks are in place."""
    return importlib.import_module("src.api.main")


@pytest.mark.unit
class TestLifespan:
    """Test the lifespan context manager for application startup and shutdown."""

    @pytest.mark.timeout(1)
    @pytest.mark.asyncio
    async def test_lifespan_startup_success(
        self,
        mocker: MockerFixture,
        mock_settings: Settings,
    ) -> None:
        """Test successful application startup when database is healthy."""
        # Configure mocks for this specific test
        mocker.patch(
            "src.api.main.check_database_connection",
            new_callable=mocker.AsyncMock,
            return_value=(True, None),
        )
        mock_close_db = mocker.patch(
            "src.api.main.close_database",
            new_callable=mocker.AsyncMock,
        )
        mock_logger = mocker.patch("src.api.main.logger")

        # Get lifespan function
        main = get_main_module()
        lifespan = main.lifespan

        # Mock FastAPI app instance
        mock_app = mocker.Mock()
        mock_app.title = mock_settings.app_name
        mock_app.version = mock_settings.app_version

        # Execute lifespan context
        async with lifespan(mock_app):
            # Verify startup behavior
            mock_logger.info.assert_any_call("Database connection successful")
            mock_logger.info.assert_any_call(
                "Application startup complete - {} v{}",
                mock_settings.app_name,
                mock_settings.app_version,
            )

        # Verify shutdown behavior
        mock_close_db.assert_called_once()
        mock_logger.info.assert_any_call("Application shutdown initiated")
        mock_logger.info.assert_any_call("Application shutdown complete")

    @pytest.mark.timeout(1)
    @pytest.mark.asyncio
    async def test_lifespan_startup_failure(
        self,
        mocker: MockerFixture,
    ) -> None:
        """Test application fails to start when database is unhealthy."""
        # Configure mocks
        mocker.patch(
            "src.api.main.check_database_connection",
            new_callable=mocker.AsyncMock,
            return_value=(False, "Connection timeout"),
        )
        mock_close_db = mocker.patch(
            "src.api.main.close_database",
            new_callable=mocker.AsyncMock,
        )
        mock_logger = mocker.patch("src.api.main.logger")

        # Get lifespan function
        main = get_main_module()
        lifespan = main.lifespan

        # Mock FastAPI app
        mock_app = mocker.Mock()

        # Test that startup raises RuntimeError
        with pytest.raises(
            RuntimeError, match="Database connection failed: Connection timeout"
        ):
            async with lifespan(mock_app):
                pass

        # Verify error was logged
        mock_logger.error.assert_called_once_with(
            "Database connection failed during startup: {}",
            "Connection timeout",
        )

        # Verify close_database was NOT called since startup failed
        mock_close_db.assert_not_called()

    @pytest.mark.timeout(1)
    @pytest.mark.asyncio
    async def test_lifespan_shutdown(
        self,
        mocker: MockerFixture,
        mock_settings: Settings,
    ) -> None:
        """Test clean shutdown process."""
        # Configure mocks
        mocker.patch(
            "src.api.main.check_database_connection",
            new_callable=mocker.AsyncMock,
            return_value=(True, None),
        )
        mock_close_db = mocker.patch(
            "src.api.main.close_database",
            new_callable=mocker.AsyncMock,
        )
        mock_logger = mocker.patch("src.api.main.logger")

        # Get lifespan function
        main = get_main_module()
        lifespan = main.lifespan

        # Mock FastAPI app
        mock_app = mocker.Mock()
        mock_app.title = mock_settings.app_name
        mock_app.version = mock_settings.app_version

        # Execute full lifespan
        async with lifespan(mock_app):
            pass

        # Verify clean shutdown
        mock_close_db.assert_called_once()
        mock_logger.info.assert_any_call("Application shutdown initiated")
        mock_logger.info.assert_any_call("Application shutdown complete")


@pytest.mark.unit
class TestCreateApp:
    """Test the create_app factory function."""

    @pytest.mark.timeout(1)
    def test_create_app_with_default_settings(
        self,
        mocker: MockerFixture,
        mock_settings: Settings,
    ) -> None:
        """Test app creation with default settings."""
        # Configure mocks
        mocker.patch("src.api.main.get_settings", return_value=mock_settings)
        mock_setup_logging = mocker.patch("src.api.main.setup_logging")
        mock_setup_tracing = mocker.patch("src.api.main.setup_tracing")
        mock_register_exception_handlers = mocker.patch(
            "src.api.main.register_exception_handlers"
        )
        mock_instrument_app = mocker.patch("src.api.main.instrument_app")

        # Mock FastAPI
        mock_app = mocker.Mock(spec=FastAPI)
        mock_fastapi = mocker.patch("src.api.main.FastAPI", return_value=mock_app)

        # Get create_app function
        main = get_main_module()
        create_app = main.create_app

        app = create_app()

        # Verify app is created correctly
        assert app == mock_app

        # Verify setup functions were called
        mock_setup_logging.assert_called_once_with(mock_settings)
        mock_setup_tracing.assert_called_once_with(mock_settings)

        # Verify FastAPI was initialized with correct parameters
        mock_fastapi.assert_called_once()
        call_kwargs = mock_fastapi.call_args.kwargs
        assert call_kwargs["title"] == mock_settings.app_name
        assert call_kwargs["version"] == mock_settings.app_version
        assert call_kwargs["debug"] == mock_settings.debug
        assert call_kwargs["docs_url"] == mock_settings.docs_url
        assert call_kwargs["redoc_url"] == mock_settings.redoc_url
        assert call_kwargs["openapi_url"] == mock_settings.openapi_url
        assert "lifespan" in call_kwargs

        # Verify exception handlers registered before middleware
        mock_register_exception_handlers.assert_called_once_with(mock_app)

        # Verify middleware added in correct order
        assert mock_app.add_middleware.call_count == 3

        # Verify instrumentation
        mock_instrument_app.assert_called_once_with(mock_app, mock_settings)

    @pytest.mark.timeout(1)
    def test_create_app_with_provided_settings(
        self,
        mocker: MockerFixture,
        mock_settings: Settings,
    ) -> None:
        """Test app creation with provided settings."""
        # Configure mocks
        mock_setup_logging = mocker.patch("src.api.main.setup_logging")
        mock_setup_tracing = mocker.patch("src.api.main.setup_tracing")
        mocker.patch("src.api.main.register_exception_handlers")
        mocker.patch("src.api.main.instrument_app")

        # Mock FastAPI
        mock_app = mocker.Mock(spec=FastAPI)
        mock_fastapi = mocker.patch("src.api.main.FastAPI", return_value=mock_app)

        # Get create_app function
        main = get_main_module()
        create_app = main.create_app

        # Create custom settings by modifying a copy
        custom_settings = mock_settings.model_copy(
            update={
                "app_name": "CustomApp",
                "app_version": "2.0.0",
                "environment": "production",
            }
        )

        app = create_app(custom_settings)

        # Verify app is created correctly
        assert app == mock_app

        # Verify setup functions were called with custom settings
        mock_setup_logging.assert_called_once_with(custom_settings)
        mock_setup_tracing.assert_called_once_with(custom_settings)

        # Verify FastAPI was initialized with custom settings
        call_kwargs = mock_fastapi.call_args.kwargs
        assert call_kwargs["title"] == "CustomApp"
        assert call_kwargs["version"] == "2.0.0"

    @pytest.mark.timeout(1)
    def test_create_app_middleware_order(
        self,
        mocker: MockerFixture,
        mock_settings: Settings,
    ) -> None:
        """Test middleware are registered in correct order."""
        # Configure mocks
        mocker.patch("src.api.main.get_settings", return_value=mock_settings)
        mock_req_logging = mocker.patch("src.api.main.RequestLoggingMiddleware")
        mock_req_context = mocker.patch("src.api.main.RequestContextMiddleware")
        mock_security = mocker.patch("src.api.main.SecurityHeadersMiddleware")

        # Mock FastAPI
        mock_app = mocker.Mock(spec=FastAPI)
        mocker.patch("src.api.main.FastAPI", return_value=mock_app)

        # Get create_app function
        main = get_main_module()
        create_app = main.create_app

        create_app()

        # Verify middleware added in correct order
        calls = mock_app.add_middleware.call_args_list
        assert len(calls) == 3

        # Order of middleware registration (reverse execution order)
        assert calls[0][0][0] == mock_req_logging
        assert calls[1][0][0] == mock_req_context
        assert calls[2][0][0] == mock_security

    @pytest.mark.timeout(1)
    def test_create_app_exception_handlers_before_middleware(
        self,
        mocker: MockerFixture,
        mock_settings: Settings,
    ) -> None:
        """Test exception handlers are registered before middleware."""
        # Configure mocks
        mocker.patch("src.api.main.get_settings", return_value=mock_settings)

        # Track call order
        call_order: list[str] = []

        def track_exception_handlers(_app: object) -> None:
            call_order.append("exception_handlers")

        def track_middleware(*_args: object, **_kwargs: object) -> None:
            call_order.append("middleware")

        mocker.patch(
            "src.api.main.register_exception_handlers",
            side_effect=track_exception_handlers,
        )

        # Mock FastAPI
        mock_app = mocker.Mock(spec=FastAPI)
        mock_app.add_middleware.side_effect = track_middleware
        mocker.patch("src.api.main.FastAPI", return_value=mock_app)

        # Get create_app function
        main = get_main_module()
        create_app = main.create_app

        create_app()

        # Verify exception handlers registered before middleware
        assert call_order[0] == "exception_handlers"
        assert all(item == "middleware" for item in call_order[1:])

    @pytest.mark.timeout(1)
    def test_create_app_fastapi_initialization(
        self,
        mocker: MockerFixture,
        mock_settings: Settings,
    ) -> None:
        """Test FastAPI is initialized with correct parameters."""
        # Configure mocks
        mocker.patch("src.api.main.get_settings", return_value=mock_settings)
        mock_response_class = mocker.patch("src.api.main.ORJSONResponse")

        # Mock FastAPI
        mock_app = mocker.Mock(spec=FastAPI)
        mock_fastapi = mocker.patch("src.api.main.FastAPI", return_value=mock_app)

        # Get create_app function
        main = get_main_module()
        create_app = main.create_app

        create_app()

        # Verify FastAPI initialization
        mock_fastapi.assert_called_once()
        call_kwargs = mock_fastapi.call_args.kwargs

        assert call_kwargs["title"] == mock_settings.app_name
        assert call_kwargs["version"] == mock_settings.app_version
        assert call_kwargs["debug"] == mock_settings.debug
        assert call_kwargs["docs_url"] == mock_settings.docs_url
        assert call_kwargs["redoc_url"] == mock_settings.redoc_url
        assert call_kwargs["openapi_url"] == mock_settings.openapi_url
        assert call_kwargs["default_response_class"] == mock_response_class
        assert "lifespan" in call_kwargs

    @pytest.mark.timeout(1)
    def test_create_app_routes_registered(
        self,
        mocker: MockerFixture,
        mock_settings: Settings,
        mock_app_with_route_capture: MockType,
    ) -> None:
        """Test routes are properly registered."""
        # Configure mocks
        mocker.patch("src.api.main.get_settings", return_value=mock_settings)
        mocker.patch("src.api.main.FastAPI", return_value=mock_app_with_route_capture)

        # Get create_app function
        main = get_main_module()
        create_app = main.create_app

        create_app()

        # Verify routes were registered
        captured_routes = mock_app_with_route_capture._captured_routes
        assert "/" in captured_routes
        assert "/health" in captured_routes
        assert "/info" in captured_routes


@pytest.mark.unit
class TestRoutes:
    """Test the application route handlers."""

    @pytest.mark.timeout(1)
    @pytest.mark.asyncio
    async def test_root_endpoint(
        self,
        mocker: MockerFixture,
        mock_settings: Settings,
        mock_app_with_route_capture: MockType,
    ) -> None:
        """Test root endpoint returns correct response."""
        # Configure mocks
        mocker.patch("src.api.main.get_settings", return_value=mock_settings)
        mocker.patch("src.api.main.FastAPI", return_value=mock_app_with_route_capture)

        # Get create_app function
        main = get_main_module()
        create_app = main.create_app

        create_app()

        # Get and call the root handler
        root_handler = mock_app_with_route_capture._captured_routes["/"]
        result = await root_handler()

        assert result == {"message": "Hello from Tributum!"}

    @pytest.mark.timeout(1)
    @pytest.mark.asyncio
    async def test_health_endpoint_database_healthy(
        self,
        mocker: MockerFixture,
        mock_settings: Settings,
        mock_app_with_route_capture: MockType,
    ) -> None:
        """Test health endpoint when database is healthy."""
        # Configure mocks
        mocker.patch(
            "src.api.main.check_database_connection",
            new_callable=mocker.AsyncMock,
            return_value=(True, None),
        )
        mocker.patch("src.api.main.get_settings", return_value=mock_settings)
        mocker.patch("src.api.main.FastAPI", return_value=mock_app_with_route_capture)

        # Get create_app function
        main = get_main_module()
        create_app = main.create_app

        create_app()

        # Get and call the health handler
        health_handler = mock_app_with_route_capture._captured_routes["/health"]
        result = await health_handler()

        assert result == {"status": "healthy", "database": True}

    @pytest.mark.timeout(1)
    @pytest.mark.asyncio
    async def test_health_endpoint_database_unhealthy(
        self,
        mocker: MockerFixture,
        mock_settings: Settings,
        mock_app_with_route_capture: MockType,
    ) -> None:
        """Test health endpoint when database is unhealthy."""
        # Configure mocks
        mocker.patch(
            "src.api.main.check_database_connection",
            new_callable=mocker.AsyncMock,
            return_value=(False, "Connection failed"),
        )
        mock_logger = mocker.patch("src.api.main.logger")
        mocker.patch("src.api.main.get_settings", return_value=mock_settings)
        mocker.patch("src.api.main.FastAPI", return_value=mock_app_with_route_capture)

        # Get create_app function
        main = get_main_module()
        create_app = main.create_app

        create_app()

        # Get and call the health handler
        health_handler = mock_app_with_route_capture._captured_routes["/health"]
        result = await health_handler()

        assert result == {"status": "degraded", "database": False}

        # Verify logging
        mock_logger.warning.assert_called_once_with(
            "Database health check failed: {}",
            "Connection failed",
        )

    @pytest.mark.timeout(1)
    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        ("db_healthy", "error_msg", "expected_status"),
        [
            (True, None, "healthy"),
            (False, "Timeout", "degraded"),
            (False, "Access denied", "degraded"),
            (False, "", "degraded"),
        ],
    )
    async def test_health_endpoint_parametrized(
        self,
        mocker: MockerFixture,
        mock_settings: Settings,
        mock_app_with_route_capture: MockType,
        db_healthy: bool,
        error_msg: str | None,
        expected_status: str,
    ) -> None:
        """Test various database states."""
        # Configure mocks
        mocker.patch(
            "src.api.main.check_database_connection",
            new_callable=mocker.AsyncMock,
            return_value=(db_healthy, error_msg),
        )
        if not db_healthy:
            mocker.patch("src.api.main.logger")

        mocker.patch("src.api.main.get_settings", return_value=mock_settings)
        mocker.patch("src.api.main.FastAPI", return_value=mock_app_with_route_capture)

        # Get create_app function
        main = get_main_module()
        create_app = main.create_app

        create_app()

        # Get and call the health handler
        health_handler = mock_app_with_route_capture._captured_routes["/health"]
        result = await health_handler()

        assert result["status"] == expected_status
        assert result["database"] == db_healthy

    @pytest.mark.timeout(1)
    @pytest.mark.asyncio
    async def test_info_endpoint(
        self,
        mocker: MockerFixture,
        mock_settings: Settings,
        mock_app_with_route_capture: MockType,
    ) -> None:
        """Test info endpoint returns application information."""
        # Configure mocks
        mocker.patch("src.api.main.get_settings", return_value=mock_settings)
        mocker.patch("src.api.main.FastAPI", return_value=mock_app_with_route_capture)

        # Get create_app function
        main = get_main_module()
        create_app = main.create_app

        create_app()

        # Get the info handler
        info_handler = mock_app_with_route_capture._captured_routes["/info"]

        # Call handler with mock settings dependency
        result = await info_handler(app_settings=mock_settings)

        assert result == {
            "app_name": mock_settings.app_name,
            "version": mock_settings.app_version,
            "environment": mock_settings.environment,
            "debug": mock_settings.debug,
        }


@pytest.mark.unit
class TestModuleLevel:
    """Test module-level app instance creation."""

    @pytest.mark.timeout(1)
    def test_module_app_creation(
        self,
        mocker: MockerFixture,
        mock_settings: Settings,
    ) -> None:
        """Test module-level app instance is created."""
        # Configure all mocks before importing
        mocker.patch("src.core.config.get_settings", return_value=mock_settings)
        mocker.patch("src.core.logging.setup_logging")
        mocker.patch("src.core.observability.setup_tracing")
        mocker.patch("src.api.middleware.error_handler.register_exception_handlers")
        mocker.patch("src.core.observability.instrument_app")
        mocker.patch("src.api.middleware.security_headers.SecurityHeadersMiddleware")
        mocker.patch("src.api.middleware.request_context.RequestContextMiddleware")
        mocker.patch("src.api.middleware.request_logging.RequestLoggingMiddleware")

        # Mock FastAPI
        mock_app = mocker.Mock(spec=FastAPI)
        mocker.patch("fastapi.FastAPI", return_value=mock_app)

        # Clear and import the module
        if "src.api.main" in sys.modules:
            del sys.modules["src.api.main"]

        main_module = importlib.import_module("src.api.main")

        # Verify app was created
        assert hasattr(main_module, "app")
        assert main_module.app == mock_app


@pytest.mark.unit
class TestEdgeCases:
    """Test edge cases and error conditions."""

    @pytest.mark.timeout(1)
    @pytest.mark.asyncio
    async def test_lifespan_unexpected_database_response(
        self,
        mocker: MockerFixture,
    ) -> None:
        """Test lifespan handles unexpected database response gracefully."""
        # Configure mocks
        mocker.patch(
            "src.api.main.check_database_connection",
            new_callable=mocker.AsyncMock,
            return_value="invalid_response",  # Non-tuple response
        )
        mocker.patch("src.api.main.logger")

        # Get lifespan function
        main = get_main_module()
        lifespan = main.lifespan

        # Mock app
        mock_app = mocker.Mock()

        # Test that it raises an error
        with pytest.raises(ValueError, match="too many values to unpack"):
            async with lifespan(mock_app):
                pass

    @pytest.mark.timeout(1)
    @pytest.mark.asyncio
    async def test_lifespan_logger_exception(
        self,
        mocker: MockerFixture,
    ) -> None:
        """Test lifespan fails if logger raises exception."""
        # Configure mocks
        mocker.patch(
            "src.api.main.check_database_connection",
            new_callable=mocker.AsyncMock,
            return_value=(True, None),
        )
        mocker.patch(
            "src.api.main.close_database",
            new_callable=mocker.AsyncMock,
        )

        # Mock logger to raise exception
        mock_logger = mocker.patch("src.api.main.logger")
        mock_logger.info.side_effect = Exception("Logger error")

        # Get lifespan function
        main = get_main_module()
        lifespan = main.lifespan

        # Mock app
        mock_app = mocker.Mock()
        mock_app.title = "Test"
        mock_app.version = "1.0"

        # Test that lifespan raises the logger error
        with pytest.raises(Exception, match="Logger error"):
            async with lifespan(mock_app):
                pass

    @pytest.mark.timeout(1)
    def test_create_app_with_none_optional_fields(
        self,
        mocker: MockerFixture,
        mock_settings: Settings,
    ) -> None:
        """Test create_app handles None values in optional settings fields."""
        # Create settings with None values
        settings_with_none = mock_settings.model_copy(
            update={
                "app_name": "TestApp",
                "app_version": "1.0.0",
                "docs_url": None,
                "redoc_url": None,
                "openapi_url": None,
            }
        )

        # Mock FastAPI
        mock_app = mocker.Mock(spec=FastAPI)
        mock_fastapi = mocker.patch("src.api.main.FastAPI", return_value=mock_app)

        # Get create_app function
        main = get_main_module()
        create_app = main.create_app

        app = create_app(settings_with_none)

        # Verify app created successfully with None values
        assert app == mock_app
        call_kwargs = mock_fastapi.call_args.kwargs
        assert call_kwargs["docs_url"] is None
        assert call_kwargs["redoc_url"] is None
        assert call_kwargs["openapi_url"] is None

    @pytest.mark.timeout(1)
    def test_create_app_middleware_initialization_error(
        self,
        mocker: MockerFixture,
        mock_settings: Settings,
    ) -> None:
        """Test create_app handles middleware initialization errors."""
        # Configure mocks
        mocker.patch("src.api.main.get_settings", return_value=mock_settings)

        # Mock FastAPI to raise error on middleware
        mock_app = mocker.Mock(spec=FastAPI)
        mock_app.add_middleware.side_effect = Exception("Middleware init error")
        mocker.patch("src.api.main.FastAPI", return_value=mock_app)

        # Get create_app function
        main = get_main_module()
        create_app = main.create_app

        with pytest.raises(Exception, match="Middleware init error"):
            create_app()

    @pytest.mark.timeout(1)
    @pytest.mark.asyncio
    async def test_health_concurrent_calls(
        self,
        mocker: MockerFixture,
        mock_settings: Settings,
        mock_app_with_route_capture: MockType,
    ) -> None:
        """Test health endpoint handles concurrent calls correctly."""
        # Configure mocks
        mocker.patch(
            "src.api.main.check_database_connection",
            new_callable=mocker.AsyncMock,
            return_value=(True, None),
        )
        mocker.patch("src.api.main.get_settings", return_value=mock_settings)
        mocker.patch("src.api.main.FastAPI", return_value=mock_app_with_route_capture)

        # Get create_app function
        main = get_main_module()
        create_app = main.create_app

        create_app()

        # Get the health handler
        health_handler = mock_app_with_route_capture._captured_routes["/health"]

        # Call health endpoint concurrently
        results = await asyncio.gather(
            health_handler(),
            health_handler(),
            health_handler(),
        )

        # All calls should return same result
        expected = {"status": "healthy", "database": True}
        assert all(result == expected for result in results)
