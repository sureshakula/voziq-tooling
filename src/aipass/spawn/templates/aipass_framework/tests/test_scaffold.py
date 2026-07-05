# =================== META ====================
# Name: test_scaffold.py
# Description: Scaffold smoke test for template test infrastructure
# Version: 1.0.0
# Created: 2026-07-04
# Modified: 2026-07-04
# =============================================

"""Scaffold smoke test — proves pytest infrastructure works in this branch."""


def test_conftest_fixtures_available(temp_test_dir, sample_test_data):
    """Verify conftest fixtures are wired and return expected types."""
    assert temp_test_dir.exists()
    assert isinstance(sample_test_data, dict)
