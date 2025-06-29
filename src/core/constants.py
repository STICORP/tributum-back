"""Core application constants."""

# Time constants
MILLISECONDS_PER_SECOND = 1000

# Security and redaction
REDACTED = "[REDACTED]"
# Note: SENSITIVE_FIELD_PATTERNS will be replaced with a simpler regex in Phase 4
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
