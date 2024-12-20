from typing import Optional
from algosdk.transaction import ApplicationCreateTxn, ApplicationCallTxn
from algosdk.transaction import AssetTransferTxn, wait_for_confirmation
from algosdk.v2client import algod
from contracts.models import CaSysCollateralConfig, CaSysYieldDistribution

class CaSysCollateralManager:
    """
    Manager for CaSys Collateral System
    Handles stablecoin collateral, yield distribution, and ratio management
    """
    def __init__(self, algod_client: algod.AlgodClient):
        self.algod_client = algod_client
    
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
        
        # Define global schema
        global_schema = {
            "num_uints": 7,  # stablecoin_id, token_id, ratio, total, last_dist, rate, period
            "num_byte_slices": 1  # manager address
        }
        local_schema = {
            "num_uints": 2,  # deposited_collateral, last_claimed
            "num_byte_slices": 0
        }
        
        # Create application
        txn = ApplicationCreateTxn(
            sender=creator_private_key,
            sp=params,
            on_complete=OnComplete.NoOpOC,
            approval_program=approval_program,
            clear_program=clear_program,
            global_schema=global_schema,
            local_schema=local_schema,
            app_args=[
                config.stablecoin_id,
                config.token_id,
                config.collateral_ratio,
                config.distribution_rate,
                config.distribution_period,
                config.manager_address
            ]
        )
        
        # Sign and send
        signed_txn = txn.sign(creator_private_key)
        tx_id = self.algod_client.send_transaction(signed_txn)
        
        # Wait for confirmation
        wait_for_confirmation(self.algod_client, tx_id)
        
        # Get app ID
        transaction_response = self.algod_client.pending_transaction_info(tx_id)
        return transaction_response["application-index"]
    
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
        
        # Get application state
        app_state = self.algod_client.application_info(app_id)
        stablecoin_id = app_state['params']['global-state']['stablecoin_id']
        
        # Create atomic transfer group
        txn1 = ApplicationCallTxn(
            sender=depositor_private_key,
            sp=params,
            index=app_id,
            on_complete=OnComplete.NoOpOC,
            app_args=["deposit_collateral"]
        )
        
        txn2 = AssetTransferTxn(
            sender=depositor_private_key,
            sp=params,
            receiver=app_id,
            amt=amount,
            index=stablecoin_id
        )
        
        # Group transactions
        gid = calculate_group_id([txn1, txn2])
        txn1.group = gid
        txn2.group = gid
        
        # Sign and send
        stxn1 = txn1.sign(depositor_private_key)
        stxn2 = txn2.sign(depositor_private_key)
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
        
        # Create withdrawal transaction
        txn = ApplicationCallTxn(
            sender=manager_private_key,
            sp=params,
            index=app_id,
            on_complete=OnComplete.NoOpOC,
            app_args=["withdraw_collateral", amount]
        )
        
        # Sign and send
        signed_txn = txn.sign(manager_private_key)
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
        
        # Create distribution transaction
        txn = ApplicationCallTxn(
            sender=manager_private_key,
            sp=params,
            index=app_id,
            on_complete=OnComplete.NoOpOC,
            app_args=["distribute_yield"]
        )
        
        # Sign and send
        signed_txn = txn.sign(manager_private_key)
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
        
        # Create update transaction
        txn = ApplicationCallTxn(
            sender=manager_private_key,
            sp=params,
            index=app_id,
            on_complete=OnComplete.NoOpOC,
            app_args=["update_ratio", new_ratio]
        )
        
        # Sign and send
        signed_txn = txn.sign(manager_private_key)
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
        
        # Create update transaction
        txn = ApplicationCallTxn(
            sender=manager_private_key,
            sp=params,
            index=app_id,
            on_complete=OnComplete.NoOpOC,
            app_args=["update_rate", new_rate]
        )
        
        # Sign and send
        signed_txn = txn.sign(manager_private_key)
        tx_id = self.algod_client.send_transaction(signed_txn)
        
        # Wait for confirmation
        wait_for_confirmation(self.algod_client, tx_id)
        return True
