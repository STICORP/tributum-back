# /do

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

## Task 1

- Investigate src/ directory to understand the project coding patterns that are relevant for the implementation of $ARGUMENTS
- Output your understanding of the discovered project patterns and how you intend to use them when implementing the code for $ARGUMENTS
- Output the details on how you are going to use the discovered patterns instead of conflicting code examples found in $ARGUMENTS

## Task 2

- Investigate the tests/unit/ directory to understand the patterns we use when implementing unit tests for our implemented code
- Output your understanding of the discovered unit testing patterns and how you intend to use them when implementing the unit tests for the implemented $ARGUMENTS code

## Task 3

- Clearly describe your strategy for the separation of concernes of the code that is going to be implemented based on your understanding of the codebase
- Clearly describe your strategy for properly implementing proper types for type hinting, and prevent "type: ignore" and the usage of the "Any" type, to abide to our strict mypy rules
- Clearly describe your strategy for understanding and implement code that will perfectly conform to out strict linting rules

## Task 4

- Clearly describe how you will prevent yourself to hallucinate and implement more than what is required by $ARGUMENTS

## Task 5

- Think harder and validate the Tasks 1 through 4, make sure you did not forget anything, is working under false assumptions or wrong information/understanding

## Task 6

- Begin the implementation of $ARGUMENTS making sure you strictly follow everything you output in the previous tasks
