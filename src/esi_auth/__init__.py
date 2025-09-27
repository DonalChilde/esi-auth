"""ESI Authentication Library for EVE Online.

A simple library for managing EVE Online ESI authentication tokens.
"""

__version__ = "0.1.0"

import logging

from .logging_config import setup_logging
from .settings import get_settings

setup_logging(log_dir=get_settings().log_dir)
logger = logging.getLogger(__name__)
logger.info("ESI Auth library initialized.")
