"""Utility functions for CaSys"""

def ensure_base64_padding(key: str) -> str:
    """
    Ensure that a base64 string has the correct padding.
    
    Args:
        key: Base64 string that might be missing padding
        
    Returns:
        str: Base64 string with correct padding
    """
    padding = len(key) % 4
    if padding:
        return key + "=" * (4 - padding)
    return key
