# /check-implementation

- Fully read pyproject.toml and Makefile
- Check if you did not ignore any quality checks. Fix them properly.
- Check if you follow the project patterns (not generic code) and properly used the in-place project frameworks the way the project intends you to.
- Check if the tests you implemented meaningful test that actually tests code behavior.
- Check if you implemented the tests following the tests patterns we used in the project.
- Check if you actually used the tests plugins and libraries you are supposed to use instead of implementting generic tests.
- Check if the tests will actually work in the CI environment (Github Actions)
- Check if the test coverage is at 100% and if not, implement the tests for missing lines.
- Before finishing, run pre-commit and fix any issues without trying to ignore the errors.
- Think Harder
