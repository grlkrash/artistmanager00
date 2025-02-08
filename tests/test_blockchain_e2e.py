import pytest
from datetime import datetime
from unittest.mock import Mock, AsyncMock

from artist_manager_agent.agent import (
    ArtistManagerAgent,
    ArtistProfile,
    BlockchainConfig,
    NFTCollection,
    Token
)

@pytest.fixture
def mock_wallet():
    """Create a mock wallet with realistic behavior."""
    mock = Mock()
    mock.deploy_nft = AsyncMock()
    mock.deploy_token = AsyncMock()
    mock.invoke_contract = AsyncMock()
    mock.transfer = AsyncMock()
    mock.faucet = AsyncMock()
    mock.network_id = "base-sepolia"
    mock.default_address = Mock(address_id="0x123")
    mock.addresses = [Mock(address_id="0x123", balance=AsyncMock(return_value="1.0"))]
    return mock

@pytest.fixture
def agent(mock_wallet):
    """Create a test agent with blockchain config."""
    profile = ArtistProfile(
        name="Test Artist",
        genre="Pop",
        career_stage="emerging",
        goals=["Release NFT collection"],
        strengths=["Digital art"],
        areas_for_improvement=["Marketing"],
        achievements=[],
        social_media={},
        streaming_profiles={},
        health_notes=[],
        brand_guidelines={},
        created_at=datetime.now(),
        updated_at=datetime.now()
    )
    
    config = BlockchainConfig(
        network_id="base-sepolia",
        wallet_address="0x123",
        api_key="test_key"
    )
    
    agent = ArtistManagerAgent(
        artist_profile=profile,
        openai_api_key="test_key",
        blockchain_config=config
    )
    
    agent.blockchain.wallet = mock_wallet
    return agent

@pytest.mark.asyncio
async def test_nft_collection_workflow(agent, mock_wallet):
    """Test complete NFT collection workflow."""
    # Set up mock responses
    mock_wallet.deploy_nft.return_value.wait.return_value.contract_address = "0x456"
    mock_wallet.invoke_contract.return_value.wait.return_value.transaction.transaction_hash = "0xhash1"
    mock_wallet.faucet.return_value.wait.return_value.transaction_link = "https://test/tx/hash2"
    
    # Request faucet funds first
    faucet_result = await agent.request_faucet_funds("eth")
    assert "Received eth from faucet" in faucet_result
    
    # Deploy NFT collection
    collection = await agent.deploy_nft_collection(
        name="Artist NFTs",
        symbol="ARTNFT",
        base_uri="https://api.example.com/nft/"
    )
    assert isinstance(collection, NFTCollection)
    assert collection.contract_address == "0x456"
    
    # Mint NFT to fan
    tx_hash = await agent.mint_nft(collection.contract_address, "0x789")
    assert tx_hash == "0xhash1"
    
    # Verify collection is tracked
    assert collection in agent.nft_collections

@pytest.mark.asyncio
async def test_token_and_transfer_workflow(agent, mock_wallet):
    """Test token deployment and transfer workflow."""
    # Set up mock responses
    mock_wallet.deploy_token.return_value.wait.return_value.contract_address = "0x789"
    mock_wallet.transfer.return_value.wait.return_value.transaction_hash = "0xhash3"
    mock_wallet.faucet.return_value.wait.return_value.transaction_link = "https://test/tx/hash4"
    
    # Request faucet funds first
    faucet_result = await agent.request_faucet_funds("eth")
    assert "Received eth from faucet" in faucet_result
    
    # Deploy fan token
    token = await agent.deploy_token(
        name="Artist Fan Token",
        symbol="ARTFAN",
        total_supply="1000000"
    )
    assert isinstance(token, Token)
    assert token.contract_address == "0x789"
    
    # Transfer tokens to fan
    tx_hash = await agent.transfer_assets(
        amount="1000",
        asset_id=token.contract_address,
        destination="0xabc",
        gasless=True
    )
    assert tx_hash == "0xhash3"
    
    # Verify token is tracked
    assert token in agent.tokens

@pytest.mark.asyncio
async def test_eth_management_workflow(agent, mock_wallet):
    """Test ETH management workflow."""
    # Set up mock responses
    mock_wallet.invoke_contract.return_value.wait.return_value.transaction.transaction_hash = "0xhash5"
    mock_wallet.faucet.return_value.wait.return_value.transaction_link = "https://test/tx/hash6"
    
    # Request faucet funds
    faucet_result = await agent.request_faucet_funds("eth")
    assert "Received eth from faucet" in faucet_result
    
    # Check balance
    balances = await agent.get_balance("eth")
    assert balances["0x123"] == "1.0"
    
    # Wrap some ETH
    tx_hash = await agent.wrap_eth("500000000000000000")  # 0.5 ETH
    assert tx_hash == "0xhash5"
    
    # Get wallet details
    details = await agent.get_wallet_details()
    assert details["network"] == "base-sepolia"
    assert details["default_address"] == "0x123"

@pytest.mark.asyncio
async def test_error_handling(agent, mock_wallet):
    """Test error handling in blockchain operations."""
    # Test network validation
    agent.blockchain.config.network_id = "mainnet"
    with pytest.raises(ValueError, match="Faucet only available on base-sepolia"):
        await agent.request_faucet_funds()
    
    # Test wallet initialization
    agent.blockchain.wallet = None
    with pytest.raises(ValueError, match="Wallet not initialized"):
        await agent.deploy_nft_collection("Test", "TEST", "https://test.com")
    
    # Test invalid faucet asset
    agent.blockchain.wallet = mock_wallet
    agent.blockchain.config.network_id = "base-sepolia"
    with pytest.raises(ValueError, match="Faucet only supports 'eth' or 'usdc'"):
        await agent.request_faucet_funds("invalid") 