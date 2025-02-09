import pytest
from datetime import datetime
from unittest.mock import Mock, AsyncMock, MagicMock, patch

from artist_manager_agent.agent import (
    ArtistManagerAgent,
    ArtistProfile,
    BlockchainConfig,
    NFTCollection,
    Token
)

@pytest.fixture
def mock_wallet():
    """Create a mock wallet for testing."""
    mock = AsyncMock()
    mock.deploy_nft = AsyncMock(return_value=NFTCollection(
        id="nft_1",
        name="Artist NFTs",
        symbol="ARTNFT",
        base_uri="https://api.example.com/nft/",
        contract_address="0x123"
    ))
    mock.deploy_token = AsyncMock(return_value=Token(
        id="token_1",
        name="Artist Fan Token",
        symbol="ARTFAN",
        total_supply="1000000",
        contract_address="0x456"
    ))
    mock.get_balance = AsyncMock(return_value={"0x123": "1.0"})
    mock.transfer = AsyncMock(return_value="0xhash")
    mock.wrap_eth = AsyncMock(return_value="0xhash")
    mock.request_faucet = AsyncMock(return_value="Received eth from faucet")
    return mock

@pytest.fixture
def agent(mock_wallet):
    """Create a test agent with blockchain config."""
    profile = ArtistProfile(
        id="test-profile-123",
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
        db_url="sqlite:///test.db"
    )
    
    agent.blockchain.wallet = mock_wallet
    return agent

@pytest.mark.asyncio
async def test_nft_collection_workflow(agent, mock_wallet):
    """Test complete NFT collection workflow."""
    with patch.object(agent.blockchain, 'wallet', mock_wallet):
        # Request faucet funds first
        faucet_result = await agent.request_faucet_funds("eth")
        assert "Received eth from faucet" in faucet_result
        
        # Deploy NFT collection
        collection = await agent.deploy_nft_collection(
            name="Artist NFTs",
            symbol="ARTNFT",
            base_uri="https://api.example.com/nft/"
        )
        assert collection.contract_address == "0x123"
        assert collection.address == "0x123"
        
        # Mint NFTs
        tx_hash = await agent.mint_nft(
            collection_address=collection.address,
            destination="0x789"
        )
        assert tx_hash == "0xhash"

@pytest.mark.asyncio
async def test_token_and_transfer_workflow(agent, mock_wallet):
    """Test token deployment and transfer workflow."""
    with patch.object(agent.blockchain, 'wallet', mock_wallet):
        # Request faucet funds first
        faucet_result = await agent.request_faucet_funds("eth")
        assert "Received eth from faucet" in faucet_result
        
        # Deploy fan token
        token = await agent.deploy_token(
            name="Artist Fan Token",
            symbol="ARTFAN",
            total_supply="1000000"
        )
        assert token.contract_address == "0x456"
        assert token.address == "0x456"
        
        # Transfer tokens
        tx_hash = await agent.transfer_assets(
            amount="100",
            asset_id=token.address,
            destination="0x789"
        )
        assert tx_hash == "0xhash"

@pytest.mark.asyncio
async def test_eth_management_workflow(agent, mock_wallet):
    """Test ETH management workflow."""
    with patch.object(agent.blockchain, 'wallet', mock_wallet):
        # Request faucet funds
        faucet_result = await agent.request_faucet_funds("eth")
        assert "Received eth from faucet" in faucet_result
        
        # Check balance
        balances = await agent.get_balance("eth")
        assert "0x123" in balances
        assert balances["0x123"] == "1.0"
        
        # Wrap ETH
        tx_hash = await agent.wrap_eth("1000000000000000000")  # 1 ETH in wei
        assert tx_hash == "0xhash"

@pytest.mark.asyncio
async def test_error_handling(agent, mock_wallet):
    """Test error handling in blockchain operations."""
    with patch.object(agent.blockchain, 'wallet', mock_wallet):
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