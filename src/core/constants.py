"""Core constants used throughout the application."""

# HTTP Status Codes
HTTP_200_OK = 200
HTTP_400_BAD_REQUEST = 400
HTTP_401_UNAUTHORIZED = 401
HTTP_404_NOT_FOUND = 404
HTTP_422_UNPROCESSABLE_ENTITY = 422
HTTP_500_INTERNAL_SERVER_ERROR = 500

# Configuration defaults
DEFAULT_API_PORT = 8000
DEFAULT_LOG_MAX_LENGTH = 2000

# Limits and thresholds
MAX_ERROR_CONTEXT_LENGTH = 1000
FINGERPRINT_MAX_PARTS = 5
STACK_FRAME_CONTEXT_LINES = 3

# Request logging
MAX_BODY_SIZE = 10 * 1024  # 10KB
REQUEST_BODY_METHODS = {"POST", "PUT", "PATCH"}

# Time constants
MILLISECONDS_PER_SECOND = 1000

# Logging and context management
MAX_CONTEXT_SIZE = 10000
MAX_CONTEXT_DEPTH = 10
MAX_VALUE_SIZE = 1000
TRUNCATED_SUFFIX = "... [TRUNCATED]"

# Content types
JSON_CONTENT_TYPES = {"application/json", "text/json"}
FORM_CONTENT_TYPES = {"application/x-www-form-urlencoded", "multipart/form-data"}
TEXT_CONTENT_TYPES = {"text/plain", "text/html", "text/xml", "application/xml"}

# Security constants
REDACTED = "[REDACTED]"
DEFAULT_HSTS_MAX_AGE = 31536000  # 1 year in seconds

# Sensitive headers (unified set)
SENSITIVE_HEADERS = {
    "authorization",
    "cookie",
    "x-api-key",
    "x-auth-token",
    "x-csrf-token",
    "set-cookie",
    "x-secret-key",
    "proxy-authorization",
}

# Sensitive field patterns for redaction
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

# Database constants
POOL_RECYCLE_SECONDS = 3600  # 1 hour
COMMAND_TIMEOUT_SECONDS = 60
DEFAULT_PAGINATION_LIMIT = 100
