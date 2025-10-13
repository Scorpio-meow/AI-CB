"""
Debugging script to find the 2-second delay
"""
import time
import asyncio
from fastapi import FastAPI
from fastapi.testclient import TestClient

# Test 1: Simple FastAPI app without any middleware
print("=" * 60)
print("Test 1: Minimal FastAPI app")
print("=" * 60)

app_simple = FastAPI()

@app_simple.get("/test")
async def test_simple():
    return {"status": "ok"}

client = TestClient(app_simple)
start = time.time()
response = client.get("/test")
elapsed = time.time() - start

print(f"Response: {response.json()}")
print(f"Time: {elapsed*1000:.0f}ms")
print(f"Status: {'PASS' if elapsed < 0.1 else 'FAIL - SLOW!'}")
print()

# Test 2: Import main app and test
print("=" * 60)
print("Test 2: Actual app from main.py")
print("=" * 60)

try:
    import sys
    sys.path.insert(0, '..')
    from main import app
    
    client_main = TestClient(app)
    
    print("Testing /health endpoint...")
    start = time.time()
    response = client_main.get("/health")
    elapsed = time.time() - start
    
    print(f"Response: {response.json()}")
    print(f"Time: {elapsed*1000:.0f}ms")
    print(f"Status: {'PASS' if elapsed < 0.1 else 'FAIL - SLOW!'}")
    
    if elapsed > 0.5:
        print(f"\nWARNING: Detected {elapsed:.1f}s delay!")
        print("Possible causes:")
        print("  1. Middleware overhead")
        print("  2. Database connection")
        print("  3. Redis connection")
        print("  4. Import side effects")
        
except Exception as e:
    print(f"Error testing main app: {e}")
    import traceback
    traceback.print_exc()

print()
print("=" * 60)
print("Diagnosis Complete")
print("=" * 60)
