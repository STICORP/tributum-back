# /task-breakdown

This document details MANDATORY steps you have to follow to create a series of sequential tasks that will be used sequentially to implement a functionality in the project.
You have to ultrathink and follow the below instructions and precisely without ignoring anything.

## Document

Read and understand $ARGUMENTS

## Instructions

I need you to write a detailed implementation plan that we can follow. This plan should have a specific format that I will detail to you now. The document above have a lot of requirements, and you have a limited context window to work with, so we will need to constantly clear your context and provide only the context relevant to the current granular task you are actually working on at the moment. Because o your context limitation, we will need to break down this document in a plan with detailed tasks and sub-tasks.

## Context gathering and project specificity

When creating the tasks, it is very important that you be aware that you will be creating code specifically for this project, its architecture and code patterns.
You have analyse the code architecture, patterns, design decisions, in-place frameworks, project configuration, deployment targets, coding standards and anything necessary for you be able to create a plan specifically for the project.
You should not rely on any markdown files for this analysis and analyse only source code for a better understanding of the project.
Do not assume any business value or functionality for this project, trat it as a generic software.

## Tasks requirements

The tasks and subtasks should be granular enough for you to be able accomplish a small objective. A "small objective" is considered "accomplished" only when, after the small task completion, we have:

1. A complete functional system.
2. The whole task is completely tested with 100% coverage.
3. We can commit the code and the whole system is working and without errors.
4. We can deploy the system to production.

## Tasks dependency

When you break down this plan in tasks and subtasks, you have to be extremely careful to make sure that all the tasks can be implemented sequentially an do not introduce a task dependency problem.
A task dependency problem happens when you devise a plan that have tasks/subtasks that cannot be fully completed successfully unless we implement a task that is scheduled to be implemented after the task you should implement.

## Task format

Each task should have:

1. A status
2. Which files you intend to work on
3. A series of steps or functional requirements that you will be able to follow to accomplish the task (written in words, without code examples),
4. A plan to test thorougly and meaningfully
5. An acceptance criteria that will indicate to you that the task is done. When creating the tasks, it is very important that you be aware that you will be creating code specifically for this project, its architecture and code patterns, so plan the tasks accordingly. You

## Output

You will create a directory inside .specs/ and save your plan using multiple markdown files.
Each file will be a major task with sequential series of subtasks and should include all the project context necessary for you to accomplish each task sequentially.
