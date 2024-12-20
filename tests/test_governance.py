import pytest
from datetime import datetime, timedelta
from algosdk import account
from contracts.governance.casys_dao_manager import CaSysDAOManager
from contracts.models import CaSysDAOConfig, ProposalAction, ProposalType

class TestCaSysGovernance:
    @pytest.fixture(scope="module")
    def accounts(self):
        return [account.generate_account() for _ in range(5)]
    
    @pytest.fixture(scope="module")
    def dao_config(self, accounts):
        return CaSysDAOConfig(
            token_id=1,
            quorum=51,  # 51%
            voting_period=86400,  # 1 jour
            execution_delay=43200,  # 12 heures
            proposal_threshold=1000000  # 1M tokens minimum
        )
    
    @pytest.fixture(scope="module")
    def dao_manager(self, algod_client):
        return CaSysDAOManager(algod_client)
    
    def test_propose_yield_rate(self, dao_manager, accounts, dao_config):
        # Configuration
        creator_private_key = accounts[0][0]
        proposer_private_key = accounts[1][0]
        new_rate = 50  # 5%
        
        # Créer la DAO
        dao_id = dao_manager.create_dao(creator_private_key, dao_config)
        
        # Créer la proposition
        proposal_id = dao_manager.propose_yield_rate(
            dao_id,
            proposer_private_key,
            new_rate
        )
        
        # Vérifier la proposition
        proposal = dao_manager.get_proposal(dao_id, proposal_id)
        assert proposal.action.type == ProposalType.YIELD_RATE
        assert proposal.action.value == new_rate
    
    def test_propose_token_mint(self, dao_manager, accounts, dao_config):
        # Configuration
        creator_private_key = accounts[0][0]
        proposer_private_key = accounts[1][0]
        amount = 1000000  # 1M tokens
        
        # Créer la DAO
        dao_id = dao_manager.create_dao(creator_private_key, dao_config)
        
        # Créer la proposition
        proposal_id = dao_manager.propose_token_mint(
            dao_id,
            proposer_private_key,
            amount
        )
        
        # Vérifier la proposition
        proposal = dao_manager.get_proposal(dao_id, proposal_id)
        assert proposal.action.type == ProposalType.MINT_TOKENS
        assert proposal.action.value == amount
    
    def test_propose_collateral_ratio(self, dao_manager, accounts, dao_config):
        # Configuration
        creator_private_key = accounts[0][0]
        proposer_private_key = accounts[1][0]
        new_ratio = 1500  # 150%
        
        # Créer la DAO
        dao_id = dao_manager.create_dao(creator_private_key, dao_config)
        
        # Créer la proposition
        proposal_id = dao_manager.propose_collateral_ratio(
            dao_id,
            proposer_private_key,
            new_ratio
        )
        
        # Vérifier la proposition
        proposal = dao_manager.get_proposal(dao_id, proposal_id)
        assert proposal.action.type == ProposalType.COLLATERAL_RATIO
        assert proposal.action.value == new_ratio
    
    def test_full_proposal_lifecycle(self, dao_manager, accounts, dao_config):
        # Configuration
        creator_private_key = accounts[0][0]
        proposer_private_key = accounts[1][0]
        voter1_private_key = accounts[2][0]
        voter2_private_key = accounts[3][0]
        new_rate = 50  # 5%
        
        # Créer la DAO
        dao_id = dao_manager.create_dao(creator_private_key, dao_config)
        
        # Créer la proposition
        proposal_id = dao_manager.propose_yield_rate(
            dao_id,
            proposer_private_key,
            new_rate
        )
        
        # Voter pour la proposition
        dao_manager.cast_vote(dao_id, proposal_id, voter1_private_key, True)
        dao_manager.cast_vote(dao_id, proposal_id, voter2_private_key, True)
        
        # Attendre la fin du vote
        proposal = dao_manager.get_proposal(dao_id, proposal_id)
        assert proposal.votes_for > proposal.votes_against
        
        # Exécuter la proposition
        success = dao_manager.execute_proposal(dao_id, proposal_id, creator_private_key)
        assert success
        
        # Vérifier que la proposition a été exécutée
        proposal = dao_manager.get_proposal(dao_id, proposal_id)
        assert proposal.executed
