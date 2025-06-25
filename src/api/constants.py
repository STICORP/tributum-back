"""API-related constants."""

# HTTP Status Codes
HTTP_200_OK = 200
HTTP_400_BAD_REQUEST = 400
HTTP_401_UNAUTHORIZED = 401
HTTP_404_NOT_FOUND = 404
HTTP_422_UNPROCESSABLE_ENTITY = 422
HTTP_500_INTERNAL_SERVER_ERROR = 500

# Configuration defaults
DEFAULT_API_PORT = 8000

# Request handling
MAX_BODY_SIZE = 10 * 1024  # 10KB
REQUEST_BODY_METHODS = {"POST", "PUT", "PATCH"}
DEFAULT_PAGINATION_LIMIT = 100

# Content types
JSON_CONTENT_TYPES = {"application/json", "text/json"}
FORM_CONTENT_TYPES = {"application/x-www-form-urlencoded", "multipart/form-data"}
TEXT_CONTENT_TYPES = {"text/plain", "text/html", "text/xml", "application/xml"}

# Security
DEFAULT_HSTS_MAX_AGE = 31536000  # 1 year in seconds
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
