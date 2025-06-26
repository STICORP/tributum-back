"""Infrastructure-related constants, particularly for the database."""

# Database constants
POOL_RECYCLE_SECONDS = 3600  # 1 hour
COMMAND_TIMEOUT_SECONDS = 60

# Naming convention for constraints to ensure consistency
# and avoid conflicts during migrations
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}
