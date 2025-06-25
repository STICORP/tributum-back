"""Unit tests for ObservabilityConfig class."""

import pytest
from pydantic import ValidationError

from src.core.config import ObservabilityConfig


@pytest.mark.unit
class TestObservabilityConfig:
    """Test cases for ObservabilityConfig class."""

    def test_default_values(self) -> None:
        """Test default values for ObservabilityConfig."""
        config = ObservabilityConfig()
        assert config.enable_tracing is False
        assert config.service_name == "tributum"
        assert config.gcp_project_id is None
        assert config.trace_sample_rate == 1.0

    def test_custom_values(self) -> None:
        """Test custom values for ObservabilityConfig."""
        config = ObservabilityConfig(
            enable_tracing=True,
            service_name="test-service",
            gcp_project_id="test-project-123",
            trace_sample_rate=0.5,
        )
        assert config.enable_tracing is True
        assert config.service_name == "test-service"
        assert config.gcp_project_id == "test-project-123"
        assert config.trace_sample_rate == 0.5

    def test_trace_sample_rate_validation(self) -> None:
        """Test trace_sample_rate validation."""
        # Valid rates
        ObservabilityConfig(trace_sample_rate=0.0)
        ObservabilityConfig(trace_sample_rate=0.5)
        ObservabilityConfig(trace_sample_rate=1.0)

        # Invalid rates
        with pytest.raises(ValidationError, match="greater than or equal to 0"):
            ObservabilityConfig(trace_sample_rate=-0.1)

        with pytest.raises(ValidationError, match="less than or equal to 1"):
            ObservabilityConfig(trace_sample_rate=1.1)
