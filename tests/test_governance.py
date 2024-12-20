import pytest
from algosdk.v2client import algod
from contracts.governance.casys_dao_manager import CaSysDAOManager
from contracts.models import CaSysDAOConfig, CaSysProposalConfig
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
def dao_manager(algod_client):
    return CaSysDAOManager(algod_client)

@pytest.fixture
def dao_config():
    return CaSysDAOConfig(
        token_id=1,  # Assuming token ID 1 exists
        quorum=51,  # 51% quorum required
        voting_period=86400,  # 24 hours
        execution_delay=43200  # 12 hours
    )

@pytest.fixture
def proposal_config():
    return CaSysProposalConfig(
        title="Test Proposal",
        description="This is a test proposal",
        action_type="transfer",
        action_data={"recipient": "test_address", "amount": 1000}
    )

def test_create_dao(dao_manager, dao_config):
    """Test DAO creation"""
    creator_private_key, _ = create_test_account()
    
    dao_id = dao_manager.create_dao(creator_private_key, dao_config)
    assert dao_id > 0
    
    # Verify DAO info
    dao_info = dao_manager.get_dao_info(dao_id)
    assert dao_info['token_id'] == dao_config.token_id
    assert dao_info['quorum'] == dao_config.quorum
    assert dao_info['voting_period'] == dao_config.voting_period
    assert dao_info['execution_delay'] == dao_config.execution_delay

def test_create_proposal(dao_manager, dao_config, proposal_config):
    """Test proposal creation"""
    creator_private_key, _ = create_test_account()
    
    # Create DAO first
    dao_id = dao_manager.create_dao(creator_private_key, dao_config)
    
    # Create proposal
    proposal_id = dao_manager.create_proposal(dao_id, creator_private_key, proposal_config)
    assert proposal_id > 0
    
    # Verify proposal info
    proposal_info = dao_manager.get_proposal_info(dao_id, proposal_id)
    assert proposal_info['title'] == proposal_config.title
    assert proposal_info['description'] == proposal_config.description
    assert proposal_info['action_type'] == proposal_config.action_type
    assert proposal_info['action_data'] == proposal_config.action_data

def test_cast_vote(dao_manager, dao_config, proposal_config):
    """Test vote casting"""
    creator_private_key, _ = create_test_account()
    voter_private_key, voter_address = create_test_account()
    
    # Create DAO and proposal
    dao_id = dao_manager.create_dao(creator_private_key, dao_config)
    proposal_id = dao_manager.create_proposal(dao_id, creator_private_key, proposal_config)
    
    # Cast vote
    success = dao_manager.cast_vote(dao_id, proposal_id, voter_private_key, True)
    assert success is True
    
    # Verify vote info
    vote_info = dao_manager.get_vote_info(dao_id, proposal_id, voter_address)
    assert vote_info['in_favor'] is True

def test_execute_proposal(dao_manager, dao_config, proposal_config):
    """Test proposal execution"""
    creator_private_key, _ = create_test_account()
    voter_private_key, voter_address = create_test_account()
    
    # Create DAO and proposal
    dao_id = dao_manager.create_dao(creator_private_key, dao_config)
    proposal_id = dao_manager.create_proposal(dao_id, creator_private_key, proposal_config)
    
    # Cast vote (assuming enough votes for quorum)
    dao_manager.cast_vote(dao_id, proposal_id, voter_private_key, True)
    
    # Fast forward time past voting period and execution delay
    # This would be handled by the testing framework
    
    # Execute proposal
    success = dao_manager.execute_proposal(dao_id, proposal_id, creator_private_key)
    assert success is True
    
    # Verify proposal status
    proposal_info = dao_manager.get_proposal_info(dao_id, proposal_id)
    assert proposal_info['status'] == 'executed'
