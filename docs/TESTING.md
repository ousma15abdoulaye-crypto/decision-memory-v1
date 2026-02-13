# Testing Guide - Decision Memory System

## Overview

This document describes how to run tests and measure code coverage for the Decision Memory System (DMS).

## Prerequisites

1. **Python 3.11+** installed
2. **PostgreSQL** database running (or use Docker Compose)
3. **Dependencies** installed:
   ```bash
   pip install -r requirements.txt
   ```

## Database Setup

### Option 1: Using Docker Compose (Recommended)

```bash
# Start PostgreSQL container
docker compose up -d

# Wait for database to be ready
sleep 5

# Run migrations
export DATABASE_URL="postgresql+psycopg://dms:dms@localhost:5432/dms"
alembic upgrade head
```

### Option 2: Using Existing PostgreSQL

```bash
# Set your database URL
export DATABASE_URL="postgresql+psycopg://username:password@localhost:5432/dbname"

# Run migrations
alembic upgrade head
```

## Running Tests

### Run All Tests

```bash
# Set environment variables
export DATABASE_URL="postgresql+psycopg://dms:dms@localhost:5432/dms"
export TESTING="true"

# Run all tests with verbose output
pytest tests/ -v
```

### Run Specific Test Files

```bash
# Run upload tests only
pytest tests/test_upload.py -v

# Run security tests only
pytest tests/test_upload_security.py -v

# Run authentication tests
pytest tests/test_auth.py -v
```

### Run Individual Tests

```bash
# Run a specific test by name
pytest tests/test_upload.py::test_upload_dao_success -v
```

### Run with Short Traceback

```bash
# Useful for quick debugging
pytest tests/ -v --tb=short
```

## Code Coverage

### Measure Coverage on All Code

```bash
# Generate coverage report with missing lines
pytest --cov=src --cov-report=term-missing tests/

# Generate HTML coverage report
pytest --cov=src --cov-report=html tests/

# View HTML report (opens in browser)
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
```

### Coverage on Specific Modules

```bash
# Coverage for auth module only
pytest --cov=src/auth --cov-report=term-missing tests/

# Coverage for upload security
pytest --cov=src/upload_security --cov-report=term-missing tests/

# Coverage for Couche A routers
pytest --cov=src/couche_a/routers --cov-report=term-missing tests/
```

## Current Test Status

As of **February 13, 2026**:

- **Total Tests**: 51
- **Passing**: 48 (94%)
- **Skipped**: 3
  - `test_upload_offer_with_lot_id` - Lots table not yet implemented (planned for M3A)
  - `test_rate_limit_upload` - Original test replaced with `test_rate_limit_upload_real`
  - 1 smoke test (marked as skip)

### Coverage Metrics (Critical Modules)

| Module | Coverage | Target | Status |
|--------|----------|--------|--------|
| `src/auth.py` | 81% | ≥60% | ✅ PASS |
| `src/upload_security.py` | 94% | ≥70% | ✅ PASS |
| `src/couche_a/routers.py` | 87% | ≥40% | ✅ PASS |
| **Overall** | **57%** | ≥40% | ✅ PASS |

## Test Categories

### 1. Authentication Tests (`test_auth.py`)
- User registration
- Login/logout
- Token validation
- Role-based access control

### 2. Upload Tests (`test_upload.py`)
- DAO upload workflow
- Offer upload workflow
- Duplicate detection
- Lot validation (skipped - future feature)

### 3. Security Tests (`test_upload_security.py`)
- File size limits (50MB per file)
- MIME type validation
- Filename sanitization (path traversal prevention)
- Rate limiting configuration
- SQL injection prevention
- Quota enforcement

### 4. RBAC Tests (`test_rbac.py`)
- Role permissions
- Ownership checks
- Admin bypass rules

### 5. Resilience Tests (`test_resilience.py`)
- Circuit breaker patterns
- Retry mechanisms
- Failure handling

### 6. Template Tests (`test_templates.py`)
- Template rendering
- Data validation

## Known Limitations

### Rate Limiting in Tests

Rate limiting is **disabled** in `TESTING` mode to avoid flaky tests. The `test_rate_limit_upload_real` test verifies that rate limiting is properly configured by:

1. Checking that `TESTING` mode is enabled during tests
2. Verifying rate limit decorators exist on critical endpoints
3. Ensuring the limiter is properly initialized

**Note**: Actual rate limiting behavior should be tested in integration/staging environments where `TESTING=false`.

### Skipped Tests

Some tests are temporarily skipped for valid reasons:

- **Lots feature**: Not yet implemented (migration planned for M3A milestone)
- **Legacy tests**: Being replaced with improved versions

## Continuous Integration

The CI pipeline automatically runs:

```bash
# Install dependencies
pip install -r requirements.txt

# Start PostgreSQL (via GitHub Actions services)
# DATABASE_URL is set automatically

# Run migrations
alembic upgrade head

# Run tests with coverage
pytest --cov=src --cov-report=term --cov-report=xml tests/

# Verify critical module coverage thresholds
```

## Troubleshooting

### Database Connection Errors

```bash
# Verify PostgreSQL is running
docker ps

# Check database URL is set
echo $DATABASE_URL

# Test database connection
psql $DATABASE_URL -c "SELECT 1"
```

### Import Errors

```bash
# Make sure you're in the project root
cd /path/to/decision-memory-v1

# Verify Python path
python -c "import sys; print(sys.path)"
```

### Test Failures

```bash
# Run with detailed output
pytest tests/failing_test.py -vv

# Run with full traceback
pytest tests/failing_test.py --tb=long

# Run with PDB debugger on failure
pytest tests/failing_test.py --pdb
```

## Best Practices

1. **Always set TESTING=true** when running tests to disable rate limiting
2. **Use fixtures** for test data setup (see `tests/test_upload.py` for examples)
3. **Clean up test data** in teardown methods or use database transactions
4. **Run tests before committing** to ensure changes don't break existing functionality
5. **Maintain coverage** above critical thresholds (≥60% for auth, ≥70% for security)

## Adding New Tests

### Example: Adding an Auth Test

```python
# tests/test_auth.py

def test_token_expiration():
    """Test JWT token expiration handling."""
    from src.auth import create_access_token, decode_token
    from datetime import datetime, timedelta
    import pytest
    from fastapi import HTTPException
    
    # Create expired token
    payload = {
        "sub": "test@example.com",
        "exp": datetime.utcnow() - timedelta(hours=1)
    }
    token = create_access_token(payload)
    
    # Should raise exception
    with pytest.raises(HTTPException):
        decode_token(token)
```

### Example: Adding a Security Test

```python
# tests/test_upload_security.py

def test_filename_sanitization():
    """Test path traversal attack prevention."""
    from src.upload_security import sanitize_filename
    
    dangerous = "../../etc/passwd"
    safe = sanitize_filename(dangerous)
    
    assert ".." not in safe
    assert "/" not in safe
```

## References

- [pytest Documentation](https://docs.pytest.org/)
- [pytest-cov Documentation](https://pytest-cov.readthedocs.io/)
- [FastAPI Testing Guide](https://fastapi.tiangolo.com/tutorial/testing/)
- [Constitution V3](./CONSTITUTION_V3.md) - DMS Testing Requirements
