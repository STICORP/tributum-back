# /enforce-quality

Enforce code quality by removing all quality check bypasses and fixing underlying issues.

## Instructions

This command ensures code quality by:
1. Finding and removing all quality check bypass comments
2. Running pre-commit checks to identify issues
3. Fixing the actual problems instead of ignoring them
4. Ensuring tests still pass and coverage doesn't drop

## Steps to Execute

### 1. Search for Quality Bypasses

First, search for all bypass patterns in src/ and tests/:

```bash
# Search for common bypass patterns
echo "=== Searching for quality bypasses ==="
echo ""
echo "Type ignore comments:"
uv run rg "# type: ignore" src/ tests/ || echo "None found"
echo ""
echo "Ruff/flake8 noqa comments:"
uv run rg "# noqa" src/ tests/ || echo "None found"
echo ""
echo "Bandit nosec comments:"
uv run rg "# nosec" src/ tests/ || echo "None found"
echo ""
echo "Mypy ignore comments:"
uv run rg "# mypy: ignore" src/ tests/ || echo "None found"
echo ""
echo "Pylint disable comments:"
uv run rg "# pylint: disable" src/ tests/ || echo "None found"
echo ""
echo "Coverage exclude comments:"
uv run rg "# pragma: no cover" src/ tests/ || echo "None found"
```

### 2. Remove All Bypass Comments

For each file containing bypass comments:

1. Read the file
2. Remove the bypass comment while preserving the code
3. Save the file

Example removal patterns:
- `some_code()  # type: ignore` → `some_code()`
- `some_code()  # noqa: F401` → `some_code()`
- `some_code()  # nosec B101` → `some_code()`
- `# pylint: disable=line-too-long` → (remove entire line)

### 3. Run Pre-commit Checks

```bash
echo "=== Running pre-commit checks ==="
uv run pre-commit run --all-files
```

### 4. Fix Issues Without Bypassing

For each failure reported:

#### Type Errors (mypy)
- Add proper type annotations
- Fix actual type mismatches
- Use proper generic types instead of Any
- Add necessary Protocol or TypeVar definitions

#### Linting Issues (ruff)
- Fix import order/organization
- Remove unused imports/variables
- Fix line length by proper refactoring
- Improve code structure

#### Security Issues (bandit)
- Replace insecure functions with secure alternatives
- Add proper input validation
- Use secure random generators
- Implement proper error handling

#### Test Coverage
- Ensure all code paths are tested
- Add missing test cases
- Don't use `# pragma: no cover` - test everything

### 5. Verify Quality

After fixing all issues:

```bash
# Run all quality checks
echo "=== Running final quality checks ==="
uv run ruff format .
uv run ruff check . --fix
uv run mypy .
uv run bandit -r . -c pyproject.toml
uv run pytest --cov=src --cov-report=term-missing

# Ensure no quality bypasses remain
echo ""
echo "=== Verifying no bypasses remain ==="
if uv run rg "# type: ignore|# noqa|# nosec|# mypy: ignore|# pylint: disable|# pragma: no cover" src/ tests/; then
    echo "ERROR: Quality bypasses still found!"
    exit 1
else
    echo "✓ No quality bypasses found"
fi
```

### 6. Common Fixes

#### Import Errors
Instead of: `from module import something  # type: ignore`
Fix: Ensure module has type stubs or create a stub file

#### Type Mismatches
Instead of: `result = func()  # type: ignore`
Fix: Add proper return type annotation to func() or handle the actual type

#### Unused Imports
Instead of: `import unused  # noqa: F401`
Fix: Remove the unused import entirely

#### Line Too Long
Instead of: `long_line_of_code_that_exceeds_limit  # noqa: E501`
Fix: Break into multiple lines or extract to variables/functions

#### Security Issues
Instead of: `eval(user_input)  # nosec`
Fix: Use ast.literal_eval() or json.loads() for safe evaluation

## Important Guidelines

1. **Never add bypass comments** - Fix the root cause
2. **Maintain test coverage** - Don't remove tests, add more if needed
3. **Keep functionality intact** - Fixes should not break existing behavior
4. **Follow project patterns** - Use existing code style and patterns
5. **Ask for clarification** - If a fix isn't obvious, ask before proceeding

## Expected Outcome

After running this command:
- Zero quality bypass comments in the codebase
- All pre-commit checks pass
- Test coverage maintained or improved
- Code follows all quality standards
- No functionality is broken
