# /refactor-tests

## Pre Task

- Find all conftest.py in the tests/ directory, read and understand them

## Task

Regarding $ARGUMENTS, think harder and validate the following:

- Are we following the tests patterns established by the codebase properly?
- Are we properly using fixtures the way we are supposed to?
- Do yuo need to create new fixtures? You can.
- Are we mocking what we should and not mocking what we shouldn't?
- Are the tests isolated and independent? They should be.
- The tests should not include implementation details. Do they?
- Are the tests deterministic? They should be.

Assess and properly fix everything that should be fixed.
Do not use "noqa" or "type: ignore". Properly find the root cause of the problems.
Find and use the proper types and not "Any" because mypy will complain anyway.
