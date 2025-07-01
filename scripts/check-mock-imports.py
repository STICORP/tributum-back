#!/usr/bin/env python3
"""Check for forbidden unittest.mock imports in test files.

This script enforces the use of pytest-mock instead of unittest.mock
in all test files. It can be run independently or as part of CI/pre-commit.
"""

import argparse
import pathlib
import sys
from typing import NoReturn

# Constants
DOCSTRING_PAIRS = 2  # Number of delimiter occurrences to close a single-line docstring
MAX_ERRORS_TO_SHOW = 20  # Maximum number of errors to display in detail


def get_test_files(root_path: pathlib.Path) -> list[pathlib.Path]:
    """Get all Python test files to check for mock imports."""
    test_files: list[pathlib.Path] = []
    for test_dir in ["tests/unit", "tests/integration", "tests/fixtures"]:
        test_path = root_path / test_dir
        if test_path.exists():
            test_files.extend(test_path.rglob("*.py"))

    # Also check conftest.py files in test directories
    conftest_files = list(root_path.rglob("conftest.py"))
    test_files.extend([f for f in conftest_files if "tests" in str(f)])
    return test_files


def check_file_for_mock_imports(
    test_file: pathlib.Path, root_path: pathlib.Path
) -> list[str]:
    """Check a single file for forbidden unittest.mock imports."""
    errors = []
    forbidden_patterns = [
        "import unittest.mock",
        "from unittest import mock",
        "from unittest.mock import",
    ]

    try:
        content = test_file.read_text(encoding="utf-8")
        lines = content.splitlines()
        in_docstring = False
        docstring_delimiter = None

        for line_num, line in enumerate(lines, 1):
            line_stripped = line.strip()

            # Track docstring state
            if '"""' in line_stripped or "'''" in line_stripped:
                if not in_docstring:
                    in_docstring = True
                    docstring_delimiter = '"""' if '"""' in line_stripped else "'''"
                    if line_stripped.count(docstring_delimiter) >= DOCSTRING_PAIRS:
                        in_docstring = False
                elif docstring_delimiter and docstring_delimiter in line_stripped:
                    in_docstring = False
                    docstring_delimiter = None

            # Skip comments, strings, and content inside docstrings
            if line_stripped.startswith(("#", '"', "'")) or in_docstring:
                continue

            # Check for forbidden patterns
            for pattern in forbidden_patterns:
                if pattern in line_stripped:
                    relative_path = test_file.relative_to(root_path)
                    errors.append(f"{relative_path}:{line_num} uses '{pattern}'")
                    break

    except (OSError, UnicodeDecodeError):
        # Skip files that can't be read
        pass

    return errors


def main() -> NoReturn:
    """Main entry point for the mock import checker."""
    parser = argparse.ArgumentParser(
        description="Check for forbidden unittest.mock imports in test files"
    )
    parser.add_argument(
        "--root",
        type=pathlib.Path,
        default=pathlib.Path.cwd(),
        help="Root directory to search for test files (default: current directory)",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Only output errors, no informational messages",
    )
    args = parser.parse_args()

    root_path = args.root.resolve()

    if not args.quiet:
        print(f"Checking for unittest.mock imports in: {root_path}")

    test_files = get_test_files(root_path)

    if not args.quiet:
        print(f"Found {len(test_files)} test files to check")

    errors = []
    for test_file in test_files:
        errors.extend(check_file_for_mock_imports(test_file, root_path))

    if errors:
        # Report all forbidden mock imports
        print("\n\nForbidden unittest.mock imports found:")
        for error in sorted(errors)[:MAX_ERRORS_TO_SHOW]:
            print(f"  - {error}")

        if len(errors) > MAX_ERRORS_TO_SHOW:
            print(f"  ... and {len(errors) - MAX_ERRORS_TO_SHOW} more")

        print(f"\nTotal: {len(errors)} forbidden imports")
        print("\nUse pytest-mock instead:")
        print("  def test_something(mocker):")
        print("      mock_obj = mocker.MagicMock()")
        print("\nSee: https://pytest-mock.readthedocs.io/")
        sys.exit(1)
    else:
        if not args.quiet:
            print("\n✓ No unittest.mock imports found!")
        sys.exit(0)


if __name__ == "__main__":
    main()
