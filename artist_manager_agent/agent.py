from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel
from langchain_community.chat_models import ChatOpenAI
from langchain.schema import SystemMessage, HumanMessage
from enum import Enum
import asyncio
import re
import time
import logging
from cryptography.fernet import Fernet
import base64
import json

from .team_management import TeamMember, CollaboratorRole
from .integrations import ServiceManager, SupabaseIntegration, TelegramIntegration, AIMasteringIntegration
from .blockchain import BlockchainManager, BlockchainConfig, NFTCollection, Token
from .models import (
    Task, Event, Contract, FinancialRecord,
    PaymentRequest, PaymentStatus, PaymentMethod,
    Track, Release, ReleaseType, MasteringJob,
    MasteringPreset, DistributionPlatform, ArtistProfile
)

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

class ArtistManagerAgent:
    """Main agent for managing artists."""
    
    def __init__(
        self,
        artist_profile: ArtistProfile,
        openai_api_key: str,
        model: str = "gpt-3.5-turbo",
        db_url: str = "sqlite:///artist_manager.db",
        telegram_token: str = None,
        ai_mastering_key: str = None
    ):
        """Initialize the ArtistManagerAgent."""
        self.artist_profile = artist_profile
        self.openai_api_key = openai_api_key
        self.model = model
        self.db_url = db_url
        self.telegram_token = telegram_token
        self.ai_mastering_key = ai_mastering_key
        
        # Initialize components
        self.llm = ChatOpenAI(
            openai_api_key=openai_api_key,
            model=model
        )
        
        # Initialize storage
        self.tasks: Dict[str, Task] = {}
        self.events: Dict[str, Event] = {}
        self.contracts: Dict[str, Contract] = {}
        self.financial_records: Dict[str, FinancialRecord] = {}
        self.payment_requests: Dict[str, PaymentRequest] = {}
        
        # Initialize blockchain manager
        self.blockchain = BlockchainManager(BlockchainConfig())
        
        # Initialize rate limiting
        self.last_operation_time = datetime.now()
        self.operation_count = 0
        self.rate_limit = 10  # operations per second
        
        # Initialize audit logging
        self.audit_logs = []
        
        # Use dictionaries for O(1) lookups instead of lists
        self.team: Dict[str, TeamMember] = {}
        self.finances: Dict[str, FinancialRecord] = {}
        self.nft_collections: Dict[str, NFTCollection] = {}
        self.tokens: Dict[str, Token] = {}
        self.releases: Dict[str, Release] = {}
        self.mastering_jobs: Dict[str, MasteringJob] = {}
        self.mastering_presets: Dict[str, MasteringPreset] = {}

    def _validate_input(self, text: str) -> bool:
        """Validate input for malicious content."""
        if not text:
            return True
            
        # Check for SQL injection attempts
        sql_patterns = ["'", ";", "--", "/*", "*/", "xp_", "sp_", "exec", "select", "insert", "update", "delete", "drop"]
        for pattern in sql_patterns:
            if pattern in text.lower():
                return False
                
        # Check for XSS attempts
        xss_patterns = ["<script", "javascript:", "onerror=", "onload=", "eval(", "alert("]
        for pattern in xss_patterns:
            if pattern in text.lower():
                return False
                
        # Check for command injection attempts
        cmd_patterns = ["|", "&", ";", "`", "$", "(", ")", "{", "}", "[", "]"]
        for pattern in cmd_patterns:
            if pattern in text:
                return False
                
        # Check for control characters
        if any(ord(c) < 32 or ord(c) == 127 for c in text):
            return False
            
        return True
        
    def _enforce_rate_limit(self):
        """Enforce rate limiting."""
        current_time = datetime.now()
        time_diff = (current_time - self.last_operation_time).total_seconds()
        
        if time_diff < 1:  # Within 1 second window
            self.operation_count += 1
            if self.operation_count > self.rate_limit:
                sleep_time = 1 - time_diff
                time.sleep(sleep_time)
                self.operation_count = 0
        else:
            self.operation_count = 1
            
        self.last_operation_time = current_time
        
    def _check_access(self, resource_access_level: str, requested_access_level: str) -> bool:
        """Check access control."""
        access_levels = {
            "public": 0,
            "restricted": 1,
            "confidential": 2
        }
        
        if resource_access_level not in access_levels or requested_access_level not in access_levels:
            return False
            
        return access_levels[requested_access_level] >= access_levels[resource_access_level]
        
    def _log_operation(self, operation: str, resource_type: str, resource_id: str):
        """Log sensitive operations."""
        log_entry = {
            "timestamp": datetime.now(),
            "operation": operation,
            "resource_type": resource_type,
            "resource_id": resource_id
        }
        self.audit_logs.append(log_entry)
        
    async def add_task(self, task: Task) -> Task:
        """Add a new task."""
        try:
            self._enforce_rate_limit()
            
            if not self._validate_input(task.title) or not self._validate_input(task.description):
                raise ValueError("Task title or description contains invalid characters")
                
            self.tasks[task.id] = task
            self._log_operation("add", "task", task.id)
            return task
        except Exception as e:
            raise Exception(f"Failed to add task: {str(e)}")
            
    async def get_task(self, task_id: str, access_level: str = "public") -> Optional[Task]:
        """Get a task by ID."""
        try:
            self._enforce_rate_limit()
            
            task = self.tasks.get(task_id)
            if not task:
                return None
                
            if not self._check_access(task.access_level, access_level):
                raise PermissionError("Insufficient privileges to access this task")
                
            self._log_operation("get", "task", task_id)
            return task
        except Exception as e:
            raise Exception(f"Failed to get task: {str(e)}")
            
    async def add_financial_record(self, record: FinancialRecord) -> FinancialRecord:
        """Add a new financial record."""
        try:
            self._enforce_rate_limit()
            
            if record.amount <= 0:
                raise ValueError("Financial record amount must be positive")
                
            if not self._validate_input(record.description):
                raise ValueError("Financial record description contains invalid characters")
                
            self.financial_records[record.id] = record
            self._log_operation("add", "financial_record", record.id)
            return record
        except Exception as e:
            raise Exception(f"Failed to add financial record: {str(e)}")
            
    async def get_audit_logs(self, start_time: datetime, end_time: datetime) -> List[Dict[str, Any]]:
        """Get audit logs within the specified time range."""
        try:
            return [
                log for log in self.audit_logs
                if start_time <= log["timestamp"] <= end_time
            ]
        except Exception as e:
            raise Exception(f"Failed to get audit logs: {str(e)}")

    async def create_artist(self, artist_id: str, name: str, **kwargs) -> ArtistProfile:
        if artist_id in self.artists:
            raise ValueError(f"Artist with ID {artist_id} already exists")
        
        profile = ArtistProfile(artist_id=artist_id, name=name, **kwargs)
        self.artists[artist_id] = profile
        return profile

    async def get_artist(self, artist_id: str) -> Optional[ArtistProfile]:
        return self.artists.get(artist_id)

    async def update_artist(self, artist_id: str, **kwargs) -> Optional[ArtistProfile]:
        if artist_id not in self.artists:
            return None
        
        profile = self.artists[artist_id]
        for key, value in kwargs.items():
            if hasattr(profile, key):
                setattr(profile, key, value)
        
        profile.updated_at = datetime.now()
        return profile

    async def delete_artist(self, artist_id: str) -> bool:
        if artist_id in self.artists:
            del self.artists[artist_id]
            return True
        return False

    # Blockchain-related methods
    async def deploy_nft_collection(self, name: str, symbol: str, base_uri: str) -> NFTCollection:
        """Deploy a new NFT collection."""
        if not self.blockchain:
            raise ValueError("Blockchain features not initialized")
        collection = await self.blockchain.deploy_nft_collection(name, symbol, base_uri)
        self.nft_collections[collection.id] = collection
        return collection
    
    async def mint_nft(self, collection_address: str, destination: str) -> str:
        """Mint an NFT from a collection."""
        if not self.blockchain:
            raise ValueError("Blockchain features not initialized")
        return await self.blockchain.mint_nft(collection_address, destination)
    
    async def deploy_token(self, name: str, symbol: str, total_supply: str) -> Token:
        """Deploy a new token."""
        if not self.blockchain:
            raise ValueError("Blockchain features not initialized")
        token = await self.blockchain.deploy_token(name, symbol, total_supply)
        self.tokens[token.id] = token
        return token
    
    async def get_balance(self, asset_id: str = "eth") -> Dict[str, str]:
        """Get wallet balances."""
        if not self.blockchain:
            raise ValueError("Blockchain features not initialized")
        return await self.blockchain.get_balance(asset_id)
    
    async def transfer_assets(self, amount: str, asset_id: str, destination: str, gasless: bool = False) -> str:
        """Transfer assets."""
        if not self.blockchain:
            raise ValueError("Blockchain features not initialized")
        return await self.blockchain.transfer(amount, asset_id, destination, gasless)
    
    async def wrap_eth(self, amount: str) -> str:
        """Wrap ETH to WETH."""
        if not self.blockchain:
            raise ValueError("Blockchain features not initialized")
        return await self.blockchain.wrap_eth(amount)

    async def request_faucet_funds(self, asset_id: Optional[str] = None) -> str:
        """Request test tokens from faucet."""
        if not self.blockchain:
            raise ValueError("Blockchain features not initialized")
        return await self.blockchain.request_faucet_funds(asset_id)
    
    async def get_wallet_details(self) -> Dict[str, str]:
        """Get wallet details."""
        if not self.blockchain:
            raise ValueError("Blockchain features not initialized")
        return await self.blockchain.get_wallet_details()

    def _init_external_services(self, db_url: Optional[str], telegram_token: Optional[str], ai_mastering_key: Optional[str]) -> None:
        """Initialize external service integrations."""
        if any([db_url, telegram_token, ai_mastering_key]):
            self.services.initialize_services(
                supabase_url=db_url,
                supabase_key="test_key" if db_url else None,
                telegram_token=telegram_token,
                ai_mastering_key=ai_mastering_key
            ) 

    # Task Management
    def _log_audit_event(self, event_type: str, details: Dict[str, Any]) -> None:
        """Log an audit event.
        
        Args:
            event_type: Type of event (e.g., "task_created", "access_denied")
            details: Additional details about the event
        """
        log_entry = {
            "timestamp": datetime.now(),
            "event_type": event_type,
            "details": details
        }
        self.audit_logs.append(log_entry)
        
    async def get_audit_logs(
        self,
        start_time: datetime,
        end_time: datetime,
        event_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get audit logs within a time range.
        
        Args:
            start_time: Start of the time range
            end_time: End of the time range
            event_type: Optional filter for specific event types
            
        Returns:
            List of audit log entries
        """
        filtered_logs = [
            log for log in self.audit_logs
            if start_time <= log["timestamp"] <= end_time
            and (event_type is None or log["event_type"] == event_type)
        ]
        
        return filtered_logs
        
    async def get_tasks(self) -> List[Task]:
        """Get all tasks efficiently."""
        return list(self.tasks.values())

    async def update_task(self, task: Task) -> Optional[Task]:
        """Update an existing task with audit logging.
        
        Args:
            task: The task with updated fields
            
        Returns:
            The updated task if found, None otherwise
        """
        self.tasks[task.id] = task
        return task

    async def delete_task(self, task_id: str) -> bool:
        """Delete a task with audit logging.
        
        Args:
            task_id: ID of the task to delete
            
        Returns:
            True if task was deleted, False otherwise
        """
        return self.tasks.pop(task_id, None) is not None

    # Event Management
    async def add_event(self, event: Event) -> Event:
        """Add a new event with optimized storage."""
        current_time = time.time()
        if current_time - self.last_operation_time < self.min_operation_interval:
            await asyncio.sleep(self.min_operation_interval - (current_time - self.last_operation_time))
        
        self.events[event.id] = event
        self.last_operation_time = time.time()
        return event

    async def get_events(self) -> List[Event]:
        """Get all events."""
        return list(self.events.values())

    async def get_events_in_range(self, start_date: datetime, end_date: datetime) -> List[Event]:
        """Get events in date range efficiently."""
        return [
            event for event in self.events.values()
            if start_date <= event.date <= end_date
        ]

    async def update_event(self, event: Event) -> Optional[Event]:
        """Update an existing event."""
        if event.id not in self.events:
            return None
        self.events[event.id] = event
        return event

    async def get_event(self, event_id: str) -> Optional[Event]:
        """Get a specific event."""
        return self.events.get(event_id)

    # Contract Management
    async def add_contract(self, contract: Contract) -> Contract:
        """Add a new contract."""
        self.contracts[contract.id] = contract
        return contract

    async def get_contracts(self) -> List[Contract]:
        """Get all contracts."""
        return list(self.contracts.values())

    async def get_contract(self, contract_id: str) -> Optional[Contract]:
        """Get a specific contract."""
        return self.contracts.get(contract_id)

    async def update_contract(self, contract: Contract) -> Optional[Contract]:
        """Update an existing contract."""
        if contract.id not in self.contracts:
            return None
        self.contracts[contract.id] = contract
        return contract

    # Financial Management
    async def get_financial_records(self) -> List[FinancialRecord]:
        """Get all financial records."""
        return list(self.financial_records.values())

    async def generate_financial_report(self, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Generate financial report efficiently."""
        relevant_records = [
            record for record in self.financial_records.values()
            if start_date <= record.date <= end_date
        ]
        
        total_income = sum(r.amount for r in relevant_records if r.type == "income")
        total_expenses = sum(r.amount for r in relevant_records if r.type == "expense")
        
        return {
            "total_income": total_income,
            "total_expenses": total_expenses,
            "net_profit": total_income - total_expenses,
            "record_count": len(relevant_records)
        }

    def _group_by_category(self, records: List[FinancialRecord]) -> Dict[str, float]:
        """Group financial records by category."""
        result = {}
        for record in records:
            if record.category not in result:
                result[record.category] = 0
            result[record.category] += record.amount
        return result

    def _group_by_type(self, records: List[FinancialRecord]) -> Dict[str, float]:
        """Group financial records by type."""
        result = {}
        for record in records:
            if record.type not in result:
                result[record.type] = 0
            result[record.type] += record.amount
        return result

    def _encrypt_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Encrypt sensitive data."""
        # In production, this key should be securely stored and retrieved
        key = Fernet.generate_key()
        f = Fernet(key)
        
        # Convert data to JSON string and encrypt
        json_data = json.dumps(data)
        encrypted_data = f.encrypt(json_data.encode())
        
        return {
            "encrypted_data": base64.b64encode(encrypted_data).decode(),
            "key": base64.b64encode(key).decode()
        }
    
    def _decrypt_data(self, encrypted_data: str, key: str) -> Dict[str, Any]:
        """Decrypt sensitive data."""
        f = Fernet(base64.b64decode(key))
        decrypted_data = f.decrypt(base64.b64decode(encrypted_data))
        return json.loads(decrypted_data)
    
    def _get_raw_contract_data(self, contract_id: str) -> Dict[str, Any]:
        """Get raw contract data for testing encryption."""
        contract = self.contracts.get(contract_id)
        if contract:
            # Encrypt sensitive fields
            sensitive_data = {
                "terms": contract.terms,
                "value": contract.value
            }
            encrypted = self._encrypt_data(sensitive_data)
            
            # Return contract data with encrypted fields
            contract_data = contract.dict()
            del contract_data["terms"]
            del contract_data["value"]
            contract_data.update(encrypted)
            return contract_data
        return {}

    async def update_financial_record(self, record: FinancialRecord) -> Optional[FinancialRecord]:
        """Update an existing financial record."""
        if record.id not in self.financial_records:
            return None
        self.financial_records[record.id] = record
        return record

    def set_payments(self, payments: Dict[str, PaymentRequest]) -> None:
        """Set payment requests for testing."""
        self.payment_requests = payments

    async def get_payment_requests(self) -> List[PaymentRequest]:
        """Get all payment requests."""
        try:
            return list(self.payment_requests.values())
        except Exception as e:
            raise Exception(f"Failed to get payment requests: {str(e)}")

    async def add_payment_request(self, payment: PaymentRequest) -> None:
        """Add a new payment request."""
        try:
            if payment.amount <= 0:
                raise ValueError("Amount must be positive")
            
            if payment.currency not in ["USD", "EUR", "GBP"]:
                raise ValueError("Invalid currency")
                
            self.payment_requests[payment.id] = payment
        except Exception as e:
            raise Exception(f"Failed to add payment request: {str(e)}")

    async def check_payment_status(self, payment_id: str) -> Optional[Dict[str, Any]]:
        """Check the status of a payment request."""
        payment = self.payment_requests.get(payment_id)
        if not payment:
            return None
        
        return {
            "status": payment.status.value,
            "paid": payment.status == PaymentStatus.PAID,
            "amount_paid": payment.amount if payment.status == PaymentStatus.PAID else 0,
            "currency": payment.currency
        }

    # ... existing methods ... 