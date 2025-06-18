# /curate-makefile

Intelligently analyze and improve the project's Makefile by examining the entire project ecosystem to ensure consistency, completeness, and best practices.

## Instructions

This command performs a holistic analysis of the project to curate the Makefile. It discovers tools, patterns, and conventions automatically rather than assuming specific toolchains.

### Phase 1: Project Discovery

1. **Identify Project Type and Toolchain**
   - Examine project manifest files:
     - Python: `pyproject.toml`, `setup.py`, `requirements*.txt`, `Pipfile`
     - Node.js: `package.json`, `yarn.lock`, `pnpm-lock.yaml`
     - Rust: `Cargo.toml`
     - Go: `go.mod`
     - Ruby: `Gemfile`
     - Others as found
   - Detect package manager from lock files and manifest content
   - Identify build tools and task runners

2. **Discover Configured Tools**
   - Parse configuration files to find all tools in use:
     ```bash
     # Python example
     grep -E "^\[tool\." pyproject.toml | cut -d. -f2 | cut -d] -f1 | sort -u

     # Node.js example
     jq -r '.scripts | keys[]' package.json 2>/dev/null || true
     ```
   - Check for tool-specific config files (`.eslintrc`, `.prettierrc`, `ruff.toml`, etc.)
   - Note which tools have configuration vs using defaults

3. **Analyze Existing Automation**
   - **Pre-commit hooks**: Parse `.pre-commit-config.yaml` to understand quality gates
   - **CI/CD workflows**: Examine `.github/workflows/*.yml`, `.gitlab-ci.yml`, etc.
   - **Scripts directory**: Inventory custom scripts that might need Makefile targets
   - **Docker/Compose**: Check for containerized workflows

### Phase 2: Makefile Analysis

1. **Current State Assessment**
   - Parse existing Makefile targets and their commands
   - Identify target categories (install, test, lint, build, deploy, etc.)
   - Map command patterns and conventions
   - Check for variables and includes

2. **Structural Issues**
   - Missing or incomplete `.PHONY` declarations
   - Targets without descriptions (missing `## ` comments)
   - Inconsistent naming conventions
   - Missing standard targets (help, clean, install)

3. **Command Analysis**
   - Compare Makefile commands with:
     - Pre-commit hook commands
     - CI/CD workflow commands
     - Package.json scripts (if applicable)
   - Identify discrepancies and missing targets

### Phase 3: Intelligent Curation

1. **Configuration Awareness**
   - For each discovered tool, verify if Makefile uses configuration files:
     ```bash
     # Detect if tool accepts config file
     <tool> --help 2>&1 | grep -iE "(config|conf|rc|toml|yaml|json)" || true
     ```
   - Suggest appropriate config flags based on tool documentation

2. **Redundancy Detection**
   - Identify targets running identical or subset commands
   - Find opportunities for composite targets using `$(MAKE)`
   - Detect repeated command patterns that could use variables

3. **Completeness Check**
   - **Missing from Makefile but in pre-commit**: Suggest adding as quality check targets
   - **Missing from Makefile but in CI/CD**: Suggest adding for local development
   - **Missing from pre-commit but in Makefile**: Question if it should be a pre-commit hook
   - **Environment-specific needs**: Development vs production targets

4. **Best Practices Application**
   - **Dependency Management**:
     - Check if install commands match CI/CD
     - Verify development dependencies are properly handled
   - **Error Handling**:
     - Identify where `|| true` or `-` prefix might be appropriate
     - Ensure critical commands fail properly
   - **Performance**:
     - Suggest parallel execution where applicable
     - Identify expensive operations that could be cached

### Phase 4: Recommendations

Generate a structured report with:

1. **Executive Summary**
   - Project type and detected toolchain
   - Number of issues found by category
   - Overall Makefile health score

2. **Detailed Findings**
   ```markdown
   ## Configuration Mismatches
   - Tool: [tool_name]
     Config file: [file]
     Current command: [command]
     Suggested: [command with config]
     Rationale: Ensures consistent behavior with pre-commit/CI

   ## Missing Targets
   - Suggested target: [name]
     Command: [command]
     Source: Found in [pre-commit/.github/workflows/etc]
     Purpose: [description]

   ## Redundancy Opportunities
   - Targets: [target1, target2]
     Overlap: [common commands]
     Suggestion: Create [base_target] and compose others
   ```

3. **Makefile Template**
   Generate a complete suggested Makefile with:
   - Proper structure and organization
   - All recommended changes applied
   - Comments explaining non-obvious choices

### Phase 5: Validation

Before finalizing recommendations:
1. Test that suggested commands are valid
2. Verify tool availability in project environment
3. Check for breaking changes to existing workflows
4. Ensure compatibility with project's development guidelines

### Output Example

```markdown
# Makefile Curation Report

## Project Analysis
- **Type**: Python project with FastAPI
- **Package Manager**: uv (detected from uv.lock)
- **Development Tools**: 12 configured tools found
- **CI/CD**: GitHub Actions with 3 workflow files

## Key Findings

### 1. Configuration Mismatches (3 found)
**vulture** - Dead code detection
- Config exists: `[tool.vulture]` in pyproject.toml
- Current: `vulture .`
- Recommended: `vulture . --config=pyproject.toml`

### 2. Missing Targets (5 found)
**From .pre-commit-config.yaml**:
- `make format` - Missing ruff format command
- `make typecheck` - Missing mypy command

**From .github/workflows/checks.yml**:
- `make ci-test` - Missing test command matching CI flags

### 3. Redundancy Opportunities (2 found)
**security targets**:
- `security`, `security-deps`, and `sec-check` overlap
- Recommend: Consolidate into composable targets

### 4. Structural Improvements
- `.PHONY` missing 8 targets
- No `help` target despite descriptive comments
- Inconsistent target naming (snake_case vs kebab-case)

## Recommended Makefile Structure
[Generated complete Makefile with all improvements]
```

## Key Principles
1. **Discover, don't assume** - Analyze the project to understand its specific needs
2. **Cross-reference everything** - Compare Makefile, pre-commit, CI/CD, and configs
3. **Preserve project patterns** - Respect existing conventions and workflows
4. **Explain recommendations** - Provide rationale for each suggestion
5. **Maintain backward compatibility** - Don't break existing workflows without warning
