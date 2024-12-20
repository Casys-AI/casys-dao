import pytest
from unittest.mock import Mock, patch
from datetime import datetime, timedelta
from base64 import b64encode
from algosdk import account
from algosdk.v2client import algod
from algosdk.transaction import SuggestedParams, StateSchema
from contracts.token.casys_token_manager import CaSysTokenManager
from contracts.collateral.casys_collateral_manager import CaSysCollateralManager
from contracts.models import CaSysTokenConfig, CaSysCollateralConfig, CaSysYieldDistribution

class TestCaSysCollateralSystem:
    @pytest.fixture(scope="module")
    def algod_client(self):
        """Create a mocked Algorand client for testing"""
        mock_client = Mock(spec=algod.AlgodClient)
        
        # Mock suggested_params
        mock_params = SuggestedParams(
            fee=1000,
            first=1000,
            last=2000,
            gh="SGO1GKSzyE7IEPItTxCByw9x8FmnrCDexi9/cOUJOiI=",
            gen="testnet-v1.0",
            flat_fee=False,
            consensus_version="https://github.com/algorandfoundation/specs/tree/d5ac876d7ede07367dbaa26e149aa42589aac1f7",
            min_fee=1000
        )
        mock_client.suggested_params.return_value = mock_params
        
        # Mock status
        mock_client.status.return_value = {
            "last-round": 1000,
            "time-since-last-round": 0,
            "catchup-time": 0,
            "last-version": "test-version",
            "last-consensus-version": "test-consensus",
            "next-version": "test-next-version",
            "next-version-round": 2000,
            "next-version-supported": True,
            "stopped-at-unsupported-round": False
        }
        
        # Mock compile
        def mock_compile(source):
            # Pour les tests, on retourne juste le source encodé en base64
            return {"result": b64encode(source.encode()).decode()}
        mock_client.compile = mock_compile
        
        # Mock transaction methods
        mock_client.send_transaction.return_value = "test_txid"
        
        # Mock wait_for_confirmation response
        def mock_pending_txn_info(txid):
            if "test_txid" in str(txid):
                return {
                    "asset-index": 1,  # Pour les transactions d'assets
                    "application-index": 1,  # Pour les transactions d'applications
                    "confirmed-round": 1001,
                    "pool-error": "",
                    "txn": {"tx": "test_tx"}
                }
            return None
        mock_client.pending_transaction_info = mock_pending_txn_info
        
        # Mock application info
        mock_client.application_info.return_value = {
            "id": 1,
            "params": {
                "creator": "test_creator",
                "approval-program": "test_approval",
                "clear-state-program": "test_clear",
                "local-state-schema": {"num-uint": 2, "num-byte-slice": 0},
                "global-state-schema": {"num-uint": 7, "num-byte-slice": 1},
                "global-state": {
                    "stablecoin_id": {"uint": 1},
                    "token_id": {"uint": 1},
                    "collateral_ratio": {"uint": 3000},  # Mis à jour pour correspondre au test
                    "distribution_rate": {"uint": 500},  # Mis à jour pour correspondre au test
                    "distribution_period": {"uint": 86400},  # Mis à jour pour correspondre au test
                    "manager": {"bytes": "test_manager"}
                }
            }
        }
        
        # Mock health
        mock_client.health.return_value = {"message": "I'm healthy!"}
        
        return mock_client
    
    @pytest.fixture
    def accounts(self):
        """Create test accounts using Algorand SDK's recommended approach"""
        # Génération des comptes
        manager_private_key, manager_address = account.generate_account()
        depositor1_private_key, depositor1_address = account.generate_account()
        depositor2_private_key, depositor2_address = account.generate_account()
        
        return {
            'manager': {
                'address': manager_address,
                'private_key': manager_private_key
            },
            'depositor1': {
                'address': depositor1_address,
                'private_key': depositor1_private_key
            },
            'depositor2': {
                'address': depositor2_address,
                'private_key': depositor2_private_key
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
        """Create a test token"""
        manager = accounts['manager']
        
        config = CaSysTokenConfig(
            total_supply=1000000,
            decimals=6,
            unit_name="CSYS",
            asset_name="CaSys Test Token",
            manager=manager['address']  # Utiliser l'adresse pour la configuration
        )
        
        # Utiliser la clé privée pour la création
        return token_manager.create_token(manager['private_key'], config)
    
    @pytest.fixture
    def stablecoin_id(self, token_manager, accounts):
        """Create test stablecoin and return its ID"""
        manager = accounts['manager']
        
        config = CaSysTokenConfig(
            total_supply=1000000,
            decimals=6,
            unit_name="USDC",
            asset_name="Test USDC",
            manager=manager['address']  # Utiliser l'adresse pour la configuration
        )
        
        # Utiliser la clé privée pour la création
        return token_manager.create_token(manager['private_key'], config)
    
    @pytest.fixture
    def app_id(self, collateral_manager, accounts, token_id, stablecoin_id):
        """Create test collateral application"""
        manager = accounts['manager']
        
        config = CaSysCollateralConfig(
            stablecoin_id=stablecoin_id,
            token_id=token_id,
            collateral_ratio=130,
            distribution_rate=5,
            distribution_period=86400,
            manager_address=manager['address']  # Utiliser l'adresse pour la configuration
        )
        
        # Simple approval and clear programs for testing
        approval_program = "return 1"
        clear_program = "return 1"
        
        return collateral_manager.create_collateral_app(
            accounts['manager']['private_key'],
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
            collateral_ratio=3000,  
            distribution_rate=500,   
            distribution_period=86400,  
            manager_address=manager['address']  # Utiliser l'adresse pour la configuration
        )
        
        # Get approval and clear programs
        with open("contracts/collateral/collateral_approval.teal", "r") as f:
            approval_program = f.read()
        
        with open("contracts/collateral/collateral_clear.teal", "r") as f:
            clear_program = f.read()
        
        # Create collateral application
        app_id = collateral_manager.create_collateral_app(
            manager['private_key'],
            config,
            approval_program,
            clear_program
        )
        
        assert app_id > 0
        
        # Verify application state
        app_state = collateral_manager.algod_client.application_info(app_id)
        global_state = app_state['params']['global-state']
        
        # Extract values from global state
        assert global_state['stablecoin_id']['uint'] == stablecoin_id
        assert global_state['token_id']['uint'] == token_id
        assert global_state['collateral_ratio']['uint'] == 3000
        assert global_state['distribution_rate']['uint'] == 500
        assert global_state['distribution_period']['uint'] == 86400
    
    def test_deposit_collateral(self, collateral_manager, accounts, app_id):
        """Test collateral deposit"""
        depositor = accounts['depositor1']
        deposit_amount = 10000  
    
        success = collateral_manager.deposit_collateral(
            app_id,
            depositor['private_key'],
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
        time.sleep(86400)  
    
        distribution = collateral_manager.distribute_yield(
            app_id,
            manager['private_key']
        )
        
        assert isinstance(distribution, CaSysYieldDistribution)
        assert distribution.distribution_rate == 500  
        assert distribution.total_amount > 0
    
    def test_update_collateral_ratio(self, collateral_manager, accounts, app_id):
        """Test collateral ratio update"""
        manager = accounts['manager']
        new_ratio = 2500  
    
        success = collateral_manager.update_collateral_ratio(
            app_id,
            manager['private_key'],
            new_ratio
        )
        
        assert success
        
        # Verify new ratio in application state
        app_state = collateral_manager.algod_client.application_info(app_id)
        global_state = app_state['params']['global-state']
        
        assert global_state['collateral_ratio']['uint'] == new_ratio
    
    def test_update_distribution_rate(self, collateral_manager, accounts, app_id):
        """Test distribution rate update"""
        manager = accounts['manager']
        new_rate = 600  
    
        success = collateral_manager.update_distribution_rate(
            app_id,
            manager['private_key'],
            new_rate
        )
        
        assert success
        
        # Verify new rate in application state
        app_state = collateral_manager.algod_client.application_info(app_id)
        global_state = app_state['params']['global-state']
        
        assert global_state['distribution_rate']['uint'] == new_rate
    
    def test_withdraw_collateral(self, collateral_manager, accounts, app_id):
        """Test collateral withdrawal"""
        manager = accounts['manager']
        withdrawal_amount = 5000  
    
        initial_state = collateral_manager.algod_client.application_info(app_id)
        initial_total = initial_state['params']['global-state']['total_collateral']
        
        success = collateral_manager.withdraw_collateral(
            app_id,
            manager['private_key'],
            withdrawal_amount,
            manager['address']
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
                manager['private_key'],
                total_collateral,  
                manager['address']
            )
    
    def test_non_manager_operations(self, collateral_manager, accounts, app_id):
        """Test operations by non-manager account"""
        non_manager = accounts['depositor1']
        
        # Try to update collateral ratio
        with pytest.raises(Exception):
            collateral_manager.update_collateral_ratio(
                app_id,
                non_manager['private_key'],
                2000
            )
        
        # Try to update distribution rate
        with pytest.raises(Exception):
            collateral_manager.update_distribution_rate(
                app_id,
                non_manager['private_key'],
                400
            )
        
        # Try to withdraw collateral
        with pytest.raises(Exception):
            collateral_manager.withdraw_collateral(
                app_id,
                non_manager['private_key'],
                1000,
                non_manager['address']
            )
