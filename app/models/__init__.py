# /home/myalgo/algo-trader/app/models/__init__.py

from app.db.base_class import Base

# Legacy models
from .user import User
from .broker_credentials import BrokerCredentials
from .bot_instance import BotInstance
from .subscription import Subscription
from .payment_method import PaymentMethod
from .invoice import Invoice
from .bot_activity_snapshot import BotActivitySnapshot
from .trade_record import TradeRecord
from .admin_action_log import AdminActionLog
from .system_settings import SystemSettings
from .support_ticket import SupportTicket
from .checkout_session import CheckoutSession
from .trial_user import TrialUser
from .red_folder_event import RedFolderEvent

# New signal service models
from .ml_signal_history import MLSignalHistory
from .ml_trade_execution import MLTradeExecution
from .ml_model_performance import MLModelPerformance

# Enums
from .enums import (
    UserRole,
    BrokerName,
    Environment,
    BotStatus,
    PlanTier,
    SubscriptionStatus,
    PaymentBrand,
    InvoiceStatus,
    TradeSide,
    AdminActionTargetType,
    SupportTicketStatus,
)

__all__ = [
    "Base",  # ✅ Needed for Alembic to work
    # Legacy models
    "User",
    "BrokerCredentials",
    "BotInstance",
    "Subscription",
    "PaymentMethod",
    "Invoice",
    "BotActivitySnapshot",
    "TradeRecord",
    "AdminActionLog",
    "SystemSettings",
    "SupportTicket",
    "CheckoutSession",
    "TrialUser",
    "RedFolderEvent",
    # New signal service models
    "MLSignalHistory",
    "MLTradeExecution",
    "MLModelPerformance",
    # Enums
    "UserRole",
    "BrokerName",
    "Environment",
    "BotStatus",
    "PlanTier",
    "SubscriptionStatus",
    "PaymentBrand",
    "InvoiceStatus",
    "TradeSide",
    "AdminActionTargetType",
    "SupportTicketStatus",
]
