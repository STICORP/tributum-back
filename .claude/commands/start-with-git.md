# /start-with-git

Follow the below steps sequentially. Only start a step after the previous step finished so you have the nexessary context for the next step.

## Step 1

Execute these analyses in parallel:

```
- Fully read and understand pyproject.toml
- Fully read and understand .pre-commit-config.yaml
- Fully read and understand .env.example
- Fully read and understand Makefile
- Fully read and understand main.py
- Fully read and understand /src/core/config.py
- Fully read and understand /src/api/main.py
- Fully read and understand any conftest.py file in the tests/
```

## Step 2

- Think harder, read and understand and especially **CRITIQUE ALL UNCOMMITED CHANGES** in the git repository.
- Ignore any markdown files, we are interested only on code changes.

## Step 3

- Think harder, read and understand all parts of the codebase that is affected, enhanced or modified by the changes.

## Step 4

- Think harder and assess if the uncommited code is correctly using the existing codebase, it's architecture, patterns, code organization and structure.
- Think harder and assess if the uncommited code chose to prefer extending existing patterns or if it introduced too many dependencies or files.
- Think harder and assess if the uncommited code is implementing some unusual hack to half-solve or bypass a problem instead of the actual best practice for the existing codebase or third party library interaction.
- Think harder and assess if the implemented code follows best practices, specially when using or interacting third party libraries (research best practices on using the libraries if you need).

## Step 5

- Output a point-by-point analysis in a markdown document with recomendations on how to proceed
