#!/usr/bin/env python3
"""Dynamic tool runner that isolates dev tools from project dependencies.

This script reads tool configurations from pyproject.toml and runs them
in isolated environments using uv, uvx, or pipx to avoid dependency conflicts.
"""

import subprocess  # nosec B404 - Required for tool execution
import sys
import tomllib
from pathlib import Path
from typing import Any, TypedDict


class ToolConfig(TypedDict, total=False):
    """Configuration for an isolated tool."""

    version: str
    extras: list[str]
    args: list[str]


def load_pyproject_toml() -> dict[str, Any]:
    """Load and parse pyproject.toml file."""
    pyproject_path = Path(__file__).parent.parent / "pyproject.toml"
    if not pyproject_path.exists():
        print(f"Error: {pyproject_path} not found", file=sys.stderr)
        sys.exit(1)

    with open(pyproject_path, "rb") as f:
        return tomllib.load(f)


def get_tool_config(pyproject: dict[str, Any], tool_name: str) -> ToolConfig | None:
    """Get configuration for a specific tool."""
    isolated_tools = pyproject.get("tool", {}).get("isolated-tools", {})
    config = isolated_tools.get(tool_name)
    if config is None or not isinstance(config, dict):
        return None
    # Ensure the config has the right type structure
    typed_config: ToolConfig = {
        "version": config.get("version", ""),
        "extras": config.get("extras", []),
        "args": config.get("args", []),
    }
    return typed_config


def build_tool_spec(tool_name: str, config: ToolConfig) -> str:
    """Build tool specification string for uv/uvx."""
    spec = tool_name
    if version := config.get("version"):
        spec += version  # version already includes operator (>=, ==, etc.)
    if extras := config.get("extras"):
        spec += f"[{','.join(extras)}]"
    return spec


def run_with_uv_tool(tool_spec: str, tool_args: list[str]) -> int:
    """Run tool using 'uv tool run' command."""
    cmd = ["uv", "tool", "run", tool_spec, *tool_args]
    return subprocess.call(cmd)  # nosec B603 - Controlled input from pyproject.toml


def run_with_uvx(tool_spec: str, tool_args: list[str]) -> int:
    """Run tool using 'uvx' command."""
    cmd = ["uvx", tool_spec, *tool_args]
    return subprocess.call(cmd)  # nosec B603 - Controlled input from pyproject.toml


def run_with_pipx(tool_spec: str, tool_args: list[str]) -> int:
    """Run tool using 'pipx run' command."""
    # pipx doesn't support version specs in the same way
    tool_name = tool_spec.split("[")[0].split(">")[0].split("=")[0]
    cmd = ["pipx", "run", tool_name, *tool_args]
    return subprocess.call(cmd)  # nosec B603 - Controlled input from pyproject.toml


def check_command_exists(command: str) -> bool:
    """Check if a command exists in PATH."""
    try:
        subprocess.run(  # nosec B603 - Checking tool availability
            [command, "--version"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
    except FileNotFoundError:
        return False
    else:
        return True


def run_tool(tool_name: str, tool_args: list[str]) -> int:
    """Run a tool in an isolated environment."""
    pyproject = load_pyproject_toml()
    config = get_tool_config(pyproject, tool_name)

    if config is None:
        # Tool not in isolated-tools, try running directly with uv run
        print(
            f"Warning: '{tool_name}' not found in [tool.isolated-tools], "
            f"running with 'uv run'",
            file=sys.stderr,
        )
        cmd = ["uv", "run", tool_name, *tool_args]
        return subprocess.call(cmd)  # nosec B603 - Fallback for unlisted tools

    # Build tool specification
    tool_spec = build_tool_spec(tool_name, config)

    # Add default args from config
    default_args = config.get("args", [])
    all_args = default_args + tool_args

    # Determine which runner to use
    runner = _get_available_runner()
    if runner is None:
        print(
            "Error: No suitable tool runner found. Please install uv, uvx, or pipx.",
            file=sys.stderr,
        )
        return 1

    # Run with the selected runner
    if runner == "uv":
        return run_with_uv_tool(tool_spec, all_args)
    if runner == "uvx":
        return run_with_uvx(tool_spec, all_args)
    # pipx
    return run_with_pipx(tool_spec, all_args)


def _get_available_runner() -> str | None:
    """Determine which tool runner is available."""
    if check_command_exists("uv"):
        # Check if uv supports 'tool run' (newer versions)
        result = subprocess.run(  # nosec B603 B607 - Checking uv capabilities
            ["uv", "tool", "--help"],
            capture_output=True,
            text=True,
            check=False,
        )
        if "run" in result.stdout:
            return "uv"
        # Fallback to uvx if available
        if check_command_exists("uvx"):
            return "uvx"
    elif check_command_exists("uvx"):
        return "uvx"
    elif check_command_exists("pipx"):
        return "pipx"
    return None


def main() -> None:
    """Main entry point."""
    min_args = 2
    if len(sys.argv) < min_args:
        print("Usage: run_tool.py <tool_name> [tool_args...]", file=sys.stderr)
        sys.exit(1)

    tool_name = sys.argv[1]
    tool_args = sys.argv[2:]

    exit_code = run_tool(tool_name, tool_args)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
