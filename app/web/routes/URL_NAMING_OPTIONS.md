# URL Naming Options for Consensus Trader Multi-Asset Pages

## Current Situation
- Assets in database: `EUR_USD`, `GBP_USD`, `USD_CAD`, `USD_JPY` (uppercase with underscore)
- Need URL structure for multiple assets under consensus-trader

## URL Naming Options

### Option 1: Lowercase, No Separator (RECOMMENDED)
**URLs:**
- `/consensus-trader/eurusd`
- `/consensus-trader/gbpusd`
- `/consensus-trader/usdcad`
- `/consensus-trader/usdjpy`

**Pros:**
- ✅ Clean, short URLs
- ✅ Easy to type and remember
- ✅ SEO-friendly
- ✅ Standard web convention

**Cons:**
- Need conversion: `eurusd` → `EUR_USD` (database format)

**Conversion Logic:**
```python
# URL: eurusd → DB: EUR_USD
asset_url = "eurusd"
asset_db = asset_url.upper().replace("usd", "_USD").replace("eur", "EUR_")
# But this gets complex with pairs like GBPUSD...

# Better approach:
url_to_db = {
    "eurusd": "EUR_USD",
    "gbpusd": "GBP_USD", 
    "usdcad": "USD_CAD",
    "usdjpy": "USD_JPY",
    "gbpjpy": "GBP_JPY",
    # etc.
}
```

---

### Option 2: Lowercase with Hyphen
**URLs:**
- `/consensus-trader/eur-usd`
- `/consensus-trader/gbp-usd`
- `/consensus-trader/usd-cad`
- `/consensus-trader/usd-jpy`

**Pros:**
- ✅ More readable
- ✅ Clear separation of currency pairs
- ✅ Easy conversion: `eur-usd` → `EUR_USD`

**Cons:**
- Slightly longer URLs
- Hyphens in URLs (minor SEO consideration)

**Conversion Logic:**
```python
# Simple conversion
asset_url = "eur-usd"
asset_db = asset_url.upper().replace("-", "_")  # EUR_USD
```

---

### Option 3: Uppercase with Underscore (Matches DB)
**URLs:**
- `/consensus-trader/EUR_USD`
- `/consensus-trader/GBP_USD`
- `/consensus-trader/USD_CAD`
- `/consensus-trader/USD_JPY`

**Pros:**
- ✅ Direct match with database format
- ✅ No conversion needed
- ✅ Clear and explicit

**Cons:**
- ❌ URLs are case-sensitive (can cause issues)
- ❌ Underscores in URLs (less SEO-friendly)
- ❌ Less user-friendly (harder to type)

---

### Option 4: Lowercase with Underscore
**URLs:**
- `/consensus-trader/eur_usd`
- `/consensus-trader/gbp_usd`
- `/consensus-trader/usd_cad`
- `/consensus-trader/usd_jpy`

**Pros:**
- ✅ Matches database format structure
- ✅ Easy conversion: `eur_usd` → `EUR_USD`

**Cons:**
- ❌ Underscores in URLs (less SEO-friendly)
- Less common web convention

**Conversion Logic:**
```python
asset_url = "eur_usd"
asset_db = asset_url.upper()  # EUR_USD
```

---

## Recommendation: Option 1 (Lowercase, No Separator)

**Why:**
1. **Cleanest URLs** - Short, memorable, professional
2. **SEO-friendly** - No special characters
3. **User-friendly** - Easy to type and share
4. **Standard convention** - Most trading/finance sites use this format

**Implementation:**
- Create a mapping dictionary for URL → DB format
- Support both formats (with/without separator) for flexibility
- Add redirects for common variations

---

## Suggested Route Structure

```python
# Main overview page
/consensus-trader

# Asset-specific pages
/consensus-trader/eurusd
/consensus-trader/gbpusd
/consensus-trader/usdcad
/consensus-trader/usdjpy
/consensus-trader/gbpjpy

# Also support hyphenated versions (redirects)
/consensus-trader/eur-usd → /consensus-trader/eurusd
/consensus-trader/gbp-usd → /consensus-trader/gbpusd
```

---

## Asset Mapping Dictionary

```python
ASSET_URL_TO_DB = {
    # Major Forex
    "eurusd": "EUR_USD",
    "gbpusd": "GBP_USD",
    "usdcad": "USD_CAD",
    "usdjpy": "USD_JPY",
    "gbpjpy": "GBP_JPY",
    "audusd": "AUD_USD",
    "nzdusd": "NZD_USD",
    "usdchf": "USD_CHF",
    
    # Commodities
    "xauusd": "XAU_USD",  # Gold
    "xagusd": "XAG_USD",  # Silver
    
    # Crypto (if added)
    "btcusd": "BTC_USD",
    "ethusd": "ETH_USD",
    
    # Indices (if added)
    "spx500usd": "SPX500_USD",
    "nas100usd": "NAS100_USD",
}
```

---

## Final Recommendation

**Use Option 1** (`/consensus-trader/eurusd`) with:
- Asset mapping dictionary for URL → DB conversion
- Support for hyphenated versions as redirects
- Clean, professional URLs that are easy to remember and share

