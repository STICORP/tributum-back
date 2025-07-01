#!/usr/bin/env python3
"""Check that test files have appropriate pytest markers based on their location.

This script ensures that:
- All tests in tests/unit/ have @pytest.mark.unit
- All tests in tests/integration/ have @pytest.mark.integration
"""

import argparse
import ast
import pathlib
import sys
from typing import NoReturn

# Constants
MAX_ERRORS_TO_SHOW = 10  # Maximum number of errors to display in detail


class MarkerChecker:
    """Check for pytest markers in test files."""

    def __init__(self, expected_marker: str) -> None:
        """Initialize the marker checker.

        Args:
            expected_marker: The marker name we expect to find (e.g., 'unit')
        """
        self.expected_marker = expected_marker
        self.has_marker = False
        self.test_functions: list[tuple[str, int]] = []
        self.test_classes: list[tuple[str, int]] = []
        self.marked_classes: set[str] = set()

    def check_tree(self, tree: ast.Module) -> None:
        """Check an AST tree for test functions and classes."""
        # Visit all nodes in the tree
        self._visit_node(tree, parent_class=None)

    def _visit_node(self, node: ast.AST, parent_class: str | None) -> None:
        """Visit a node and its children, tracking parent class context."""
        if isinstance(node, ast.ClassDef) and node.name.startswith("Test"):
            self._visit_class(node)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            self._visit_function(node, parent_class)
        else:
            # For other node types, visit children with same parent context
            for child in ast.iter_child_nodes(node):
                self._visit_node(child, parent_class)

    def _visit_class(self, node: ast.ClassDef) -> None:
        """Visit a test class node."""
        self.test_classes.append((node.name, node.lineno))

        # Check if class has the expected marker
        for decorator in node.decorator_list:
            if self._has_marker(decorator):
                self.has_marker = True
                self.marked_classes.add(node.name)
                break

        # Visit children with this class as parent
        for child in node.body:
            self._visit_node(child, parent_class=node.name)

    def _visit_function(
        self, node: ast.FunctionDef | ast.AsyncFunctionDef, parent_class: str | None
    ) -> None:
        """Visit a test function node."""
        if not node.name.startswith("test_"):
            return

        # If we're inside any test class, skip this function
        # We'll only report the class-level missing marker
        if parent_class:
            return

        # Found a test function outside any class
        self.test_functions.append((node.name, node.lineno))

        # Check if function has the expected marker
        for decorator in node.decorator_list:
            if self._has_marker(decorator):
                self.has_marker = True
                break

    def _has_marker(self, decorator: ast.expr) -> bool:
        """Check if a decorator is the expected pytest marker."""
        # Handle @pytest.mark.unit or @pytest.mark.integration
        if isinstance(decorator, ast.Attribute):
            if (
                isinstance(decorator.value, ast.Attribute)
                and isinstance(decorator.value.value, ast.Name)
                and decorator.value.value.id == "pytest"
                and decorator.value.attr == "mark"
                and decorator.attr == self.expected_marker
            ):
                return True
        # Handle @mark.unit or @mark.integration (if mark is imported)
        elif (
            isinstance(decorator, ast.Attribute)
            and isinstance(decorator.value, ast.Name)
            and decorator.value.id == "mark"
            and decorator.attr == self.expected_marker
        ):
            return True
        return False


def check_file_for_markers(test_file: pathlib.Path, expected_marker: str) -> list[str]:
    """Check a single test file for required markers.

    Args:
        test_file: Path to the test file
        expected_marker: The marker we expect (e.g., 'unit', 'integration')

    Returns:
        List of error messages for missing markers
    """
    errors: list[str] = []

    try:
        content = test_file.read_text(encoding="utf-8")
        tree = ast.parse(content, filename=str(test_file))

        checker = MarkerChecker(expected_marker)
        checker.check_tree(tree)

        # If no test functions or classes found, skip
        if not checker.test_functions and not checker.test_classes:
            return errors

        # If marker not found at module level, check for missing markers
        if not checker.has_marker:
            # Report test functions missing the marker
            for func_name, line_no in checker.test_functions:
                errors.append(
                    f"{test_file}::{func_name} (line {line_no}) is missing "
                    f"@pytest.mark.{expected_marker} marker"
                )
            # Report test classes missing the marker (only if not already marked)
            for class_name, line_no in checker.test_classes:
                if class_name not in checker.marked_classes:
                    errors.append(
                        f"{test_file}::{class_name} (line {line_no}) is missing "
                        f"@pytest.mark.{expected_marker} marker"
                    )

    except (OSError, SyntaxError) as e:
        # Skip files that can't be read or parsed
        print(f"Warning: Could not parse {test_file}: {e}", file=sys.stderr)

    return errors


def get_test_files(root_path: pathlib.Path) -> dict[str, list[pathlib.Path]]:
    """Get test files organized by expected marker type.

    Args:
        root_path: Root directory to search

    Returns:
        Dictionary mapping marker name to list of test files
    """
    test_files: dict[str, list[pathlib.Path]] = {
        "unit": [],
        "integration": [],
    }

    # Find unit test files
    unit_path = root_path / "tests" / "unit"
    if unit_path.exists():
        test_files["unit"].extend(
            f for f in unit_path.rglob("test_*.py") if f.is_file()
        )

    # Find integration test files
    integration_path = root_path / "tests" / "integration"
    if integration_path.exists():
        test_files["integration"].extend(
            f for f in integration_path.rglob("test_*.py") if f.is_file()
        )

    return test_files


def main() -> NoReturn:
    """Main entry point for the test marker checker."""
    parser = argparse.ArgumentParser(
        description="Check that test files have appropriate pytest markers"
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
        print(f"Checking test markers in: {root_path}")

    test_files = get_test_files(root_path)
    total_files = sum(len(files) for files in test_files.values())

    if not args.quiet:
        print(f"Found {total_files} test files to check")

    errors: list[str] = []
    for marker_type, files in test_files.items():
        for test_file in files:
            file_errors = check_file_for_markers(test_file, marker_type)
            errors.extend(file_errors)

    if errors:
        # Report missing markers
        print("\n\nMissing pytest markers found:")
        for error in sorted(errors)[:MAX_ERRORS_TO_SHOW]:
            print(f"  - {error}")

        if len(errors) > MAX_ERRORS_TO_SHOW:
            print(f"  ... and {len(errors) - MAX_ERRORS_TO_SHOW} more")

        print(f"\nTotal: {len(errors)} missing markers")
        print(
            "\nPlease add the appropriate @pytest.mark.unit or "
            "@pytest.mark.integration decorator to your test classes or functions."
        )
        sys.exit(1)
    else:
        if not args.quiet:
            print("\n✓ All test files have appropriate markers!")
        sys.exit(0)


if __name__ == "__main__":
    main()
