# /commit

Analyze project changes and create logical commits using conventional commit messaging.

## Instructions

When analyzing changes:

1. **Review all changes** - Use `git status` and `git diff` to understand what has been modified
2. **Group changes logically** - Split commits by:
   - Feature/functionality
   - File purpose (e.g., tests, docs, config)
   - Module or component
   - Don't mix unrelated changes in one commit

3. **Use conventional commit format**:
   ```
   <type>(<scope>): <subject>

   <body>

   <footer>
   ```

4. **Commit types**:
   - `feat`: New feature
   - `fix`: Bug fix
   - `docs`: Documentation changes
   - `style`: Code style changes (formatting, semicolons, etc)
   - `refactor`: Code refactoring without changing functionality
   - `test`: Adding or modifying tests
   - `chore`: Maintenance tasks, dependency updates
   - `perf`: Performance improvements
   - `build`: Build system changes
   - `ci`: CI/CD changes

5. **Commit message guidelines**:
   - Subject line: Clear, concise summary (50 chars max)
   - Body: Explain WHAT changed and WHY (not how)
   - Include design decisions and reasoning
   - Describe the problem being solved
   - Mention any trade-offs or alternatives considered
   - Never mention AI assistance or automated generation
   - Never include references to Claude Code, Anthropic, or AI tools

6. **Multiple file handling**:
   - If changes span multiple files but serve one purpose, commit together
   - If files serve different purposes, create separate commits
   - Stage files selectively using `git add <file>`

7. **Example commit message**:
   ```
   feat(auth): implement JWT authentication system

   Added JWT-based authentication to secure API endpoints. Chose JWT over
   session-based auth for stateless operation and better scalability.

   Key decisions:
   - Used RS256 algorithm for enhanced security
   - Token expiry set to 24 hours with refresh token support
   - Implemented middleware for route protection

   This establishes the foundation for user authentication across
   the application and enables secure API access.
   ```

## Automatic CHANGELOG Updates

After creating each commit, automatically update CHANGELOG.md:

1. **Parse commit message** to determine change type and description
2. **Map commit types to changelog categories**:
   - `feat:` → `### Added`
   - `fix:` → `### Fixed`
   - `docs:` → `### Changed` (only if significant)
   - `refactor:` → `### Changed`
   - `perf:` → `### Changed`
   - `test:` → Skip (don't add to changelog)
   - `chore:` → Skip (unless dependencies/security)
   - `style:` → Skip (don't add to changelog)
   - `build:` → `### Changed`
   - `ci:` → Skip (unless affects users)

3. **Format changelog entry**:
   - Extract subject line without type/scope prefix
   - Capitalize first letter
   - Rephrase for end-users (not developers)
   - Include key details from commit body if relevant

4. **Update CHANGELOG.md**:
   - Add under `## [Unreleased]` in appropriate category
   - Create category if it doesn't exist
   - Avoid duplicates - check if similar entry exists
   - Preserve existing entries

5. **Skip changelog for**:
   - Test-only commits
   - Style/formatting changes
   - Minor doc updates (typos, comments)
   - Dev tool configs (unless affects users)

6. **Changelog entry examples**:
   ```
   Commit: feat(auth): implement JWT authentication
   Entry:  - JWT authentication for API endpoints

   Commit: fix(api): resolve memory leak in handler
   Entry:  - Memory leak in request handling

   Commit: chore(deps): bump fastapi to 0.115.12
   Entry:  - Updated FastAPI to 0.115.12 (under ### Security if security update)
   ```

7. **Changelog commit message format**:
   ```
   docs: update changelog for <feature/fix description>

   Added entry to [Unreleased] section under <category> for the
   <commit type> that <what it does>.

   This keeps the changelog current with development progress and
   ensures all user-facing changes are properly documented for
   the next release.
   ```

   Example:
   ```
   docs: update changelog for JWT authentication feature

   Added entry to [Unreleased] section under Added category for the
   authentication feature that implements JWT-based API security.

   This keeps the changelog current with development progress and
   ensures all user-facing changes are properly documented for
   the next release.
   ```

## Usage

When I ask you to commit changes, follow these steps:
1. Analyze all uncommitted changes
2. Group them logically
3. Create atomic commits with descriptive messages
4. After each commit, check if it should update CHANGELOG.md
5. If yes, stage and commit the changelog update with a descriptive message following the format above
6. Explain what was done and why, focusing on the reasoning behind the implementation
