"""Proxy — INV-F06 dashboard tests.

The actual tests live in tests/unit/test_dashboard.py to avoid
the integration conftest that requires a live DB connection.
This file re-exports them for the CI pipeline path
`pytest tests/integration/test_dashboard.py -v`.
"""

from tests.unit.test_dashboard import *  # noqa: F401, F403
