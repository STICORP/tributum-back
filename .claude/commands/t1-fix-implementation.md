# /t1-fix-implementation

Below is a mandatory list of validations that should be performed, one-by-one, without exception.
Before starting the actual validation, output your understanding of each of the items and what you plan to do for each of them.
Make sure that, at the end of the validations, you output a comprehensive report, item-by-item stating your findings and actions performed.

Ultrathink and make sure that:

- You are using pytest_mock EVERYWHERE instead of unittest mocks and there are no imports of unittest.mock
- Every test that can be async is async and only tests strictly required to be sync for some reason are sync
- Every test is completely isolated and do not affect each other
- Everything that should be a fixture is a fixture
- You used the proper existing fixtures and/or implemented new fixtures.
- All fixtures are in a conftest.py file and not in the actual test file for reusability
- You are using parametrize where you should.
- Everything that should be a mock is a mock and everything that shouldn't, isn't
- The tests can be executed in any order (pytest-randomly)
- The tests are verifying behavior and not implementation details.
- REMOVE every "noqa" and "type: ignore" comments
- Run make all-checks, as many times as you need, and if any problem was found, properly fix all of them:
  - All linting and typing complains WITHOUT using "noqa" and "type: ignore" comments and without adding ignore rules to pyproject.toml
  - Find the root cause of the complains and properly fix them
  - Find the proper types and do not use Any type because mypy will also complain
- Analyse if your fixes changed any test purpose and behaviour and make sure that it DID NOT.
