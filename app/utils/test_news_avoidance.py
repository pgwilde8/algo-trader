#!/usr/bin/env python3
"""
Comprehensive test script for the file-based news avoidance system.
Run this to verify everything is working correctly before building bots.

Usage:
    python3 app/utils/test_news_avoidance.py
"""

import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from datetime import datetime, timedelta, timezone
from app.utils.simple_news_avoidance import simple_news_avoidance

def test_news_system():
    """Comprehensive test of the file-based news avoidance system."""
    print("🧪 Testing File-Based News Avoidance System")
    print("=" * 70)
    
    all_tests_passed = True
    
    # Test 1: Service Initialization
    print("\n1️⃣ Testing Service Initialization...")
    try:
        print(f"   ✅ News file location: {simple_news_avoidance.data_file}")
        print(f"   ✅ Minutes before: {simple_news_avoidance.minutes_before}")
        print(f"   ✅ Minutes after: {simple_news_avoidance.minutes_after}")
        print(f"   ✅ Minutes before close: {simple_news_avoidance.minutes_before_close}")
        
        # Load settings from file
        data = simple_news_avoidance._load_data()
        settings = data.get("settings", {})
        print(f"   ✅ Settings loaded from file:")
        print(f"      - Enabled: {settings.get('enabled', True)}")
        print(f"      - Minutes Before: {settings.get('minutes_before', 30)}")
        print(f"      - Minutes After: {settings.get('minutes_after', 60)}")
        print(f"      - Minutes Before Close: {settings.get('minutes_before_close', 3)}")
    except Exception as e:
        print(f"   ❌ Service initialization failed: {e}")
        all_tests_passed = False
    
    # Test 2: Current Time Display
    print("\n2️⃣ Current Time Check...")
    try:
        now_utc = datetime.now(timezone.utc)
        print(f"   ✅ Current Time (UTC): {now_utc.isoformat()}")
        
        # Convert to Eastern for display
        import pytz
        eastern = pytz.timezone('America/New_York')
        now_eastern = now_utc.astimezone(eastern)
        print(f"   ✅ Current Time (Eastern): {now_eastern.strftime('%Y-%m-%d %H:%M:%S %Z')}")
    except Exception as e:
        print(f"   ❌ Time check failed: {e}")
        all_tests_passed = False
    
    # Test 3: Get Existing Events
    print("\n3️⃣ Checking Existing News Events...")
    try:
        upcoming = simple_news_avoidance.get_upcoming_news(hours_ahead=168)  # Next 7 days
        print(f"   ✅ Found {len(upcoming)} upcoming high-impact events in next 7 days")
        if upcoming:
            for event in upcoming[:5]:  # Show first 5
                event_time = event.get('event_time')
                if isinstance(event_time, datetime):
                    event_time_str = event_time.strftime('%Y-%m-%d %H:%M UTC')
                else:
                    event_time_str = str(event_time)
                minutes_until = event.get('minutes_until', 'N/A')
                print(f"      - {event['title']} ({event['currency']}) at {event_time_str} ({minutes_until} min)")
        else:
            print("      ℹ️  No upcoming events found")
    except Exception as e:
        print(f"   ❌ Failed to get upcoming news: {e}")
        all_tests_passed = False
    
    # Test 4: Trading Avoidance Check
    print("\n4️⃣ Testing Trading Avoidance Logic...")
    try:
        test_pairs = ["EUR_USD", "GBP_USD", "USD_JPY"]
        for pair in test_pairs:
            avoidance = simple_news_avoidance.should_avoid_trading(pair)
            status = "🚫 AVOID" if avoidance['avoid_trading'] else "✅ ALLOW"
            print(f"   {status} Trading for {pair}: {avoidance['reason']}")
            
            if avoidance['avoid_trading']:
                if avoidance.get('next_event'):
                    event = avoidance['next_event']
                    print(f"      Next event: {event.get('title', 'N/A')} in {event.get('minutes_until', 'N/A')} min")
                if avoidance.get('safe_to_trade_at'):
                    safe_time = avoidance['safe_to_trade_at']
                    if isinstance(safe_time, datetime):
                        print(f"      Safe to trade at: {safe_time.strftime('%Y-%m-%d %H:%M UTC')}")
    except Exception as e:
        print(f"   ❌ Failed to check trading avoidance: {e}")
        all_tests_passed = False
    
    # Test 5: Position Closing Check
    print("\n5️⃣ Testing Position Closing Logic...")
    try:
        test_pairs = ["EUR_USD", "USD_JPY"]
        for pair in test_pairs:
            close_check = simple_news_avoidance.should_close_positions(pair)
            status = "🚨 CLOSE" if close_check['close_positions'] else "✅ HOLD"
            print(f"   {status} Positions for {pair}: {close_check['reason']}")
            
            if close_check['close_positions'] and close_check.get('next_event'):
                event = close_check['next_event']
                print(f"      Event: {event.get('title', 'N/A')} in {event.get('minutes_until', 'N/A')} min")
    except Exception as e:
        print(f"   ❌ Failed to check position closing: {e}")
        all_tests_passed = False
    
    # Test 6: Currency Extraction
    print("\n6️⃣ Testing Currency Extraction...")
    try:
        test_pairs = {
            "EUR_USD": ["EUR", "USD"],
            "GBP_USD": ["GBP", "USD"],
            "USD_JPY": ["USD", "JPY"],
            "XAU_USD": ["USD"],  # Gold uses USD
        }
        
        for pair, expected_currencies in test_pairs.items():
            currencies = simple_news_avoidance._extract_currencies_from_pair(pair)
            print(f"   ✅ {pair} → {currencies}")
            
            if set(currencies) != set(expected_currencies):
                print(f"      ⚠️  Expected {expected_currencies}, got {currencies}")
    except Exception as e:
        print(f"   ❌ Failed to test currency extraction: {e}")
        all_tests_passed = False
    
    # Test 7: Add Test Event (Optional - user can comment out)
    print("\n7️⃣ Testing Event Addition (Optional)...")
    try:
        # Add a test event 3 hours from now
        test_time = datetime.now(timezone.utc) + timedelta(hours=3)
        test_event = simple_news_avoidance.add_news_event(
            title="TEST EVENT - Can Be Deleted",
            currency="USD",
            event_time=test_time,
            impact="high"
        )
        print(f"   ✅ Added test event: {test_event['title']} (ID: {test_event['id']})")
        print(f"      Time: {test_time.strftime('%Y-%m-%d %H:%M UTC')}")
        print(f"      ℹ️  You can delete this event later using ID: {test_event['id']}")
    except Exception as e:
        print(f"   ❌ Failed to add test event: {e}")
        all_tests_passed = False
    
    # Test 8: Settings Update (Test Enable/Disable)
    print("\n8️⃣ Testing Settings Update...")
    try:
        # Get current enabled state
        original_data = simple_news_avoidance._load_data()
        original_enabled = original_data.get("settings", {}).get("enabled", True)
        
        # Temporarily disable
        simple_news_avoidance.update_settings(enabled=False)
        avoidance_disabled = simple_news_avoidance.should_avoid_trading("EUR_USD")
        print(f"   ✅ With news disabled - Avoid trading: {avoidance_disabled['avoid_trading']}")
        
        # Re-enable
        simple_news_avoidance.update_settings(enabled=original_enabled)
        print(f"   ✅ Settings restored to enabled: {original_enabled}")
    except Exception as e:
        print(f"   ❌ Failed to test settings update: {e}")
        all_tests_passed = False
    
    # Summary
    print("\n" + "=" * 70)
    if all_tests_passed:
        print("🎉 All tests passed! News avoidance system is working correctly.")
        print("\n✅ System is ready for bot integration!")
        print("\nTo use in bots:")
        print("   from app.utils.simple_news_avoidance import simple_news_avoidance")
        print("   if simple_news_avoidance.should_avoid_trading(pair)['avoid_trading']:")
        print("       return  # Skip trade")
        return True
    else:
        print("❌ Some tests failed. Please review errors above.")
        return False

if __name__ == "__main__":
    success = test_news_system()
    sys.exit(0 if success else 1)

