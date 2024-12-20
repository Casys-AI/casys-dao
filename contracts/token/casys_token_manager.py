from algosdk.v2client import algod
from algosdk.transaction import AssetConfigTxn, AssetTransferTxn
from algosdk.transaction import wait_for_confirmation
from algosdk import account
from contracts.models import CaSysTokenConfig

class CaSysTokenManager:
    """
    CaSys Token Management System
    """
    def __init__(self, algod_client: algod.AlgodClient):
        self.algod_client = algod_client
    
    def create_token(self, creator_private_key: str, config: CaSysTokenConfig) -> int:
        """
        Create the CaSys Token
        
        Args:
            creator_private_key: Creator's private key in base64 format
            config: CaSysTokenConfig model instance
            
        Returns:
            int: Token ID
        """
        # Get suggested parameters
        params = self.algod_client.suggested_params()
        
        # Get creator's address from private key
        creator_address = account.address_from_private_key(creator_private_key)
        
        # Create the token
        txn = AssetConfigTxn(
            sender=creator_address,
            sp=params,
            total=config.total_supply,
            default_frozen=False,
            unit_name=config.unit_name,
            asset_name=config.asset_name,
            manager=config.manager,
            reserve=config.manager,
            freeze=config.manager,
            clawback=config.manager,
            url="",
            decimals=config.decimals
        )
        
        # Sign and send transaction
        signed_txn = txn.sign(creator_private_key)
        tx_id = self.algod_client.send_transaction(signed_txn)
        
        # Wait for confirmation
        wait_for_confirmation(self.algod_client, tx_id)
        
        # Get the token ID
        ptx = self.algod_client.pending_transaction_info(tx_id)
        return ptx['asset-index']
    
    def get_token_info(self, token_id: int) -> dict:
        """
        Get token information
        
        Args:
            token_id: Token ID
            
        Returns:
            dict: Token information
        """
        return self.algod_client.asset_info(token_id)
    
    def transfer(self, token_id: int, sender_private_key: str, receiver: str, amount: int) -> bool:
        """
        Transfer tokens
        
        Args:
            token_id: Token ID
            sender_private_key: Sender's private key in base64 format
            receiver: Receiver's address
            amount: Amount to transfer
            
        Returns:
            bool: Success status
        """
        params = self.algod_client.suggested_params()
        
        txn = AssetTransferTxn(
            sender=account.address_from_private_key(sender_private_key),
            sp=params,
            receiver=receiver,
            amt=amount,
            index=token_id
        )
        
        signed_txn = txn.sign(sender_private_key)
        tx_id = self.algod_client.send_transaction(signed_txn)
        
        wait_for_confirmation(self.algod_client, tx_id)
        return True
    
    def get_balance(self, token_id: int, address: str) -> int:
        """
        Get token balance for an address
        
        Args:
            token_id: Token ID
            address: Account address
            
        Returns:
            int: Token balance
        """
        account_info = self.algod_client.account_info(address)
        for asset in account_info['assets']:
            if asset['asset-id'] == token_id:
                return asset['amount']
        return 0
    
    def freeze_account(self, token_id: int, freeze_manager_private_key: str, target: str) -> bool:
        """
        Freeze an account's token holdings
        
        Args:
            token_id: Token ID
            freeze_manager_private_key: Freeze manager's private key in base64 format
            target: Target account address
            
        Returns:
            bool: Success status
        """
        params = self.algod_client.suggested_params()
        
        txn = AssetTransferTxn(
            sender=account.address_from_private_key(freeze_manager_private_key),
            sp=params,
            receiver=target,
            amt=0,
            index=token_id,
            freeze=True
        )
        
        signed_txn = txn.sign(freeze_manager_private_key)
        tx_id = self.algod_client.send_transaction(signed_txn)
        
        wait_for_confirmation(self.algod_client, tx_id)
        return True
    
    def unfreeze_account(self, token_id: int, freeze_manager_private_key: str, target: str) -> bool:
        """
        Unfreeze an account's token holdings
        
        Args:
            token_id: Token ID
            freeze_manager_private_key: Freeze manager's private key in base64 format
            target: Target account address
            
        Returns:
            bool: Success status
        """
        params = self.algod_client.suggested_params()
        
        txn = AssetTransferTxn(
            sender=account.address_from_private_key(freeze_manager_private_key),
            sp=params,
            receiver=target,
            amt=0,
            index=token_id,
            freeze=False
        )
        
        signed_txn = txn.sign(freeze_manager_private_key)
        tx_id = self.algod_client.send_transaction(signed_txn)
        
        wait_for_confirmation(self.algod_client, tx_id)
        return True
    
    def is_frozen(self, token_id: int, address: str) -> bool:
        """
        Check if an account's token holdings are frozen
        
        Args:
            token_id: Token ID
            address: Account address
            
        Returns:
            bool: Frozen status
        """
        account_info = self.algod_client.account_info(address)
        for asset in account_info['assets']:
            if asset['asset-id'] == token_id:
                return asset['is-frozen']
        return False
