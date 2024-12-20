import pytest
import base64
from datetime import datetime, timedelta
from algosdk import account, mnemonic, encoding
from algosdk.v2client import algod
from contracts.token.casys_token_manager import CaSysTokenManager
from contracts.bonds.casys_bond_manager import CaSysBondManager
from contracts.collateral.casys_collateral_manager import CaSysCollateralManager
from contracts.governance.casys_dao_manager import CaSysDAOManager
from contracts.models import (
    CaSysTokenConfig,
    CaSysBondConfig,
    CaSysCollateralConfig,
    CaSysDAOConfig,
    CaSysBond,
    CaSysYieldDistribution
)
from contracts.utils import ensure_base64_padding
from .utils import safe_mnemonic_from_private_key

class TestCaSysIntegration:
    @pytest.fixture(scope="module")
    def algod_client(self):
        """Create and return an Algorand client instance"""
        algod_address = "http://localhost:4001"
        algod_token = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
        return algod.AlgodClient(algod_token, algod_address)
    
    @pytest.fixture(scope="module")
    def accounts(self):
        """Create test accounts"""
        return {
            'creator': self.create_test_account(),
            'investor1': self.create_test_account(),
            'investor2': self.create_test_account(),
            'manager': self.create_test_account()
        }
    
    def create_test_account(self):
        """Create a test account with initial funds"""
        account_tuple = account.generate_account()
        # Get the base32 address from the private key
        address = account.address_from_private_key(ensure_base64_padding(account_tuple[1]))
        return {
            'address': address,
            'private_key': account_tuple[1],
            'mnemonic': mnemonic.from_private_key(ensure_base64_padding(account_tuple[1]))
        }
    
    @pytest.fixture(scope="module")
    def managers(self, algod_client):
        """Create instances of all managers"""
        return {
            'token': CaSysTokenManager(algod_client),
            'bond': CaSysBondManager(algod_client),
            'dao': CaSysDAOManager(algod_client),
            'collateral': CaSysCollateralManager(algod_client)
        }
    
    @pytest.fixture(scope="module")
    def system_tokens(self, managers, accounts):
        """Create and configure all system tokens"""
        token_manager = managers['token']
        creator = accounts['creator']
        
        # Create main token
        main_token_config = CaSysTokenConfig(
            total_supply=10000000,  # 10M tokens
            decimals=6,
            unit_name="CSYS",
            asset_name="CaSys Token",
            manager=creator['address']
        )
        main_token_id = token_manager.create_token(creator['private_key'], main_token_config)
        
        # Create stablecoin for testing
        stablecoin_config = CaSysTokenConfig(
            total_supply=1000000,  # 1M USDC
            decimals=6,
            unit_name="USDC",
            asset_name="Test USDC",
            manager=creator['address']
        )
        stablecoin_id = token_manager.create_token(creator['private_key'], stablecoin_config)
        
        return {
            'main_token': main_token_id,
            'stablecoin': stablecoin_id
        }
    
    @pytest.fixture(scope="module")
    def system_apps(self, managers, accounts, system_tokens):
        """Create and configure all system applications"""
        creator = accounts['creator']
        
        # Create bond system
        bond_config = CaSysBondConfig(
            token_id=system_tokens['main_token'],
            maturity_date=datetime.now() + timedelta(days=365),
            interest_rate=1000,  # 10%
            minimum_investment=1000,
            collateral_ratio=3000  # 30%
        )
        
        # Create DAO system
        dao_config = CaSysDAOConfig(
            token_id=system_tokens['main_token'],
            proposal_threshold=100000,  # 1% of total supply
            voting_period=86400,  # 1 day
            execution_delay=43200,  # 12 hours
            quorum=3000  # 30% participation required
        )
        
        # Create collateral system
        collateral_config = CaSysCollateralConfig(
            stablecoin_id=system_tokens['stablecoin'],
            token_id=system_tokens['main_token'],
            collateral_ratio=3000,  # 30%
            distribution_rate=500,  # 5%
            distribution_period=86400,  # 1 day
            manager_address=creator['address']
        )
        
        # Get TEAL programs
        with open("contracts/bonds/bond_approval.teal", "r") as f:
            bond_approval = f.read()
        with open("contracts/bonds/bond_clear.teal", "r") as f:
            bond_clear = f.read()
            
        with open("contracts/governance/dao_approval.teal", "r") as f:
            dao_approval = f.read()
        with open("contracts/governance/dao_clear.teal", "r") as f:
            dao_clear = f.read()
            
        with open("contracts/collateral/collateral_approval.teal", "r") as f:
            collateral_approval = f.read()
        with open("contracts/collateral/collateral_clear.teal", "r") as f:
            collateral_clear = f.read()
        
        # Create applications
        bond_app = managers['bond'].create_bond_app(
            creator['private_key'],
            bond_config,
            bond_approval,
            bond_clear
        )
        
        dao_app = managers['dao'].create_dao_app(
            creator['private_key'],
            dao_config,
            dao_approval,
            dao_clear
        )
        
        collateral_app = managers['collateral'].create_collateral_app(
            creator['private_key'],
            collateral_config,
            collateral_approval,
            collateral_clear
        )
        
        return {
            'bond': bond_app,
            'dao': dao_app,
            'collateral': collateral_app
        }
    
    def test_full_investment_cycle(self, managers, accounts, system_tokens, system_apps):
        """Test complete investment cycle with all components"""
        investor = accounts['investor1']
        creator = accounts['creator']
        
        # 1. Investor buys tokens
        token_amount = 100000
        managers['token'].transfer(
            system_tokens['main_token'],
            creator['private_key'],
            investor['address'],
            token_amount
        )
        
        # 2. Investor creates bond
        bond = managers['bond'].create_bond(
            system_apps['bond'],
            investor['private_key'],
            token_amount
        )
        assert isinstance(bond, CaSysBond)
        assert bond.amount == token_amount
        
        # 3. Creator deposits collateral
        collateral_amount = (token_amount * 3000) // 10000  # 30% collateral
        managers['collateral'].deposit_collateral(
            system_apps['collateral'],
            creator['private_key'],
            collateral_amount
        )
        
        # 4. Investor creates governance proposal
        proposal = managers['dao'].create_proposal(
            system_apps['dao'],
            investor['private_key'],
            "Increase Yield Rate",
            "Proposal to increase yield rate to 6%",
            43200  # 12 hours execution delay
        )
        assert isinstance(proposal, CaSysProposal)
        
        # 5. Vote on proposal
        managers['dao'].vote(
            system_apps['dao'],
            investor['private_key'],
            proposal.id,
            True
        )
        
        # 6. Wait for voting period and execute proposal
        import time
        time.sleep(86400 + 43200)  # Wait for voting period + execution delay
        
        managers['dao'].execute_proposal(
            system_apps['dao'],
            investor['private_key'],
            proposal.id
        )
        
        # 7. Distribute yield
        distribution = managers['collateral'].distribute_yield(
            system_apps['collateral'],
            creator['private_key']
        )
        assert isinstance(distribution, CaSysYieldDistribution)
        assert distribution.distribution_rate == 500  # 5%
        
        # 8. Verify final states
        # Check token balance
        token_balance = managers['token'].get_balance(
            system_tokens['main_token'],
            investor['address']
        )
        assert token_balance > 0
        
        # Check bond state
        bond_info = managers['bond'].get_bond(system_apps['bond'], bond.id)
        assert not bond_info.claimed
        
        # Check collateral state
        collateral_info = managers['collateral'].get_collateral_info(
            system_apps['collateral']
        )
        assert collateral_info['total_collateral'] == collateral_amount
    
    def test_emergency_scenario(self, managers, accounts, system_tokens, system_apps):
        """Test system behavior in emergency scenarios"""
        creator = accounts['creator']
        investor = accounts['investor2']
        
        # 1. Simulate market stress by dropping token value
        # Create emergency proposal
        proposal = managers['dao'].create_proposal(
            system_apps['dao'],
            creator['private_key'],
            "Emergency Collateral Adjustment",
            "Adjust collateral ratio due to market conditions",
            0  # Immediate execution
        )
        
        # 2. Emergency vote
        managers['dao'].vote(
            system_apps['dao'],
            creator['private_key'],
            proposal.id,
            True
        )
        
        # 3. Execute emergency measures
        managers['dao'].execute_proposal(
            system_apps['dao'],
            creator['private_key'],
            proposal.id
        )
        
        # 4. Adjust collateral ratio
        managers['collateral'].update_collateral_ratio(
            system_apps['collateral'],
            creator['private_key'],
            4000  # Increase to 40%
        )
        
        # 5. Verify system stability
        collateral_info = managers['collateral'].get_collateral_info(
            system_apps['collateral']
        )
        assert collateral_info['collateral_ratio'] == 4000
        
        # 6. Ensure bonds are still valid
        bond_state = managers['bond'].get_system_state(system_apps['bond'])
        assert bond_state['active']
    
    def test_yield_distribution_cycle(self, managers, accounts, system_tokens, system_apps):
        """Test complete yield distribution cycle"""
        creator = accounts['creator']
        investor1 = accounts['investor1']
        investor2 = accounts['investor2']
        
        # 1. Multiple investors create bonds
        bond1 = managers['bond'].create_bond(
            system_apps['bond'],
            investor1['private_key'],
            50000
        )
        
        bond2 = managers['bond'].create_bond(
            system_apps['bond'],
            investor2['private_key'],
            30000
        )
        
        # 2. Creator deposits collateral for both bonds
        total_bond_amount = 80000  # 50000 + 30000
        collateral_amount = (total_bond_amount * 3000) // 10000  # 30% collateral
        
        managers['collateral'].deposit_collateral(
            system_apps['collateral'],
            creator['private_key'],
            collateral_amount
        )
        
        # 3. Wait for distribution period
        time.sleep(86400)  # Wait 1 day
        
        # 4. Distribute yield
        distribution = managers['collateral'].distribute_yield(
            system_apps['collateral'],
            creator['private_key']
        )
        
        # 5. Verify proportional distribution
        # Investor1 should get 62.5% (50000/80000)
        # Investor2 should get 37.5% (30000/80000)
        yield_amount = distribution.total_amount
        
        investor1_yield = (yield_amount * 50000) // 80000
        investor2_yield = (yield_amount * 30000) // 80000
        
        # Verify yields through token balances
        investor1_balance = managers['token'].get_balance(
            system_tokens['stablecoin'],
            investor1['address']
        )
        investor2_balance = managers['token'].get_balance(
            system_tokens['stablecoin'],
            investor2['address']
        )
        
        assert abs(investor1_balance - investor1_yield) <= 1  # Allow for rounding
        assert abs(investor2_balance - investor2_yield) <= 1  # Allow for rounding
