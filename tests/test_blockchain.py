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
    """Create a mock wallet."""
    mock = Mock()
    mock.deploy_nft = AsyncMock()
    mock.deploy_token = AsyncMock()
    mock.invoke_contract = AsyncMock()
    mock.transfer = AsyncMock()
    mock.addresses = [Mock(address_id="0x123", balance=AsyncMock(return_value="1.0"))]
    return mock

@pytest.fixture
def agent(mock_wallet):
    """Create a test agent with blockchain config."""
    profile = ArtistProfile(
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
        blockchain_config=config
    )
    
    # Replace the real wallet with our mock
    agent.blockchain.wallet = mock_wallet
    return agent

@pytest.mark.asyncio
async def test_deploy_nft_collection(agent, mock_wallet):
    """Test NFT collection deployment."""
    mock_wallet.deploy_nft.return_value.wait.return_value.contract_address = "0x456"
    
    collection = await agent.deploy_nft_collection(
        name="Test NFT",
        symbol="TEST",
        base_uri="https://test.com/metadata/"
    )
    
    assert isinstance(collection, NFTCollection)
    assert collection.name == "Test NFT"
    assert collection.symbol == "TEST"
    assert collection.contract_address == "0x456"
    assert collection in agent.nft_collections

@pytest.mark.asyncio
async def test_mint_nft(agent, mock_wallet):
    """Test NFT minting."""
    mock_wallet.invoke_contract.return_value.wait.return_value.transaction.transaction_hash = "0xhash"
    
    tx_hash = await agent.mint_nft(
        collection_address="0x456",
        destination="0x789"
    )
    
    assert tx_hash == "0xhash"
    mock_wallet.invoke_contract.assert_called_once()

@pytest.mark.asyncio
async def test_deploy_token(agent, mock_wallet):
    """Test token deployment."""
    mock_wallet.deploy_token.return_value.wait.return_value.contract_address = "0x789"
    
    token = await agent.deploy_token(
        name="Test Token",
        symbol="TST",
        total_supply="1000000"
    )
    
    assert isinstance(token, Token)
    assert token.name == "Test Token"
    assert token.symbol == "TST"
    assert token.contract_address == "0x789"
    assert token in agent.tokens

@pytest.mark.asyncio
async def test_get_balance(agent, mock_wallet):
    """Test getting wallet balances."""
    balances = await agent.get_balance("eth")
    
    assert isinstance(balances, dict)
    assert "0x123" in balances
    assert balances["0x123"] == "1.0"

@pytest.mark.asyncio
async def test_transfer_assets(agent, mock_wallet):
    """Test asset transfer."""
    mock_wallet.transfer.return_value.wait.return_value.transaction_hash = "0xhash"
    
    tx_hash = await agent.transfer_assets(
        amount="1.0",
        asset_id="eth",
        destination="0x789"
    )
    
    assert tx_hash == "0xhash"
    mock_wallet.transfer.assert_called_once_with(
        amount="1.0",
        asset_id="eth",
        destination="0x789",
        gasless=False
    )

@pytest.mark.asyncio
async def test_wrap_eth(agent, mock_wallet):
    """Test wrapping ETH to WETH."""
    mock_wallet.invoke_contract.return_value.wait.return_value.transaction.transaction_hash = "0xhash"
    
    tx_hash = await agent.wrap_eth("1000000000000000000")  # 1 ETH in wei
    
    assert tx_hash == "0xhash"
    mock_wallet.invoke_contract.assert_called_once() 