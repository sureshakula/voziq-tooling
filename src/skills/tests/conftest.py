# ===================AIPASS====================
# META DATA HEADER
# Name: conftest.py - Skills test configuration
# Date: 2026-03-07
# Version: 1.0.0
# Category: skills/tests
#
# CHANGELOG (Max 5 entries):
#   - v1.0.0 (2026-03-07): Initial implementation
#
# CODE STANDARDS:
#   - Adds skills root to sys.path for test imports
# =============================================

"""Skills test configuration."""

import sys
from pathlib import Path

# Add skills root to path for imports
skills_root = Path(__file__).parent.parent
if str(skills_root) not in sys.path:
    sys.path.insert(0, str(skills_root))
