from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel
from cdp import Wallet
from web3 import Web3

class BlockchainConfig(BaseModel):
    """Blockchain configuration."""
    network_id: str = "base-sepolia"  # Default to testnet
    wallet_address: Optional[str] = None
    api_key: Optional[str] = None

class NFTCollection(BaseModel):
    """NFT collection information."""
    name: str
    symbol: str
    base_uri: str
    contract_address: Optional[str] = None
    created_at: datetime = datetime.now()
    updated_at: datetime = datetime.now()

class Token(BaseModel):
    """Token information."""
    name: str
    symbol: str
    total_supply: str
    contract_address: Optional[str] = None
    created_at: datetime = datetime.now()
    updated_at: datetime = datetime.now()

class BlockchainManager:
    """Manager for blockchain operations."""
    
    def __init__(self, config: BlockchainConfig):
        self.config = config
        self.wallet = None
        self._initialize_wallet()
    
    def _initialize_wallet(self):
        """Initialize CDP wallet."""
        if self.config.wallet_address and self.config.api_key:
            self.wallet = Wallet(
                network_id=self.config.network_id,
                api_key=self.config.api_key
            )
    
    async def deploy_nft_collection(self, name: str, symbol: str, base_uri: str) -> NFTCollection:
        """Deploy a new NFT collection."""
        if not self.wallet:
            raise ValueError("Wallet not initialized")
        
        try:
            nft_contract = self.wallet.deploy_nft(
                name=name,
                symbol=symbol,
                base_uri=base_uri
            ).wait()
            
            return NFTCollection(
                name=name,
                symbol=symbol,
                base_uri=base_uri,
                contract_address=nft_contract.contract_address
            )
        except Exception as e:
            raise Exception(f"Failed to deploy NFT collection: {str(e)}")
    
    async def mint_nft(self, collection_address: str, destination: str) -> str:
        """Mint an NFT from a collection."""
        if not self.wallet:
            raise ValueError("Wallet not initialized")
        
        try:
            result = self.wallet.invoke_contract(
                contract_address=collection_address,
                method="mint",
                args={"to": destination, "quantity": "1"}
            ).wait()
            return result.transaction.transaction_hash
        except Exception as e:
            raise Exception(f"Failed to mint NFT: {str(e)}")
    
    async def deploy_token(self, name: str, symbol: str, total_supply: str) -> Token:
        """Deploy a new token."""
        if not self.wallet:
            raise ValueError("Wallet not initialized")
        
        try:
            token_contract = self.wallet.deploy_token(
                name=name,
                symbol=symbol,
                total_supply=total_supply
            ).wait()
            
            return Token(
                name=name,
                symbol=symbol,
                total_supply=total_supply,
                contract_address=token_contract.contract_address
            )
        except Exception as e:
            raise Exception(f"Failed to deploy token: {str(e)}")
    
    async def get_balance(self, asset_id: str = "eth") -> Dict[str, str]:
        """Get balance for all addresses in wallet."""
        if not self.wallet:
            raise ValueError("Wallet not initialized")
        
        try:
            balances = {}
            for address in self.wallet.addresses:
                balance = address.balance(asset_id)
                balances[address.address_id] = balance
            return balances
        except Exception as e:
            raise Exception(f"Failed to get balance: {str(e)}")
    
    async def transfer(self, amount: str, asset_id: str, destination: str, gasless: bool = False) -> str:
        """Transfer assets."""
        if not self.wallet:
            raise ValueError("Wallet not initialized")
        
        try:
            result = self.wallet.transfer(
                amount=amount,
                asset_id=asset_id,
                destination=destination,
                gasless=gasless
            ).wait()
            return result.transaction_hash
        except Exception as e:
            raise Exception(f"Failed to transfer: {str(e)}")
    
    async def wrap_eth(self, amount: str) -> str:
        """Wrap ETH to WETH."""
        if not self.wallet:
            raise ValueError("Wallet not initialized")
        
        try:
            result = self.wallet.invoke_contract(
                contract_address="0x4200000000000000000000000000000000000006",
                method="deposit",
                args={},
                amount=amount,
                asset_id="wei"
            ).wait()
            return result.transaction.transaction_hash
        except Exception as e:
            raise Exception(f"Failed to wrap ETH: {str(e)}")
    
    async def request_faucet_funds(self, asset_id: Optional[str] = None) -> str:
        """Request test tokens from faucet."""
        if not self.wallet:
            raise ValueError("Wallet not initialized")
            
        if self.config.network_id != "base-sepolia":
            raise ValueError("Faucet only available on base-sepolia network")
            
        if asset_id and asset_id not in ["eth", "usdc"]:
            raise ValueError("Faucet only supports 'eth' or 'usdc'")
        
        try:
            faucet_tx = self.wallet.faucet(asset_id=asset_id)
            faucet_tx.wait()
            return f"Received {asset_id or 'ETH'} from faucet. Transaction: {faucet_tx.transaction_link}"
        except Exception as e:
            raise Exception(f"Failed to request faucet funds: {str(e)}")
            
    async def get_wallet_details(self) -> Dict[str, str]:
        """Get wallet details."""
        if not self.wallet:
            raise ValueError("Wallet not initialized")
            
        return {
            "network": self.wallet.network_id,
            "default_address": self.wallet.default_address.address_id
        } 