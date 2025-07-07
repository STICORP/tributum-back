# /t1-fix-implementation

Read and understand the uncommited changes in the git repository, except markdown files.
Below is a mandatory list of validations that should be performed, one-by-one, without exception, in the uncommited git changes (ONLY in the uncmmited git changes).
Before starting the actual validation, output your understanding of each of the items and what you plan to do for each of them.
Make sure that, at the end of the validations, you output a comprehensive report, item-by-item stating your findings and actions performed.

Ultrathink and go through every single item below (1 to 13) and make sure that:

1. You are using pytest_mock EVERYWHERE instead of unittest mocks and there are no imports of unittest.mock
2. Every test that can be async is async and only tests strictly required to be sync for some reason are sync
3. Every test is completely isolated and do not affect each other
4. Everything that should be a fixture is a fixture
5. You used the proper existing fixtures and/or implemented new fixtures.
6. All fixtures are in a conftest.py file and not in the actual test file for reusability
7. You are using parametrize where you should.
8. Everything that should be a mock is a mock and everything that shouldn't, isn't
9. The tests can be executed in any order (pytest-randomly)
10. The tests are verifying behavior and not implementation details.
11. REMOVE every "noqa" and "type: ignore" comments
12. Run make all-checks, as many times as you need, and ONLY IF any problem was found, properly fix the following sub-items:
  12.1. All linting and typing complains WITHOUT using "noqa" and "type: ignore" comments and without adding ignore rules to pyproject.toml
  12.2. Find the root cause of the complains and properly fix them
  12.3. Find the proper types and do not use Any type because mypy will also complain
13. Analyse if your fixes changed any test purpose and behaviour and make sure that it DID NOT.

Your final report should explicitly expose what was done (or not done) for all 13 items in the list above
