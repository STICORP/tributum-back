# /create-release

Manage semantic versioning and changelog updates for the Tributum project.

## Pre-Release Checks

1. **Verify Clean Working Directory**
   - Run `git status` to ensure no uncommitted changes
   - Run `git fetch --tags` to sync with remote tags
   - Verify on correct branch: `git branch --show-current` (should be master/main)

2. **Run Quality Checks**
   - `uv sync --group dev` to ensure dependencies are up to date
   - `uv run pre-commit run --all-files` to run all quality checks
   - Ensure all tests pass before proceeding

3. **Verify Unreleased Changes**
   - Check CHANGELOG.md has content in [Unreleased] section
   - If empty, stop and inform user that no unreleased changes are documented
   - Note: With automatic changelog updates from /commit, this should rarely be empty

## Release Steps

1. **Analyze Recent Changes**
   - Run `git log --oneline --decorate --graph $(git describe --tags --abbrev=0 2>/dev/null || echo "")..HEAD` to see commits since last tag
   - Run `git diff --name-status $(git describe --tags --abbrev=0 2>/dev/null || git rev-list --max-parents=0 HEAD)..HEAD` to see changed files
   - Review changes to determine impact

2. **Determine Version Bump Type**
   Based on the CHANGELOG.md [Unreleased] section content:
   - **PATCH (0.0.X)**: Only entries in Fixed, Security categories, or minor dependency updates
   - **MINOR (0.X.0)**: Any entries in Added category, or significant entries in Changed
   - **MAJOR (X.0.0)**: Any entries in Removed category, breaking changes noted, or entries marked as BREAKING CHANGE

   Additional analysis from git commits:
   - Check commit messages for "BREAKING CHANGE" in footer
   - Verify API contract changes
   - Review configuration structure modifications

3. **Update CHANGELOG.md**
   - Read current CHANGELOG.md
   - Move items from [Unreleased] section to new version section with format: `## [X.Y.Z] - YYYY-MM-DD`
   - Ensure changes are categorized: Added, Changed, Deprecated, Removed, Fixed, Security
   - Keep [Unreleased] section at top for future changes
   - Update comparison links at bottom:
     - Update [Unreleased] link to compare from new version to HEAD
     - Add new version link comparing from previous version

4. **Review Project Metadata**
   - Check if pyproject.toml metadata needs updates (description, keywords, classifiers)
   - Update Development Status classifier if needed (Alpha → Beta → Stable)
   - Ensure consistency across all version references

5. **Execute Release**
   - Stage CHANGELOG.md: `git add CHANGELOG.md`
   - Run appropriate bump command: `uv run bump-my-version bump [patch|minor|major]`
     - This automatically creates annotated git tag (v0.1.1) with message "Release version vX.Y.Z"
     - Updates version in: pyproject.toml, src/core/config.py, VERSION file
     - Creates commit with message: "chore: bump version from X.Y.Z to X.Y.Z"
   - Show `git status`, `git log -1`, and `git tag -n` for review

6. **Push and Create GitHub Release**
   - Push the changes and tags:

     ```bash
     git push origin master
     git push origin --tags
     ```

   - Extract the changelog content for this version from CHANGELOG.md
   - Create GitHub release using `gh release create`:

     ```bash
     gh release create vX.Y.Z \
       --title "Release vX.Y.Z" \
       --notes "changelog content for this version" \
       --target master
     ```

   - Show the release URL from the command output

7. **Post-Release Summary**
   - Display summary of actions taken:
     - Version bumped from X.Y.Z to X.Y.Z
     - CHANGELOG.md updated
     - Git tag created and pushed
     - GitHub release published at URL
   - Remind to monitor for any deployment or dependency issues

## Important Notes

- Always analyze the actual code changes, not just commit messages
- When in doubt between version types, choose the higher one (e.g., minor over patch)
- Breaking changes ALWAYS require a major version bump
- The version 0.x.x indicates the project is still in initial development
- Version 1.0.0 should be reserved for the first stable, production-ready release

## Example Analysis

When analyzing changes, look for:

- **API changes**: Modified endpoints, request/response formats
- **Configuration changes**: New required env vars, changed settings structure
- **Core module changes**: Exceptions, logging, context handling
- **New features**: New endpoints, new modules, new functionality
- **Bug fixes**: Error corrections, exception handling improvements
- **Dependencies**: Security updates, major version bumps of dependencies

## Rollback Instructions (If Needed)

If something goes wrong after version bump but before pushing:

1. **Reset the version commit**: `git reset --hard HEAD~1`
2. **Delete the local tag**: `git tag -d vX.Y.Z`
3. **Restore CHANGELOG.md**: `git checkout HEAD -- CHANGELOG.md`
4. **Fix the issue and retry the release process**

If already pushed:

1. **DO NOT force push to rewrite history**
2. **Create a new patch release to fix the issue**
3. **Document the problem in the new release notes**
