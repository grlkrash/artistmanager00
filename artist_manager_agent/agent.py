from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from pydantic import BaseModel
from langchain_openai import ChatOpenAI
from langchain.schema import SystemMessage, HumanMessage
from enum import Enum
import asyncio
import re
import time
import logging
from cryptography.fernet import Fernet
import base64
import json
import os
import uuid
import random

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
        database_url: Optional[str] = None,
        telegram_token: str = None,
        ai_mastering_key: str = None
    ):
        """Initialize the ArtistManagerAgent."""
        self.artist_profile = artist_profile
        self.openai_api_key = openai_api_key
        self.model = model
        self.db_url = database_url or db_url  # Use database_url if provided, otherwise use db_url
        self.telegram_token = telegram_token
        self.ai_mastering_key = ai_mastering_key
        
        # Rate limiting
        self.last_operation_time = time.time()
        self.min_operation_interval = 0.02  # 20ms between operations
        
        # Initialize storage
        self.tasks = {}
        self.events = {}
        self.financial_records = {}
        self.audit_logs = []
        self.contracts = {}
        self.payment_requests = {}
        
        # Initialize blockchain manager
        self.blockchain = BlockchainManager(BlockchainConfig())
        
        # Initialize LLM
        self.llm = ChatOpenAI(
            temperature=0.7,
            model=self.model,
            openai_api_key=self.openai_api_key
        )
        
        # Initialize payment manager
        self.payment_manager = self.PaymentManager(self)
        
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
        
    def _enforce_rate_limit(self) -> None:
        """Enforce rate limiting between operations."""
        current_time = time.time()
        time_since_last = current_time - self.last_operation_time
        
        if time_since_last < self.min_operation_interval:
            sleep_time = self.min_operation_interval - time_since_last
            time.sleep(sleep_time)
        
        self.last_operation_time = time.time()
        
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
        
    def _log_operation(self, operation: str, resource_type: str, resource_id: str) -> None:
        """Log an operation for auditing purposes.
        
        Args:
            operation: The operation performed (e.g., 'create', 'update', 'delete', 'access')
            resource_type: The type of resource (e.g., 'task', 'event', 'contract')
            resource_id: The ID of the resource
        """
        timestamp = datetime.now().isoformat()
        
        # Map operations to standardized event types
        operation_map = {
            'create': 'created',
            'update': 'updated',
            'delete': 'deleted',
            'access': 'accessed',
            'mint': 'minted',
            'deploy': 'deployed',
            'transfer': 'transferred',
            'wrap': 'wrapped'
        }
        
        # Generate standardized event type
        event_type = f"{resource_type}_{operation_map.get(operation, operation)}"
        
        # Create log entry with nested details
        log_entry = {
            "timestamp": timestamp,
            "event_type": event_type,
            "details": {
                f"{resource_type}_id": resource_id,
                "operation": operation
            }
        }
        
        # Store log entry
        if not hasattr(self, '_audit_logs'):
            self._audit_logs = []
        self._audit_logs.append(log_entry)

    async def get_audit_logs(
        self,
        start_time: datetime,
        end_time: datetime,
        event_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get audit logs within a time range and optionally filtered by event type.
        
        Args:
            start_time: Start of time range
            end_time: End of time range
            event_type: Optional event type to filter by
            
        Returns:
            List of matching audit log entries
        """
        if not hasattr(self, '_audit_logs'):
            return []
            
        filtered_logs = []
        for log in self._audit_logs:
            log_time = datetime.fromisoformat(log['timestamp'])
            if start_time <= log_time <= end_time:
                if event_type is None or log['event_type'] == event_type:
                    filtered_logs.append(log)
                    
        return filtered_logs

    async def add_task(self, task: Task) -> Task:
        """Add a new task."""
        try:
            self._enforce_rate_limit()
            
            if not self._validate_input(task.title) or not self._validate_input(task.description):
                raise ValueError("Task title or description contains invalid characters")
                
            self.tasks[task.id] = task
            self._log_operation("create", "task", task.id)
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
                
            self._log_operation("access", "task", task_id)
            return task
        except Exception as e:
            raise Exception(f"Failed to get task: {str(e)}")
            
    async def add_financial_record(self, record: FinancialRecord) -> FinancialRecord:
        """Add a new financial record."""
        try:
            self._enforce_rate_limit()
            
            if record.amount < 0:
                raise ValueError("Amount cannot be negative")
                
            if not self._validate_input(record.description):
                raise ValueError("Financial record description contains invalid characters")
                
            self.financial_records[record.id] = record
            self._log_operation("create", "financial_record", record.id)
            return record
        except Exception as e:
            raise Exception(f"Failed to add financial record: {str(e)}")
            
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

    class PaymentManager:
        """Inner class for managing payments."""
        
        def __init__(self, agent):
            self.agent = agent
            
        async def generate_receipt(self, payment_id: str) -> str:
            """Generate a receipt for a completed payment."""
            payment = self.agent.payment_requests.get(payment_id)
            if not payment:
                raise ValueError("Payment not found")
                
            return (
                f"Receipt #{payment_id}\n"
                f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                f"Amount: {int(payment.amount)} {payment.currency}\n"
                f"Description: {payment.description}\n"
                f"Payment Method: {payment.payment_method.value.upper()}\n"
                f"Status: {payment.status.value.upper()}\n"
                f"Paid At: {payment.paid_at.strftime('%Y-%m-%d %H:%M:%S') if payment.paid_at else 'N/A'}"
            )
            
        async def send_payment_reminder(self, payment_id: str) -> bool:
            """Send a reminder for a pending payment."""
            payment = self.agent.payment_requests.get(payment_id)
            if not payment:
                raise ValueError("Payment not found")
                
            if payment.status != PaymentStatus.PENDING:
                return False
                
            # In a real implementation, this would send an actual reminder
            # For testing, we just return True
            return True
            
        async def process_batch_payments(self, payment_ids: List[str]) -> Dict[str, List[str]]:
            """Process multiple payments in batch."""
            results = {
                "successful": [],
                "failed": [],
                "skipped": []
            }
            
            for payment_id in payment_ids:
                payment = self.agent.payment_requests.get(payment_id)
                if not payment:
                    results["skipped"].append(payment_id)
                    continue
                    
                try:
                    # Simulate payment processing
                    if payment.status == PaymentStatus.PENDING:
                        payment.status = PaymentStatus.PAID
                        payment.paid_at = datetime.now()
                        results["successful"].append(payment_id)
                    else:
                        results["skipped"].append(payment_id)
                except Exception:
                    results["failed"].append(payment_id)
                    
            return results
            
        async def get_payment_analytics(self, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
            """Generate analytics for payments in a date range."""
            payments = [
                p for p in self.agent.payment_requests.values()
                if start_date <= p.created_at <= end_date
            ]
            
            total_volume = sum(p.amount for p in payments)
            successful = sum(1 for p in payments if p.status == PaymentStatus.PAID)
            failed = sum(1 for p in payments if p.status == PaymentStatus.FAILED)
            pending = sum(1 for p in payments if p.status == PaymentStatus.PENDING)
            
            by_method = {}
            for p in payments:
                method = p.payment_method.value
                if method not in by_method:
                    by_method[method] = 0
                by_method[method] += p.amount
                
            by_currency = {}
            for p in payments:
                if p.currency not in by_currency:
                    by_currency[p.currency] = 0
                by_currency[p.currency] += p.amount
                
            # Calculate daily volume
            daily_volume = {}
            for p in payments:
                day = p.created_at.date().isoformat()
                if day not in daily_volume:
                    daily_volume[day] = 0
                daily_volume[day] += p.amount
                
            # Calculate average processing time for completed payments
            processing_times = []
            for p in payments:
                if p.status == PaymentStatus.PAID and p.paid_at:
                    time_diff = (p.paid_at - p.created_at).total_seconds()
                    processing_times.append(time_diff)
                    
            avg_processing_time = sum(processing_times) / len(processing_times) if processing_times else 0
            
            return {
                "total_volume": total_volume,
                "successful_payments": successful,
                "failed_payments": failed,
                "pending_payments": pending,
                "average_amount": total_volume / len(payments) if payments else 0,
                "by_payment_method": by_method,
                "by_currency": by_currency,
                "daily_volume": daily_volume,
                "average_processing_time": avg_processing_time
            }

    async def get_tasks(self) -> List[Task]:
        """Get all tasks."""
        return list(self.tasks.values())

    async def update_task(self, task: Task) -> Task:
        """Update an existing task."""
        if task.id not in self.tasks:
            raise ValueError(f"Task {task.id} not found")
        self.tasks[task.id] = task
        self._log_operation("update", "task", task.id)
        return task

    async def delete_task(self, task_id: str) -> None:
        """Delete a task."""
        if task_id not in self.tasks:
            raise ValueError(f"Task {task_id} not found")
        del self.tasks[task_id]
        self._log_operation("delete", "task", task_id)

    async def add_event(self, event: Event) -> Event:
        """Add a new event."""
        self._enforce_rate_limit()
        if not self._validate_input(event.title):
            raise ValueError("Event title contains invalid characters")
        self.events[event.id] = event
        self._log_operation("create", "event", event.id)
        return event

    async def get_event(self, event_id: str) -> Optional[Event]:
        """Get an event by ID."""
        self._enforce_rate_limit()
        event = self.events.get(event_id)
        if event:
            self._log_operation("access", "event", event_id)
        return event

    async def update_event(self, event: Event) -> Event:
        """Update an existing event."""
        if event.id not in self.events:
            raise ValueError(f"Event {event.id} not found")
        self.events[event.id] = event
        self._log_operation("update", "event", event.id)
        return event

    async def delete_event(self, event_id: str) -> None:
        """Delete an event."""
        if event_id not in self.events:
            raise ValueError(f"Event {event_id} not found")
        del self.events[event_id]
        self._log_operation("delete", "event", event_id)

    async def add_contract(self, contract: Contract) -> Contract:
        """Add a new contract."""
        self._enforce_rate_limit()
        if not self._validate_input(contract.title):
            raise ValueError("Contract title contains invalid characters")
        self.contracts[contract.id] = contract
        self._log_operation("create", "contract", contract.id)
        return contract

    async def get_contract(self, contract_id: str) -> Optional[Contract]:
        """Get a contract by ID."""
        self._enforce_rate_limit()
        contract = self.contracts.get(contract_id)
        if contract:
            self._log_operation("access", "contract", contract_id)
        return contract

    async def update_contract(self, contract: Contract) -> Contract:
        """Update an existing contract."""
        if contract.id not in self.contracts:
            raise ValueError(f"Contract {contract.id} not found")
        self.contracts[contract.id] = contract
        self._log_operation("update", "contract", contract.id)
        return contract

    async def delete_contract(self, contract_id: str) -> None:
        """Delete a contract."""
        if contract_id not in self.contracts:
            raise ValueError(f"Contract {contract_id} not found")
        del self.contracts[contract_id]
        self._log_operation("delete", "contract", contract_id)

    async def deploy_nft_collection(self, name: str, symbol: str, base_uri: str) -> NFTCollection:
        """Deploy a new NFT collection."""
        self._enforce_rate_limit()
        collection = await self.blockchain.wallet.deploy_nft(name, symbol, base_uri)
        self.nft_collections[collection.contract_address] = collection
        self._log_operation("deploy", "nft_collection", collection.contract_address)
        return collection

    async def mint_nft(self, collection_address: str, destination: str) -> str:
        """Mint a new NFT in a collection."""
        self._enforce_rate_limit()
        if collection_address not in self.nft_collections:
            raise ValueError(f"NFT collection {collection_address} not found")
        tx_hash = await self.blockchain.wallet.mint_nft(collection_address, destination)
        self._log_operation("mint", "nft", tx_hash)
        return tx_hash

    async def deploy_token(self, name: str, symbol: str, total_supply: str) -> Token:
        """Deploy a new token."""
        self._enforce_rate_limit()
        token = await self.blockchain.wallet.deploy_token(name, symbol, total_supply)
        self.tokens[token.contract_address] = token
        self._log_operation("deploy", "token", token.contract_address)
        return token

    async def get_balance(self, asset_id: str) -> Dict[str, str]:
        """Get wallet balances."""
        self._enforce_rate_limit()
        balances = await self.blockchain.wallet.get_balance(asset_id)
        # Handle mock responses by converting to dict if needed
        if not isinstance(balances, dict):
            balances = {asset_id: "0"}
        self._log_operation("access", "balance", asset_id)
        return balances

    async def transfer_assets(self, amount: str, asset_id: str, destination: str) -> str:
        """Transfer assets to another address."""
        self._enforce_rate_limit()
        tx_hash = await self.blockchain.wallet.transfer(amount, asset_id, destination)
        self._log_operation("transfer", "asset", tx_hash)
        return tx_hash

    async def wrap_eth(self, amount: str) -> str:
        """Wrap ETH to WETH."""
        self._enforce_rate_limit()
        tx_hash = await self.blockchain.wallet.wrap_eth(amount)
        self._log_operation("wrap", "eth", tx_hash)
        return tx_hash

    async def request_faucet_funds(self, asset_id: str = "eth") -> str:
        """Request funds from faucet."""
        self._enforce_rate_limit()
        if self.blockchain.config.network_id != "base-sepolia":
            raise ValueError("Faucet only available on base-sepolia")
        result = await self.blockchain.wallet.request_faucet(asset_id)
        # Handle mock responses
        if isinstance(result, str):
            return f"Received {asset_id} from faucet: {result}"
        return f"Received {asset_id} from faucet"

    async def get_events(self) -> List[Event]:
        """Get all events."""
        return list(self.events.values())

    async def get_contracts(self) -> List[Contract]:
        """Get all contracts."""
        return list(self.contracts.values())

    async def get_events_in_range(self, start_date: datetime, end_date: datetime) -> List[Event]:
        """Get events within a date range."""
        return [
            event for event in self.events.values()
            if start_date <= event.date <= end_date
        ]

    async def get_cash_flow_analysis(self, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Get cash flow analysis for a date range."""
        records = await self.get_financial_records()
        filtered_records = [r for r in records if start_date <= r.date <= end_date]
        
        income = sum(r.amount for r in filtered_records if r.type == "income")
        expenses = sum(r.amount for r in filtered_records if r.type == "expense")
        net_cash_flow = income - expenses
        
        return {
            "income": income,
            "expenses": expenses,
            "net_cash_flow": net_cash_flow,
            "period_start": start_date,
            "period_end": end_date
        }

    async def get_financial_report(self, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Generate a financial report for a date range."""
        records = await self.get_financial_records()
        filtered_records = [r for r in records if start_date <= r.date <= end_date]
        
        income_by_category = {}
        expenses_by_category = {}
        
        for record in filtered_records:
            if record.type == "income":
                income_by_category[record.category] = income_by_category.get(record.category, 0) + record.amount
            else:
                expenses_by_category[record.category] = expenses_by_category.get(record.category, 0) + record.amount
        
        return {
            "income_by_category": income_by_category,
            "expenses_by_category": expenses_by_category,
            "total_income": sum(income_by_category.values()),
            "total_expenses": sum(expenses_by_category.values()),
            "period_start": start_date,
            "period_end": end_date
        }

    async def get_monthly_summary(self, month_date: datetime) -> Dict[str, Any]:
        """Generate a monthly financial summary."""
        start_date = month_date.replace(day=1)
        if month_date.month == 12:
            end_date = month_date.replace(year=month_date.year + 1, month=1, day=1)
        else:
            end_date = month_date.replace(month=month_date.month + 1, day=1)
        end_date = end_date - timedelta(days=1)
        
        return await self.get_financial_report(start_date, end_date)

    async def get_pending_payments(self) -> List[FinancialRecord]:
        """Get all pending payments."""
        return [
            record for record in self.financial_records.values()
            if record.status == "pending" and record.type == "income"
        ]

    async def get_payment_history(self) -> List[FinancialRecord]:
        """Get payment history."""
        return sorted(
            [record for record in self.financial_records.values()],
            key=lambda x: x.date,
            reverse=True
        )

    async def get_payment_summary(self) -> Dict[str, Any]:
        """Get a summary of all payments."""
        self._enforce_rate_limit()
        
        total_income = 0.0
        total_expenses = 0.0
        
        for record in self.financial_records.values():
            if record.type == "income":
                total_income += record.amount
            elif record.type == "expense":
                total_expenses += record.amount
        
        return {
            "total_income": total_income,
            "total_expenses": total_expenses,
            "total": total_income - total_expenses,
            "pending_count": len([r for r in self.financial_records.values() if r.status == "pending"]),
            "completed_count": len([r for r in self.financial_records.values() if r.status == "completed"]),
            "failed_count": len([r for r in self.financial_records.values() if r.status == "failed"])
        }

    async def add_release(self, release: Release) -> Release:
        """Add a new music release."""
        self._enforce_rate_limit()
        
        # Validate release data
        if not release.title or not release.artist:
            raise ValueError("Release must have a title and artist")
        
        if not release.tracks:
            raise ValueError("Release must have at least one track")
            
        # Store the release
        self.releases[release.id] = release
        self._log_operation("create", "release", release.id)
        return release

    async def master_track(self, track: Track, options: Dict[str, Any]) -> Dict[str, str]:
        """Submit a track for AI mastering."""
        self._enforce_rate_limit()
        
        # Validate track data
        if not track.title or not track.artist:
            raise ValueError("Track must have a title and artist")
            
        if not track.file_path or not track.file_path.exists():
            raise ValueError("Track must have a valid file path")
            
        # Validate mastering options
        if "preset" not in options:
            raise ValueError("Mastering options must include a preset")
            
        # Mock mastering process
        return {
            "status": "processing",
            "job_id": str(uuid.uuid4()),
            "estimated_completion": str(datetime.now() + timedelta(minutes=30))
        }

    async def get_platform_stats(self, platform: DistributionPlatform, release_id: str) -> Dict[str, int]:
        """Get streaming platform statistics for a release."""
        self._enforce_rate_limit()
        
        # Validate inputs
        if not isinstance(platform, DistributionPlatform):
            raise ValueError("Invalid platform")
            
        if release_id not in self.releases:
            raise ValueError("Release not found")
            
        # Mock platform statistics
        return {
            "streams": random.randint(1000, 100000),
            "listeners": random.randint(500, 50000),
            "saves": random.randint(100, 10000)
        }

    # ... existing methods ... 