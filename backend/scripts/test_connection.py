"""
Simple test to isolate the delay issue
"""
import requests
import time

print("Testing with different connection settings...")
print("=" * 60)

# Test 1: Default
print("\nTest 1: Default requests settings")
start = time.time()
r = requests.get("http://localhost:8001/health", timeout=5)
elapsed = time.time() - start
print(f"Status: {r.status_code}, Time: {elapsed*1000:.0f}ms")

# Test 2: Disable keep-alive
print("\nTest 2: Connection: close header")
start = time.time()
r = requests.get("http://localhost:8001/health", 
                 headers={"Connection": "close"},
                 timeout=5)
elapsed = time.time() - start
print(f"Status: {r.status_code}, Time: {elapsed*1000:.0f}ms")

# Test 3: New session each time
print("\nTest 3: Fresh session")
session = requests.Session()
start = time.time()
r = session.get("http://localhost:8001/health", timeout=5)
elapsed = time.time() - start
print(f"Status: {r.status_code}, Time: {elapsed*1000:.0f}ms")
session.close()

# Test 4: urllib instead
print("\nTest 4: Using urllib")
from urllib.request import urlopen
start = time.time()
response = urlopen("http://localhost:8001/health", timeout=5)
data = response.read()
elapsed = time.time() - start
print(f"Status: {response.status}, Time: {elapsed*1000:.0f}ms")

print("\n" + "=" * 60)
print("If Test 4 (urllib) is fast but others are slow,")
print("the issue is with the requests library or keep-alive.")
