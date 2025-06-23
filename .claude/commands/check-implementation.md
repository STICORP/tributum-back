# /check-implementation

- Think Harder
- **IMPORTANT AND MANDATORY** All the validations below are to be conducted only on uncommited and changed code. **DO NOT** validate what is already commited.

## Understand the project

- Fully read pyproject.toml
- Fully read Makefile
- Fully read .pre-commit-config.yaml
- Fully read main.py
- Fully read /src/core/config.py
- Fully read /src/api/main.py

## Dependencies

- If you added any new dependency to the project, make sure you added the absolutely latest version of that library that is supported by our project.

## Configuration management

- Check if you added, removed or changed any project configuration.
- Check if you were consistent and are using configuration the way that the project expects you to.
- Check if the configuration follows the established project patterns and you properly used the project configuration framework.
- Check that, if you added, removed or changed and configuration, you did **EVERYWHERE** it is required and maintained configuration consistency

## Error handling

- Check if properly **handled errors** where it needs to be handled.
- Check if you **handled errors** in the way the project expects you to.
- Check if you properly used the **error handling framework** and patterns implemented by the project.

## Logging

- Check if you implemented **logging** where it is required by best practices.
- Check if your implementation of **logging** was done in the way the project expects you to.
- Check if you properly used the **logging framework** and patterns implemented by the project.

## Logging

- Check if you implemented **observability** where it is required by best practices.
- Check if your implementation of **observability** was done in the way the project expects you to.
- Check if you properly used the **observability framework** and patterns implemented by the project.

## Database interaction

- Check if your implementation of **database interaction** was done in the way the project expects you to.
- Check if you properly used the **database framework** and patterns implemented by the project.

## FastAPI

- If, **AND ONLY IF** you implemented code directly related to FastAPI, read .specs/fastapi_best_practices.md and make sure we do not violate any of these practices.

## Tests implementation

- Check if the tests you implemented meaningful test that actually tests code behavior.
- Check other test files to verify that you are being consistent on how you implemented the tests and are actually following the tests patterns the project expects.
- Check if you are actually using the installed pytest plugins everywhere you should instead of relying on vanilla test implementations (e.g. pytest_mock instead of unittest mock)
- Check if you did not introduce any test behavior that will be impossible or difficult to test on our CI (Github Actions)
- Check if the test coverage remains at 100% and if not, implement the tests for missing lines.

## Docker implementation

- Check if what we implemented needs to be integrated with our docker implementation
- Check if we need to change Dockerfiles, docker-compose files
- Check if we introduced configuration that should be integrated in docker
- Check if we introduced or changed anything that will require that we change anything anywhere in our docker implementation

## Other files

- Do our implementation requires we add, remove or modify anything from Makefile
- Do our implementation requires we add, remove or modify anything from our Pre-Commit
- Do our implementation requires we add, remove or modify anything from Github Actions

## Quality checks and linting

- Check if you did not ignore any quality checks by using "# type: ignore", "# noqa" or anything of the sort.
- Make sure you did not added rules to the ignore section in pyproject.toml.
- If you did, remove them and properly fix quality checks and add proper types.
- Before finishing, run pre-commit and fix any issues without trying to ignore the errors.
