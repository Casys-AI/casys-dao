"""Test utilities for CaSys Token system"""

import base64
from algosdk import account

def ensure_base64_padding(key: str) -> str:
    """
    Ensure proper base64 padding for a key.
    
    Args:
        key: Base64 encoded key string
        
    Returns:
        str: Properly padded base64 string
    """
    padding = len(key) % 4
    if padding:
        key += '=' * (4 - padding)
    return key

def safe_mnemonic_from_private_key(private_key: str) -> str:
    """
    Safely convert a private key to mnemonic with proper base64 padding.
    
    Args:
        private_key: Private key string
        
    Returns:
        str: Mnemonic words for the private key
    """
    from algosdk import mnemonic
    padded_key = ensure_base64_padding(private_key)
    return mnemonic.from_private_key(padded_key)

def safe_address_from_private_key(private_key: str) -> str:
    """
    Safely get address from private key with proper base64 padding.
    
    Args:
        private_key: Private key string
        
    Returns:
        str: Algorand address
    """
    padded_key = ensure_base64_padding(private_key)
    return account.address_from_private_key(padded_key)
