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
    wallet = AsyncMock()
    
    # Configure mock responses
    deploy_nft_response = AsyncMock()
    deploy_nft_response.wait = AsyncMock(return_value=MagicMock(contract_address="0x456"))
    wallet.deploy_nft.return_value = deploy_nft_response
    
    mint_response = AsyncMock()
    mint_response.wait = AsyncMock(return_value=MagicMock(transaction_hash="0xhash"))
    wallet.mint_nft.return_value = mint_response
    
    deploy_token_response = AsyncMock()
    deploy_token_response.wait = AsyncMock(return_value=MagicMock(contract_address="0x789"))
    wallet.deploy_token.return_value = deploy_token_response
    
    transfer_response = AsyncMock()
    transfer_response.wait = AsyncMock(return_value=MagicMock(transaction_hash="0xtx123"))
    wallet.transfer.return_value = transfer_response
    
    wrap_response = AsyncMock()
    wrap_response.wait = AsyncMock(return_value=MagicMock(transaction=MagicMock(transaction_hash="0xwrap456")))
    wallet.invoke_contract.return_value = wrap_response
    
    # Configure balance response
    wallet.addresses = [MagicMock(address_id="0x123", balance=AsyncMock(return_value="1.0"))]
    
    # Configure faucet response
    faucet_response = AsyncMock()
    faucet_response.wait = AsyncMock(return_value=MagicMock(transaction_link="https://test/tx/hash"))
    wallet.faucet.return_value = faucet_response
    
    return wallet

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
        
        assert isinstance(collection, NFTCollection)
        assert collection.name == "Test NFT"
        assert collection.symbol == "TEST"
        assert collection.contract_address == "0x456"

@pytest.mark.asyncio
async def test_mint_nft(agent, mock_wallet):
    """Test NFT minting."""
    with patch.object(agent.blockchain, 'wallet', mock_wallet):
        tx_hash = await agent.mint_nft(
            collection_address="0x456",
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
        
        assert isinstance(token, Token)
        assert token.name == "Test Token"
        assert token.symbol == "TST"
        assert token.contract_address == "0x789"

@pytest.mark.asyncio
async def test_get_balance(agent, mock_wallet):
    """Test getting wallet balances."""
    with patch.object(agent.blockchain, 'wallet', mock_wallet):
        balances = await agent.get_balance("eth")
        assert balances["address"] == "0x789"
        assert balances["balance"] == "1.5"

@pytest.mark.asyncio
async def test_transfer_assets(agent, mock_wallet):
    """Test asset transfer."""
    with patch.object(agent.blockchain, 'wallet', mock_wallet):
        tx_hash = await agent.transfer_assets(
            amount="1.0",
            asset_id="eth",
            destination="0x789"
        )
        assert tx_hash == "0xtx123"

@pytest.mark.asyncio
async def test_wrap_eth(agent, mock_wallet):
    """Test wrapping ETH to WETH."""
    with patch.object(agent.blockchain, 'wallet', mock_wallet):
        tx_hash = await agent.wrap_eth("1000000000000000000")  # 1 ETH in wei
        assert tx_hash == "0xwrap456"