"""
SSRF (Server-Side Request Forgery) 防護模組
提供完整的 URL 驗證、IP 位址安全檢核、雲端 Metadata 防護以及防禦 SSRF 的安全 HTTP 抓取功能。
"""

import asyncio
import ipaddress
import logging
import re
import socket
from typing import Dict, List, Optional, Set, Tuple, Union
from urllib.parse import ParseResult, urljoin, urlparse
import httpx

logger = logging.getLogger(__name__)

# 禁止存取的保留/私有/特殊 IPv4 網段
DISALLOWED_IPV4_NETWORKS = [
    ipaddress.ip_network("0.0.0.0/8"),          # Current network (this host)
    ipaddress.ip_network("10.0.0.0/8"),         # Private Class A
    ipaddress.ip_network("100.64.0.0/10"),      # Shared Address Space (Carrier-grade NAT)
    ipaddress.ip_network("127.0.0.0/8"),        # Loopback
    ipaddress.ip_network("169.254.0.0/16"),     # Link-local / Cloud Metadata (AWS/GCP/Azure: 169.254.169.254)
    ipaddress.ip_network("172.16.0.0/12"),      # Private Class B
    ipaddress.ip_network("192.0.0.0/24"),       # IETF Protocol Assignments
    ipaddress.ip_network("192.0.2.0/24"),       # TEST-NET-1 (Documentation)
    ipaddress.ip_network("192.88.99.0/24"),     # 6to4 Relay Anycast
    ipaddress.ip_network("192.168.0.0/16"),     # Private Class C
    ipaddress.ip_network("198.18.0.0/15"),      # Network Benchmark Tests
    ipaddress.ip_network("198.51.100.0/24"),    # TEST-NET-2 (Documentation)
    ipaddress.ip_network("203.0.113.0/24"),     # TEST-NET-3 (Documentation)
    ipaddress.ip_network("224.0.0.0/4"),        # Multicast
    ipaddress.ip_network("240.0.0.0/4"),        # Reserved (Class E)
    ipaddress.ip_network("255.255.255.255/32"), # Broadcast
]

# 禁止存取的保留/私有/特殊 IPv6 網段
DISALLOWED_IPV6_NETWORKS = [
    ipaddress.ip_network("::/128"),             # Unspecified
    ipaddress.ip_network("::1/128"),           # Loopback
    ipaddress.ip_network("::ffff:0:0/96"),      # IPv4-mapped IPv6
    ipaddress.ip_network("64:ff9b::/96"),       # IPv4/IPv6 translation
    ipaddress.ip_network("100::/64"),           # Discard-only
    ipaddress.ip_network("2001::/23"),          # IETF Protocol Assignments
    ipaddress.ip_network("2001:db8::/32"),      # Documentation
    ipaddress.ip_network("fc00::/7"),           # Unique Local Address (ULA)
    ipaddress.ip_network("fe80::/10"),          # Link-Local unicast
    ipaddress.ip_network("ff00::/8"),           # Multicast
]

# 明確禁止的主機名稱關鍵字與後綴
DISALLOWED_HOSTNAMES: Set[str] = {
    "localhost",
    "localhost.localdomain",
    "broadcasthost",
    "ip6-localhost",
    "ip6-loopback",
    "local",
    "internal",
    "metadata.google.internal",
    "metadata.internal",
}

DISALLOWED_HOSTNAME_SUFFIXES: Tuple[str, ...] = (
    ".localhost",
    ".local",
    ".internal",
    ".lan",
    ".home.arpa",
    ".localdomain",
    ".corp",
)

# 敏感內部服務常見危險連接埠（除標準 HTTP/HTTPS 服務外之內部服務）
BLOCKED_DANGEROUS_PORTS: Set[int] = {
    22,    # SSH
    23,    # Telnet
    25,    # SMTP
    111,   # RPC
    135,   # RPC
    139,   # NetBIOS
    445,   # SMB
    1433,  # MSSQL
    1521,  # Oracle
    2375,  # Docker
    2376,  # Docker SSL
    3306,  # MySQL
    5432,  # PostgreSQL
    6379,  # Redis
    11211, # Memcached
    27017, # MongoDB
}


class SSRFProtectionError(ValueError):
    """SSRF 安全防護觸發異常"""
    pass


def is_ip_disallowed(ip: Union[str, ipaddress.IPv4Address, ipaddress.IPv6Address]) -> Tuple[bool, str]:
    """
    檢查指定的 IP 位址是否屬於私有、迴路、Link-local、雲端 Metadata 或保留網段。
    
    回傳:
        (is_disallowed, reason_message)
    """
    try:
        if isinstance(ip, str):
            ip_obj = ipaddress.ip_address(ip.strip())
        else:
            ip_obj = ip
    except ValueError:
        return True, f"無效的 IP 位址格式: {ip}"

    # 檢查 IPv4-mapped IPv6 位址 (例如 ::ffff:127.0.0.1)
    if isinstance(ip_obj, ipaddress.IPv6Address) and ip_obj.ipv4_mapped:
        ipv4_target = ip_obj.ipv4_mapped
        return is_ip_disallowed(ipv4_target)

    # 檢查內建屬性 (is_private, is_loopback, is_link_local, is_reserved, is_multicast, is_unspecified)
    if ip_obj.is_private:
        return True, f"禁止存取私有網路 IP 位址: {ip_obj}"
    if ip_obj.is_loopback:
        return True, f"禁止存取本機迴路 (Loopback) IP 位址: {ip_obj}"
    if ip_obj.is_link_local:
        return True, f"禁止存取 Link-Local (含雲端 Metadata) IP 位址: {ip_obj}"
    if ip_obj.is_reserved:
        return True, f"禁止存取保留網段 IP 位址: {ip_obj}"
    if ip_obj.is_multicast:
        return True, f"禁止存取群播 (Multicast) IP 位址: {ip_obj}"
    if ip_obj.is_unspecified:
        return True, f"禁止存取未指定 (0.0.0.0 / ::) IP 位址: {ip_obj}"

    # 檢查明確定義的 IPv4 / IPv6 禁止網段
    if isinstance(ip_obj, ipaddress.IPv4Address):
        for net in DISALLOWED_IPV4_NETWORKS:
            if ip_obj in net:
                return True, f"IP 位址 {ip_obj} 位於禁止網段 {net}"
    elif isinstance(ip_obj, ipaddress.IPv6Address):
        for net in DISALLOWED_IPV6_NETWORKS:
            if ip_obj in net:
                return True, f"IP 位址 {ip_obj} 位於禁止網段 {net}"

    return False, ""


def _resolve_hostname_sync(hostname: str, port: int) -> List[Union[ipaddress.IPv4Address, ipaddress.IPv6Address]]:
    """同步 DNS 解析主機名稱為 IP 清單"""
    resolved_ips: List[Union[ipaddress.IPv4Address, ipaddress.IPv6Address]] = []
    try:
        addr_info = socket.getaddrinfo(hostname, port, proto=socket.IPPROTO_TCP)
        for entry in addr_info:
            sockaddr = entry[4]
            ip_str = sockaddr[0]
            try:
                resolved_ips.append(ipaddress.ip_address(ip_str))
            except ValueError:
                continue
    except socket.gaierror as e:
        logger.warning(f"DNS 解析主機失敗 ({hostname}): {e}")
    return resolved_ips


async def resolve_hostname(hostname: str, port: int = 80) -> List[Union[ipaddress.IPv4Address, ipaddress.IPv6Address]]:
    """非阻塞非同步 DNS 解析主機名稱"""
    return await asyncio.to_thread(_resolve_hostname_sync, hostname, port)


async def validate_url_ssrf(
    url: str,
    allowed_schemes: Tuple[str, ...] = ("http", "https"),
    allow_private_ips: bool = False
) -> Tuple[bool, str, Optional[ParseResult]]:
    """
    全方位 SSRF URL 驗證器。
    
    檢查項目：
    1. URL 格式與 Scheme 是否合法 (僅允許 http/https)
    2. 禁止 Userinfo (如 http://user:pass@host)
    3. 禁止危險字元與異常編碼
    4. 檢查主機名稱是否為 localhost、.local、.internal 等保留域名
    5. 檢查連接埠是否為被封鎖的高危險內部服務連接埠
    6. 執行 DNS 解析並驗證所有關聯 IP 是否為公開合法 IP（非私有/迴路/雲端 metadata）
    
    回傳：
        (is_valid, error_reason, parsed_result)
    """
    if not url or not isinstance(url, str):
        return False, "URL 不能為空值", None

    clean_url = url.strip()
    try:
        parsed = urlparse(clean_url)
    except Exception as e:
        return False, f"URL 解析失敗: {str(e)}", None

    # 1. 協議驗證
    scheme = (parsed.scheme or "").lower()
    if scheme not in allowed_schemes:
        return False, f"不允許的 URL 協議 '{scheme}'，僅支援: {', '.join(allowed_schemes)}", None

    # 2. 主機名稱檢查
    hostname = parsed.hostname
    if not hostname:
        return False, "URL 中缺少有效的主機名稱 (Host)", None

    hostname_lower = hostname.lower().strip("[]")

    # 禁止包含認證資訊在 URL 中 (防止使用者名稱偽造攻擊)
    if parsed.username or parsed.password:
        return False, "URL 禁止包含帳號密碼資訊 (Userinfo)", None

    # 3. 檢查連接埠
    port = parsed.port
    if port is None:
        port = 443 if scheme == "https" else 80
    else:
        if port <= 0 or port > 65535:
            return False, f"無效的連接埠號碼: {port}", None
        if not allow_private_ips and port in BLOCKED_DANGEROUS_PORTS:
            return False, f"禁止存取受保護的內部服務連接埠: {port}", None

    # 4. 檢查主機名稱關鍵字與特殊域名後綴
    if not allow_private_ips:
        if hostname_lower in DISALLOWED_HOSTNAMES:
            return False, f"禁止訪問保留/內部主機名稱: {hostname_lower}", None

        for suffix in DISALLOWED_HOSTNAME_SUFFIXES:
            if hostname_lower.endswith(suffix):
                return False, f"禁止訪問內部專屬域名: {hostname_lower}", None

        # 檢查是否為直接輸入的 IP 位址字串
        try:
            direct_ip = ipaddress.ip_address(hostname_lower)
            is_disallowed, reason = is_ip_disallowed(direct_ip)
            if is_disallowed:
                return False, f"目標 IP 位址不被允許: {reason}", None
        except ValueError:
            # 不是直接的 IP 位址，為標準網域名稱
            pass

        # 5. DNS 解析並驗證所有解析出的 IP
        resolved_ips = await resolve_hostname(hostname_lower, port)
        if not resolved_ips:
            return False, f"無法解析主機名稱之 IP 位址: {hostname}", None

        for ip_addr in resolved_ips:
            is_disallowed, reason = is_ip_disallowed(ip_addr)
            if is_disallowed:
                logger.warning(f"SSRF 防護阻止存取 {url}: 解析出禁止 IP {ip_addr} ({reason})")
                return False, f"主機解析至受保護或私有 IP 位址 ({ip_addr}): {reason}", None

    return True, "", parsed


async def safe_fetch_text(
    url: str,
    timeout: float = 15.0,
    max_redirects: int = 5,
    max_size_bytes: int = 10 * 1024 * 1024,
    headers: Optional[Dict[str, str]] = None,
    allow_private_ips: bool = False
) -> str:
    """
    執行具備 SSRF 防護、安全轉址追蹤與回應大小限制的非同步 HTTP GET 請求。
    
    安全特性：
    - 在發送每次請求前嚴格驗證 URL 與 DNS 解析出的 IP
    - 手動處理轉址 (Redirect)，對每一次轉址目標皆重新進行 SSRF 檢核
    - 串流讀取回應本體，超過 max_size_bytes 即刻中斷，防止記憶體炸彈 / DoS
    
    參數:
        url: 目標 URL
        timeout: 超時秒數 (預設 15 秒)
        max_redirects: 最大轉址次數 (預設 5 次)
        max_size_bytes: 最大回應大小位元組 (預設 10MB)
        headers: 自訂 HTTP 標頭
        allow_private_ips: 是否允許存取私有 IP (預設 False)
        
    回傳:
        回應本文文字內容 (str)
        
    異常:
        SSRFProtectionError: 觸發 SSRF 防護規則
        ValueError: 請求失敗或內容異常
    """
    current_url = url.strip()
    redirect_count = 0
    visited_urls: Set[str] = set()

    req_headers = {
        "User-Agent": "Mozilla/5.0 (compatible; AskMiaoBot/1.0; +https://github.com/Scorpio-meow/AskMiao)",
        "Accept": "application/json, application/yaml, application/x-yaml, text/yaml, text/plain, */*",
    }
    if headers:
        req_headers.update(headers)

    while True:
        # 1. 驗證當前 URL 的 SSRF 安全性
        is_safe, error_msg, _ = await validate_url_ssrf(
            current_url,
            allowed_schemes=("http", "https"),
            allow_private_ips=allow_private_ips
        )
        if not is_safe:
            raise SSRFProtectionError(f"SSRF 防護拒絕連線: {error_msg}")

        visited_urls.add(current_url)

        # 2. 建立安全客戶端 (停用自動轉址，由我們手動逐一驗證轉址目標)
        client_kwargs = {
            "timeout": timeout,
            "follow_redirects": False,
        }

        try:
            async with httpx.AsyncClient(**client_kwargs) as client:
                req = client.build_request("GET", current_url, headers=req_headers)
                resp = await client.send(req, stream=True)

                try:
                    # 3. 處理轉址 (301, 302, 303, 307, 308)
                    if resp.status_code in (301, 302, 303, 307, 308):
                        redirect_count += 1
                        if redirect_count > max_redirects:
                            raise ValueError(f"轉址次數超過上限 ({max_redirects})")

                        location = resp.headers.get("Location")
                        if not location:
                            raise ValueError(f"轉址回應缺少 Location 標頭 (狀態碼 {resp.status_code})")

                        next_url = urljoin(current_url, location.strip())
                        if next_url in visited_urls:
                            raise ValueError(f"檢測到循環轉址: {next_url}")

                        logger.info(f"安全轉址 ({redirect_count}/{max_redirects}): {current_url} -> {next_url}")
                        current_url = next_url
                        continue

                    # 4. 驗證非轉址的回應狀態碼
                    if resp.status_code != 200:
                        raise ValueError(f"遠端伺服器返回非成功狀態碼: {resp.status_code}")

                    # 5. 檢查 Content-Length 標頭
                    content_length = resp.headers.get("Content-Length")
                    if content_length and content_length.isdigit():
                        if int(content_length) > max_size_bytes:
                            raise ValueError(
                                f"回應檔案過大: {int(content_length)} 位元組 (上限 {max_size_bytes} 位元組)"
                            )

                    # 6. 串流下載並檢查實際大小
                    chunks = []
                    total_bytes = 0
                    async for chunk in resp.aiter_bytes():
                        total_bytes += len(chunk)
                        if total_bytes > max_size_bytes:
                            raise ValueError(
                                f"回應內容大小超過限制 ({max_size_bytes} 位元組)"
                            )
                        chunks.append(chunk)

                    raw_bytes = b"".join(chunks)
                    encoding = resp.encoding or "utf-8"
                    try:
                        return raw_bytes.decode(encoding)
                    except (UnicodeDecodeError, LookupError):
                        return raw_bytes.decode("utf-8", errors="replace")

                finally:
                    await resp.aclose()

        except (SSRFProtectionError, ValueError):
            raise
        except Exception as e:
            raise ValueError(f"無法存取遠端 URL: {str(e)}")