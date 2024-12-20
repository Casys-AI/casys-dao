import pytest
from algosdk.v2client import algod
from contracts.bonds.casys_bond_manager import CaSysBondManager
from contracts.models import CaSysBondConfig
from algosdk import account
import time

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
def bond_manager(algod_client):
    return CaSysBondManager(algod_client)

@pytest.fixture
def bond_config():
    return CaSysBondConfig(
        token_id=1,  # Assuming token ID 1 exists
        amount=10000,
        interest_rate=5.0,  # 5% annual interest
        maturity_date=int(time.time()) + 30 * 24 * 60 * 60,  # 30 days from now
        collateral_ratio=130  # 130% collateral required
    )

def test_create_bond(bond_manager, bond_config):
    """Test bond creation"""
    creator_private_key, _ = create_test_account()
    investor_private_key, investor_address = create_test_account()
    
    bond_id = bond_manager.create_bond(creator_private_key, investor_address, bond_config)
    assert bond_id > 0
    
    # Verify bond info
    bond_info = bond_manager.get_bond_info(bond_id)
    assert bond_info['token_id'] == bond_config.token_id
    assert bond_info['amount'] == bond_config.amount
    assert bond_info['interest_rate'] == bond_config.interest_rate
    assert bond_info['maturity_date'] == bond_config.maturity_date
    assert bond_info['collateral_ratio'] == bond_config.collateral_ratio

def test_redeem_bond(bond_manager, bond_config):
    """Test bond redemption"""
    creator_private_key, _ = create_test_account()
    investor_private_key, investor_address = create_test_account()
    
    # Create bond
    bond_id = bond_manager.create_bond(creator_private_key, investor_address, bond_config)
    
    # Fast forward time to maturity (in testing environment)
    # This would be handled by the testing framework
    
    # Redeem bond
    success = bond_manager.redeem_bond(bond_id, investor_private_key)
    assert success is True

def test_calculate_interest(bond_manager, bond_config):
    """Test interest calculation"""
    amount = 10000
    rate = 5.0  # 5% annual interest
    duration = 365  # 1 year
    
    interest = bond_manager.calculate_interest(amount, rate, duration)
    expected_interest = 500  # 5% of 10000
    assert interest == expected_interest

def test_verify_collateral(bond_manager, bond_config):
    """Test collateral verification"""
    creator_private_key, _ = create_test_account()
    investor_private_key, investor_address = create_test_account()
    
    # Create bond
    bond_id = bond_manager.create_bond(creator_private_key, investor_address, bond_config)
    
    # Verify collateral
    is_sufficient = bond_manager.verify_collateral(bond_id)
    assert is_sufficient is True  # Assuming collateral was provided during creation
