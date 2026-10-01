#!/usr/bin/env python3
"""
Simple test for Daily Dispatch Report endpoint - date-wise segregation
"""
import requests
import json
from datetime import datetime, timezone, timedelta

BASE_URL = "https://clone-fortytwo.preview.emergentagent.com/api"

# Login
print("=== LOGIN ===")
resp = requests.post(f"{BASE_URL}/auth/login", json={"email": "user", "password": "user123"})
print(f"Login status: {resp.status_code}")
if resp.status_code != 200:
    print(f"Login failed: {resp.text}")
    exit(1)

token = resp.json()["token"]
headers = {"Authorization": f"Bearer {token}"}
print("✓ Login successful\n")

def ist_date_from_utc(utc_str):
    """Convert UTC ISO string to IST date."""
    IST = timezone(timedelta(hours=5, minutes=30))
    dt = datetime.fromisoformat(utc_str.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(IST).date().isoformat()

# Test 1: Single day mode
print("="*80)
print("TEST 1: SINGLE DAY MODE")
print("="*80)
resp = requests.get(f"{BASE_URL}/reports/daily-dispatch", params={"date": "2026-07-28"}, headers=headers)
print(f"Status: {resp.status_code}")
data = resp.json()
print(f"range_mode: {data['range_mode']}")
print(f"groups: {len(data['groups'])}")
print(f"dispatch_count: {data['dispatch_count']}")
print(f"grand_total_pcs: {data['grand_total_pcs']}")

if data['range_mode'] != False:
    print("✗ FAIL: range_mode should be False")
    exit(1)

# Check no duplicate customer_ids
customer_ids = [g['customer_id'] for g in data['groups']]
if len(customer_ids) != len(set(customer_ids)):
    print("✗ FAIL: Duplicate customer_ids found in single-day mode")
    exit(1)

print("✓ PASS: Single-day mode working\n")

# Test 2: Range mode
print("="*80)
print("TEST 2: RANGE MODE (2026-07-28 to 2026-08-14)")
print("="*80)
resp = requests.get(f"{BASE_URL}/reports/daily-dispatch", 
                   params={"date": "2026-07-28", "end_date": "2026-08-14"}, 
                   headers=headers)
print(f"Status: {resp.status_code}")
data = resp.json()
print(f"range_mode: {data['range_mode']}")
print(f"groups: {len(data['groups'])}")
print(f"dispatch_count: {data['dispatch_count']}")
print(f"grand_total_pcs: {data['grand_total_pcs']}")

if data['range_mode'] != True:
    print("✗ FAIL: range_mode should be True")
    exit(1)

# Track parties by day
party_days = {}
for g in data['groups']:
    cid = g['customer_id']
    day = g['day']
    if cid not in party_days:
        party_days[cid] = []
    party_days[cid].append(day)

# Find parties with multiple days
multi_day = {cid: days for cid, days in party_days.items() if len(days) > 1}
print(f"\nParties with multi-day dispatches: {len(multi_day)}")

if multi_day:
    # Show first party with multi-day dispatches
    cid = list(multi_day.keys())[0]
    days = multi_day[cid]
    cname = next(g['customer_name'] for g in data['groups'] if g['customer_id'] == cid)
    print(f"\nExample: {cname} (customer_id={cid})")
    print(f"  Appears on {len(days)} days: {sorted(set(days))}")
    
    # Verify each group's dispatches share the same IST day
    for g in data['groups']:
        if g['customer_id'] == cid:
            group_day = g['day']
            for d in g['dispatches']:
                dispatch_day = ist_date_from_utc(d['dispatched_at'])
                if dispatch_day != group_day:
                    print(f"✗ FAIL: Dispatch day mismatch! group_day={group_day}, dispatch_day={dispatch_day}")
                    exit(1)
    
    print("✓ PASS: Date-wise segregation working correctly")
else:
    print("⚠ WARNING: No parties with multi-day dispatches found in this range")

# Test 3: No data loss
print("\n" + "="*80)
print("TEST 3: NO DATA LOSS")
print("="*80)
sum_dispatch_count = sum(g['dispatch_count'] for g in data['groups'])
sum_total_pcs = sum(g['total_pcs'] for g in data['groups'])
sum_total_value = sum(g['total_value'] for g in data['groups'])

print(f"Sum of groups dispatch_count: {sum_dispatch_count}")
print(f"Grand dispatch_count: {data['dispatch_count']}")
print(f"Sum of groups total_pcs: {sum_total_pcs}")
print(f"Grand total_pcs: {data['grand_total_pcs']}")
print(f"Sum of groups total_value: {sum_total_value:.2f}")
print(f"Grand total_value: {data['grand_total_value']:.2f}")

if sum_dispatch_count != data['dispatch_count']:
    print(f"✗ FAIL: dispatch_count mismatch")
    exit(1)

if sum_total_pcs != data['grand_total_pcs']:
    print(f"✗ FAIL: total_pcs mismatch")
    exit(1)

value_diff = abs(sum_total_value - data['grand_total_value'])
if value_diff > 0.02:
    print(f"✗ FAIL: total_value mismatch (diff={value_diff:.4f})")
    exit(1)

print("✓ PASS: No data loss\n")

# Test 4: Edge case - invalid range
print("="*80)
print("TEST 4: EDGE CASE (end_date < date)")
print("="*80)
resp = requests.get(f"{BASE_URL}/reports/daily-dispatch", 
                   params={"date": "2026-09-30", "end_date": "2026-08-01"}, 
                   headers=headers)
print(f"Status: {resp.status_code}")
if resp.status_code != 400:
    print(f"✗ FAIL: Expected 400, got {resp.status_code}")
    exit(1)
print("✓ PASS: Correctly returns 400 for invalid range\n")

print("="*80)
print("✓✓ ALL TESTS PASSED ✓✓")
print("="*80)
