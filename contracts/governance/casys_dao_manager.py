from algosdk.transaction import ApplicationCreateTxn, ApplicationCallTxn
from algosdk.transaction import wait_for_confirmation
from algosdk.v2client import algod
from contracts.models import CaSysDAOConfig, CaSysProposalConfig, ProposalAction, ProposalType
from algosdk.transaction import OnComplete
from algosdk.account import address_from_private_key

class CaSysDAOManager:
    """
    Manager class for the CaSys DAO System
    """
    def __init__(self, algod_client: algod.AlgodClient):
        self.algod_client = algod_client
    
    def create_dao(self, creator_private_key: str, config: CaSysDAOConfig) -> int:
        """
        Create a new DAO
        
        Args:
            creator_private_key: Creator's private key
            config: CaSysDAOConfig model instance
            
        Returns:
            int: DAO ID
        """
        params = self.algod_client.suggested_params()
        
        # Define global and local schema
        global_schema = {
            "num_uints": 5,  # token_id, quorum, voting_period, execution_delay, proposal_count
            "num_byte_slices": 1  # creator
        }
        local_schema = {
            "num_uints": 1,  # voting_power
            "num_byte_slices": 0
        }
        
        # Create the DAO application
        app_txn = ApplicationCreateTxn(
            sender=creator_private_key,
            sp=params,
            on_complete=OnComplete.NoOpOC,
            approval_program=self._get_approval_program(),
            clear_program=self._get_clear_program(),
            global_schema=global_schema,
            local_schema=local_schema,
            app_args=[
                config.token_id,
                config.quorum,
                config.voting_period,
                config.execution_delay
            ]
        )
        
        # Sign and send transaction
        signed_txn = app_txn.sign(creator_private_key)
        tx_id = self.algod_client.send_transaction(signed_txn)
        
        # Wait for confirmation
        wait_for_confirmation(self.algod_client, tx_id)
        
        # Get the application ID
        ptx = self.algod_client.pending_transaction_info(tx_id)
        return ptx['application-index']
    
    def create_proposal(self, dao_id: int, creator_private_key: str,
                       config: CaSysProposalConfig) -> int:
        """
        Create a new proposal
        
        Args:
            dao_id: DAO ID
            creator_private_key: Creator's private key
            config: CaSysProposalConfig model instance
            
        Returns:
            int: Proposal ID
        """
        params = self.algod_client.suggested_params()
        
        # Create proposal transaction
        txn = ApplicationCallTxn(
            sender=creator_private_key,
            sp=params,
            index=dao_id,
            app_args=[
                "create_proposal",
                config.title,
                config.description,
                config.action_type,
                str(config.action_data)
            ]
        )
        
        # Sign and send transaction
        signed_txn = txn.sign(creator_private_key)
        tx_id = self.algod_client.send_transaction(signed_txn)
        
        # Wait for confirmation
        wait_for_confirmation(self.algod_client, tx_id)
        
        # Get proposal ID from app state
        app_info = self.algod_client.application_info(dao_id)
        return app_info['params']['global-state']['proposal_count']
    
    def propose_yield_rate(self, dao_id: int, proposer_private_key: str, new_rate: int) -> int:
        """
        Propose un nouveau taux de yield
        
        Args:
            dao_id: DAO ID
            proposer_private_key: Clé privée du proposeur
            new_rate: Nouveau taux (0-1000 pour 0% à 100%)
            
        Returns:
            int: ID de la proposition
        """
        action = ProposalAction(
            type=ProposalType.YIELD_RATE,
            value=new_rate
        )
        config = CaSysProposalConfig(
            title="Modification du taux de yield",
            description=f"Proposition de changement du taux de yield à {new_rate/10}%",
            action=action
        )
        return self.create_proposal(dao_id, proposer_private_key, config)
    
    def propose_token_mint(self, dao_id: int, proposer_private_key: str, amount: int) -> int:
        """
        Propose la création de nouveaux tokens
        
        Args:
            dao_id: DAO ID
            proposer_private_key: Clé privée du proposeur
            amount: Nombre de tokens à créer
            
        Returns:
            int: ID de la proposition
        """
        action = ProposalAction(
            type=ProposalType.MINT_TOKENS,
            value=amount
        )
        config = CaSysProposalConfig(
            title="Création de nouveaux tokens",
            description=f"Proposition de création de {amount} nouveaux tokens",
            action=action
        )
        return self.create_proposal(dao_id, proposer_private_key, config)
    
    def propose_collateral_ratio(self, dao_id: int, proposer_private_key: str, new_ratio: int) -> int:
        """
        Propose un nouveau ratio de collatéral
        
        Args:
            dao_id: DAO ID
            proposer_private_key: Clé privée du proposeur
            new_ratio: Nouveau ratio (0-10000 pour 0% à 1000%)
            
        Returns:
            int: ID de la proposition
        """
        action = ProposalAction(
            type=ProposalType.COLLATERAL_RATIO,
            value=new_ratio
        )
        config = CaSysProposalConfig(
            title="Modification du ratio de collatéral",
            description=f"Proposition de changement du ratio de collatéral à {new_ratio/10}%",
            action=action
        )
        return self.create_proposal(dao_id, proposer_private_key, config)
    
    def cast_vote(self, dao_id: int, proposal_id: int, voter_private_key: str,
                 in_favor: bool) -> bool:
        """
        Cast a vote on a proposal
        
        Args:
            dao_id: DAO ID
            proposal_id: Proposal ID
            voter_private_key: Voter's private key
            in_favor: True for yes, False for no
            
        Returns:
            bool: Success status
        """
        params = self.algod_client.suggested_params()
        
        # Create vote transaction
        txn = ApplicationCallTxn(
            sender=voter_private_key,
            sp=params,
            index=dao_id,
            app_args=[
                "vote",
                proposal_id,
                "1" if in_favor else "0"
            ]
        )
        
        # Sign and send transaction
        signed_txn = txn.sign(voter_private_key)
        tx_id = self.algod_client.send_transaction(signed_txn)
        
        # Wait for confirmation
        wait_for_confirmation(self.algod_client, tx_id)
        return True
    
    def execute_proposal(self, dao_id: int, proposal_id: int,
                        executor_private_key: str) -> bool:
        """
        Execute a passed proposal
        
        Args:
            dao_id: DAO ID
            proposal_id: Proposal ID
            executor_private_key: Executor's private key
            
        Returns:
            bool: Success status
        """
        params = self.algod_client.suggested_params()
        
        # Create execution transaction
        txn = ApplicationCallTxn(
            sender=executor_private_key,
            sp=params,
            index=dao_id,
            app_args=[
                "execute",
                proposal_id
            ]
        )
        
        # Sign and send transaction
        signed_txn = txn.sign(executor_private_key)
        tx_id = self.algod_client.send_transaction(signed_txn)
        
        # Wait for confirmation
        wait_for_confirmation(self.algod_client, tx_id)
        return True
    
    def get_dao_info(self, dao_id: int) -> dict:
        """
        Get DAO information
        
        Args:
            dao_id: DAO ID
            
        Returns:
            dict: DAO information
        """
        app_info = self.algod_client.application_info(dao_id)
        global_state = app_info['params']['global-state']
        
        return {
            'token_id': global_state['token_id'],
            'quorum': global_state['quorum'],
            'voting_period': global_state['voting_period'],
            'execution_delay': global_state['execution_delay'],
            'proposal_count': global_state['proposal_count']
        }
    
    def get_proposal_info(self, dao_id: int, proposal_id: int) -> dict:
        """
        Get proposal information
        
        Args:
            dao_id: DAO ID
            proposal_id: Proposal ID
            
        Returns:
            dict: Proposal information
        """
        app_info = self.algod_client.application_info(dao_id)
        proposal_state = app_info['params']['local-state'][proposal_id]
        
        return {
            'title': proposal_state['title'],
            'description': proposal_state['description'],
            'action_type': proposal_state['action_type'],
            'action_data': proposal_state['action_data'],
            'status': proposal_state['status'],
            'votes_for': proposal_state['votes_for'],
            'votes_against': proposal_state['votes_against']
        }
    
    def get_vote_info(self, dao_id: int, proposal_id: int, voter: str) -> dict:
        """
        Get vote information
        
        Args:
            dao_id: DAO ID
            proposal_id: Proposal ID
            voter: Voter's address
            
        Returns:
            dict: Vote information
        """
        app_info = self.algod_client.application_info(dao_id)
        voter_state = app_info['params']['local-state'][voter]
        
        return {
            'voting_power': voter_state['voting_power'],
            'in_favor': voter_state[f'vote_{proposal_id}'] == 1
        }
    
    def _get_approval_program(self) -> bytes:
        """Get the approval program bytecode"""
        # TODO: Implement TEAL program compilation
        return bytes()
    
    def _get_clear_program(self) -> bytes:
        """Get the clear program bytecode"""
        # TODO: Implement TEAL program compilation
        return bytes()
