# t1-what-to-test

You will first execute the "Pre Task" and then the "Main Task", which is dependent of you having completed the "Pre Task".
After the "Main Task" is completely done, you should execute the "Post Task" based on the "Main Task" output markdown file.
After the "Post Task" is completely done, you should execute the "Quality Checks".

## Best Practices (EXTRMELY IMPORTANT AND MANDATORY)

- **Async Tests**: All tests should be async, unless we have a very specific reason to make it sync.
- **Thread Tests**: Ensure proper cleanup of threads after tests
- **Isolation**: Each test should be completely isolated and not affect each other
- **Clean Up**: Each test must clean up its context to prevent interference
- **Test Order Independence**: Tests should pass regardless of execution order (use pytest-randomly)
- **Implementation Details**: Tests should verify behaviour, NOT implementation details.
- **Timeout**: Set appropriate timeouts for async and thread tests to prevent hanging
- **External Dependencies**: Decide if these are pure unit tests with no database, network, file I/O, or not.
- **Mocking**: Use conventional testing wisdom to decide what should be mocked and what shouldn't
- **No Side Effects**: Tests should not start actual servers or create log files
- **Clear Assertions**: Each test should have clear, specific assertions
- **Error Messages**: Tests should verify error messages and log outputs
- **Parametrization**: Use pytest.mark.parametrize for similar tests with different inputs
- **Fixtures**: Search for existing or create reusable fixtures for common mocks and settings.
- **Test Organization**: Group related tests in a Class marked with @pytest.mark.unit. All fixtures should go in conftest.py files
- **Test Markers**: All tests must be marked with @pytest.mark.unit decorator
- **No unittest.mock**: Exclusively use pytest_mock fixture, never import unittest.mock
- **Type Safety**: Everything should match the type signatures of the real objects. Mypy and pyright are very strict and will complain.
- **Coverage**: These tests should achieve 100% coverage for the file

## Pre Task

Execute these analyses in parallel:

```
- Fully read and understand pyproject.toml
- Fully read and understand .pre-commit-config.yaml
- Fully read and understand .env.example
- Fully read and understand Makefile
- Fully read and understand every conftest.py fixture we have in the test/ directory
```

Then:

- Think hard and understand $ARGUMENTS, its interaction with the codebase, what it is supposed to do and output your detailed understanding of it.
- Think hard and output your understanding of all existing fixtures.
- Think hard and output your understanding of every best practice in the "Best Practices" section and how you plan to strictly implment them.

## Main Task

Based on your understanding of $ARGUMENTS, define a reasonable set of unit tests that will completely test all of the intended $ARGUMENTS behavior.
By "define", you should output IN WORDS, NOT CODE, what the tests should test and if fixtures and mocks are needed, describe them too.
Each test should follow every best practice outlined in the "Best Practice" section and for eache of them you should plan ahead and output, for each of the tests, how you will implement the best practice.
Save the output in a markdown file in the .specs/testing-reqs folder with a meningful name based on the directory structure from the root of the project and the file name ("full-path-and-name-of-the-file.md, e.g. "src-api-error-handler-py.md).

## Post Task

Read the markdown file from the output of the previous tasks.
Think hard and critique what you did, check for anything missing or any wrong information. Ignore any formating issues, focus on the contents only.
If necessary correct the markdown file.

## Quality Check

Now, you have to think hard and make sure that, for every test defined in the document:

- You found the correct existing fixtures to use OR planned to create the necessary fixtures in a conftest.py
- You did not use any CODE in the specification.
- You were very specific about the usage of pytest_mock instead of unittest.mock for ALL TESTS.
- For each test, you clearly described how each of the items in the "Best Practices" section will be enforced.

## Final Report

You will validate if every single step of this command was executed and make sure you did not skip anything.
Output to the console a complete report of what you did.
