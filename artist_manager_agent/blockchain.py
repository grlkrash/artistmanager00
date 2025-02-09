import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel
from enum import Enum

class NetworkType(Enum):
    BASE_SEPOLIA = "base-sepolia"
    BASE_MAINNET = "base-mainnet"

@dataclass
class Wallet:
    """Represents a blockchain wallet."""
    address: str
    network: NetworkType
    private_key: Optional[str] = None
    
    def get_balance(self, asset_id: str = "eth") -> float:
        """Get wallet balance for specified asset."""
        # Mock implementation for testing
        return 1.0
    
    def transfer(self, to_address: str, amount: float, asset_id: str = "eth") -> str:
        """Transfer assets to another address."""
        # Mock implementation for testing
        return f"tx_hash_{datetime.now().timestamp()}"
    
    def deploy_contract(self, contract_type: str, params: Dict[str, Any]) -> str:
        """Deploy a smart contract."""
        # Mock implementation for testing
        return f"contract_{contract_type}_{datetime.now().timestamp()}"
    
    def invoke_contract(self, contract_address: str, method: str, params: Dict[str, Any]) -> Any:
        """Invoke a smart contract method."""
        # Mock implementation for testing
        return {"status": "success", "tx_hash": f"tx_{method}_{datetime.now().timestamp()}"}

class BlockchainConfig(BaseModel):
    """Blockchain configuration."""
    network_id: str = "base-sepolia"  # Default to testnet
    wallet_address: Optional[str] = None
    api_key: Optional[str] = None
    weth_address: str = "0x4200000000000000000000000000000000000006"  # Base Sepolia WETH

class NFTCollection(BaseModel):
    """NFT collection information."""
    id: str
    name: str
    symbol: str
    base_uri: str
    contract_address: Optional[str] = None
    created_at: datetime = datetime.now()
    updated_at: datetime = datetime.now()

class Token(BaseModel):
    """Token information."""
    id: str
    name: str
    symbol: str
    total_supply: str
    contract_address: Optional[str] = None
    created_at: datetime = datetime.now()
    updated_at: datetime = datetime.now()

class BlockchainManager:
    """Manager for blockchain operations."""
    
    def __init__(self, config: BlockchainConfig):
        """Initialize the BlockchainManager."""
        self.config = config
        self.wallet = None
        self._initialize_wallet()
    
    def _initialize_wallet(self):
        """Initialize CDP wallet."""
        if self.config.wallet_address and self.config.api_key:
            self.wallet = Wallet(
                address=self.config.wallet_address,
                network=NetworkType(self.config.network_id)
            )
    
    async def deploy_nft_collection(self, name: str, symbol: str, base_uri: str) -> NFTCollection:
        """Deploy a new NFT collection."""
        if not self.wallet:
            raise ValueError("Wallet not initialized")
            
        try:
            nft_contract = await self.wallet.deploy_nft(
                name=name,
                symbol=symbol,
                base_uri=base_uri
            )
            
            # Wait for contract deployment and get address
            if hasattr(nft_contract, 'wait'):
                nft_contract = await nft_contract.wait()
            
            contract_address = getattr(nft_contract, 'contract_address', None)
            if not contract_address:
                raise ValueError("Failed to get contract address")
                
            return NFTCollection(
                id=str(uuid.uuid4()),
                name=name,
                symbol=symbol,
                base_uri=base_uri,
                contract_address=contract_address
            )
        except Exception as e:
            raise Exception(f"Failed to deploy NFT collection: {str(e)}")
    
    async def mint_nft(self, collection_address: str, recipient: str, token_uri: str) -> str:
        """Mint a new NFT."""
        if not self.wallet:
            raise ValueError("Wallet not initialized")
            
        try:
            result = await self.wallet.mint_nft(
                contract_address=collection_address,
                recipient=recipient,
                token_uri=token_uri
            )
            
            # Wait for transaction completion
            if hasattr(result, 'wait'):
                result = await result.wait()
            
            # Try different ways to get transaction hash based on response structure
            tx_hash = None
            if hasattr(result, 'transaction_hash'):
                tx_hash = result.transaction_hash
            elif hasattr(result, 'transaction'):
                tx_hash = result.transaction.transaction_hash
                
            if not tx_hash:
                raise ValueError("Failed to get transaction hash")
                
            return str(tx_hash)
        except Exception as e:
            raise Exception(f"Failed to mint NFT: {str(e)}")
    
    async def deploy_token(self, name: str, symbol: str, total_supply: str) -> Token:
        """Deploy a new token."""
        if not self.wallet:
            raise ValueError("Wallet not initialized")
        
        try:
            token_contract = await self.wallet.deploy_token(
                name=name,
                symbol=symbol,
                total_supply=total_supply
            )
            
            # Wait for contract deployment and get address
            if hasattr(token_contract, 'wait'):
                token_contract = await token_contract.wait()
            
            contract_address = getattr(token_contract, 'contract_address', None)
            if not contract_address:
                raise ValueError("Failed to get contract address")
                
            return Token(
                id=str(uuid.uuid4()),
                name=name,
                symbol=symbol,
                total_supply=total_supply,
                contract_address=contract_address
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
                balance = await address.balance(asset_id)
                balances[address.address_id] = balance
            return balances
        except Exception as e:
            raise Exception(f"Failed to get balance: {str(e)}")
    
    async def transfer(self, token_address: str, recipient: str, amount: str) -> str:
        """Transfer tokens."""
        if not self.wallet:
            raise ValueError("Wallet not initialized")
            
        try:
            result = await self.wallet.transfer(
                contract_address=token_address,
                recipient=recipient,
                amount=amount
            )
            
            tx_hash = str(getattr(result, 'transaction_hash', None))
            if not tx_hash:
                raise ValueError("Failed to get transaction hash")
                
            return tx_hash
        except Exception as e:
            raise Exception(f"Failed to transfer tokens: {str(e)}")
    
    async def wrap_eth(self, amount: str) -> str:
        """Wrap ETH to WETH."""
        if not self.wallet:
            raise ValueError("Wallet not initialized")
            
        try:
            result = await self.wallet.invoke_contract(
                contract_address=self.config.weth_address,
                function_name="deposit",
                args=[amount]
            )
            
            tx_hash = str(getattr(result, 'transaction_hash', None))
            if not tx_hash:
                raise ValueError("Failed to get transaction hash")
                
            return tx_hash
        except Exception as e:
            raise Exception(f"Failed to wrap ETH: {str(e)}")
    
    async def request_faucet_funds(self, asset_id: Optional[str] = None) -> str:
        """Request test tokens from faucet."""
        if not self.wallet:
            raise ValueError("Wallet not initialized")
            
        if self.config.network_id != NetworkType.BASE_SEPOLIA.value:
            self.config.network_id = NetworkType.BASE_SEPOLIA.value
            self._initialize_wallet()
            
        if asset_id and asset_id not in ["eth", "usdc"]:
            raise ValueError("Faucet only supports 'eth' or 'usdc'")
        
        try:
            faucet_tx = await self.wallet.faucet(asset_id=asset_id)
            tx_link = str(getattr(faucet_tx, 'transaction_link', None))
            if not tx_link:
                raise ValueError("Failed to get transaction link")
            return f"Received {asset_id or 'ETH'} from faucet. Transaction: {tx_link}"
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