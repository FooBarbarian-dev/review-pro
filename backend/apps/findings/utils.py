"""
Finding utilities including fingerprint generation (ADR-002).
"""
import hashlib
from typing import Optional


def generate_finding_fingerprint(
    rule_id: str,
    file_path: str,
    start_line: int,
    column: Optional[int],
    message: str
) -> str:
    """
    Generate deterministic fingerprint for finding deduplication (ADR-002).

    Fingerprint = SHA-256(rule_id + file_path + start_line + column + message_hash)

    Args:
        rule_id: Security rule identifier (e.g., "SEC-001")
        file_path: Relative file path where finding was detected
        start_line: Starting line number
        column: Column number (optional)
        message: Finding message/description

    Returns:
        64-character hexadecimal fingerprint string
    """
    # Normalize inputs to ensure consistent fingerprints
    normalized_path = file_path.strip().lower().replace('\\', '/')

    # Create short hash of message to handle variations in wording
    message_hash = hashlib.sha256(message.encode('utf-8')).hexdigest()[:16]

    # Build fingerprint components
    components = [
        rule_id.strip(),
        normalized_path,
        str(start_line),
        str(column or 0),
        message_hash
    ]

    # Generate SHA-256 hash of combined components
    fingerprint_data = '|'.join(components)
    fingerprint = hashlib.sha256(fingerprint_data.encode('utf-8')).hexdigest()

    return fingerprint


def deduplicate_finding(fingerprint: str, organization_id: str):
    """
    Check for existing finding with same fingerprint (ADR-002).

    Only considers findings that are still open or in review.
    Resolved/dismissed findings are not deduplicated against.

    Args:
        fingerprint: The fingerprint to check
        organization_id: Organization UUID to scope search

    Returns:
        Existing Finding object if found, None otherwise
    """
    from apps.findings.models import Finding

    existing = Finding.objects.filter(
        organization_id=organization_id,
        fingerprint=fingerprint,
        status__in=['open', 'in_review']  # Don't dedupe against resolved findings
    ).first()

    return existing


def handle_fingerprint_collision(
    fingerprint: str,
    rule_id: str,
    file_path: str,
    start_line: int,
    message: str
) -> str:
    """
    Handle fingerprint collision by appending a sequence number.

    This is a rare edge case where two different findings have the same fingerprint.

    Args:
        fingerprint: The colliding fingerprint
        rule_id: Rule ID of new finding
        file_path: File path of new finding
        start_line: Line number of new finding
        message: Message of new finding

    Returns:
        Modified fingerprint with sequence suffix
    """
    # Simple collision handling: append counter
    sequence = 1
    new_fingerprint = f"{fingerprint}-{sequence}"

    from apps.findings.models import Finding

    # Keep incrementing until we find a unique fingerprint
    while Finding.objects.filter(fingerprint=new_fingerprint).exists():
        sequence += 1
        new_fingerprint = f"{fingerprint}-{sequence}"

    return new_fingerprint
