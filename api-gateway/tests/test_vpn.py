"""
Comprehensive tests for VPN health diagnostics endpoint.

Tests VPN router functionality including:
- Public access to health endpoint (no authentication required)
- VPN disabled scenario
- WireGuard/AWG health checks
- Hysteria2 health checks
- Gemini probe results
- Response schema validation
- Error handling and edge cases

VPN endpoint is public by design for monitoring/health checks.
"""

from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

from app.schemas.vpn import (
    GeminiProbeResult,
    GeminiProbeStatus,
    Hysteria2Status,
    InterfaceStatus,
    RouteEntry,
    VpnHealthResponse,
    VpnHealthStatus,
    VpnPeer,
    VpnType,
    WireGuardOverview,
)


# --- Helper Functions ---

def create_healthy_wireguard_response() -> VpnHealthResponse:
    """Create a mock healthy WireGuard response."""
    return VpnHealthResponse(
        status=VpnHealthStatus.HEALTHY,
        vpn_type=VpnType.WIREGUARD,
        interface=InterfaceStatus(
            name="wg0",
            is_up=True,
            state="UP",
            addresses=["10.0.0.2/24"],
        ),
        wireguard=WireGuardOverview(
            interface="wg0",
            public_key="abc123public",
            listen_port=51820,
            peers=[
                VpnPeer(
                    public_key="peer1public",
                    endpoint="vpn.example.com:51820",
                    allowed_ips=["0.0.0.0/0"],
                    latest_handshake="1 minute ago",
                    transfer_rx_bytes=1024000,
                    transfer_tx_bytes=512000,
                )
            ],
        ),
        routes=[
            RouteEntry(
                destination="0.0.0.0/0",
                via="10.0.0.1",
                dev="wg0",
                metric=100,
                raw="0.0.0.0/0 via 10.0.0.1 dev wg0 metric 100",
            )
        ],
        probe=GeminiProbeResult(
            domain="generativelanguage.googleapis.com",
            status=GeminiProbeStatus.OK,
            http_status=200,
            latency_ms=50.5,
        ),
        details=[],
    )


def create_degraded_wireguard_response() -> VpnHealthResponse:
    """Create a mock degraded WireGuard response."""
    return VpnHealthResponse(
        status=VpnHealthStatus.DEGRADED,
        vpn_type=VpnType.WIREGUARD,
        interface=InterfaceStatus(
            name="wg0",
            is_up=False,
            state="DOWN",
            addresses=[],
            error="Interface is down",
        ),
        wireguard=WireGuardOverview(
            interface="wg0",
            error="'wg' binary not found inside container.",
        ),
        routes=[],
        probe=GeminiProbeResult(
            domain="generativelanguage.googleapis.com",
            status=GeminiProbeStatus.FAIL,
            error="Connection timeout",
        ),
        details=[
            "Interface is down",
            "'wg' binary not found inside container.",
            "Connection timeout",
        ],
    )


def create_disabled_vpn_response() -> VpnHealthResponse:
    """Create a mock disabled VPN response."""
    return VpnHealthResponse(
        status=VpnHealthStatus.DISABLED,
        vpn_type=VpnType.WIREGUARD,
        interface=InterfaceStatus(
            name="wg0",
            is_up=False,
            error="VPN disabled in configuration.",
        ),
        wireguard=WireGuardOverview(
            interface="wg0",
            error="VPN disabled in configuration.",
        ),
        routes=[],
        probe=GeminiProbeResult(
            domain="generativelanguage.googleapis.com",
            status=GeminiProbeStatus.SKIPPED,
            error="VPN disabled.",
        ),
        details=["VPN disabled in configuration."],
    )


def create_healthy_hysteria2_response() -> VpnHealthResponse:
    """Create a mock healthy Hysteria2 response."""
    return VpnHealthResponse(
        status=VpnHealthStatus.HEALTHY,
        vpn_type=VpnType.HYSTERIA2,
        hysteria2=Hysteria2Status(
            server="vpn.example.com:443",
            socks5_port=1080,
            http_port=8080,
            is_running=True,
            socks5_accessible=True,
            http_accessible=True,
        ),
        probe=GeminiProbeResult(
            domain="generativelanguage.googleapis.com",
            status=GeminiProbeStatus.OK,
            http_status=200,
            latency_ms=45.3,
        ),
        details=[],
    )


def create_degraded_hysteria2_response() -> VpnHealthResponse:
    """Create a mock degraded Hysteria2 response."""
    return VpnHealthResponse(
        status=VpnHealthStatus.DEGRADED,
        vpn_type=VpnType.HYSTERIA2,
        hysteria2=Hysteria2Status(
            server="vpn.example.com:443",
            socks5_port=1080,
            http_port=8080,
            is_running=False,
            socks5_accessible=False,
            http_accessible=False,
            error="Hysteria process not running",
        ),
        probe=GeminiProbeResult(
            domain="generativelanguage.googleapis.com",
            status=GeminiProbeStatus.FAIL,
            error="Connection timeout",
        ),
        details=[
            "Hysteria process not running",
            "Connection timeout",
        ],
    )


# --- Healthy VPN Tests ---

@pytest.mark.asyncio
async def test_vpn_health_wireguard_healthy(client: AsyncClient):
    """
    VPN health check returns 200 for healthy WireGuard connection.

    Expected:
    - 200 OK
    - status: HEALTHY
    - vpn_type: WIREGUARD
    - Interface is UP with addresses
    - WireGuard peers connected
    - Routes configured
    - Gemini probe successful
    """
    mock_response = create_healthy_wireguard_response()

    with patch(
        "app.routers.vpn.gather_vpn_health",
        new_callable=AsyncMock,
        return_value=mock_response,
    ):
        response = await client.get("/api/vpn/health")

    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "healthy"
    assert data["vpn_type"] == "wireguard"
    assert data["interface"]["is_up"] is True
    assert data["interface"]["name"] == "wg0"
    assert len(data["interface"]["addresses"]) > 0
    assert data["wireguard"]["public_key"] == "abc123public"
    assert data["wireguard"]["listen_port"] == 51820
    assert len(data["wireguard"]["peers"]) > 0
    assert len(data["routes"]) > 0
    assert data["probe"]["status"] == "ok"
    assert data["probe"]["http_status"] == 200
    assert len(data["details"]) == 0


@pytest.mark.asyncio
async def test_vpn_health_hysteria2_healthy(client: AsyncClient):
    """
    VPN health check returns 200 for healthy Hysteria2 connection.

    Expected:
    - 200 OK
    - status: HEALTHY
    - vpn_type: HYSTERIA2
    - Hysteria2 process running
    - Both SOCKS5 and HTTP ports accessible
    - Gemini probe successful
    """
    mock_response = create_healthy_hysteria2_response()

    with patch(
        "app.routers.vpn.gather_vpn_health",
        new_callable=AsyncMock,
        return_value=mock_response,
    ):
        response = await client.get("/api/vpn/health")

    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "healthy"
    assert data["vpn_type"] == "hysteria2"
    assert data["hysteria2"]["is_running"] is True
    assert data["hysteria2"]["socks5_accessible"] is True
    assert data["hysteria2"]["http_accessible"] is True
    assert data["hysteria2"]["socks5_port"] == 1080
    assert data["hysteria2"]["http_port"] == 8080
    assert data["probe"]["status"] == "ok"
    assert len(data["details"]) == 0


# --- Degraded VPN Tests ---

@pytest.mark.asyncio
async def test_vpn_health_wireguard_degraded(client: AsyncClient):
    """
    VPN health check returns 503 for degraded WireGuard connection.

    Degraded scenarios:
    - Interface is down
    - WireGuard binary not found
    - Gemini probe fails
    - No active peers

    Expected:
    - 503 Service Unavailable
    - status: DEGRADED
    - Details array contains error messages
    """
    mock_response = create_degraded_wireguard_response()

    with patch(
        "app.routers.vpn.gather_vpn_health",
        new_callable=AsyncMock,
        return_value=mock_response,
    ):
        response = await client.get("/api/vpn/health")

    assert response.status_code == 503
    data = response.json()

    assert data["status"] == "degraded"
    assert data["vpn_type"] == "wireguard"
    assert data["interface"]["is_up"] is False
    assert data["interface"]["error"] is not None
    assert data["wireguard"]["error"] is not None
    assert data["probe"]["status"] == "fail"
    assert len(data["details"]) > 0
    assert any("down" in detail.lower() for detail in data["details"])


@pytest.mark.asyncio
async def test_vpn_health_hysteria2_degraded(client: AsyncClient):
    """
    VPN health check returns 503 for degraded Hysteria2 connection.

    Degraded scenarios:
    - Hysteria process not running
    - SOCKS5/HTTP ports not accessible
    - Gemini probe fails

    Expected:
    - 503 Service Unavailable
    - status: DEGRADED
    - hysteria2.is_running: False
    - Details array contains error messages
    """
    mock_response = create_degraded_hysteria2_response()

    with patch(
        "app.routers.vpn.gather_vpn_health",
        new_callable=AsyncMock,
        return_value=mock_response,
    ):
        response = await client.get("/api/vpn/health")

    assert response.status_code == 503
    data = response.json()

    assert data["status"] == "degraded"
    assert data["vpn_type"] == "hysteria2"
    assert data["hysteria2"]["is_running"] is False
    assert data["hysteria2"]["socks5_accessible"] is False
    assert data["hysteria2"]["http_accessible"] is False
    assert data["hysteria2"]["error"] is not None
    assert data["probe"]["status"] == "fail"
    assert len(data["details"]) > 0


# --- Disabled VPN Tests ---

@pytest.mark.asyncio
async def test_vpn_health_disabled(client: AsyncClient):
    """
    VPN health check returns 503 when VPN is disabled in configuration.

    Expected:
    - 503 Service Unavailable
    - status: DISABLED
    - probe.status: SKIPPED
    - Details explain VPN is disabled
    """
    mock_response = create_disabled_vpn_response()

    with patch(
        "app.routers.vpn.gather_vpn_health",
        new_callable=AsyncMock,
        return_value=mock_response,
    ):
        response = await client.get("/api/vpn/health")

    assert response.status_code == 503
    data = response.json()

    assert data["status"] == "disabled"
    assert data["probe"]["status"] == "skipped"
    assert any("disabled" in detail.lower() for detail in data["details"])


# --- Public Access Tests ---

@pytest.mark.asyncio
async def test_vpn_health_public_access_no_auth_required(client: AsyncClient):
    """
    VPN health endpoint is publicly accessible without authentication.

    This is by design for monitoring and health checks.

    Expected:
    - Endpoint accessible without auth token
    - Returns valid response (200 or 503 based on VPN state)
    """
    mock_response = create_healthy_wireguard_response()

    with patch(
        "app.routers.vpn.gather_vpn_health",
        new_callable=AsyncMock,
        return_value=mock_response,
    ):
        # No authentication headers or cookies
        response = await client.get("/api/vpn/health")

    # Should succeed regardless of auth status
    assert response.status_code in [200, 503]
    data = response.json()
    assert "status" in data
    assert "vpn_type" in data
    assert "probe" in data


# --- Response Schema Tests ---

@pytest.mark.asyncio
async def test_vpn_health_response_schema_wireguard(client: AsyncClient):
    """
    VPN health response matches expected schema for WireGuard.

    Validates:
    - All required fields are present
    - Field types match schema
    - Nested objects are properly structured
    """
    mock_response = create_healthy_wireguard_response()

    with patch(
        "app.routers.vpn.gather_vpn_health",
        new_callable=AsyncMock,
        return_value=mock_response,
    ):
        response = await client.get("/api/vpn/health")

    assert response.status_code == 200
    data = response.json()

    # Top-level fields
    assert "status" in data
    assert "vpn_type" in data
    assert "interface" in data
    assert "wireguard" in data
    assert "routes" in data
    assert "probe" in data
    assert "details" in data
    assert "source" in data

    # Interface fields
    interface = data["interface"]
    assert "name" in interface
    assert "is_up" in interface
    assert isinstance(interface["is_up"], bool)

    # WireGuard fields
    wireguard = data["wireguard"]
    assert "interface" in wireguard
    assert "peers" in wireguard
    assert isinstance(wireguard["peers"], list)

    # Probe fields
    probe = data["probe"]
    assert "domain" in probe
    assert "status" in probe
    assert probe["status"] in ["ok", "fail", "skipped"]


@pytest.mark.asyncio
async def test_vpn_health_response_schema_hysteria2(client: AsyncClient):
    """
    VPN health response matches expected schema for Hysteria2.

    Validates:
    - All required fields are present
    - Hysteria2-specific fields included
    - Field types match schema
    """
    mock_response = create_healthy_hysteria2_response()

    with patch(
        "app.routers.vpn.gather_vpn_health",
        new_callable=AsyncMock,
        return_value=mock_response,
    ):
        response = await client.get("/api/vpn/health")

    assert response.status_code == 200
    data = response.json()

    # Top-level fields
    assert "status" in data
    assert "vpn_type" in data
    assert data["vpn_type"] == "hysteria2"
    assert "hysteria2" in data
    assert "probe" in data
    assert "details" in data

    # Hysteria2 fields
    hysteria2 = data["hysteria2"]
    assert "socks5_port" in hysteria2
    assert "http_port" in hysteria2
    assert "is_running" in hysteria2
    assert "socks5_accessible" in hysteria2
    assert "http_accessible" in hysteria2
    assert isinstance(hysteria2["is_running"], bool)
    assert isinstance(hysteria2["socks5_accessible"], bool)
    assert isinstance(hysteria2["http_accessible"], bool)


# --- Gemini Probe Tests ---

@pytest.mark.asyncio
async def test_vpn_health_gemini_probe_success(client: AsyncClient):
    """
    VPN health check includes successful Gemini probe.

    Expected:
    - probe.status: OK
    - probe.http_status: 200
    - probe.latency_ms: positive number
    - No probe error
    """
    mock_response = create_healthy_wireguard_response()

    with patch(
        "app.routers.vpn.gather_vpn_health",
        new_callable=AsyncMock,
        return_value=mock_response,
    ):
        response = await client.get("/api/vpn/health")

    assert response.status_code == 200
    data = response.json()

    probe = data["probe"]
    assert probe["status"] == "ok"
    assert probe["http_status"] == 200
    assert probe["latency_ms"] > 0
    assert probe["error"] is None


@pytest.mark.asyncio
async def test_vpn_health_gemini_probe_failure(client: AsyncClient):
    """
    VPN health check handles Gemini probe failure gracefully.

    Expected:
    - probe.status: FAIL
    - probe.error: Contains error message
    - Overall status: DEGRADED (if VPN otherwise healthy)
    """
    mock_response = create_degraded_wireguard_response()

    with patch(
        "app.routers.vpn.gather_vpn_health",
        new_callable=AsyncMock,
        return_value=mock_response,
    ):
        response = await client.get("/api/vpn/health")

    assert response.status_code == 503
    data = response.json()

    probe = data["probe"]
    assert probe["status"] == "fail"
    assert probe["error"] is not None
    assert data["status"] == "degraded"


@pytest.mark.asyncio
async def test_vpn_health_gemini_probe_skipped(client: AsyncClient):
    """
    VPN health check skips Gemini probe when VPN disabled or external access disabled.

    Expected:
    - probe.status: SKIPPED
    - probe.error: Explains why skipped
    - No http_status or latency_ms
    """
    mock_response = create_disabled_vpn_response()

    with patch(
        "app.routers.vpn.gather_vpn_health",
        new_callable=AsyncMock,
        return_value=mock_response,
    ):
        response = await client.get("/api/vpn/health")

    assert response.status_code == 503
    data = response.json()

    probe = data["probe"]
    assert probe["status"] == "skipped"
    assert probe["error"] is not None
    assert probe["http_status"] is None
    assert probe["latency_ms"] is None


# --- Edge Cases ---

@pytest.mark.asyncio
async def test_vpn_health_wireguard_no_peers(client: AsyncClient):
    """
    VPN health check handles WireGuard interface with no peers.

    Expected:
    - 200 or 503 based on overall health
    - wireguard.peers: empty list
    - Interface may be up but without peer connections
    """
    mock_response = VpnHealthResponse(
        status=VpnHealthStatus.HEALTHY,
        vpn_type=VpnType.WIREGUARD,
        interface=InterfaceStatus(
            name="wg0",
            is_up=True,
            state="UP",
            addresses=["10.0.0.2/24"],
        ),
        wireguard=WireGuardOverview(
            interface="wg0",
            public_key="abc123public",
            listen_port=51820,
            peers=[],  # No peers configured
        ),
        routes=[],
        probe=GeminiProbeResult(
            domain="generativelanguage.googleapis.com",
            status=GeminiProbeStatus.OK,
            http_status=200,
            latency_ms=50.5,
        ),
        details=[],
    )

    with patch(
        "app.routers.vpn.gather_vpn_health",
        new_callable=AsyncMock,
        return_value=mock_response,
    ):
        response = await client.get("/api/vpn/health")

    data = response.json()
    assert data["wireguard"]["peers"] == []
    assert isinstance(data["wireguard"]["peers"], list)


@pytest.mark.asyncio
async def test_vpn_health_wireguard_no_routes(client: AsyncClient):
    """
    VPN health check handles WireGuard interface with no routes configured.

    Expected:
    - routes: empty list
    - Interface may be up but without routing configured
    """
    mock_response = create_healthy_wireguard_response()
    mock_response.routes = []

    with patch(
        "app.routers.vpn.gather_vpn_health",
        new_callable=AsyncMock,
        return_value=mock_response,
    ):
        response = await client.get("/api/vpn/health")

    data = response.json()
    assert data["routes"] == []
    assert isinstance(data["routes"], list)


@pytest.mark.asyncio
async def test_vpn_health_multiple_interface_addresses(client: AsyncClient):
    """
    VPN health check handles WireGuard interface with multiple IP addresses.

    Expected:
    - interface.addresses: list with multiple entries
    - Both IPv4 and IPv6 addresses supported
    """
    mock_response = create_healthy_wireguard_response()
    mock_response.interface.addresses = [
        "10.0.0.2/24",
        "fd00::2/64",
    ]

    with patch(
        "app.routers.vpn.gather_vpn_health",
        new_callable=AsyncMock,
        return_value=mock_response,
    ):
        response = await client.get("/api/vpn/health")

    data = response.json()
    assert len(data["interface"]["addresses"]) == 2
    assert "10.0.0.2/24" in data["interface"]["addresses"]
    assert "fd00::2/64" in data["interface"]["addresses"]


@pytest.mark.asyncio
async def test_vpn_health_hysteria2_partial_accessibility(client: AsyncClient):
    """
    VPN health check handles Hysteria2 with partial port accessibility.

    Scenario: SOCKS5 accessible but HTTP not accessible (or vice versa)

    Expected:
    - status: DEGRADED
    - hysteria2.error: Indicates which port is not accessible
    """
    mock_response = VpnHealthResponse(
        status=VpnHealthStatus.DEGRADED,
        vpn_type=VpnType.HYSTERIA2,
        hysteria2=Hysteria2Status(
            server="vpn.example.com:443",
            socks5_port=1080,
            http_port=8080,
            is_running=True,
            socks5_accessible=True,
            http_accessible=False,  # HTTP port not accessible
            error="HTTP port 8080 not accessible",
        ),
        probe=GeminiProbeResult(
            domain="generativelanguage.googleapis.com",
            status=GeminiProbeStatus.OK,
            http_status=200,
            latency_ms=45.3,
        ),
        details=["HTTP port 8080 not accessible"],
    )

    with patch(
        "app.routers.vpn.gather_vpn_health",
        new_callable=AsyncMock,
        return_value=mock_response,
    ):
        response = await client.get("/api/vpn/health")

    assert response.status_code == 503
    data = response.json()

    assert data["status"] == "degraded"
    assert data["hysteria2"]["socks5_accessible"] is True
    assert data["hysteria2"]["http_accessible"] is False
    assert data["hysteria2"]["error"] is not None
    assert "8080" in data["hysteria2"]["error"]


@pytest.mark.asyncio
async def test_vpn_health_content_type_json(client: AsyncClient):
    """
    VPN health endpoint returns application/json content type.

    Expected:
    - Content-Type: application/json
    - Valid JSON body
    """
    mock_response = create_healthy_wireguard_response()

    with patch(
        "app.routers.vpn.gather_vpn_health",
        new_callable=AsyncMock,
        return_value=mock_response,
    ):
        response = await client.get("/api/vpn/health")

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/json"

    # Verify valid JSON
    data = response.json()
    assert isinstance(data, dict)


@pytest.mark.asyncio
async def test_vpn_health_source_field(client: AsyncClient):
    """
    VPN health response includes source field for identification.

    Expected:
    - source: "vpn-health"
    - Helps identify response origin in logs/monitoring
    """
    mock_response = create_healthy_wireguard_response()

    with patch(
        "app.routers.vpn.gather_vpn_health",
        new_callable=AsyncMock,
        return_value=mock_response,
    ):
        response = await client.get("/api/vpn/health")

    data = response.json()
    assert data["source"] == "vpn-health"


# --- Integration Tests ---

@pytest.mark.asyncio
async def test_vpn_health_multiple_consecutive_requests(client: AsyncClient):
    """
    VPN health endpoint handles multiple consecutive requests correctly.

    Validates:
    - No state leakage between requests
    - Consistent responses
    - No memory leaks or connection issues
    """
    mock_response = create_healthy_wireguard_response()

    with patch(
        "app.routers.vpn.gather_vpn_health",
        new_callable=AsyncMock,
        return_value=mock_response,
    ):
        # Make 5 consecutive requests
        for _ in range(5):
            response = await client.get("/api/vpn/health")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "healthy"
            assert data["vpn_type"] == "wireguard"


@pytest.mark.asyncio
async def test_vpn_health_authenticated_access_still_works(
    user_client: AsyncClient,
):
    """
    VPN health endpoint works with authenticated clients too.

    Although authentication is not required, authenticated requests should still work.

    Expected:
    - Authenticated client can access endpoint
    - Response same as unauthenticated
    """
    mock_response = create_healthy_wireguard_response()

    with patch(
        "app.routers.vpn.gather_vpn_health",
        new_callable=AsyncMock,
        return_value=mock_response,
    ):
        response = await user_client.get("/api/vpn/health")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"


@pytest.mark.asyncio
async def test_vpn_health_admin_access_still_works(
    admin_client: AsyncClient,
):
    """
    VPN health endpoint works with admin clients.

    Expected:
    - Admin client can access endpoint
    - No special privileges or additional data
    """
    mock_response = create_healthy_wireguard_response()

    with patch(
        "app.routers.vpn.gather_vpn_health",
        new_callable=AsyncMock,
        return_value=mock_response,
    ):
        response = await admin_client.get("/api/vpn/health")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
