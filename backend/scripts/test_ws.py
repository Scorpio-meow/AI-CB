import asyncio
import os
import json
import websockets

# Usage:
# TEST_WS_URL and TEST_ACCESS_TOKEN can be set in the environment
# Example:
# $env:TEST_WS_URL = 'wss://1848b1fg-8001.asse.devtunnels.ms/api/workflow/ws'
# $env:TEST_ACCESS_TOKEN = '<your_jwt>'

URL = os.getenv('TEST_WS_URL', 'wss://1848b1fg-8001.asse.devtunnels.ms/api/workflow/ws')
TOKEN = os.getenv('TEST_ACCESS_TOKEN')

headers = {}
if TOKEN:
    headers['Authorization'] = f'Bearer {TOKEN}'

async def main():
    print(f"Testing WebSocket URL: {URL}")
    if TOKEN:
        print("Using Authorization header (Bearer token present)")

    try:
        async with websockets.connect(URL, extra_headers=headers) as ws:
            print('Connected to server')
            # Try sending a simple ping message
            try:
                payload = json.dumps({"type": "ping"})
                await ws.send(payload)
                print('Sent ping payload')
            except Exception as e:
                print('Failed to send ping:', e)

            try:
                msg = await asyncio.wait_for(ws.recv(), timeout=5)
                print('Received message:', msg)
            except asyncio.TimeoutError:
                print('No message received within 5 seconds')
    except Exception as e:
        print('Connection failed:', type(e).__name__, e)

if __name__ == '__main__':
    asyncio.run(main())
