# /investigate-deps

- Read pyproject.md
- Read Makefile
- Treat me as an expert.
- ALWAYS read whole files. NEVER just the beginning to get a sense of it.
- If adding a new dependency to the project, ALWAYS find out what is the absolutely latest version and try to use that.
- NEVER try to fix a quality check by ignoring it. If the check is unfixable, think step-py-step why, justify it to me, and ask if you can ignore.
- Completely analize the project, what is currently implemented, the tooling it uses, the patterns it uses.
- Investigate the benefits and come to a conclusion if $ARGUMENTS should be added to the project. Think Harder.
- If you concluded that it is beneficial to add it to the project, formulate a plan to add it and integrate it to the project.
- In your plan you should include where and how you are going to integrate it with the existing parts of the project.
- If the library affects existing tests, NEVER change ANY test intended behavior when integrating the library. Make the test work with it.
