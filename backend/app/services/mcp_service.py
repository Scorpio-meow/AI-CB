import asyncio
import json
import logging
import os
import re
import sys
import time
from typing import Any, Dict, List, Optional, Tuple
import httpx
logger = logging.getLogger(__name__)
MCP_PROTOCOL_VERSION = "2024-11-05"
class McpStdioClient:
    """
    基於 Stdio (標準輸入/輸出子進程) 的 MCP 用戶端通訊器
    透過 JSON-RPC 2.0 協議與本地 MCP 伺服器交握並調用工具
    """
    def __init__(
        self,
        command: str,
        args: Optional[List[str]] = None,
        env_vars: Optional[Dict[str, str]] = None,
        timeout: float = 30.0
    ):
        self.command = command
        self.args = args or []
        self.env_vars = env_vars or {}
        self.timeout = timeout
        self.process: Optional[asyncio.subprocess.Process] = None
        self._request_id = 0
    def _next_id(self) -> int:
        self._request_id += 1
        return self._request_id
    async def start(self):
        """啟動子進程"""
        env = dict(os.environ)
        env.update(self.env_vars)
        full_cmd = [self.command] + self.args
        try:
            self.process = await asyncio.create_subprocess_exec(
                *full_cmd,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env
            )
        except Exception as e:
            raise RuntimeError(f"無法啟動 MCP 子進程 ({' '.join(full_cmd)}): {str(e)}")
    async def close(self):
        """關閉子進程"""
        if self.process:
            try:
                self.process.terminate()
                await asyncio.wait_for(self.process.wait(), timeout=3.0)
            except Exception:
                try:
                    self.process.kill()
                except Exception:
                    pass
            finally:
                self.process = None
    async def _send_rpc_request(self, method: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """發送單次 JSON-RPC 2.0 請求並讀取回應"""
        if not self.process or not self.process.stdin or not self.process.stdout:
            raise RuntimeError("MCP 子進程尚未啟動或通訊管線已中斷")
        req_id = self._next_id()
        payload = {
            "jsonrpc": "2.0",
            "id": req_id,
            "method": method,
            "params": params or {}
        }
        msg_line = json.dumps(payload, ensure_ascii=False) + "\n"
        self.process.stdin.write(msg_line.encode("utf-8"))
        await self.process.stdin.drain()
        start_t = time.time()
        while True:
            if time.time() - start_t > self.timeout:
                raise TimeoutError(f"等待 MCP 伺服器回應逾時 ({self.timeout}s)")
            try:
                line_bytes = await asyncio.wait_for(self.process.stdout.readline(), timeout=self.timeout)
            except asyncio.TimeoutError:
                raise TimeoutError(f"讀取 MCP 伺服器輸出逾時")
            if not line_bytes:
 
                err_bytes = b""
                if self.process.stderr:
                    try:
                        err_bytes = await asyncio.wait_for(self.process.stderr.read(2048), timeout=0.5)
                    except Exception:
                        pass
                raise RuntimeError(f"MCP 伺服器已異常退出: {err_bytes.decode('utf-8', errors='ignore')}")
            line_str = line_bytes.decode("utf-8", errors="ignore").strip()
            if not line_str:
                continue
            try:
                data = json.loads(line_str)
                if isinstance(data, dict) and data.get("id") == req_id:
                    if "error" in data:
                        raise RuntimeError(f"MCP JSON-RPC 錯誤: {data['error']}")
                    return data.get("result", {})
            except json.JSONDecodeError:
 
                logger.debug(f"[MCP Stdio Log] {line_str}")
                continue
    async def initialize(self) -> Dict[str, Any]:
        """執行 MCP Initialize 交握"""
        result = await self._send_rpc_request(
            "initialize",
            {
                "protocolVersion": MCP_PROTOCOL_VERSION,
                "capabilities": {
                    "roots": {"listChanged": True},
                    "sampling": {}
                },
                "clientInfo": {
                    "name": "AskMiao-MCP-Client",
                    "version": "1.0.0"
                }
            }
        )
        if self.process and self.process.stdin:
            notif = {
                "jsonrpc": "2.0",
                "method": "notifications/initialized"
            }
            self.process.stdin.write((json.dumps(notif) + "\n").encode("utf-8"))
            await self.process.stdin.drain()
        return result
    async def list_tools(self) -> List[Dict[str, Any]]:
        """向 MCP 伺服器查詢所有可用工具"""
        result = await self._send_rpc_request("tools/list", {})
        return result.get("tools", [])
    async def call_tool(self, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """向 MCP 伺服器發送 tools/call 工具執行請求"""
        result = await self._send_rpc_request("tools/call", {
            "name": name,
            "arguments": arguments or {}
        })
        return result
class McpHttpClient:
    """
    基於 HTTP / SSE 網路連線的 MCP 用戶端通訊器
    """
    def __init__(
        self,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        timeout: float = 30.0
    ):
        self.url = url
        self.headers = headers or {}
        self.timeout = timeout
        self._request_id = 0
    def _next_id(self) -> int:
        self._request_id += 1
        return self._request_id
    async def _send_rpc_request(self, method: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        req_id = self._next_id()
        payload = {
            "jsonrpc": "2.0",
            "id": req_id,
            "method": method,
            "params": params or {}
        }
        async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True) as client:
            resp = await client.post(self.url, headers=self.headers, json=payload)
            if resp.status_code != 200:
                raise RuntimeError(f"HTTP MCP 伺服器返回狀態碼 {resp.status_code}: {resp.text}")
            data = resp.json()
            if "error" in data:
                raise RuntimeError(f"MCP JSON-RPC 錯誤: {data['error']}")
            return data.get("result", {})
    async def initialize(self) -> Dict[str, Any]:
        return await self._send_rpc_request("initialize", {
            "protocolVersion": MCP_PROTOCOL_VERSION,
            "capabilities": {},
            "clientInfo": {
                "name": "AskMiao-MCP-Client",
                "version": "1.0.0"
            }
        })
    async def list_tools(self) -> List[Dict[str, Any]]:
        result = await self._send_rpc_request("tools/list", {})
        return result.get("tools", [])
    async def call_tool(self, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        return await self._send_rpc_request("tools/call", {
            "name": name,
            "arguments": arguments or {}
        })
class McpManager:
    """
    MCP 伺服器與工具調度管理器
    """
    @classmethod
    def get_preset_servers(cls) -> List[Dict[str, Any]]:
        """常見官方與社群 MCP 伺服器快速範本"""
        return [
            {
                "name": "mcp_time",
                "display_name": "即時時間與時區轉換 (Time)",
                "description": "提供全球各大城市當前精確時間查詢、時區換算與時間差計算工具。",
                "transport_type": "stdio",
                "command": "python",
                "args": ["-c", """import sys, json, datetime, zoneinfo
def main():
    while True:
        line = sys.stdin.readline()
        if not line: break
        try:
            req = json.loads(line)
            mid = req.get('id')
            method = req.get('method')
            if method == 'initialize':
                res = {'jsonrpc': '2.0', 'id': mid, 'result': {'protocolVersion': '2024-11-05', 'capabilities': {'tools': {}}, 'serverInfo': {'name': 'mcp-time-server', 'version': '1.0'}}}
                sys.stdout.write(json.dumps(res) + '\\n'); sys.stdout.flush()
            elif method == 'tools/list':
                tools = [{
                    'name': 'get_current_time',
                    'description': '查詢指定時區或城市的當前精確時間',
                    'inputSchema': {
                        'type': 'object',
                        'properties': {
                            'timezone': {'type': 'string', 'description': '時區名稱 (例如 Asia/Taipei, UTC, America/New_York)', 'default': 'Asia/Taipei'}
                        }
                    }
                }]
                res = {'jsonrpc': '2.0', 'id': mid, 'result': {'tools': tools}}
                sys.stdout.write(json.dumps(res) + '\\n'); sys.stdout.flush()
            elif method == 'tools/call':
                params = req.get('params', {})
                tz_name = params.get('arguments', {}).get('timezone', 'Asia/Taipei')
                try:
                    tz = zoneinfo.ZoneInfo(tz_name)
                    now_str = datetime.datetime.now(tz).strftime('%Y-%m-%d %H:%M:%S %Z')
                except Exception:
                    now_str = datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')
                content = [{'type': 'text', 'text': f'當前時間: {now_str}'}]
                res = {'jsonrpc': '2.0', 'id': mid, 'result': {'content': content, 'isError': False}}
                sys.stdout.write(json.dumps(res) + '\\n'); sys.stdout.flush()
        except Exception:
            pass
if __name__ == '__main__':
    main()
"""],
                "env_vars": {}
            },
            {
                "name": "mcp_filesystem",
                "display_name": "檔案系統安全讀取 (Filesystem)",
                "description": "提供本機安全沙箱目錄下的檔案瀏覽、搜尋與檔案讀取工具。",
                "transport_type": "stdio",
                "command": "npx",
                "args": ["-y", "@modelcontextprotocol/server-filesystem", "./data"],
                "env_vars": {}
            },
            {
                "name": "mcp_fetch",
                "display_name": "網頁內容深度擷取 (Fetch)",
                "description": "提供將指定公開網址之 HTML 轉換為乾淨 Markdown 的網頁讀取工具。",
                "transport_type": "stdio",
                "command": "uvx",
                "args": ["mcp-server-fetch"],
                "env_vars": {}
            }
        ]
    @classmethod
    async def discover_server_tools(cls, server_dict: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """
        向指定 MCP 伺服器進行 Initialize 交握並探索工具清單 (tools/list)
        回傳: (tools_list, server_info)
        """
        transport_type = server_dict.get("transport_type", "stdio")
        timeout = float(server_dict.get("timeout", 20))
        if transport_type == "stdio":
            cmd = server_dict.get("command")
            if not cmd:
                raise ValueError("Stdio 傳輸模式必須指定 command 執行指令")
            raw_args = server_dict.get("args") or []
            if isinstance(raw_args, str):
                try:
                    raw_args = json.loads(raw_args)
                except Exception:
                    raw_args = [raw_args]
            raw_env = server_dict.get("env_vars") or {}
            if isinstance(raw_env, str):
                try:
                    raw_env = json.loads(raw_env)
                except Exception:
                    raw_env = {}
            client = McpStdioClient(
                command=cmd,
                args=raw_args,
                env_vars=raw_env,
                timeout=timeout
            )
            try:
                await client.start()
                init_res = await client.initialize()
                tools = await client.list_tools()
                return tools, init_res
            finally:
                await client.close()
        elif transport_type in ["sse", "http"]:
            url = server_dict.get("url")
            if not url:
                raise ValueError("SSE/HTTP 傳輸模式必須指定 url 連線網址")
            raw_headers = server_dict.get("headers") or {}
            if isinstance(raw_headers, str):
                try:
                    raw_headers = json.loads(raw_headers)
                except Exception:
                    raw_headers = {}
            client = McpHttpClient(
                url=url,
                headers=raw_headers,
                timeout=timeout
            )
            init_res = await client.initialize()
            tools = await client.list_tools()
            return tools, init_res
        else:
            raise ValueError(f"不支援的傳輸模式: {transport_type}")
    @classmethod
    async def execute_mcp_tool(
        cls,
        server_dict: Dict[str, Any],
        tool_name: str,
        arguments: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        調用指定 MCP 伺服器之特定工具 (tools/call)
        """
        start_t = time.time()
        transport_type = server_dict.get("transport_type", "stdio")
        timeout = float(server_dict.get("timeout", 30))
        try:
            if transport_type == "stdio":
                cmd = server_dict.get("command")
                raw_args = server_dict.get("args") or []
                if isinstance(raw_args, str):
                    try:
                        raw_args = json.loads(raw_args)
                    except Exception:
                        raw_args = [raw_args]
                raw_env = server_dict.get("env_vars") or {}
                if isinstance(raw_env, str):
                    try:
                        raw_env = json.loads(raw_env)
                    except Exception:
                        raw_env = {}
                client = McpStdioClient(
                    command=cmd,
                    args=raw_args,
                    env_vars=raw_env,
                    timeout=timeout
                )
                try:
                    await client.start()
                    await client.initialize()
                    res = await client.call_tool(tool_name, arguments)
                    duration = round(time.time() - start_t, 3)
                    return {
                        "is_success": not res.get("isError", False),
                        "duration_seconds": duration,
                        "content": res.get("content", []),
                        "raw_result": res
                    }
                finally:
                    await client.close()
            elif transport_type in ["sse", "http"]:
                url = server_dict.get("url")
                raw_headers = server_dict.get("headers") or {}
                if isinstance(raw_headers, str):
                    try:
                        raw_headers = json.loads(raw_headers)
                    except Exception:
                        raw_headers = {}
                client = McpHttpClient(
                    url=url,
                    headers=raw_headers,
                    timeout=timeout
                )
                await client.initialize()
                res = await client.call_tool(tool_name, arguments)
                duration = round(time.time() - start_t, 3)
                return {
                    "is_success": not res.get("isError", False),
                    "duration_seconds": duration,
                    "content": res.get("content", []),
                    "raw_result": res
                }
            else:
                raise ValueError(f"不支援的傳輸模式: {transport_type}")
        except Exception as e:
            duration = round(time.time() - start_t, 3)
            logger.error(f"調用 MCP 工具 {tool_name} 失敗: {e}")
            return {
                "is_success": False,
                "duration_seconds": duration,
                "error": f"調用 MCP 工具失敗: {str(e)}"
            }
    @classmethod
    def convert_mcp_tool_to_function_def(
        cls,
        server_name: str,
        server_display_name: str,
        mcp_tool: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        將 MCP tool 規格轉換為 OpenAI Function Calling 相容之 Tool Definition
        """
        t_name = mcp_tool.get("name", "")
        clean_server = re.sub(r'[^a-zA-Z0-9_]', '_', server_name).lower()
        clean_tool = re.sub(r'[^a-zA-Z0-9_]', '_', t_name).lower()
        fn_name = f"mcp_{clean_server}_{clean_tool}"
        desc = mcp_tool.get("description") or f"由 MCP 伺服器 [{server_display_name}] 提供的工具: {t_name}"
        input_schema = mcp_tool.get("inputSchema") or {"type": "object", "properties": {}}
        return {
            "type": "function",
            "function": {
                "name": fn_name,
                "description": f"【MCP 協定工具】{server_display_name} -> {t_name}：{desc}",
                "parameters": input_schema
            }
        }