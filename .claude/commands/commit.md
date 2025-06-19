# /commit

Analyze project changes and create logical commits using conventional commit messaging.

## CRITICAL: Prohibited Content in Commit Messages

**You MUST NEVER include ANY of the following in commit messages:**

### Prohibited Patterns:
- `🤖` emoji or any AI-related emojis
- `Generated with [Claude Code]` or similar attribution
- `Co-Authored-By: Claude` or any AI co-author lines
- References to being "AI-generated", "AI-assisted", "automated"
- Any mention of Anthropic, Claude (except when legitimately part of the change description, e.g., "update CLAUDE.md")

### Why This Matters:
- Commit history should reflect human decisions and reasoning
- AI attribution is not relevant to the change itself
- Professional repositories don't include tool attribution in commits

### Self-Check Before Committing:
After composing a commit message, you MUST ask yourself:
"Does this message contain ANY attribution to AI tools?"
If yes, remove it before proceeding.

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
   - **FORBIDDEN**: Never mention AI assistance or automated generation
   - **FORBIDDEN**: Never include references to Claude Code, Anthropic, or AI tools
   - **FORBIDDEN**: No 🤖 emojis or "Co-Authored-By: Claude" lines

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

   [END OF COMMIT MESSAGE - NO ADDITIONAL CONTENT BELOW THIS LINE]
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

## Pre-Commit Validation (MANDATORY - DO NOT SKIP)

Before executing ANY git commit command, you MUST:

1. **Show the complete commit message** you plan to use (display it in a code block)
2. **Explicitly verify** it contains NONE of these:
   - 🤖 emoji
   - "Generated with [Claude" or any variation
   - "Co-Authored-By: Claude" or any AI attribution
   - Any reference to AI/Anthropic/automated generation
3. **State your verification** by saying: "Verified: No AI attribution in commit message"
4. **Only proceed** with git commit after this verification

Example validation:
```
Planned commit message:
```
feat(auth): implement JWT authentication

Added JWT-based authentication...
```

Verified: No AI attribution in commit message ✓
```

## Usage

When I ask you to commit changes, follow these steps:
1. Analyze all uncommitted changes
2. Group them logically
3. Compose commit message following the format above
4. **MANDATORY: Complete Pre-Commit Validation (see section above)**
5. Execute the commit only after verification
6. After each commit, check if it should update CHANGELOG.md
7. If yes, stage and commit the changelog update (also verify no AI attribution)
8. Explain what was done and why, focusing on the reasoning behind the implementation
