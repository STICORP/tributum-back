# /analyze

Analyze the current project state and read project-specific instructions before starting a new task.

## Instructions

When this command is invoked, perform the following analysis:

1. **Read CLAUDE.md** - Always start by reading the CLAUDE.md file at the project root to understand:
   - Project-specific instructions and guidelines
   - Development conventions and policies
   - Build, test, and lint commands
   - Technology stack preferences
   - Any special requirements or constraints

2. **Analyze Project Structure** - Explore the codebase to understand:
   - Directory organization and architecture
   - Main source code locations
   - Test structure and organization
   - Configuration file locations
   - Infrastructure and deployment setup

3. **Identify Technology Stack** - Check for:
   - Programming languages used (Python, TypeScript, etc.)
   - Package managers (uv, npm, yarn, pip, etc.)
   - Framework files (FastAPI, Django, React, etc.)
   - Build tools and configurations
   - Dependencies and their versions

4. **Review Configuration Files** - Examine:
   - `pyproject.toml`, `package.json`, `requirements.txt`
   - `.env` files and environment configuration
   - Build and deployment configurations
   - CI/CD pipeline files
   - Docker or containerization files

5. **Check Git Status** - Understand the current state:
   - Current branch
   - Any uncommitted changes
   - Recent commit history (last 5-10 commits)
   - Remote repository status

6. **Summarize Findings** - After analysis, provide:
   - Project overview and current state
   - Technology stack summary
   - Key conventions from CLAUDE.md
   - Any important context for development
   - Current work in progress (if any)

## Usage

Run this command before starting any new development task to ensure you have full context about:
- Project-specific requirements and conventions
- Current codebase state
- Technology choices and constraints
- Recent changes and ongoing work

This helps maintain consistency with project standards and avoids redundant questions about the codebase structure or conventions.

## Example Output

After running `/analyze`, you should be able to answer:
- What is this project about?
- What technologies does it use?
- What are the key development conventions?
- What build/test commands should I use?
- What has been recently worked on?
- Are there any special instructions I need to follow?