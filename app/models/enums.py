# /home/myalgo/algo-trader/app/models/enums.py

from enum import Enum

class UserRole(str, Enum):
    user = "user"
    admin = "admin"

class BrokerName(str, Enum):
    alpaca = "alpaca"
    oanda = "oanda"

class Environment(str, Enum):
    live = "live"
    demo = "demo"

class BotStatus(str, Enum):
    launched = "launched"
    stopped = "stopped"
    error = "error"

class PlanTier(str, Enum):
    basic = "basic"
    pro = "pro"
    elite = "elite"

class SubscriptionStatus(str, Enum):
    active = "active"
    trialing = "trialing"
    canceled = "canceled"

class PaymentBrand(str, Enum):
    Visa = "Visa"
    Mastercard = "Mastercard"

class InvoiceStatus(str, Enum):
    paid = "paid"
    failed = "failed"
    refunded = "refunded"

class TradeSide(str, Enum):
    buy = "buy"
    sell = "sell"

class AdminActionTargetType(str, Enum):
    bot = "bot"
    user = "user"
    subscription = "subscription"

class SupportTicketStatus(str, Enum):
    open = "open"
    closed = "closed"
    pending = "pending"

