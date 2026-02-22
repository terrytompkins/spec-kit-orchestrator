"""Secret masking utilities for logs and UI displays."""

import re
from typing import List, Optional


def mask_secrets(text: str, secrets: Optional[List[str]] = None) -> str:
    """
    Mask secrets in text by replacing them with [REDACTED].
    
    Args:
        text: Text that may contain secrets
        secrets: Optional list of specific secrets to mask. If None, uses
                 common secret patterns (tokens, API keys, etc.)
    
    Returns:
        Text with secrets masked
    """
    if not text:
        return text
    
    masked = text
    
    # If specific secrets provided, mask them
    if secrets:
        for secret in secrets:
            if secret:  # Skip empty strings
                masked = masked.replace(secret, '[REDACTED]')
    
    # Also mask common secret patterns
    # GitHub tokens (ghp_*)
    masked = re.sub(r'ghp_[A-Za-z0-9]{36,}', '[REDACTED]', masked)
    
    # Generic tokens (token: * or TOKEN=*)
    masked = re.sub(r'(?i)(token|api[_-]?key|secret|password)\s*[:=]\s*[\'"]([^\'"]+)[\'"]', 
                   r'\1: [REDACTED]', masked)
    
    # API keys (sk-*, pk_*, etc.)
    masked = re.sub(r'(sk|pk|AKIA)[_-]?[A-Za-z0-9]{20,}', '[REDACTED]', masked)
    
    # Bearer tokens
    masked = re.sub(r'Bearer\s+[A-Za-z0-9\-._~+/]+=*', 'Bearer [REDACTED]', masked)
    
    return masked


def mask_in_logs(log_content: str, secrets: Optional[List[str]] = None) -> str:
    """
    Mask secrets in log content.
    
    Alias for mask_secrets for clarity in log processing contexts.
    
    Args:
        log_content: Log content that may contain secrets
        secrets: Optional list of specific secrets to mask
    
    Returns:
        Log content with secrets masked
    """
    return mask_secrets(log_content, secrets)

