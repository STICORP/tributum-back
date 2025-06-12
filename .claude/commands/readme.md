# /readme

Generate or update a comprehensive README.md file by analyzing all aspects of the project.

## Instructions

When this command is invoked, perform the following comprehensive analysis and create/update the README:

### 0. **Update Strategy: Commit-Based Intelligent Updates**

The README tracks its generation state and updates intelligently based on changes:

#### Metadata Tracking
Add an HTML comment at the end of README.md:
```markdown
<!-- README-METADATA
Last Updated: 2024-12-06
Last Commit: 7c634e2
Update Count: 3
-->
```

#### Update Process
1. **Check README state**
   ```bash
   # Extract metadata from README
   grep -A3 "README-METADATA" README.md

   # Get commits since last update
   LAST_COMMIT=$(grep "Last Commit:" README.md | cut -d' ' -f3)
   git log --oneline $LAST_COMMIT..HEAD
   ```

2. **Analyze changes since last update**
   ```bash
   # What files changed?
   git diff --name-only $LAST_COMMIT..HEAD

   # What types of changes?
   git log --pretty=format:"%s" $LAST_COMMIT..HEAD
   ```

3. **Determine update scope**
   - **Dependencies changed** (pyproject.toml, requirements.txt) → Update Tech Stack, Installation
   - **New Python files** → Update Project Structure, possibly Architecture
   - **Config files changed** → Update Configuration section
   - **Tests added** → Update Testing section
   - **Terraform changes** → Update Deployment section
   - **Documentation files** → Update relevant sections
   - **Feature commits** → Update Overview, Roadmap
   - **CI/CD files** → Update Development or Deployment sections

4. **Smart section updates**
   - Preserve sections marked with `<!-- MANUAL -->` comments
   - Update auto-generated sections based on file analysis
   - Add new sections if needed (e.g., API docs when endpoints are added)
   - Flag sections needing manual review with `<!-- NEEDS-REVIEW -->`

#### Full Regeneration Triggers
Force full README regeneration when:
- Major architectural changes detected
- README structure is corrupted
- Explicitly requested with `--force` flag
- Project structure significantly reorganized

#### Example Update Logic
```python
# Pseudo-code for update logic
changes = analyze_commits_since(last_commit)

if 'pyproject.toml' in changes.files:
    update_sections(['tech-stack', 'installation', 'development'])

if any(f.endswith('.py') for f in changes.new_files):
    update_sections(['project-structure', 'architecture'])
    if 'test' in any_new_file:
        update_sections(['testing'])

if 'terraform/' in changes.paths:
    update_sections(['deployment', 'infrastructure'])

if commit_messages_mention(['api', 'endpoint']):
    check_and_add_section('api-documentation')
```

### 1. **Project Analysis**
Analyze these aspects:
- Project name, description, and purpose
- Technology stack and versions
- Project structure and architecture
- Dependencies (production and development)
- Configuration files and their purposes
- Infrastructure setup
- Development tools and workflows
- Testing framework and coverage
- CI/CD pipelines
- Documentation structure

### 2. **README Sections to Include**

#### Header
- Project name with appropriate badges (Python version, license, etc.)
- Brief, compelling description
- Key features or goals

#### Table of Contents
- Auto-generated based on sections
- Properly linked to headers

#### Overview
- Detailed project description
- Problem it solves
- Target audience/users
- Current status (alpha, beta, production)

#### Architecture
- System design overview
- Directory structure explanation
- Key architectural decisions
- Domain model (if applicable)

#### Tech Stack
- Languages and versions
- Frameworks and libraries
- Infrastructure tools
- Development tools

#### Prerequisites
- System requirements
- Required software versions
- Account requirements (GCP, etc.)

#### Installation
- Step-by-step setup instructions
- Environment configuration
- Dependencies installation
- Database setup (if applicable)

#### Configuration
- Environment variables
- Configuration files
- Secrets management

#### Usage
- How to run the application
- CLI commands
- API endpoints (if applicable)
- Examples

#### Development
- Development setup
- Code style and standards
- Pre-commit hooks
- Type checking
- Linting and formatting
- Testing procedures

#### Testing
- How to run tests
- Test structure
- Coverage requirements

#### Deployment
- Deployment process
- Infrastructure setup
- Environment-specific configurations
- Monitoring and logging

#### Contributing
- How to contribute
- Code review process
- Branch strategy
- Commit conventions

#### Project Structure
- Detailed directory tree
- Purpose of each directory
- Important files explained

#### API Documentation
- Available endpoints
- Request/response formats
- Authentication

#### Troubleshooting
- Common issues and solutions
- FAQ

#### Roadmap
- Future features
- Known issues
- Version planning

#### License
- License information
- Copyright

#### Acknowledgments
- Credits
- Third-party licenses

### 3. **Implementation Process**

1. **Gather Information**
   ```bash
   # Analyze project structure
   find . -type f -name "*.py" | head -20
   find . -type f -name "*.md" | grep -v README

   # Check dependencies
   cat pyproject.toml

   # Analyze configuration
   ls -la .* *.{json,yaml,yml,toml} 2>/dev/null

   # Check for tests
   find . -name "*test*" -type f

   # Look for documentation
   find . -name "*.md" -type f
   ```

2. **Extract Key Information**
   - Parse pyproject.toml for dependencies and project metadata
   - Read CLAUDE.md for project-specific guidelines
   - Check for API documentation
   - Identify infrastructure configuration
   - Find example code or usage

3. **Generate README**
   - Use markdown best practices
   - Include code examples with syntax highlighting
   - Add helpful links and references
   - Ensure all commands are tested and working
   - Make it scannable with clear headers
   - Include visual elements where helpful (architecture diagrams in mermaid)

4. **Validate**
   - All links work
   - All commands are accurate
   - Examples run successfully
   - Markdown renders correctly

### 4. **Style Guidelines**

- Use clear, concise language
- Write for both technical and non-technical audiences where appropriate
- Include plenty of examples
- Use badges for quick visual information
- Keep line length reasonable for readability
- Use tables for structured information
- Include code blocks with proper language tags

### 5. **Maintenance**

The README should be:
- Updated whenever significant changes occur
- Kept in sync with actual project state
- Reviewed for accuracy regularly
- Version-specific where needed

### 6. **Handling Edge Cases**

#### Manual Edits Preservation
- Detect sections with manual content by comparing with expected auto-generated content
- Use fuzzy matching to identify moved or slightly modified sections
- Preserve custom examples, descriptions, and additional sections

#### Conflict Resolution
When conflicts arise between auto-updates and manual edits:
1. Preserve manual content in a `<!-- PRESERVED -->` block
2. Generate new content below it
3. Add `<!-- CONFLICT: Please review and merge -->` marker
4. List conflicts in update summary

#### Update Summary
After each update, provide a summary:
```
README Update Summary:
- Updated: Tech Stack (added pytest 8.3.0)
- Updated: Project Structure (new src/domain/users/)
- Preserved: Custom examples in Usage section
- Conflict: Installation section has manual edits
- New Section: API Documentation added
- Commits analyzed: 7c634e2..HEAD (12 commits)
```

## Example Usage

```bash
# Smart update based on recent commits
/readme

# Force full regeneration
/readme --force

# Preview what would be updated without making changes
/readme --dry-run

# Update specific sections only
/readme --sections tech-stack,installation
```

### What happens:

1. **First run** (no README exists):
   - Generates complete README from scratch
   - Adds metadata tracking at the end
   - Commits: Analyzing all files

2. **Subsequent runs** (README exists):
   - Reads last commit hash from metadata
   - Analyzes only changes since then
   - Updates only affected sections
   - Preserves manual edits
   - Shows update summary

3. **Smart detection examples**:
   - New `.py` files → Updates project structure
   - Modified `pyproject.toml` → Updates dependencies
   - New `test_*.py` files → Updates testing section
   - Commits with "feat:" → Updates features/roadmap
   - New API routes → Adds API documentation section

## Benefits of Commit-Based Updates

1. **Efficiency**: Only analyzes and updates what actually changed
2. **Preservation**: Manual edits and customizations are maintained
3. **Accuracy**: Updates are based on actual code changes, not assumptions
4. **Traceability**: Know exactly when README was last in sync with code
5. **Granularity**: Different types of changes trigger appropriate updates
6. **Intelligence**: Learns project patterns over time for better updates

## Notes

- Always verify that commands and examples work before including them
- Include both basic and advanced usage examples
- Make sure prerequisites are complete and accurate
- Test installation instructions in a clean environment if possible
- Keep security considerations in mind (don't expose secrets)
- The commit-based tracking ensures README stays synchronized with actual development
