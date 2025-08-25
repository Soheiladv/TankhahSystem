import logging
from django.db import connection, ProgrammingError

logger = logging.getLogger(__name__)


def _load_status_codes_from_db():
    """
    #BEST_PRACTICE: A private function to load status codes, running only once
    when this module is first imported. It's robust against migration errors.
    """
    logger.info("Attempting to load status codes from database for constants module...")

    # KNOWLEDGE_BIT: We must verify table existence to prevent crashes during
    # the `makemigrations` command before the 'core_status' table is created.
    table_name = 'core_status'  # Default Django naming: appname_modelname
    try:
        with connection.cursor() as cursor:
            all_tables = connection.introspection.table_names(cursor)
    except Exception:
        # This can happen if DB is not configured yet.
        logger.warning("Could not connect to DB to check for status table. Skipping.")
        return {}

    if table_name not in all_tables:
        logger.warning(
            f"Table '{table_name}' not found. Skipping status code loading. (This is normal during initial migrations)")
        return {}

    try:
        # This import is safe here because we've confirmed the table exists.
        from core.models import Status
        statuses = Status.objects.filter(is_active=True).values_list('code', flat=True)
        # Sanitize codes to be valid Python attribute names (e.g., 'PENDING-APPROVAL' -> 'PENDING_APPROVAL')
        status_map = {code.upper().replace('-', '_'): code for code in statuses}
        logger.info(f"Successfully loaded {len(status_map)} status codes into constants module.")
        return status_map
    except ProgrammingError as e:
        logger.warning(f"Database ProgrammingError while loading status codes. Skipping. Error: {e}")
        return {}
    except Exception as e:
        logger.error(f"An unexpected error occurred while loading status codes: {e}", exc_info=True)
        return {}


# ===== THE SINGLE SOURCE OF TRUTH (Module-level execution) =====

# This code runs ONCE when the module is first imported. The result is cached by Python's module system.
_STATUS_MAP = _load_status_codes_from_db()


class StatusCodes:
    """
    A simple, dynamic class providing access to status codes as attributes.
    This approach is lightweight, efficient, and leverages Python's module caching.
    """

    def __getattr__(self, name):
        """
        Dynamically retrieves the original status code string from the loaded map.
        Example: `STATUSES.PAID` will look for 'PAID' in `_STATUS_MAP` and return its value (e.g., 'PAID').
        """
        if name in _STATUS_MAP:
            return _STATUS_MAP[name]

        logger.error(
            f"FATAL: Accessed a non-existent or inactive status code: '{name}'. Please check the 'core_status' table in your database.")
        # In a production system, you might want to raise an Exception here.
        # For now, returning None to prevent crashes, but the error log is critical.
        return None


# The single instance you will import and use everywhere. It's clean and simple.
STATUSES = StatusCodes()

# Derived constants are defined directly here, making them easy to find and manage.
COMMITTED_FACTOR_STATUSES = [
    STATUSES.PENDING_APPROVAL,
    STATUSES.APPROVED,
    # Add other "committed" statuses here if needed
]
# Filter out None values to make the list safe for '__in' lookups.
COMMITTED_FACTOR_STATUSES = [s for s in COMMITTED_FACTOR_STATUSES if s]
