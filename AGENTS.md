# AGENTS.md

This file provides guidance for agentic coding agents working with the keiba (競馬データ収集システム) codebase.

## Build/Lint/Test Commands

### Environment Setup
```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
```

### Testing Commands
```bash
# Run all tests with coverage
pytest tests/ -v --cov=keiba --cov-report=term-missing

# Run single test file
pytest tests/test_scrapers.py -v

# Run single test method
pytest tests/test_scrapers.py::TestBaseScraperInit::test_default_delay -v

# Run tests for specific module
pytest tests/ml/ -v
pytest tests/backtest/ -v
```

### Code Quality
```bash
# No specific linting commands configured in pyproject.toml
# Use standard Python formatting tools if needed:
# black keiba/
# isort keiba/
# flake8 keiba/
```

## Code Style Guidelines

### Import Organization
- Standard library imports first (e.g., `import calendar`, `import time`)
- Third-party imports next (e.g., `import click`, `import requests`)
- Local imports last (e.g., `from keiba.db import get_engine`)
- Group imports by type with blank lines between groups
- Use explicit imports over `from module import *`

### Type Annotations
- Use Python 3.10+ type hints (e.g., `str | None` instead of `Optional[str]`)
- All function parameters and return types should be typed
- Class attributes should be typed where appropriate
- Use `from typing import` only when necessary for complex types

### Naming Conventions
- **Classes**: PascalCase (e.g., `BaseScraper`, `RaceDetailScraper`)
- **Functions/Methods**: snake_case (e.g., `extract_race_id_from_url`)
- **Variables**: snake_case (e.g., `last_request_time`, `user_agent`)
- **Constants**: UPPER_SNAKE_CASE (e.g., `DEFAULT_USER_AGENT`, `VENUE_CODE_MAP`)
- **Private members**: prefix with underscore (e.g., `_last_request_time`, `_apply_delay`)

### Error Handling
- Use specific exception types (e.g., `requests.HTTPError`, `ValueError`)
- Include descriptive error messages with context
- Raise exceptions with clear explanations of what went wrong
- Use `raise_for_status()` for HTTP requests to handle bad responses

### Documentation Style
- Use docstrings for all classes and public methods
- Follow Google-style or NumPy-style docstring format
- Include Args, Returns, and Raises sections where applicable
- Provide usage examples in docstrings for complex classes
- Use Japanese for user-facing descriptions, English for technical comments

### Class Design Patterns
- Use composition over inheritance where appropriate
- Base classes should provide common functionality (e.g., `BaseScraper`)
- Implement abstract methods with `raise NotImplementedError`
- Use `@property` decorators for computed attributes
- Include `__init__` method docstrings with parameter descriptions

### Database Patterns
- Use SQLAlchemy 2.0 style with `DeclarativeBase`
- All models inherit from `Base` class in `keiba.models.base`
- Use session context managers for database operations
- Separate model definitions from business logic

### Web Scraping Patterns
- All scrapers inherit from `BaseScraper`
- Implement rate limiting with delay between requests
- Handle encoding properly (netkeiba.com uses EUC-JP)
- Use appropriate User-Agent headers
- Parse HTML with BeautifulSoup and lxml parser

### Testing Patterns
- Use descriptive test class names (e.g., `TestBaseScraperInit`)
- Test one thing per test method with clear names
- Use pytest fixtures for setup/teardown
- Mock external dependencies (HTTP requests, database)
- Include both positive and negative test cases

### Project Structure
- `keiba/scrapers/` - Web scraping modules
- `keiba/models/` - SQLAlchemy data models
- `keiba/ml/` - Machine learning components
- `keiba/analyzers/` - Data analysis modules
- `keiba/backtest/` - Backtesting functionality
- `keiba/services/` - Business logic services
- `keiba/config/` - Configuration constants
- `tests/` - Test modules mirroring source structure

### CLI Design
- Use click for CLI interface
- Group related commands under click groups
- Provide helpful error messages for invalid input
- Use `--help` text that explains command purpose and options
- Support both required and optional parameters with sensible defaults

### Constants and Configuration
- Define constants in appropriate modules (e.g., `keiba.constants`)
- Use dictionaries for mappings (e.g., venue codes)
- Keep configuration separate from business logic
- Use environment variables for sensitive data when needed

### ML and Data Processing
- Use scikit-learn and lightgbm for machine learning
- Separate feature building from model training
- Use joblib for model serialization
- Implement proper data splitting to prevent leakage
- Handle missing data gracefully in preprocessing