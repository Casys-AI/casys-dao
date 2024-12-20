import pytest
from algosdk.v2client import algod
from contracts.token.casys_token_manager import CaSysTokenManager
from contracts.models import CaSysTokenConfig
from algosdk import account, mnemonic

def create_test_account():
    private_key, address = account.generate_account()
    return private_key, address

@pytest.fixture
def algod_client():
    # Connect to Algorand node
    algod_token = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
    algod_address = "http://localhost:4001"
    return algod.AlgodClient(algod_token, algod_address)

@pytest.fixture
def token_manager(algod_client):
    return CaSysTokenManager(algod_client)

@pytest.fixture
def token_config():
    creator_private_key, creator_address = create_test_account()
    return CaSysTokenConfig(
        total_supply=1000000,
        decimals=6,
        unit_name="CSYS",
        asset_name="CaSys Token",
        manager=creator_address
    )

def test_create_token(token_manager, token_config):
    """Test token creation"""
    creator_private_key, _ = create_test_account()
    token_id = token_manager.create_token(creator_private_key, token_config)
    assert token_id > 0
    
    # Verify token info
    token_info = token_manager.get_token_info(token_id)
    assert token_info['total'] == token_config.total_supply
    assert token_info['decimals'] == token_config.decimals
    assert token_info['unit-name'] == token_config.unit_name
    assert token_info['name'] == token_config.asset_name

def test_transfer_token(token_manager, token_config):
    """Test token transfer"""
    creator_private_key, creator_address = create_test_account()
    receiver_private_key, receiver_address = create_test_account()
    
    # Create token
    token_id = token_manager.create_token(creator_private_key, token_config)
    
    # Transfer tokens
    amount = 1000
    token_manager.transfer_token(creator_private_key, receiver_address, token_id, amount)
    
    # Verify balances
    creator_balance = token_manager.get_token_balance(creator_address, token_id)
    receiver_balance = token_manager.get_token_balance(receiver_address, token_id)
    assert creator_balance == token_config.total_supply - amount
    assert receiver_balance == amount

def test_freeze_token(token_manager, token_config):
    """Test token freezing"""
    creator_private_key, creator_address = create_test_account()
    target_private_key, target_address = create_test_account()
    
    # Create token
    token_id = token_manager.create_token(creator_private_key, token_config)
    
    # Freeze account
    token_manager.freeze_token(creator_private_key, target_address, token_id)
    
    # Verify frozen status
    is_frozen = token_manager.is_frozen(target_address, token_id)
    assert is_frozen is True
    
    # Unfreeze account
    token_manager.unfreeze_token(creator_private_key, target_address, token_id)
    
    # Verify unfrozen status
    is_frozen = token_manager.is_frozen(target_address, token_id)
    assert is_frozen is False

def test_token_balance(token_manager, token_config):
    """Test token balance checking"""
    creator_private_key, creator_address = create_test_account()
    
    # Create token
    token_id = token_manager.create_token(creator_private_key, token_config)
    
    # Check initial balance
    balance = token_manager.get_token_balance(creator_address, token_id)
    assert balance == token_config.total_supply

def test_opt_in_out(token_manager, token_config):
    """Test opt-in and opt-out"""
    creator_private_key, _ = create_test_account()
    user_private_key, user_address = create_test_account()
    
    # Create token
    token_id = token_manager.create_token(creator_private_key, token_config)
    
    # Opt in
    token_manager.opt_in(user_private_key, token_id)
    
    # Verify opt-in status
    is_opted_in = token_manager.is_opted_in(user_address, token_id)
    assert is_opted_in is True
    
    # Opt out
    token_manager.opt_out(user_private_key, token_id)
    
    # Verify opt-out status
    is_opted_in = token_manager.is_opted_in(user_address, token_id)
    assert is_opted_in is False
