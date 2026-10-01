#!/usr/bin/env python3
"""
Backend test for Daily Dispatch Report endpoint with date-wise segregation.
Tests both single-day and range modes.
"""
import requests
import json
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List

# Backend URL from frontend/.env
BASE_URL = "https://clone-fortytwo.preview.emergentagent.com/api"

# Test credentials - using 'user' account to avoid OTP
# From DB: username='user', email='user@factory.com', otp_login=false
TEST_USER = "user"
TEST_PASSWORD = "user123"

def login() -> str:
    """Login and return Bearer token."""
    print("\n=== LOGIN ===")
    url = f"{BASE_URL}/auth/login"
    payload = {"email": TEST_USER, "password": TEST_PASSWORD}  # 'email' field accepts username too
    print(f"POST {url}")
    print(f"Payload: {payload}")
    
    resp = requests.post(url, json=payload)
    print(f"Status: {resp.status_code}")
    
    if resp.status_code != 200:
        print(f"ERROR: Login failed - {resp.text}")
        raise Exception(f"Login failed: {resp.status_code} - {resp.text}")
    
    data = resp.json()
    print(f"Response: {json.dumps(data, indent=2)}")
    
    if "otp_required" in data and data["otp_required"]:
        raise Exception("OTP required - should not happen with 'user' account")
    
    token = data.get("token")
    if not token:
        raise Exception("No token in response")
    
    print(f"✓ Login successful, token obtained")
    return token


def ist_date_from_utc(utc_str: str) -> str:
    """Convert UTC ISO string to IST date (YYYY-MM-DD)."""
    IST = timezone(timedelta(hours=5, minutes=30))
    dt = datetime.fromisoformat(utc_str.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(IST).date().isoformat()


def test_single_day_mode(token: str, test_date: str = "2026-07-28"):
    """Test single-day mode: date only, no end_date."""
    print(f"\n{'='*80}")
    print(f"TEST 1: SINGLE DAY MODE (date={test_date})")
    print(f"{'='*80}")
    
    url = f"{BASE_URL}/reports/daily-dispatch"
    params = {"date": test_date}
    headers = {"Authorization": f"Bearer {token}"}
    
    print(f"GET {url}")
    print(f"Params: {params}")
    
    resp = requests.get(url, params=params, headers=headers)
    print(f"Status: {resp.status_code}")
    
    if resp.status_code != 200:
        print(f"ERROR: {resp.text}")
        return False
    
    data = resp.json()
    print(f"\nResponse structure:")
    print(f"  - range_mode: {data.get('range_mode')}")
    print(f"  - date: {data.get('date')}")
    print(f"  - end_date: {data.get('end_date')}")
    print(f"  - groups count: {len(data.get('groups', []))}")
    print(f"  - grand_total_pcs: {data.get('grand_total_pcs')}")
    print(f"  - grand_total_value: {data.get('grand_total_value')}")
    print(f"  - dispatch_count: {data.get('dispatch_count')}")
    
    # Verify required fields
    required_fields = ["range_mode", "groups", "grand_total_pcs", "grand_total_value", 
                       "dispatch_count", "date", "end_date"]
    missing = [f for f in required_fields if f not in data]
    if missing:
        print(f"\n✗ FAIL: Missing required fields: {missing}")
        return False
    
    # Verify range_mode is False
    if data["range_mode"] != False:
        print(f"\n✗ FAIL: range_mode should be False, got {data['range_mode']}")
        return False
    
    # Check groups structure
    groups = data.get("groups", [])
    if not groups:
        print(f"\n⚠ WARNING: No groups found for date {test_date}")
        print(f"  Skipping detailed validation (no data for this date)")
        return True  # Not a failure, just no data
    
    print(f"\nGroups analysis:")
    customer_ids_seen = set()
    for i, group in enumerate(groups):
        cid = group.get("customer_id")
        cname = group.get("customer_name")
        day = group.get("day")
        dispatch_count = group.get("dispatch_count", 0)
        total_pcs = group.get("total_pcs", 0)
        
        print(f"  Group {i+1}: customer_id={cid}, customer_name={cname}, day={day}, "
              f"dispatches={dispatch_count}, pcs={total_pcs}")
        
        # Check for required group fields
        if "day" not in group:
            print(f"    ✗ FAIL: Group missing 'day' field")
            return False
        
        if "customer_id" not in group:
            print(f"    ✗ FAIL: Group missing 'customer_id' field")
            return False
        
        # Check for duplicate customer_id (should not happen in single-day mode)
        if cid in customer_ids_seen:
            print(f"    ✗ FAIL: customer_id {cid} appears multiple times (should be unique in single-day mode)")
            return False
        customer_ids_seen.add(cid)
    
    print(f"\n✓ PASS: Single-day mode working correctly")
    print(f"  - range_mode = False ✓")
    print(f"  - All groups have 'day' field ✓")
    print(f"  - No duplicate customer_ids ✓")
    print(f"  - {len(groups)} unique customers found")
    
    return True


def test_range_mode(token: str, start_date: str = "2026-08-01", end_date: str = "2026-10-01"):
    """Test range mode: date + end_date spanning multiple days."""
    print(f"\n{'='*80}")
    print(f"TEST 2: RANGE MODE (date={start_date}, end_date={end_date})")
    print(f"{'='*80}")
    
    url = f"{BASE_URL}/reports/daily-dispatch"
    params = {"date": start_date, "end_date": end_date}
    headers = {"Authorization": f"Bearer {token}"}
    
    print(f"GET {url}")
    print(f"Params: {params}")
    
    resp = requests.get(url, params=params, headers=headers)
    print(f"Status: {resp.status_code}")
    
    if resp.status_code != 200:
        print(f"ERROR: {resp.text}")
        return False
    
    data = resp.json()
    print(f"\nResponse structure:")
    print(f"  - range_mode: {data.get('range_mode')}")
    print(f"  - date: {data.get('date')}")
    print(f"  - end_date: {data.get('end_date')}")
    print(f"  - groups count: {len(data.get('groups', []))}")
    print(f"  - grand_total_pcs: {data.get('grand_total_pcs')}")
    print(f"  - grand_total_value: {data.get('grand_total_value')}")
    print(f"  - dispatch_count: {data.get('dispatch_count')}")
    
    # Verify range_mode is True
    if data["range_mode"] != True:
        print(f"\n✗ FAIL: range_mode should be True, got {data['range_mode']}")
        return False
    
    groups = data.get("groups", [])
    if not groups:
        print(f"\n⚠ WARNING: No groups found for range {start_date} to {end_date}")
        return False
    
    # Analyze groups for date-wise segregation
    print(f"\n{'='*80}")
    print(f"ANALYZING DATE-WISE SEGREGATION")
    print(f"{'='*80}")
    
    # Track parties that appear on multiple days
    party_days: Dict[str, List[str]] = {}  # customer_id -> [day1, day2, ...]
    party_names: Dict[str, str] = {}  # customer_id -> customer_name
    
    # Verify each group's dispatches share the same IST day
    all_valid = True
    for i, group in enumerate(groups):
        cid = group.get("customer_id")
        cname = group.get("customer_name")
        group_day = group.get("day")
        dispatches = group.get("dispatches", [])
        
        if cid not in party_days:
            party_days[cid] = []
            party_names[cid] = cname
        party_days[cid].append(group_day)
        
        # Verify all dispatches in this group share the same IST day
        for j, dispatch in enumerate(dispatches):
            dispatched_at = dispatch.get("dispatched_at")
            if dispatched_at:
                dispatch_ist_day = ist_date_from_utc(dispatched_at)
                if dispatch_ist_day != group_day:
                    print(f"\n✗ FAIL: Group {i+1} (customer={cname}, group_day={group_day})")
                    print(f"  Dispatch {j+1} has dispatched_at={dispatched_at}")
                    print(f"  Which converts to IST day={dispatch_ist_day}")
                    print(f"  But group['day']={group_day} (MISMATCH!)")
                    all_valid = False
    
    if not all_valid:
        return False
    
    print(f"✓ All dispatches within each group share the same IST day as group['day']")
    
    # Find parties with dispatches on multiple days
    multi_day_parties = {cid: days for cid, days in party_days.items() if len(days) > 1}
    
    print(f"\n{'='*80}")
    print(f"PARTIES WITH MULTI-DAY DISPATCHES")
    print(f"{'='*80}")
    
    if not multi_day_parties:
        print(f"⚠ WARNING: No parties found with dispatches on multiple days")
        print(f"  This might indicate the date range doesn't span enough activity")
        print(f"  or the test data doesn't have multi-day dispatches.")
    else:
        print(f"Found {len(multi_day_parties)} parties with dispatches on multiple days:\n")
        for cid, days in multi_day_parties.items():
            cname = party_names[cid]
            print(f"  Party: {cname} (customer_id={cid})")
            print(f"    Appears on {len(days)} different days: {sorted(set(days))}")
            
            # Show per-day breakdown for this party
            for day in sorted(set(days)):
                matching_groups = [g for g in groups if g.get("customer_id") == cid and g.get("day") == day]
                for g in matching_groups:
                    print(f"      {day}: {g.get('dispatch_count')} dispatches, "
                          f"{g.get('total_pcs')} pcs, ₹{g.get('total_value')}")
        
        print(f"\n✓ PASS: Parties with multi-day dispatches appear as MULTIPLE groups (one per day)")
    
    # Verify sorting: groups should be ordered by (day asc, customer_name)
    print(f"\n{'='*80}")
    print(f"VERIFYING SORT ORDER")
    print(f"{'='*80}")
    
    prev_day = None
    prev_name = None
    sort_valid = True
    
    for i, group in enumerate(groups):
        day = group.get("day")
        name = group.get("customer_name", "").lower()
        
        if prev_day is not None:
            if day < prev_day:
                print(f"✗ FAIL: Group {i+1} has day={day} which is before previous day={prev_day}")
                sort_valid = False
            elif day == prev_day and prev_name is not None and name < prev_name:
                print(f"✗ FAIL: Group {i+1} has name={name} which is before previous name={prev_name} on same day")
                sort_valid = False
        
        prev_day = day
        prev_name = name if day == prev_day else None
    
    if sort_valid:
        print(f"✓ Groups are correctly sorted by (day ascending, customer_name)")
    else:
        return False
    
    return True


def test_no_data_loss(token: str, start_date: str = "2026-08-01", end_date: str = "2026-10-01"):
    """Test that no data is lost: sum of groups equals grand totals."""
    print(f"\n{'='*80}")
    print(f"TEST 3: NO DATA LOSS (sum of groups = grand totals)")
    print(f"{'='*80}")
    
    url = f"{BASE_URL}/reports/daily-dispatch"
    params = {"date": start_date, "end_date": end_date}
    headers = {"Authorization": f"Bearer {token}"}
    
    resp = requests.get(url, params=params, headers=headers)
    if resp.status_code != 200:
        print(f"ERROR: {resp.text}")
        return False
    
    data = resp.json()
    groups = data.get("groups", [])
    
    # Sum up all groups
    sum_dispatch_count = sum(g.get("dispatch_count", 0) for g in groups)
    sum_total_pcs = sum(g.get("total_pcs", 0) for g in groups)
    sum_total_value = sum(g.get("total_value", 0.0) for g in groups)
    
    # Compare with grand totals
    grand_dispatch_count = data.get("dispatch_count", 0)
    grand_total_pcs = data.get("grand_total_pcs", 0)
    grand_total_value = data.get("grand_total_value", 0.0)
    
    print(f"\nSum of all groups:")
    print(f"  dispatch_count: {sum_dispatch_count}")
    print(f"  total_pcs: {sum_total_pcs}")
    print(f"  total_value: {sum_total_value:.2f}")
    
    print(f"\nGrand totals from response:")
    print(f"  dispatch_count: {grand_dispatch_count}")
    print(f"  grand_total_pcs: {grand_total_pcs}")
    print(f"  grand_total_value: {grand_total_value:.2f}")
    
    # Verify dispatch_count
    if sum_dispatch_count != grand_dispatch_count:
        print(f"\n✗ FAIL: Sum of groups' dispatch_count ({sum_dispatch_count}) != "
              f"grand dispatch_count ({grand_dispatch_count})")
        return False
    
    # Verify total_pcs
    if sum_total_pcs != grand_total_pcs:
        print(f"\n✗ FAIL: Sum of groups' total_pcs ({sum_total_pcs}) != "
              f"grand_total_pcs ({grand_total_pcs})")
        return False
    
    # Verify total_value (allow small float rounding difference)
    value_diff = abs(sum_total_value - grand_total_value)
    if value_diff > 0.02:  # Allow 2 paisa difference for rounding
        print(f"\n✗ FAIL: Sum of groups' total_value ({sum_total_value:.2f}) differs from "
              f"grand_total_value ({grand_total_value:.2f}) by {value_diff:.2f}")
        return False
    
    print(f"\n✓ PASS: No data loss detected")
    print(f"  - dispatch_count matches ✓")
    print(f"  - total_pcs matches ✓")
    print(f"  - total_value matches (diff={value_diff:.4f}) ✓")
    
    return True


def test_edge_case_invalid_range(token: str):
    """Test edge case: end_date earlier than date should return 400."""
    print(f"\n{'='*80}")
    print(f"TEST 4: EDGE CASE (end_date < date should return 400)")
    print(f"{'='*80}")
    
    url = f"{BASE_URL}/reports/daily-dispatch"
    params = {"date": "2026-09-30", "end_date": "2026-08-01"}  # end before start
    headers = {"Authorization": f"Bearer {token}"}
    
    print(f"GET {url}")
    print(f"Params: {params}")
    
    resp = requests.get(url, params=params, headers=headers)
    print(f"Status: {resp.status_code}")
    
    if resp.status_code != 400:
        print(f"\n✗ FAIL: Expected 400, got {resp.status_code}")
        print(f"Response: {resp.text}")
        return False
    
    print(f"Response: {resp.text}")
    print(f"\n✓ PASS: Correctly returns 400 for invalid date range")
    
    return True


def main():
    """Run all tests."""
    print("="*80)
    print("DAILY DISPATCH REPORT - DATE-WISE SEGREGATION TEST")
    print("="*80)
    print(f"Backend URL: {BASE_URL}")
    print(f"Test User: {TEST_USER}")
    
    try:
        # Login
        token = login()
        
        # Run tests
        results = {
            "Single Day Mode": test_single_day_mode(token),
            "Range Mode": test_range_mode(token),
            "No Data Loss": test_no_data_loss(token),
            "Edge Case (Invalid Range)": test_edge_case_invalid_range(token),
        }
        
        # Summary
        print(f"\n{'='*80}")
        print(f"TEST SUMMARY")
        print(f"{'='*80}")
        
        for test_name, passed in results.items():
            status = "✓ PASS" if passed else "✗ FAIL"
            print(f"{status}: {test_name}")
        
        all_passed = all(results.values())
        
        print(f"\n{'='*80}")
        if all_passed:
            print(f"✓✓ ALL TESTS PASSED ✓✓")
        else:
            print(f"✗✗ SOME TESTS FAILED ✗✗")
        print(f"{'='*80}")
        
        return 0 if all_passed else 1
        
    except Exception as e:
        print(f"\n{'='*80}")
        print(f"✗✗ TEST EXECUTION FAILED ✗✗")
        print(f"{'='*80}")
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(main())
