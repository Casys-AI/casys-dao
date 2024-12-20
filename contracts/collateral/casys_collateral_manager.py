from typing import Optional, Tuple
from base64 import b64decode
from algosdk.transaction import (
    ApplicationCreateTxn, 
    ApplicationCallTxn,
    AssetTransferTxn, 
    wait_for_confirmation,
    OnComplete,
    StateSchema,
    calculate_group_id
)
from algosdk import account
from algosdk.v2client import algod
from contracts.models import CaSysCollateralConfig, CaSysYieldDistribution

class CaSysCollateralManager:
    """
    Manager for CaSys Collateral System
    Handles stablecoin collateral, yield distribution, and ratio management
    """
    def __init__(self, algod_client: algod.AlgodClient):
        self.algod_client = algod_client
    
    def _compile_program(self, source_code: str) -> bytes:
        """Compile TEAL source code to bytes"""
        compile_response = self.algod_client.compile(source_code)
        return b64decode(compile_response['result'])
    
    def _get_address_from_private_key(self, private_key: str) -> str:
        """Get the public address from a private key"""
        return account.address_from_private_key(private_key)
    
    def create_collateral_app(self, creator_private_key: str, config: CaSysCollateralConfig,
                            approval_program: str, clear_program: str) -> int:
        """
        Create the collateral management application
        
        Args:
            creator_private_key: Creator's private key
            config: CaSysCollateralConfig model instance
            approval_program: Approval program TEAL code
            clear_program: Clear program TEAL code
            
        Returns:
            int: Application ID
        """
        params = self.algod_client.suggested_params()
        
        # Get creator's address from private key
        creator_address = self._get_address_from_private_key(creator_private_key)
        
        # Compile TEAL programs
        approval_program_compiled = self._compile_program(approval_program)
        clear_program_compiled = self._compile_program(clear_program)
        
        # Define global schema
        global_schema = StateSchema(
            num_uints=7,  # stablecoin_id, token_id, ratio, total, last_dist, rate, period
            num_byte_slices=1  # manager address
        )
        local_schema = StateSchema(
            num_uints=2,  # deposited_collateral, last_claimed
            num_byte_slices=0
        )
        
        # Create application
        txn = ApplicationCreateTxn(
            sender=creator_address,  # Utiliser l'adresse, pas la clé privée
            sp=params,
            on_complete=OnComplete.NoOpOC,
            approval_program=approval_program_compiled,
            clear_program=clear_program_compiled,
            global_schema=global_schema,
            local_schema=local_schema,
            app_args=[
                str(config.stablecoin_id),
                str(config.token_id),
                str(config.collateral_ratio),
                str(config.distribution_rate),
                str(config.distribution_period),
                str(config.manager_address)
            ]
        )
        
        # Sign transaction with private key
        signed_txn = txn.sign(creator_private_key)
        
        # Send transaction
        tx_id = self.algod_client.send_transaction(signed_txn)
        
        # Wait for confirmation
        confirmed_txn = wait_for_confirmation(self.algod_client, tx_id)
        
        # Get the application ID
        app_id = confirmed_txn['application-index']
        return app_id
    
    def deposit_collateral(self, app_id: int, depositor_private_key: str,
                          amount: int) -> bool:
        """
        Deposit stablecoin collateral
        
        Args:
            app_id: Application ID
            depositor_private_key: Depositor's private key
            amount: Amount of stablecoin to deposit
            
        Returns:
            bool: Success status
        """
        params = self.algod_client.suggested_params()
        
        # Get depositor's address from private key
        depositor_address = self._get_address_from_private_key(depositor_private_key)
        
        # Get application state
        app_state = self.algod_client.application_info(app_id)
        stablecoin_id = app_state['params']['global-state']['stablecoin_id']
        
        # Create atomic transfer group
        txn1 = ApplicationCallTxn(
            sender=depositor_address,  # Utiliser l'adresse, pas la clé privée
            sp=params,
            index=app_id,
            on_complete=OnComplete.NoOpOC,
            app_args=["deposit_collateral"]
        )
        
        txn2 = AssetTransferTxn(
            sender=depositor_address,  # Utiliser l'adresse, pas la clé privée
            sp=params,
            receiver=app_id,
            amt=amount,
            index=stablecoin_id
        )
        
        # Group transactions
        gid = calculate_group_id([txn1, txn2])
        txn1.group = gid
        txn2.group = gid
        
        # Sign transactions with private key
        stxn1 = txn1.sign(depositor_private_key)
        stxn2 = txn2.sign(depositor_private_key)
        
        # Send transactions
        tx_id = self.algod_client.send_transactions([stxn1, stxn2])
        
        # Wait for confirmation
        wait_for_confirmation(self.algod_client, tx_id)
        return True
    
    def withdraw_collateral(self, app_id: int, manager_private_key: str,
                           amount: int, recipient: str) -> bool:
        """
        Withdraw stablecoin collateral
        
        Args:
            app_id: Application ID
            manager_private_key: Manager's private key
            amount: Amount of stablecoin to withdraw
            recipient: Recipient address
            
        Returns:
            bool: Success status
        """
        params = self.algod_client.suggested_params()
        
        # Get manager's address from private key
        manager_address = self._get_address_from_private_key(manager_private_key)
        
        # Create withdrawal transaction
        txn = ApplicationCallTxn(
            sender=manager_address,  # Utiliser l'adresse, pas la clé privée
            sp=params,
            index=app_id,
            on_complete=OnComplete.NoOpOC,
            app_args=["withdraw_collateral", str(amount)]
        )
        
        # Sign transaction with private key
        signed_txn = txn.sign(manager_private_key)
        
        # Send transaction
        tx_id = self.algod_client.send_transaction(signed_txn)
        
        # Wait for confirmation
        wait_for_confirmation(self.algod_client, tx_id)
        return True
    
    def distribute_yield(self, app_id: int, manager_private_key: str) -> Optional[CaSysYieldDistribution]:
        """
        Distribute yield to token holders
        
        Args:
            app_id: Application ID
            manager_private_key: Manager's private key
            
        Returns:
            Optional[CaSysYieldDistribution]: Distribution details if successful
        """
        params = self.algod_client.suggested_params()
        
        # Get manager's address from private key
        manager_address = self._get_address_from_private_key(manager_private_key)
        
        # Create distribution transaction
        txn = ApplicationCallTxn(
            sender=manager_address,  # Utiliser l'adresse, pas la clé privée
            sp=params,
            index=app_id,
            on_complete=OnComplete.NoOpOC,
            app_args=["distribute_yield"]
        )
        
        # Sign transaction with private key
        signed_txn = txn.sign(manager_private_key)
        
        # Send transaction
        tx_id = self.algod_client.send_transaction(signed_txn)
        
        # Wait for confirmation
        wait_for_confirmation(self.algod_client, tx_id)
        
        # Get distribution details
        app_state = self.algod_client.application_info(app_id)
        global_state = app_state['params']['global-state']
        
        return CaSysYieldDistribution(
            timestamp=params.first_round_time,
            total_amount=global_state['total_collateral'] * global_state['distribution_rate'] // 10000,
            distribution_rate=global_state['distribution_rate']
        )
    
    def update_collateral_ratio(self, app_id: int, manager_private_key: str,
                              new_ratio: int) -> bool:
        """
        Update collateral ratio
        
        Args:
            app_id: Application ID
            manager_private_key: Manager's private key
            new_ratio: New collateral ratio (in basis points, e.g. 3000 = 30%)
            
        Returns:
            bool: Success status
        """
        params = self.algod_client.suggested_params()
        
        # Get manager's address from private key
        manager_address = self._get_address_from_private_key(manager_private_key)
        
        # Create update transaction
        txn = ApplicationCallTxn(
            sender=manager_address,  # Utiliser l'adresse, pas la clé privée
            sp=params,
            index=app_id,
            on_complete=OnComplete.NoOpOC,
            app_args=["update_ratio", str(new_ratio)]
        )
        
        # Sign transaction with private key
        signed_txn = txn.sign(manager_private_key)
        
        # Send transaction
        tx_id = self.algod_client.send_transaction(signed_txn)
        
        # Wait for confirmation
        wait_for_confirmation(self.algod_client, tx_id)
        return True
    
    def update_distribution_rate(self, app_id: int, manager_private_key: str,
                               new_rate: int) -> bool:
        """
        Update yield distribution rate
        
        Args:
            app_id: Application ID
            manager_private_key: Manager's private key
            new_rate: New distribution rate (in basis points, e.g. 500 = 5%)
            
        Returns:
            bool: Success status
        """
        params = self.algod_client.suggested_params()
        
        # Get manager's address from private key
        manager_address = self._get_address_from_private_key(manager_private_key)
        
        # Create update transaction
        txn = ApplicationCallTxn(
            sender=manager_address,  # Utiliser l'adresse, pas la clé privée
            sp=params,
            index=app_id,
            on_complete=OnComplete.NoOpOC,
            app_args=["update_rate", str(new_rate)]
        )
        
        # Sign transaction with private key
        signed_txn = txn.sign(manager_private_key)
        
        # Send transaction
        tx_id = self.algod_client.send_transaction(signed_txn)
        
        # Wait for confirmation
        wait_for_confirmation(self.algod_client, tx_id)
        return True
