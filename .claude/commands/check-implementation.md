# /check-implementation

- Fully read pyproject.toml and Makefile
- Check if you did not ignore any quality checks by using "# type: ignore", "# noqa" or anything of the sort. Also make sure you did not added rules to the ignore section in pyproject.toml. If you did, remove them and fix quality checks properly and add proper types.
- Check if you follow the project patterns (not generic code) and properly used the in-place project frameworks like error handling, logging, observability, database, and others the way the project intends you to.
- Check if the tests you implemented meaningful test that actually tests code behavior.
- Check if you implemented the tests following the tests patterns we used in the project.
- Check if you actually consistently used the tests plugins available (e.g. pytest_mock instead of unittest mock) and libraries you are supposed to use instead of implementting generic tests.
- Check if the tests will actually work in the CI environment (Github Actions) or if you introduced any incompatible tests.
- Check if the test coverage is at 100% and if not, implement the tests for missing lines.
- Restrain yourself to check only the uncommited and changed code. No need to check what is already commited.
- Before finishing, run pre-commit and fix any issues without trying to ignore the errors.
- Think Harder
