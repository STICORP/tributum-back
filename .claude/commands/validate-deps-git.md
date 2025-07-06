# /validate-deps-git

## Execution Protocol - MANDATORY READING

**YOU MUST:**

1. Execute EVERY instruction in this command IN ORDER
2. After EACH instruction, provide a REPORT: section showing what you found
3. After EACH instruction, if we have an ACTION section, execute the ACTION if the REPORT tells you to.
4. Use checkboxes [ ] to track completion - mark [x] when done
5. NEVER skip any instruction - even if not applicable, report "N/A - [reason]"
6. At the end, verify ALL checkboxes are marked before completing

---

## Bootstraping

[ ] **Think Harder**
REPORT: [State that you are thinking harder about the implementation]

[ ] **DEEPLY ANALYSE AND UNDERSTAND all uncommited changes in the git repository and how they relate to the existing codebase. Ignore any markdown files.**
REPORT: [List all uncommitted files, except markdown files. Summarize the changes, what we are trying to implement, and how they affect the codebase.]

[ ] **IMPORTANT AND MANDATORY** All the validations below are to be conducted only on uncommited and changed code. **DO NOT** validate what is already commited.
REPORT: [Confirm understanding and list which files will be validated]

---

## Understand the project

[ ] Execute these analyses in parallel:

```
- Fully read and understand pyproject.toml
- Fully read and understand .pre-commit-config.yaml
- Fully read and understand .env.example
- Fully read and understand Makefile
- Fully read and understand main.py
- Fully read and understand /src/core/config.py
- Fully read and understand /src/api/main.py
- Fully read and understand any conftest.py file in the tests/
```

REPORT: [Confirm all 6 files were read and provide key insights from each]

---

## Validate Dependencies

[ ] **New dependencies added to the project should be at its absolute newest version, unless it causes dependency conflicts with other existing libraries.**
REPORT: [List any new dependencies found and their versions and EXECUTE ACTION or state "No new dependencies"]
ACTION: [Validate version is the most recent. If not, update to the newest version that won't cause a conflict with other dependencies in the project]

---

## Quality Assurance

[ ] **The make pre-commit should pass flawlessly.**
REPORT: [Show pre-commit output and if there are any issues that needs to be fixed, EXECUTE ACTION]
ACTION: [Properly fix every single issue found by the pre-commit hooks and keep executing make pre-commit until everything is fixed.]

[ ] **This command will only be successful when we achieve 100% test coverage**
REPORT: [Show test coverage percentage. If not at 100%, EXECUTE ACTION.]
ACTION: [Implement tests for the missing lines.]

---

## Final Verification

[ ] **Make sure you extensively performed ALL verifications and tasks outlined in this command.**
REPORT: [Count total checkboxes and confirm all are marked]

[ ] **Check if you neglected to perform any of the instructions outlined in this command and DO EVERY SINGLE ONE you neglected.**
REPORT: [Review all checkboxes above and confirm none were skipped]

[ ] **DO NOT finish this command without making sure ABSOLUTELY ALL tasks above were completed successfully.**
REPORT: [Final confirmation that all tasks are complete]

---

## Completion Requirements

Before marking this command as complete:

1. Count all checkboxes: there should be 10 checkboxes total
2. Verify ALL 10 checkboxes are marked with [x]
3. Verify each checkbox has a REPORT: section with actual findings
4. Verify that each ACTION required to be executed, was actually executed
5. Verify pre-commit passes
6. Verify test coverage is 100%

**ONLY when all 6 requirements above are met, output:**
"CHECK-IMPLEMENTATION COMPLETE - All 10 validations executed with reports"
