# /check-implementation

- Think Harder
- Restrain yourself to check only the uncommited and changed code. No need to check what is already commited.

## Understand the project

- Fully read pyproject.toml
- Fully read Makefile
- Fully read .pre-commit-config.yaml
- Fully read main.py
- Fully read /src/core/config.py
- Fully read /src/api/main.py

## Check the usage of the project frameworks

- Was the configuration management done according with the project patterns and how the project expects the configuration management framework to be used?
- Was error handling implemented using the project patterns and how the project expects the error handling framework to be used?
- Was logging implemented using the project patterns and how the project expects the logging framework to be used?
- Was observability implemented using the project patterns and how the project expects the observability framework to be used?
- Was database interaction implemented using the project patterns and how the project expects the database interaction framework to be used?
- If we implemented anything related to FastAPI, read .specs/fastapi_best_practices.md and make sure we do not violate any of these practices.

## Tests implementation

- Check if the tests you implemented meaningful test that actually tests code behavior.
- Check other test files to verify that you are being consistent on how you implemented the tests and are actually following the tests patterns the project expects.
- Check if you are actually using the installed pytest plugins everywhere you should instead of relying on vanilla test implementations (e.g. pytest_mock instead of unittest mock)
- Check if you did not introduce any test behavior that will be impossible or difficult to test on our CI (Github Actions)
- Check if the test coverage remains at 100% and if not, implement the tests for missing lines.

## Quality checks and linting

- Check if you did not ignore any quality checks by using "# type: ignore", "# noqa" or anything of the sort.
- Make sure you did not added rules to the ignore section in pyproject.toml.
- If you did, remove them and properly fix quality checks and add proper types.
- Before finishing, run pre-commit and fix any issues without trying to ignore the errors.
