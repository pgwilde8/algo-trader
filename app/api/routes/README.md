# API Routes Directory

This directory contains REST API endpoints for the algo-trader application.

## 📁 Current Routes

### ✅ **Implemented Routes:**

1. **`news_avoidance.py`** - News avoidance API endpoints
   - Base URL: `/api/news-avoidance`
   - 7 endpoints for managing news events and checking trading avoidance

---

## 📋 Legacy Routes (Not Yet Migrated)

The legacy directory (`/home/admintrader/tradermain/app/api/routes`) has 15 route files:

| Route File | Status | Notes |
|-----------|--------|-------|
| `news_avoidance.py` | ✅ **Migrated** | Currently in algo-trader |
| `health.py` | ⚠️ Partial | Basic health endpoint in main.py |
| `auth.py` | ❌ Not migrated | User authentication |
| `users.py` | ❌ Not migrated | User management |
| `bots.py` | ❌ Not migrated | Bot management (478+ lines) |
| `bot_launch.py` | ❌ Not migrated | Bot launching |
| `subscriptions.py` | ❌ Not migrated | Subscription management |
| `checkout.py` | ❌ Not migrated | Payment processing |
| `trade_records.py` | ❌ Not migrated | Trade history |
| `support_tickets.py` | ❌ Not migrated | Support system |
| `admin.py` | ❌ Not migrated | Admin endpoints |
| `trial.py` | ❌ Not migrated | Trial users |
| `strength.py` | ❌ Not migrated | Currency strength |
| `webhooks.py` | ❌ Not migrated | Webhook handlers |
| `launch.py` | ❌ Not migrated | Launch endpoints |

**See `LEGACY_API_ROUTES_SUMMARY.md` for detailed breakdown of what each route does.**

---

## 🚀 Current API Routes

### News Avoidance API (`/api/news-avoidance`)

**Base URL:** `/api/news-avoidance`

#### Endpoints:

1. **GET** `/news-events`
   - Get upcoming high-impact news events
   - Query params: `hours_ahead` (default: 24), `currency` (optional)

2. **POST** `/news-events`
   - Create a new news event
   - Body: `{title, currency, event_time, impact}`

3. **DELETE** `/news-events/{event_id}`
   - Delete a news event by ID

4. **GET** `/should-avoid-trading/{currency_pair}`
   - Check if trading should be avoided
   - Path param: currency_pair (e.g., "EUR_USD")

5. **GET** `/should-close-positions/{currency_pair}`
   - Check if positions should be closed before news

6. **GET** `/settings`
   - Get current news avoidance settings

7. **PATCH** `/settings`
   - Update news avoidance settings

---

## 📝 Adding New API Routes

1. Create a new file in this directory (e.g., `signals.py`)
2. Create an `APIRouter` instance:
   ```python
   router = APIRouter()
   ```
3. Define your endpoints
4. Export the router in `__init__.py`:
   ```python
   from .signals import router as signals_router
   ```
5. Include the router in `app/main.py`:
   ```python
   from app.api.routes import signals_router
   app.include_router(signals_router, prefix="/api/signals", tags=["signals"])
   ```

---

## 📚 Documentation Files

- **`README.md`** (this file) - Current routes and how to add new ones
- **`LEGACY_API_ROUTES_SUMMARY.md`** - Detailed breakdown of all legacy routes
- **`API_ROUTES_COMPARISON.md`** - Comparison of legacy vs new implementations

---

## 🎯 Next Steps

### **Priority 1: Signal API (NEW - not in legacy)**
Create `/app/api/routes/signals.py`:
- `GET /api/signals/latest/{instrument}` - Get latest ML signal
- `GET /api/signals/history/{instrument}` - Get signal history
- `GET /api/signals/multi` - Get all signals

### **Priority 2: Migrate routes as needed**
- Health API (enhance existing)
- Auth routes (if needed)
- Bot routes (when building bots)

---

## Notes

- All routes are prefixed with `/api` in the main application
- Use Pydantic models for request/response validation
- Use async/await for all endpoints
- Include proper error handling with HTTPException
