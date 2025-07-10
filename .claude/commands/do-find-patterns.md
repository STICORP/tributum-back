# /do-find-patterns

- You will execute the "Tasks" below IN ORDER. EVERY task is dependent on the successful execution of the previous one
- You can only begin the next task when you successfully finished ALL the requirements of the previous task

## Task 0

Execute these analyses in parallel:

```
- Fully read and understand pyproject.toml
- Fully read and understand .pre-commit-config.yaml
- Fully read and understand .env.example
- Fully read and understand Makefile
- Fully read and understand main.py
```

## Task 0

- Clearly describe how you will prevent yourself from hallucinating then discovering, understanding and writing the code and unit tests patterns

## Task 1

- Read and understand the code patterns documented in .specs/patterns/code_patterns.md
- Output your understanding of these code patterns and how they should be used when we implement new code

## Task 2

- Independently investigate src/ directory to discover and understand the project coding patterns
- Output your understanding of the discovered project coding patterns and how they should be used when we implement new code

## Task 3

- Think harder and **SUCCICTLY** modify (add, remove or change) the .specs/patterns/code_patterns.md to be on par with the discovery done in "Task 2"
- The .specs/patterns/code_patterns.md file should succinctly explain (to an LLM) how and when to use code these code patterns and not only contain example source code of the patterns
- Be ECONOMICAL, especially with code examples, because these files will be used as context to the LLM writing the code.

## Task 4

- Read and understand the unit testing patterns documented in .specs/patterns/test_unit_patterns.md
- Output your understanding of these unit testing patterns and how they should be used when we implement new unit tests

## Task 5

- Independently investigate tests/unit/ directory to discover and understand the project unit testing patterns
- Output your understanding of the discovered project unit testing patterns and how they should be used when we implement new unit tests

## Task 6

- Think harder and **SUCCICTLY** modify (add, remove or change) the .specs/patterns/test_unit_patterns.md to be on par with the discovery done in "Task 5"
- The .specs/patterns/test_unit_patterns.md file should succinctly explain (to an LLM) how and when to use code these code patterns and not only contain example source code of the patterns
- Be ECONOMICAL, especially with code examples, because these files will be used as context to the LLM writing the unit tests.

## Task 7

- Think harder and validate the Tasks 0 through 6, make sure you did not forget anything, is working under false assumptions or wrong information/understanding
- If yopu forgot or wrote any wrong information, correct it
