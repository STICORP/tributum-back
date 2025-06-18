# analyze-project

Perform a comprehensive analysis of the project's configuration and management quality.

## Usage

```
/analyze-project [focus-area]
```

## Description

This command performs an ultra-thorough analysis of the project configuration, examining:

1. **pyproject.toml Configuration Analysis**
   - Dependencies and versions
   - Tool configurations (Ruff, MyPy, pytest, etc.)
   - Project metadata correctness
   - Version management setup

2. **Project Structure Verification**
   - Directory organization
   - File naming conventions
   - Module structure
   - Test organization

3. **Quality Tools Assessment**
   - Linting strictness levels
   - Type checking configuration
   - Security scanning setup
   - Test coverage requirements
   - Documentation standards
   - Pre-commit hooks
   - CI/CD pipeline quality

4. **Missing Tools Identification**
   - Development tools gaps
   - Security tooling needs
   - Performance testing tools
   - Monitoring/observability
   - Documentation tools

5. **Best Practices Compliance**
   - Modern Python practices
   - Security standards
   - Testing strategies
   - Version management
   - Documentation quality

## Arguments

- `focus-area` (optional): Specific area to focus on
  - `security` - Deep dive into security configurations
  - `testing` - Focus on test setup and coverage
  - `tooling` - Analyze development tools
  - `deps` - Dependency management analysis
  - `docs` - Documentation standards review

## Output

The command generates a comprehensive report including:
- Executive summary with overall score
- Detailed strengths analysis
- Configuration correctness assessment
- Best practices compliance review
- Quality metrics comparison
- Tooling gaps identification
- Prioritized improvement recommendations
- Final assessment with letter grade

## Examples

```
/analyze-project
# Performs complete project analysis

/analyze-project security
# Focuses on security configurations and tools

/analyze-project tooling
# Deep dive into development tools and quality checks
```

## Implementation

When this command is run, perform these steps:

1. **Read and analyze pyproject.toml** thoroughly
2. **Explore project structure** using ls, glob, and find
3. **Check all quality tool configurations**:
   - .pre-commit-config.yaml
   - .github/workflows/
   - Makefile
   - Tool-specific configs
4. **Verify version consistency** across all files
5. **Check for missing configurations**:
   - LICENSE, SECURITY.md, CONTRIBUTING.md
   - Docker/containerization
   - API documentation
   - Monitoring setup
6. **Assess dependency freshness**
7. **Generate comprehensive report** with:
   - Strengths and weaknesses
   - Specific improvement recommendations
   - Priority rankings
   - Code examples for fixes

Save the report to `report.md` and stage it for commit.

## Notes

- Use ultra-thorough thinking for deep analysis
- Leave plan.md out of the analysis
- Focus on actionable recommendations
- Include specific code examples for improvements
- Compare against industry best practices
- Provide quantitative scoring where possible
