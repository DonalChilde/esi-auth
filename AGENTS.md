---
description: "Python coding conventions and guidelines"
applyTo: "**/*.py"
project-name: "esi-auth"
---

# Python Coding Conventions

## Python Instructions

- Write clear and concise comments for each function.
- Ensure functions have descriptive names and include type hints.
- Provide docstrings following PEP 257 conventions.
- Break down complex functions into smaller, more manageable functions.
- During development, use the virtual environment found at the project root - `./.venv`

## General Instructions

- Always prioritize readability and clarity.
- For algorithm-related code, include explanations of the approach used.
- Write code with good maintainability practices, including comments on why certain design decisions were made.
- Handle edge cases and write clear exception handling.
- For libraries or external dependencies, mention their usage and purpose in comments.
- Use consistent naming conventions and follow language-specific best practices.
- Write concise, efficient, and idiomatic code that is also easily understandable.

## Code Style and Formatting

- Follow the **PEP 8** style guide for Python.
- Maintain proper indentation (use 4 spaces for each level of indentation).
- Prefer lines do not exceed 88 characters.
- Use blank lines to separate functions, classes, and code blocks where appropriate.
- Code will be formatted and linted using ruff. The configuration is located in the `pyproject.toml`.

## Edge Cases and Testing

- Always include test cases for critical paths of the application.
- Account for common edge cases like empty inputs, invalid data types, and large datasets.
- Include comments for edge cases and the expected behavior in those cases.
- Write unit tests for functions and document them with docstrings explaining the test cases.

## Documentation

- Ensure all public functions and classes have appropriate docstrings.
- Use Google style docstrings.
- Include examples in docstrings where applicable.
- Classes with an `__init__` function should have the docstring after that `__init__` function.
- Classes without an `__init__` function should have the docstring immediately following the class definition.

# Project Specific Information

## Project Overview

esi-auth manages obtaining, storing, and refreshing authentication tokens for the Eve Online ESI api.

- Application settings are managed by pydantic-settings.
- The application directory can be set through environment variables, and defaults to the directory provided by `typer.get_app_dir("pfmsoft-esi-auth")`
- client id and secret used for authentication is located in an env file loaded by pydantic settings.
- A testing-only client id and secret will be loaded from a testing only application settings profile.
- the user must provide their own client id and secret obtained from the EVE Online Developers Portal
- Tokens and related metadata are stored in a json file located in the application directory. This file is loaded and saved through a pydantic.BaseModel
- The cli uses typer. The cli entry point is located at `esi_auth.cli.main_typer.py` and each group of commands is in a separate `.py` file located in the `esi_auth.cli` package.
- the cli has commands that can:
  - list authenticated characters, with token expiration data.
  - authenticate a character_id to a list of scopes provided as a json-serialized string, or loaded from a json file.
  - refresh a character_id token
  - do a simple proof of authentication by retrieving character data and printing it to terminal.
  - remove a character_id from the collection of authenticated characters.
- esi-auth exposes the following api:
  - load_characters -> loads the authenticated characters from file, and returns the pydantic.BaseModel containing the data.
  - refresh_token -> refreshes the token for one character_id
  - authenticate character -> authenticate one character_id for a list of scopes.
  - remove_character -> remove a character_id from collection of authenticated characters.
- html templates use Jinja2
- data models are collected in a `models.py` file

## Project Dependencies

- aiohttp is used to make network requests
- Jinja2 is used to manage html templates
- pydantic is used to serialize and validate application data
- pydantic-settings is ued to manage application settings.
- typer is used to provide the cli interface
- whenever is used to interact with datetimes

## Conventions

- test files are located in `tests/esi_auth/`, and the test file layout mirrors the src file layout when possible.
