"""Test orjson import error handling.

This test is in a separate file because it needs to test the import-time
behavior of the logging module when orjson is not available.
"""

import subprocess
import sys
import textwrap


def test_orjson_import_error() -> None:
    """Test that logging module handles orjson ImportError correctly."""
    # Create a test script that will run in a subprocess
    test_script = textwrap.dedent("""
    import sys
    import os

    # Add the project root to Python path
    # Since we're running with -c, we need to use the current directory
    project_root = os.getcwd()
    sys.path.insert(0, project_root)

    # Block orjson from being imported
    import builtins
    real_import = builtins.__import__

    def mock_import(name, *args, **kwargs):
        if name == 'orjson':
            raise ImportError('No module named orjson')
        return real_import(name, *args, **kwargs)

    builtins.__import__ = mock_import

    # Now import the logging module - this will trigger the except block
    import src.core.logging

    # Verify the fallback behavior
    assert src.core.logging.ORJSON_AVAILABLE is False
    assert src.core.logging.ORJSONRenderer is None

    print("SUCCESS: Import error handling works correctly")
    """)

    # Run the test in a subprocess to get a clean import environment
    import os

    project_root = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "..", "..")
    )
    result = subprocess.run(
        [sys.executable, "-c", test_script],
        capture_output=True,
        text=True,
        cwd=project_root,  # Use the project root as working directory
    )

    # Check the result
    assert result.returncode == 0, f"Test failed: {result.stderr}"
    assert "SUCCESS" in result.stdout, f"Test output unexpected: {result.stdout}"


if __name__ == "__main__":
    test_orjson_import_error()
    print("✓ test_orjson_import_error passed")
