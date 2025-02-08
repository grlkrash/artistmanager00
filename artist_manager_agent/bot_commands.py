from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from typing import Dict, Any, Optional
import re

class BlockchainCommands:
    """Blockchain-related bot commands."""
    
    def __init__(self, agent: Any):
        self.agent = agent
        
    async def handle_wallet(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /wallet command - show wallet details and options."""
        if not self.agent.blockchain:
            await update.message.reply_text(
                "Blockchain features are not initialized. Please check your configuration."
            )
            return
            
        try:
            details = await self.agent.get_wallet_details()
            balances = await self.agent.get_balance()
            
            keyboard = [
                [
                    InlineKeyboardButton("Request Test ETH", callback_data="faucet_eth"),
                    InlineKeyboardButton("Request Test USDC", callback_data="faucet_usdc")
                ],
                [
                    InlineKeyboardButton("Deploy NFT Collection", callback_data="deploy_nft"),
                    InlineKeyboardButton("Deploy Token", callback_data="deploy_token")
                ],
                [
                    InlineKeyboardButton("Transfer Assets", callback_data="transfer"),
                    InlineKeyboardButton("Wrap ETH", callback_data="wrap_eth")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            message = (
                f"🔗 Wallet Details:\n"
                f"Network: {details['network']}\n"
                f"Address: {details['default_address']}\n\n"
                f"💰 Balances:\n"
            )
            
            for addr, balance in balances.items():
                message += f"{addr}: {balance} ETH\n"
                
            await update.message.reply_text(message, reply_markup=reply_markup)
            
        except Exception as e:
            await update.message.reply_text(f"Error getting wallet details: {str(e)}")
    
    async def handle_deploy_nft(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /deploy_nft command."""
        usage = (
            "Usage: /deploy_nft <name> <symbol> <base_uri>\n"
            "Example: /deploy_nft 'My NFT Collection' MYNFT https://api.example.com/metadata/"
        )
        
        if not context.args or len(context.args) < 3:
            await update.message.reply_text(usage)
            return
            
        try:
            name = context.args[0]
            symbol = context.args[1]
            base_uri = context.args[2]
            
            collection = await self.agent.deploy_nft_collection(name, symbol, base_uri)
            await update.message.reply_text(
                f"✨ NFT Collection deployed!\n"
                f"Name: {collection.name}\n"
                f"Symbol: {collection.symbol}\n"
                f"Contract: {collection.contract_address}"
            )
        except Exception as e:
            await update.message.reply_text(f"Error deploying NFT collection: {str(e)}")
    
    async def handle_mint_nft(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /mint_nft command."""
        usage = (
            "Usage: /mint_nft <collection_address> <destination_address>\n"
            "Example: /mint_nft 0x123... 0x456..."
        )
        
        if not context.args or len(context.args) < 2:
            await update.message.reply_text(usage)
            return
            
        try:
            collection = context.args[0]
            destination = context.args[1]
            
            if not re.match(r"^0x[a-fA-F0-9]{40}$", collection):
                await update.message.reply_text("Invalid collection address format")
                return
                
            if not re.match(r"^0x[a-fA-F0-9]{40}$", destination):
                await update.message.reply_text("Invalid destination address format")
                return
            
            tx_hash = await self.agent.mint_nft(collection, destination)
            await update.message.reply_text(f"🎨 NFT minted! Transaction: {tx_hash}")
        except Exception as e:
            await update.message.reply_text(f"Error minting NFT: {str(e)}")
    
    async def handle_deploy_token(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /deploy_token command."""
        usage = (
            "Usage: /deploy_token <name> <symbol> <total_supply>\n"
            "Example: /deploy_token 'My Token' MTK 1000000"
        )
        
        if not context.args or len(context.args) < 3:
            await update.message.reply_text(usage)
            return
            
        try:
            name = context.args[0]
            symbol = context.args[1]
            total_supply = context.args[2]
            
            token = await self.agent.deploy_token(name, symbol, total_supply)
            await update.message.reply_text(
                f"💎 Token deployed!\n"
                f"Name: {token.name}\n"
                f"Symbol: {token.symbol}\n"
                f"Supply: {token.total_supply}\n"
                f"Contract: {token.contract_address}"
            )
        except Exception as e:
            await update.message.reply_text(f"Error deploying token: {str(e)}")
    
    async def handle_transfer(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /transfer command."""
        usage = (
            "Usage: /transfer <amount> <asset_id> <destination> [--gasless]\n"
            "Example: /transfer 1.0 eth 0x123...\n"
            "Example: /transfer 100 usdc 0x123... --gasless"
        )
        
        if not context.args or len(context.args) < 3:
            await update.message.reply_text(usage)
            return
            
        try:
            amount = context.args[0]
            asset_id = context.args[1].lower()
            destination = context.args[2]
            gasless = "--gasless" in context.args
            
            if not re.match(r"^0x[a-fA-F0-9]{40}$", destination):
                await update.message.reply_text("Invalid destination address format")
                return
            
            tx_hash = await self.agent.transfer_assets(amount, asset_id, destination, gasless)
            await update.message.reply_text(
                f"💸 Transfer complete!\n"
                f"Amount: {amount} {asset_id.upper()}\n"
                f"To: {destination}\n"
                f"Transaction: {tx_hash}"
            )
        except Exception as e:
            await update.message.reply_text(f"Error transferring assets: {str(e)}")
    
    async def handle_wrap_eth(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /wrap_eth command."""
        usage = (
            "Usage: /wrap_eth <amount_in_wei>\n"
            "Example: /wrap_eth 1000000000000000000  # 1 ETH"
        )
        
        if not context.args:
            await update.message.reply_text(usage)
            return
            
        try:
            amount = context.args[0]
            tx_hash = await self.agent.wrap_eth(amount)
            await update.message.reply_text(
                f"🔄 ETH wrapped to WETH!\n"
                f"Amount: {amount} wei\n"
                f"Transaction: {tx_hash}"
            )
        except Exception as e:
            await update.message.reply_text(f"Error wrapping ETH: {str(e)}")
    
    async def handle_faucet(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /faucet command."""
        usage = (
            "Usage: /faucet [asset_id]\n"
            "Example: /faucet eth\n"
            "Example: /faucet usdc"
        )
        
        try:
            asset_id = context.args[0].lower() if context.args else None
            
            if asset_id and asset_id not in ["eth", "usdc"]:
                await update.message.reply_text("Only 'eth' and 'usdc' are supported for faucet")
                return
            
            result = await self.agent.request_faucet_funds(asset_id)
            await update.message.reply_text(f"💧 {result}")
        except Exception as e:
            await update.message.reply_text(f"Error requesting faucet funds: {str(e)}")
    
    async def handle_blockchain_callback(self, query: Any, action: str) -> None:
        """Handle blockchain-related callback queries."""
        try:
            if action.startswith("faucet_"):
                asset_id = action.split("_")[1]
                result = await self.agent.request_faucet_funds(asset_id)
                await query.edit_message_text(f"💧 {result}")
                
            elif action == "deploy_nft":
                await query.edit_message_text(
                    "To deploy an NFT collection, use:\n"
                    "/deploy_nft <name> <symbol> <base_uri>"
                )
                
            elif action == "deploy_token":
                await query.edit_message_text(
                    "To deploy a token, use:\n"
                    "/deploy_token <name> <symbol> <total_supply>"
                )
                
            elif action == "transfer":
                await query.edit_message_text(
                    "To transfer assets, use:\n"
                    "/transfer <amount> <asset_id> <destination> [--gasless]"
                )
                
            elif action == "wrap_eth":
                await query.edit_message_text(
                    "To wrap ETH to WETH, use:\n"
                    "/wrap_eth <amount_in_wei>"
                )
                
        except Exception as e:
            await query.edit_message_text(f"Error: {str(e)}")

class BotCommandHandler:
    """Main bot command handler."""
    
    def __init__(self, agent: Any):
        self.agent = agent
        self.blockchain = BlockchainCommands(agent)
        // ... rest of existing code ...
    
    async def register_handlers(self, application: Any) -> None:
        """Register command handlers."""
        // ... existing handlers ...
        
        # Blockchain commands
        application.add_handler(CommandHandler("wallet", self.blockchain.handle_wallet))
        application.add_handler(CommandHandler("deploy_nft", self.blockchain.handle_deploy_nft))
        application.add_handler(CommandHandler("mint_nft", self.blockchain.handle_mint_nft))
        application.add_handler(CommandHandler("deploy_token", self.blockchain.handle_deploy_token))
        application.add_handler(CommandHandler("transfer", self.blockchain.handle_transfer))
        application.add_handler(CommandHandler("wrap_eth", self.blockchain.handle_wrap_eth))
        application.add_handler(CommandHandler("faucet", self.blockchain.handle_faucet))
    
    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle callback queries."""
        query = update.callback_query
        action = query.data
        
        if action.startswith(("faucet_", "deploy_", "transfer", "wrap_")):
            await self.blockchain.handle_blockchain_callback(query, action)
        else:
            // ... existing callback handling ... 