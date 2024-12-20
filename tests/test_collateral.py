import pytest
import base64
from datetime import datetime, timedelta
from algosdk import account, mnemonic, encoding, kmd
from algosdk.v2client import algod, indexer
from contracts.token.casys_token_manager import CaSysTokenManager
from contracts.collateral.casys_collateral_manager import CaSysCollateralManager
from contracts.models import CaSysTokenConfig, CaSysCollateralConfig, CaSysYieldDistribution
from contracts.utils import ensure_base64_padding

class TestCaSysCollateralSystem:
    @pytest.fixture(scope="module")
    def algod_client(self):
        """Create and return an Algorand client instance"""
        algod_address = "http://localhost:4001"
        algod_token = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
        return algod.AlgodClient(algod_token, algod_address)
    
    @pytest.fixture
    def accounts(self):
        """Create test accounts"""
        # Generate accounts using algosdk's generate_account
        manager = account.generate_account()
        depositor1 = account.generate_account()
        depositor2 = account.generate_account()
        
        # Print debug info for verification
        print(f"Manager address: {manager[0]}")  # [0] is the public address
        print(f"Manager private key: {manager[1]}")  # [1] is the private key
        print(f"Manager mnemonic: {mnemonic.from_private_key(ensure_base64_padding(manager[1]))}")
        
        # Get the addresses from the private keys
        manager_addr = account.address_from_private_key(ensure_base64_padding(manager[1]))
        depositor1_addr = account.address_from_private_key(ensure_base64_padding(depositor1[1]))
        depositor2_addr = account.address_from_private_key(ensure_base64_padding(depositor2[1]))
        
        return {
            'manager': {
                'pk': manager_addr,  # Use the base32 address
                'sk': manager[1],
                'mnemonic': mnemonic.from_private_key(ensure_base64_padding(manager[1]))
            },
            'depositor1': {
                'pk': depositor1_addr,  # Use the base32 address
                'sk': depositor1[1],
                'mnemonic': mnemonic.from_private_key(ensure_base64_padding(depositor1[1]))
            },
            'depositor2': {
                'pk': depositor2_addr,  # Use the base32 address
                'sk': depositor2[1],
                'mnemonic': mnemonic.from_private_key(ensure_base64_padding(depositor2[1]))
            }
        }
    
    @pytest.fixture
    def token_manager(self, algod_client):
        """Create CaSysTokenManager instance"""
        return CaSysTokenManager(algod_client)
    
    @pytest.fixture
    def collateral_manager(self, algod_client):
        """Create CaSysCollateralManager instance"""
        return CaSysCollateralManager(algod_client)
    
    @pytest.fixture
    def token_id(self, token_manager, accounts):
        """Create test token and return its ID"""
        manager = accounts['manager']
        
        config = CaSysTokenConfig(
            total_supply=1000000,
            decimals=6,
            unit_name="CSYS",
            asset_name="CaSys Test Token",
            manager=manager['pk']  # Already in base32 format from generate_account()
        )
        
        return token_manager.create_token(manager['sk'], config)
    
    @pytest.fixture
    def stablecoin_id(self, token_manager, accounts):
        """Create test stablecoin and return its ID"""
        manager = accounts['manager']
        
        config = CaSysTokenConfig(
            total_supply=10000000,
            decimals=6,
            unit_name="USDC",
            asset_name="Test USDC",
            manager=manager['pk']  # Already in base32 format from generate_account()
        )
        
        return token_manager.create_token(manager['sk'], config)
    
    @pytest.fixture
    def app_id(self, collateral_manager, accounts, token_id, stablecoin_id):
        """Create a test collateral system and return its ID"""
        config = CaSysCollateralConfig(
            stablecoin_id=stablecoin_id,
            token_id=token_id,
            collateral_ratio=130,
            distribution_rate=5,
            distribution_period=86400,
            manager_address=accounts['manager']['pk']
        )
        
        # Simple approval and clear programs for testing
        approval_program = "return 1"
        clear_program = "return 1"
        
        return collateral_manager.create_collateral_app(
            accounts['manager']['sk'],
            config,
            approval_program,
            clear_program
        )
    
    def test_create_collateral_system(self, collateral_manager, accounts, token_id, stablecoin_id):
        """Test collateral system creation"""
        manager = accounts['manager']
        
        # Create collateral configuration
        config = CaSysCollateralConfig(
            stablecoin_id=stablecoin_id,
            token_id=token_id,
            collateral_ratio=3000,  # 30%
            distribution_rate=500,   # 5%
            distribution_period=86400,  # 1 day
            manager_address=manager['pk']
        )
        
        # Get approval and clear programs
        with open("contracts/collateral/collateral_approval.teal", "r") as f:
            approval_program = f.read()
        
        with open("contracts/collateral/collateral_clear.teal", "r") as f:
            clear_program = f.read()
        
        # Create collateral application
        app_id = collateral_manager.create_collateral_app(
            manager['sk'],
            config,
            approval_program,
            clear_program
        )
        
        assert app_id > 0
        
        # Verify application state
        app_state = collateral_manager.algod_client.application_info(app_id)
        global_state = app_state['params']['global-state']
        
        assert global_state['stablecoin_id'] == stablecoin_id
        assert global_state['token_id'] == token_id
        assert global_state['collateral_ratio'] == 3000
        assert global_state['distribution_rate'] == 500
    
    def test_deposit_collateral(self, collateral_manager, accounts, app_id):
        """Test collateral deposit"""
        depositor = accounts['depositor1']
        deposit_amount = 10000  # 10 USDC
        
        success = collateral_manager.deposit_collateral(
            app_id,
            depositor['sk'],
            deposit_amount
        )
        
        assert success
        
        # Verify deposit in application state
        app_state = collateral_manager.algod_client.application_info(app_id)
        global_state = app_state['params']['global-state']
        
        assert global_state['total_collateral'] == deposit_amount
    
    def test_distribute_yield(self, collateral_manager, accounts, app_id):
        """Test yield distribution"""
        manager = accounts['manager']
        
        # Wait for distribution period
        import time
        time.sleep(86400)  # Wait 1 day
        
        distribution = collateral_manager.distribute_yield(
            app_id,
            manager['sk']
        )
        
        assert isinstance(distribution, CaSysYieldDistribution)
        assert distribution.distribution_rate == 500  # 5%
        assert distribution.total_amount > 0
    
    def test_update_collateral_ratio(self, collateral_manager, accounts, app_id):
        """Test collateral ratio update"""
        manager = accounts['manager']
        new_ratio = 2500  # 25%
        
        success = collateral_manager.update_collateral_ratio(
            app_id,
            manager['sk'],
            new_ratio
        )
        
        assert success
        
        # Verify new ratio in application state
        app_state = collateral_manager.algod_client.application_info(app_id)
        global_state = app_state['params']['global-state']
        
        assert global_state['collateral_ratio'] == new_ratio
    
    def test_update_distribution_rate(self, collateral_manager, accounts, app_id):
        """Test distribution rate update"""
        manager = accounts['manager']
        new_rate = 600  # 6%
        
        success = collateral_manager.update_distribution_rate(
            app_id,
            manager['sk'],
            new_rate
        )
        
        assert success
        
        # Verify new rate in application state
        app_state = collateral_manager.algod_client.application_info(app_id)
        global_state = app_state['params']['global-state']
        
        assert global_state['distribution_rate'] == new_rate
    
    def test_withdraw_collateral(self, collateral_manager, accounts, app_id):
        """Test collateral withdrawal"""
        manager = accounts['manager']
        withdrawal_amount = 5000  # 5 USDC
        
        initial_state = collateral_manager.algod_client.application_info(app_id)
        initial_total = initial_state['params']['global-state']['total_collateral']
        
        success = collateral_manager.withdraw_collateral(
            app_id,
            manager['sk'],
            withdrawal_amount,
            manager['pk']
        )
        
        assert success
        
        # Verify withdrawal in application state
        app_state = collateral_manager.algod_client.application_info(app_id)
        global_state = app_state['params']['global-state']
        
        assert global_state['total_collateral'] == initial_total - withdrawal_amount
    
    def test_invalid_withdrawal(self, collateral_manager, accounts, app_id):
        """Test invalid collateral withdrawal"""
        manager = accounts['manager']
        
        # Try to withdraw more than allowed by collateral ratio
        app_state = collateral_manager.algod_client.application_info(app_id)
        total_collateral = app_state['params']['global-state']['total_collateral']
        
        with pytest.raises(Exception):
            collateral_manager.withdraw_collateral(
                app_id,
                manager['sk'],
                total_collateral,  # Try to withdraw everything
                manager['pk']
            )
    
    def test_non_manager_operations(self, collateral_manager, accounts, app_id):
        """Test operations by non-manager account"""
        non_manager = accounts['depositor1']
        
        # Try to update collateral ratio
        with pytest.raises(Exception):
            collateral_manager.update_collateral_ratio(
                app_id,
                non_manager['sk'],
                2000
            )
        
        # Try to update distribution rate
        with pytest.raises(Exception):
            collateral_manager.update_distribution_rate(
                app_id,
                non_manager['sk'],
                400
            )
        
        # Try to withdraw collateral
        with pytest.raises(Exception):
            collateral_manager.withdraw_collateral(
                app_id,
                non_manager['sk'],
                1000,
                non_manager['pk']
            )
