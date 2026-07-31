"""
Adds ingestion/ and dashboard/ to sys.path so tests can import the
project's modules directly (they're not packaged, just plain scripts).
"""

import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(PROJECT_ROOT, "ingestion"))
sys.path.insert(0, os.path.join(PROJECT_ROOT, "dashboard"))
