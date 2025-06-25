"""Core application constants."""

# Logging and context management
DEFAULT_LOG_MAX_LENGTH = 2000
MAX_ERROR_CONTEXT_LENGTH = 1000
FINGERPRINT_MAX_PARTS = 5
STACK_FRAME_CONTEXT_LINES = 3
MAX_CONTEXT_SIZE = 10000
MAX_CONTEXT_DEPTH = 10
MAX_VALUE_SIZE = 1000
TRUNCATED_SUFFIX = "... [TRUNCATED]"

# Time constants
MILLISECONDS_PER_SECOND = 1000

# Security and redaction
REDACTED = "[REDACTED]"
SENSITIVE_FIELD_PATTERNS = [
    r".*password.*",
    r".*passwd.*",
    r".*pwd.*",
    r".*secret.*",
    r".*token.*",
    r".*key.*",
    r".*auth.*",
    r".*credential.*",
    r".*api[-_]?key.*",
    r".*access[-_]?token.*",
    r".*refresh[-_]?token.*",
    r".*private.*",
    r".*ssn.*",
    r".*social[-_]?security.*",
    r".*credit[-_]?card.*",
    r".*cvv.*",
    r".*pin.*",
    r".*session.*",
    r".*bearer.*",
]
