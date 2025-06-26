# /check-implementation-new

## EXECUTION PROTOCOL - MANDATORY READING

**YOU MUST:**
1. Execute EVERY instruction in this command IN ORDER
2. After EACH instruction, provide a REPORT: section showing what you found
3. Use checkboxes [ ] to track completion - mark [x] when done
4. NEVER skip any instruction - even if not applicable, report "N/A - [reason]"
5. At the end, verify ALL checkboxes are marked before completing

---

## INITIALIZATION

[ ] **Think Harder**
REPORT: [State that you are thinking harder about the implementation]

[ ] **Read and understand all uncommited changes in the git repository**
REPORT: [List all uncommitted files and summary of changes]

[ ] **IMPORTANT AND MANDATORY** All the validations below are to be conducted only on uncommited and changed code. **DO NOT** validate what is already commited.
REPORT: [Confirm understanding and list which files will be validated]

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

## Dependencies

[ ] **If you added any new dependency to the project, make sure you added the absolutely latest version of that library that is supported by our project.**
REPORT: [List any new dependencies found and their versions, or state "No new dependencies added"]

---

## Configuration management

[ ] **COMPLETELY UNDERSTAND** the configuration framework for this project and how it is supposed to be used.
REPORT: [Describe the configuration framework you discovered and how it works]

[ ] **Check if you added, removed or changed any project configuration.**
REPORT: [List all configuration changes found, or state "No configuration changes"]

[ ] **Check if you were consistent and are using configuration the way that the project expects you to.**
REPORT: [Describe how configurations are used and confirm consistency]

[ ] **Check if the configuration follows the established project patterns and you properly used the project configuration framework.**
REPORT: [Confirm pattern adherence with specific examples]

[ ] **Check that, if you added, removed or changed and configuration, you did EVERYWHERE it is required and maintained configuration consistency**
REPORT: [List all places checked and confirm consistency, or state "No configuration changes to verify"]

[ ] **Especially check the .env.example file and if it is complete (With all variables that should be there and no variables that shouldn't be there)**
REPORT: [List all variables checked and confirm consistency, or state "No variable changes to verify"]

---

## Error handling

[ ] **COMPLETELY UNDERSTAND** the error handling framework for this project and how it is supposed to be used.
REPORT: [Describe the error handling framework you discovered and how it works]

[ ] **Are we using the proper custom exceptions we have and should we implement new ones to make this code properly use error handling?**
REPORT: [List custom exceptions used and any new ones needed]

[ ] **Check if properly handled errors where it needs to be handled.**
REPORT: [List all error handling locations checked and results]

[ ] **Check if you handled errors in the way the project expects you to.**
REPORT: [Confirm error handling follows project patterns with examples]

[ ] **Check if you properly used the error handling framework and patterns implemented by the project.**
REPORT: [Confirm framework usage with specific examples]

---

## Logging

[ ] **COMPLETELY UNDERSTAND** the logging framework for this project and how it is supposed to be used.
REPORT: [Describe the logging framework you discovered and how it works]

[ ] **Check if you implemented logging where it is required by best practices.**
REPORT: [List all locations where logging was checked/added]

[ ] **Check if your implementation of logging was done in the way the project expects you to.**
REPORT: [Confirm logging follows project patterns with examples]

[ ] **Check if you properly used the logging framework and patterns implemented by the project.**
REPORT: [Confirm framework usage with specific examples]

---

## Observability

[ ] **COMPLETELY UNDERSTAND** the observability framework for this project and how it is supposed to be used.
REPORT: [Describe the observability framework you discovered and how it works]

[ ] **Check if you implemented observability where it is required by best practices.**
REPORT: [List all locations where observability was checked/added]

[ ] **Check if your implementation of observability was done in the way the project expects you to.**
REPORT: [Confirm observability follows project patterns with examples]

[ ] **Check if you properly used the observability framework and patterns implemented by the project.**
REPORT: [Confirm framework usage with specific examples]

---

## Database interaction

[ ] **COMPLETELY UNDERSTAND** the database interaction framework for this project and how it is supposed to be used.
REPORT: [Describe the database framework you discovered and how it works]

[ ] **Check if your implementation of database interaction was done in the way the project expects you to.**
REPORT: [Confirm database usage follows project patterns, or state "No database changes"]

[ ] **Check if you properly used the database framework and patterns implemented by the project.**
REPORT: [Confirm framework usage with examples, or state "No database changes"]

---

## FastAPI

[ ] **If, AND ONLY IF you implemented code directly related to FastAPI, read .specs/fastapi_best_practices.md and make sure we do not violate any of these practices.**
REPORT: [State if FastAPI code was changed and validation results, or "No FastAPI changes"]

---

## Tests implementation

[ ] **COMPLETELY UNDERSTAND** the test framework for this project and how it is supposed to be used.
REPORT: [Describe the test framework you discovered and how it works]

[ ] **Check if the tests you implemented meaningful test that actually tests code behavior.**
REPORT: [List all tests reviewed and confirm they test behavior]

[ ] **Check other test files to verify that you are being consistent on how you implemented the tests and are actually following the tests patterns the project expects.**
REPORT: [List test files compared and confirm consistency]

[ ] **Check if you are actually using the installed pytest plugins everywhere you should instead of relying on vanilla test implementations (e.g. pytest_mock instead of unittest mock)**
REPORT: [List pytest plugins used and confirm proper usage]

[ ] **Check if you did not introduce any test behavior that will be impossible or difficult to test on our CI (Github Actions)**
REPORT: [Confirm all tests are CI-compatible]

[ ] **Check if the test coverage remains at 100% and if not, implement the tests for missing lines.**
REPORT: [Show coverage percentage and list any missing lines fixed]

---

## Docker implementation

[ ] **COMPLETELY UNDERSTAND** how docker is used in this project.
REPORT: [Describe the Docker setup you discovered]

[ ] **Check if what we implemented needs to be integrated with our docker implementation**
REPORT: [State if Docker integration is needed and why]

[ ] **Check if we need to change Dockerfiles, docker-compose files**
REPORT: [List any Docker files that need changes, or state "No Docker changes needed"]

[ ] **Check if we introduced configuration that should be integrated in docker**
REPORT: [List any configuration that needs Docker integration, or state "None"]

[ ] **Check if we introduced or changed anything that will require that we change anything anywhere in our docker implementation**
REPORT: [List all Docker-related impacts, or state "No Docker impact"]

---

## Other files

[ ] **Do our implementation requires we add, remove or modify anything from Makefile**
REPORT: [List Makefile changes needed, or state "No Makefile changes needed"]

[ ] **Do our implementation requires we add, remove or modify anything from our Pre-Commit**
REPORT: [List pre-commit changes needed, or state "No pre-commit changes needed"]

[ ] **Do our implementation requires we add, remove or modify anything from Github Actions**
REPORT: [List GitHub Actions changes needed, or state "No GitHub Actions changes needed"]

---

## Quality checks and linting

[ ] **Check if you did not ignore any quality checks by using "# type: ignore", "# noqa" or anything of the sort.**
REPORT: [State result of search for these patterns]

[ ] **Make sure you did not added rules to the ignore section in pyproject.toml.**
REPORT: [Confirm no new ignores added to pyproject.toml]

[ ] **If you did, remove them and properly fix quality checks and add proper types.**
REPORT: [List any fixes made, or state "No quality bypasses found"]

[ ] **Make sure you pute constants in the appropriate constants.py file instead of the source code of the feature.**
REPORT: [List constants moved or confirm all constants are properly placed]

---

## FINAL INSTRUCTIONS

[ ] **Before finishing, run pre-commit and fix any issues without trying to ignore the errors or bypass tests in any way.**
REPORT: [Show pre-commit output and list any fixes made]

[ ] **This command will only be finished when all pre-commit passes perfectly**
REPORT: [Confirm pre-commit passes with output]

[ ] **This command will only be successful when we achieve 100% test coverage**
REPORT: [Show test coverage percentage]

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
1. Count all checkboxes: there should be 44 checkboxes total
2. Verify ALL 44 checkboxes are marked with [x]
3. Verify each checkbox has a REPORT: section with actual findings
4. Verify pre-commit passes
5. Verify test coverage is 100%

**ONLY when all 5 requirements above are met, output:**
"CHECK-IMPLEMENTATION COMPLETE - All 44 validations executed with reports"
