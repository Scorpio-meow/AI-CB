"""
SSRF 防護單元測試與整合測試
驗證：
1. 私有 IP、迴路 IP、Link-Local、雲端 Metadata IP 檢測
2. IPv6 與 IPv4-mapped IPv6 檢測
3. 特殊/保留主機名稱與域名後綴檢測
4. 危險通訊協定與危險連接埠檢測
5. 轉址 (Redirect) SSRF 攻擊防禦 (轉址到內部 IP 自動中斷)
6. 回應本文大小上限限制 (防止 Memory Bomb / DoS)
7. OpenApiParser 與 InputValidator 整合驗證
"""

import ipaddress
from unittest.mock import AsyncMock, patch, MagicMock
import pytest
import httpx

from app.core.ssrf_protection import (
    is_ip_disallowed,
    validate_url_ssrf,
    safe_fetch_text,
    SSRFProtectionError,
)
from app.services.openapi_parser import OpenApiParser
from app.core.input_validator import InputValidator


# ==========================================
# 1. IP 位址禁止檢測 (is_ip_disallowed)
# ==========================================

def test_ip_disallowed_private_ipv4():
    """測試私有 IPv4 網段 (RFC 1918)"""
    private_ips = [
        "10.0.0.1",
        "10.255.255.254",
        "172.16.0.1",
        "172.31.255.255",
        "192.168.0.1",
        "192.168.1.100",
        "192.168.255.254",
    ]
    for ip in private_ips:
        disallowed, reason = is_ip_disallowed(ip)
        assert disallowed is True, f"應該封鎖私有 IP: {ip}"
        assert "私有" in reason or "禁止網段" in reason


def test_ip_disallowed_loopback_and_special():
    """測試迴路與特殊用途 IPv4 網段"""
    special_ips = [
        "127.0.0.1",
        "127.0.0.2",
        "127.255.255.255",
        "0.0.0.0",
        "169.254.169.254",  # AWS / Azure / GCP Metadata IP
        "169.254.1.1",      # Link-local
        "100.64.0.1",       # Carrier-grade NAT
        "192.0.2.1",        # TEST-NET-1
        "198.51.100.1",     # TEST-NET-2
        "203.0.113.1",      # TEST-NET-3
        "224.0.0.1",        # Multicast
        "240.0.0.1",        # Reserved
        "255.255.255.255",  # Broadcast
    ]
    for ip in special_ips:
        disallowed, reason = is_ip_disallowed(ip)
        assert disallowed is True, f"應該封鎖特殊/迴路 IP: {ip}"


def test_ip_disallowed_ipv6():
    """測試 IPv6 迴路、私有與 Link-Local"""
    ipv6_blocked = [
        "::1",                 # Loopback
        "::",                  # Unspecified
        "fe80::1",             # Link-local
        "fc00::1",             # ULA
        "fd12:3456:789a::1",   # ULA
        "ff02::1",             # Multicast
        "::ffff:127.0.0.1",    # IPv4-mapped loopback
        "::ffff:169.254.169.254", # IPv4-mapped metadata
        "::ffff:10.0.0.1",     # IPv4-mapped private
        "::ffff:192.168.1.1",  # IPv4-mapped private
    ]
    for ip in ipv6_blocked:
        disallowed, reason = is_ip_disallowed(ip)
        assert disallowed is True, f"應該封鎖 IPv6 IP: {ip}"


def test_ip_allowed_public_ips():
    """測試合法的公開 IPv4 / IPv6 位址"""
    public_ips = [
        "8.8.8.8",
        "1.1.1.1",
        "93.184.216.34",       # example.com
        "140.82.112.4",        # github.com
        "2606:4700:4700::1111",# Cloudflare DNS IPv6
    ]
    for ip in public_ips:
        disallowed, reason = is_ip_disallowed(ip)
        assert disallowed is False, f"合法的公開 IP 不應被封鎖: {ip}, reason={reason}"


# ==========================================
# 2. URL SSRF 驗證 (validate_url_ssrf)
# ==========================================

@pytest.mark.anyio
async def test_validate_url_disallowed_schemes():
    """測試拒絕非 HTTP/HTTPS 協議"""
    invalid_urls = [
        "file:///etc/passwd",
        "ftp://ftp.example.com/files",
        "gopher://evil.com:70/1",
        "dict://dict.org/d:word",
        "ldap://localhost:389",
        "javascript:alert(1)",
    ]
    for u in invalid_urls:
        is_safe, reason, _ = await validate_url_ssrf(u)
        assert is_safe is False
        assert "協議" in reason or "格式" in reason


@pytest.mark.anyio
async def test_validate_url_disallowed_hostnames():
    """測試拒絕保留或內部主機名稱與後綴"""
    blocked_hosts = [
        "http://localhost/openapi.json",
        "http://localhost:8080/spec.yaml",
        "https://localhost.localdomain/api",
        "http://test.localhost/docs",
        "http://api.local/spec",
        "http://db.internal/metrics",
        "http://server.lan/v1",
        "http://metadata.google.internal/computeMetadata/v1/",
    ]
    for u in blocked_hosts:
        is_safe, reason, _ = await validate_url_ssrf(u)
        assert is_safe is False
        assert "保留" in reason or "內部" in reason or "主機" in reason


@pytest.mark.anyio
async def test_validate_url_direct_private_ips():
    """測試直接以私有/迴路 IP 為主機的 URL"""
    blocked_ip_urls = [
        "http://127.0.0.1:8000/api",
        "http://127.0.0.1/openapi.json",
        "http://169.254.169.254/latest/meta-data/",
        "http://10.0.0.1:8080/swagger.json",
        "http://192.168.1.1/admin",
        "http://172.16.1.1/openapi.json",
        "http://[::1]:8080/spec",
    ]
    for u in blocked_ip_urls:
        is_safe, reason, _ = await validate_url_ssrf(u)
        assert is_safe is False
        assert "IP" in reason or "禁止" in reason or "主機" in reason


@pytest.mark.anyio
async def test_validate_url_userinfo_blocked():
    """測試禁止 URL 攜帶認證帳密資訊"""
    u = "http://admin:secret@example.com/api"
    is_safe, reason, _ = await validate_url_ssrf(u)
    assert is_safe is False
    assert "Userinfo" in reason or "帳號密碼" in reason


@pytest.mark.anyio
async def test_validate_url_dangerous_ports():
    """測試封鎖敏感內部服務端口 (如 22, 6379, 3306)"""
    dangerous_port_urls = [
        "http://example.com:22/",
        "http://example.com:3306/",
        "http://example.com:6379/",
        "http://example.com:5432/",
        "http://example.com:27017/",
    ]
    for u in dangerous_port_urls:
        is_safe, reason, _ = await validate_url_ssrf(u)
        assert is_safe is False
        assert "連接埠" in reason or "連接" in reason


@pytest.mark.anyio
async def test_validate_url_valid_public_domain():
    """測試合法公開網域名稱通過驗證 (使用 mock DNS 解析為公網 IP)"""
    mock_ips = [ipaddress.ip_address("93.184.216.34")]
    with patch("app.core.ssrf_protection.resolve_hostname", new_callable=AsyncMock) as mock_dns:
        mock_dns.return_value = mock_ips
        is_safe, reason, parsed = await validate_url_ssrf("https://example.com/openapi.json")
        assert is_safe is True
        assert reason == ""
        assert parsed is not None
        assert parsed.hostname == "example.com"


# ==========================================
# 3. 安全 HTTP 抓取 (safe_fetch_text)
# ==========================================

@pytest.mark.anyio
async def test_safe_fetch_text_blocks_ssrf():
    """測試 safe_fetch_text 直接阻擋私有 IP 與惡意 URL"""
    with pytest.raises(SSRFProtectionError):
        await safe_fetch_text("http://127.0.0.1:8000/secret.json")

    with pytest.raises(SSRFProtectionError):
        await safe_fetch_text("http://169.254.169.254/latest/meta-data/")

    with pytest.raises(SSRFProtectionError):
        await safe_fetch_text("file:///etc/passwd")


@pytest.mark.anyio
async def test_safe_fetch_text_blocks_redirect_to_private_ip():
    """
    重要安全測試：防止 302 轉址繞過 SSRF 防護
    伺服器回傳 302 轉址到 http://169.254.169.254/ 時，應在追蹤轉址時被攔截並拋出 SSRFProtectionError
    """
    mock_public_ips = [ipaddress.ip_address("93.184.216.34")]
    with patch("app.core.ssrf_protection.resolve_hostname", new_callable=AsyncMock) as mock_dns:
        mock_dns.return_value = mock_public_ips

        # 模擬第一個請求返回 302 轉址到 AWS Metadata IP
        mock_response_302 = MagicMock()
        mock_response_302.status_code = 302
        mock_response_302.headers = {"Location": "http://169.254.169.254/latest/meta-data/"}
        mock_response_302.aclose = AsyncMock()

        with patch("httpx.AsyncClient.send", new_callable=AsyncMock) as mock_send:
            mock_send.return_value = mock_response_302

            with pytest.raises(SSRFProtectionError) as exc_info:
                await safe_fetch_text("https://example.com/redirect-to-metadata")

            assert "SSRF 防護" in str(exc_info.value)
            assert "169.254.169.254" in str(exc_info.value) or "禁止" in str(exc_info.value)


@pytest.mark.anyio
async def test_safe_fetch_text_size_limit():
    """測試防止巨大檔案 / 記憶體炸彈攻擊 (> 10MB)"""
    mock_public_ips = [ipaddress.ip_address("93.184.216.34")]
    with patch("app.core.ssrf_protection.resolve_hostname", new_callable=AsyncMock) as mock_dns:
        mock_dns.return_value = mock_public_ips

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {"Content-Length": "20000000"}  # 20MB
        mock_response.aclose = AsyncMock()

        with patch("httpx.AsyncClient.send", new_callable=AsyncMock) as mock_send:
            mock_send.return_value = mock_response

            with pytest.raises(ValueError) as exc_info:
                await safe_fetch_text("https://example.com/large_spec.json", max_size_bytes=10 * 1024 * 1024)

            assert "過大" in str(exc_info.value) or "超過限制" in str(exc_info.value)


# ==========================================
# 4. OpenApiParser 整合安全測試
# ==========================================

@pytest.mark.anyio
async def test_openapi_parser_ssrf_protection():
    """測試 OpenApiParser.parse() 拒絕惡意 URL"""
    malicious_inputs = [
        "http://127.0.0.1:8000/openapi.json",
        "http://localhost:5000/swagger.yaml",
        "http://169.254.169.254/latest/meta-data/",
        "http://10.0.0.1/spec.json",
        "http://192.168.1.1/api-docs",
    ]
    for url in malicious_inputs:
        with pytest.raises(ValueError) as exc_info:
            await OpenApiParser.parse(url)
        assert "安全防護" in str(exc_info.value) or "SSRF" in str(exc_info.value) or "失敗" in str(exc_info.value)


@pytest.mark.anyio
async def test_openapi_parser_valid_text_still_works():
    """驗證非 URL 的原始 YAML/JSON 規格依然能正常解析"""
    valid_spec = """
openapi: 3.0.0
info:
  title: Safe Test API
  version: 1.0.0
paths:
  /test:
    get:
      summary: Safe Endpoint
      responses:
        '200':
          description: OK
"""
    res = await OpenApiParser.parse(valid_spec)
    assert res["title"] == "Safe Test API"
    assert res["version"] == "openapi_3.0"
    assert len(res["endpoints"]) == 1


# ==========================================
# 5. InputValidator 工具測試
# ==========================================

def test_input_validator_ssrf_helper():
    """測試 InputValidator 中的 SSRF 驗證函式"""
    is_safe_bad, reason_bad = InputValidator.validate_url_for_ssrf("http://127.0.0.1:9000/api")
    assert is_safe_bad is False

    is_safe_bad2, reason_bad2 = InputValidator.validate_url_for_ssrf("http://localhost/test")
    assert is_safe_bad2 is False

    clean_url = InputValidator.sanitize_url("https://api.example.com/v1/users")
    assert clean_url == "https://api.example.com/v1/users"

    dirty_url = InputValidator.sanitize_url("javascript:alert(1)")
    assert dirty_url is None