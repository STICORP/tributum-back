# /task-breakdown

Think Harder

This document details **MANDATORY** steps you have to follow to create a series of sequential tasks with granular sub-tasks that will be used sequentially to implement a feature in the project.
You have to follow the below instructions and precisely without ignoring anything.

## Document

Read and understand the requirements in $ARGUMENTS

## Instructions

Write a detailed implementation plan that can be followed by an LLM. This plan should have a specific format that will be detailed below. The requirements in $ARGUMENTS represent a feature that should be implemented, and you have a limited context window to work with, so you will need to constantly clear your context and be able to re-discover all the context relevant to the current task you are actually working on at the moment. Because o your context limitation, you will need to break down the requirements in $ARGUMENTS in a plan with detailed tasks and sub-tasks.

## Context gathering and project specificity

**YOU MUST** when create the tasks specifically for this project, its architecture and code patterns. **NO GUESSING**, **NO HALLUCINATIONS**
**YOU MUST** discover and analyse:
1. The code architecture
2. Code patterns
3. Design decisions
4. In-place frameworks
5. Project configuration
6. Deployment targets
7. Coding standards
8. Development environment
9. Testing standards
10. Anything else that might be necessary for you be able to create a plan that is **NOT GENERIC**, **DOES NOT CONTAIN HALLUCINATIONS** and is **DEVISED SPECIFICALLY FOR THIS PROJECT**
**DO NOT** rely on any markdown files you find in the project for this analysis
**YOU MUST** analyse only source code for a better understanding of the project.
**DO NOT** assume any business value or functionality for this project, treat it as a generic software.

## Tasks requirements

The tasks and subtasks should be **GRANULAR** enough for you to be able accomplish a small objective. A "small objective" is considered "accomplished" only when, after the small task completion, we have:

1. A complete functional system.
2. The whole task is completely tested with 100% coverage.
3. We can commit the code and the whole system is working and without errors.
4. We can deploy the system to production.

## Tasks dependency

When you break down the requirements in $ARGUMENTS into tasks and sub-tasks, you have to be extremely careful to make sure that all the tasks can be implemented sequentially and you **CANNOT** introduce a task dependency problem.
A task dependency problem happens when you devise a plan with a series of tasks and sub-tasks where a tasks/sub-task that cannot be fully completed successfully unless we implement a task/sub-task that is scheduled to be implemented after that task/sub-task.

## Task file format

A task file should be a markdown document that containing all the instructions necessary to implement a feature. It should contain:

1. The complete project context necessary to accomplish the task. (file pointers, code integration, how to use existing code, how to use and respect other implemented frameworks, etc)
2. A series of extremely granular sub-tasks that should be implemented sequentially to successfully implement the functionality.

## Subtask format

Each sub-task should have:

1. A status indicating if it is already done.
2. Which files you intend to work on
3. A series of steps or functional requirements that an LLM will be able to follow to accomplish the task.
4. The series of steps **MUST** be written words and contain **NO CODE IMPLEMENTATION**
5. A plan to test thorougly and meaningfully using the test patterns and standards of the projecte.
6. An acceptance criteria that will indicate to you that the task is done.

## Output

You will create a directory (with a meaningful name according to the requirements in $ARGUMENTS) inside .specs/ and save your splitted into multiple markdown files.
Each markdown file will be a major task with sequential series of sub-tasks and should include all the project context necessary for you to accomplish each sub-task sequentially.
