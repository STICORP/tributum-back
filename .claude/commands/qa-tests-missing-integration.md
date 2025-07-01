# /qa-tests-missing-integration

## EXECUTION PROTOCOL - MANDATORY READING

**YOU MUST:**
1. Execute EVERY instruction in this command IN ORDER
2. After EACH instruction, provide a REPORT: section showing what you found
3. After EACH instruction, if we have an ACTION section, execute the ACTION if the REPORT tells you to.
4. Use checkboxes [ ] to track completion - mark [x] when done
5. NEVER skip any instruction - even if not applicable, report "N/A - [reason]"
6. At the end, verify ALL checkboxes are marked before completing

---

## INITIALIZATION

[ ] **Think Harder**
REPORT: [State that you are thinking harder about the implementation]

---

## Understand the project

[ ] Execute these analyses in parallel:
```
- Fully read pyproject.toml
- Fully read Makefile
- Fully read .pre-commit-config.yaml
- Fully read .env.example
- Fully read main.py
- Fully read /src/core/config.py
- Fully read /src/api/main.py
```
REPORT: [Confirm all 6 files were read and provide key insights from each]

---

[ ] **DEEPLY ANALYSE AND UNDERSTAND the tests framework and how it is used by the codebase, by navigating the src/ directory and analysing the source code. Ignore any markdown files.**
REPORT: [Describe the tests framework you discovered, its patterns, how test files are organized, the pytest plugin they use, the linting and type strictness of the code, and how we should use this information to implement tests.]

[ ] **DEEPLY ANALYSE AND UNDERSTAND our codebase in src/ and check if we neglected to implement integration tests for important functionalities. Ignore any markdown files.**
REPORT: [Describe important functionality that is neglected and EXECUTE ACTION or state "No functionality neglected by integration tests"]
ACTION: [Implement the missing integration tests]

[ ] **The implemented tests should be consistent follow the patterns discovered by the test framework analysis and understanding.**
REPORT: [Provide a complete report of the consistency of the implemented tests against the codebase patterns. If any inconsistency was found EXECUTE ACTION]
ACTION: [Fix inconsistencies and make the implemented tests consistent with project patterns]

[ ] **The implemented tests should ALWAYS use pytest_mock instead of unittest.mock**
REPORT: [Confirm pytest_mock was used everywhere. If not, EXECUTE ACTION.]
ACTION: [Search for unittest.mock in the implemented tests and modify the code to use pytest_mock]

[ ] **Proper types should be used. Never use "type: ignore" comments**
REPORT: [Confirm that no "type: ignore" comments were used in the implemented tests and if we have any such comment EXECUTE ACTION]
ACTION: [Remove all "type: ignore" comments, implement proper types, execute make pre-commit and fix everything until everything passes.]

[ ] **Proper quality checks should pass. Never use "noqa" comments**
REPORT: [Confirm no "noqa" comments were used in the implemented tests and if we have any such comment EXECUTE ACTION]
ACTION: [Remove all "noqa" comments, fix the errors properly, execute make pre-commit and fix everything until everything passes.]

---

## FINAL INSTRUCTIONS

[ ] **The make pre-commit should pass flawlessly.**
REPORT: [Show pre-commit output and if there are any issues that needs to be fixed, EXECUTE ACTION]
ACTION: [Properly fix every single issue found by the pre-commit hooks and keep executing make pre-commit until everything is fixed.]

[ ] **This command will only be successful when we achieve 100% test coverage**
REPORT: [Show test coverage percentage. If not at 100%, EXECUTE ACTION.]
ACTION: [Implement tests for the missing lines.]

---

## FINAL VERIFICATION CHECKLIST

[ ] **Make sure you extensively performed ALL verifications and tasks outlined in this command.**
REPORT: [Count total checkboxes and confirm all are marked]

[ ] **Check if you neglected to perform any of the instructions outlined in this command and DO EVERY SINGLE ONE you neglected.**
REPORT: [Review all checkboxes above and confirm none were skipped]

[ ] **DO NOT finish this command without making sure ABSOLUTELY ALL tasks above were completed successfully.**
REPORT: [Final confirmation that all tasks are complete]

---

## COMPLETION REQUIREMENTS

Before marking this command as complete:
1. Count all checkboxes: there should be 12 checkboxes total
2. Verify ALL 12 checkboxes are marked with [x]
3. Verify each checkbox has a REPORT: section with actual findings
4. Verify that each ACTION required to be executed, was actually executed
5. Verify pre-commit passes
6. Verify test coverage is 100%

**ONLY when all 6 requirements above are met, output:**
"CHECK-IMPLEMENTATION COMPLETE - All 12 validations executed with reports"
