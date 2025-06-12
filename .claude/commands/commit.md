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

## Usage

When I ask you to commit changes, follow these steps:
1. Analyze all uncommitted changes
2. Group them logically
3. Create atomic commits with descriptive messages
4. Explain what was done and why, focusing on the reasoning behind the implementation
