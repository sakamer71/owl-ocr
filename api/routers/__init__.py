"""
Router module initialization.

This file ensures proper module exports for FastAPI router registration.
"""

try:
    from . import process, jobs
except ImportError:
    # For direct imports
    import process
    import jobs