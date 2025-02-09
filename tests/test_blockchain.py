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
from artist_manager_agent.blockchain import BlockchainManager

@pytest.fixture
def mock_wallet():
    """Create a mock wallet for testing."""
    mock = AsyncMock()
    mock.deploy_nft.return_value = NFTCollection(
        id="nft_1",
        name="Test NFT",
        symbol="TEST",
        base_uri="https://test.com/metadata/",
        contract_address="0x123"
    )
    mock.deploy_token.return_value = Token(
        id="token_1",
        name="Test Token",
        symbol="TST",
        total_supply="1000000",
        contract_address="0x456"
    )
    mock.get_balance.return_value = {"0x123": "1.0"}
    mock.transfer.return_value = "0xhash"
    mock.wrap_eth.return_value = "0xhash"
    mock.request_faucet.return_value = "Received eth from faucet"
    return mock

@pytest.fixture
def agent(mock_wallet):
    """Create a test agent with blockchain config."""
    profile = ArtistProfile(
        id="test-profile-123",
        name="Test Artist",
        genre="Pop",
        career_stage="emerging",
        goals=["Release album"],
        strengths=["Vocals"],
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
    
    # Replace the real wallet with our mock
    agent.blockchain.wallet = mock_wallet
    return agent

@pytest.mark.asyncio
async def test_deploy_nft_collection(agent, mock_wallet):
    """Test NFT collection deployment."""
    with patch.object(agent.blockchain, 'wallet', mock_wallet):
        collection = await agent.deploy_nft_collection(
            name="Test NFT",
            symbol="TEST",
            base_uri="https://test.com/metadata/"
        )
        assert collection.contract_address == "0x123"
        assert collection.name == "Test NFT"
        assert collection.symbol == "TEST"

@pytest.mark.asyncio
async def test_mint_nft(agent, mock_wallet):
    """Test NFT minting."""
    with patch.object(agent.blockchain, 'wallet', mock_wallet):
        # First deploy a collection
        collection = await agent.deploy_nft_collection(
            name="Test NFT",
            symbol="TEST",
            base_uri="https://test.com/metadata/"
        )
        # Then mint an NFT
        tx_hash = await agent.mint_nft(
            collection_address=collection.contract_address,
            destination="0x789"
        )
        assert tx_hash == "0xhash"

@pytest.mark.asyncio
async def test_deploy_token(agent, mock_wallet):
    """Test token deployment."""
    with patch.object(agent.blockchain, 'wallet', mock_wallet):
        token = await agent.deploy_token(
            name="Test Token",
            symbol="TST",
            total_supply="1000000"
        )
        assert token.contract_address == "0x456"
        assert token.name == "Test Token"
        assert token.symbol == "TST"

@pytest.mark.asyncio
async def test_get_balance(agent, mock_wallet):
    """Test getting wallet balances."""
    with patch.object(agent.blockchain, 'wallet', mock_wallet):
        balances = await agent.get_balance("eth")
        assert "0x123" in balances
        assert balances["0x123"] == "1.0"

@pytest.mark.asyncio
async def test_transfer_assets(agent, mock_wallet):
    """Test asset transfer."""
    with patch.object(agent.blockchain, 'wallet', mock_wallet):
        tx_hash = await agent.transfer_assets(
            amount="1.0",
            asset_id="eth",
            destination="0x789"
        )
        assert tx_hash == "0xhash"

@pytest.mark.asyncio
async def test_wrap_eth(agent, mock_wallet):
    """Test wrapping ETH to WETH."""
    with patch.object(agent.blockchain, 'wallet', mock_wallet):
        tx_hash = await agent.wrap_eth("1000000000000000000")  # 1 ETH in wei
        assert tx_hash == "0xhash"