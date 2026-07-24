"""Shared slowapi rate limiter, keyed by client IP.

Wired into the FastAPI app in ``main.py`` and applied to sensitive routes
(e.g. ``/api/v1/auth/login``) via the ``@limiter.limit(...)`` decorator.
"""

from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
