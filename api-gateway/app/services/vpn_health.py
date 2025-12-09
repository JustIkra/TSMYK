"""
Service helpers for the VPN health endpoint (VPN-03).
Supports WireGuard, AWG (AmneziaWG), and Hysteria2.
"""

from __future__ import annotations

import asyncio
import math
import socket
import subprocess
import time
from collections.abc import Sequence

import httpx

from app.core.config import settings
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

COMMAND_TIMEOUT = 3.0
PROBE_TIMEOUT = 5.0


def _run_command(cmd: Sequence[str]) -> subprocess.CompletedProcess[str]:
    """Run command and return completed process."""
    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=COMMAND_TIMEOUT,
    )


def _parse_interface_state(output: str) -> tuple[bool, str | None]:
    """Extract interface UP/DOWN info from `ip link show` output."""
    lines = output.splitlines()
    if not lines:
        return False, None
    first = lines[0]
    state = None
    if "state" in first:
        state = first.split("state", 1)[1].strip().split()[0]
    flags = set()
    if "<" in first and ">" in first:
        flag_block = first.split("<", 1)[1].split(">", 1)[0]
        flags = {flag.strip() for flag in flag_block.split(",")}
    is_up = state == "UP" or "UP" in flags or "LOWER_UP" in flags
    return is_up, state


def collect_interface_status(interface: str) -> InterfaceStatus:
    """Inspect the WireGuard interface via `ip`."""
    try:
        result = _run_command(["ip", "link", "show", "dev", interface])
    except FileNotFoundError:
        return InterfaceStatus(
            name=interface,
            is_up=False,
            error="'ip' binary not found inside container.",
        )
    except subprocess.TimeoutExpired:
        return InterfaceStatus(
            name=interface,
            is_up=False,
            error="Timed out while waiting for 'ip link show'.",
        )

    if result.returncode != 0:
        return InterfaceStatus(
            name=interface,
            is_up=False,
            error=result.stderr.strip() or f"'ip link show' failed ({result.returncode}).",
        )

    is_up, state = _parse_interface_state(result.stdout or "")

    addresses: list[str] = []
    try:
        addr_result = _run_command(["ip", "-o", "addr", "show", "dev", interface])
    except (FileNotFoundError, subprocess.TimeoutExpired):
        addr_result = None

    if addr_result and addr_result.returncode == 0:
        for line in addr_result.stdout.splitlines():
            tokens = line.split()
            if len(tokens) >= 4 and tokens[2] in {"inet", "inet6"}:
                addresses.append(tokens[3])

    return InterfaceStatus(
        name=interface,
        is_up=is_up,
        state=state,
        addresses=addresses,
    )


def _parse_route_line(line: str) -> RouteEntry:
    tokens = line.split()
    destination = tokens[0] if tokens else line
    via = None
    dev = None
    metric: int | None = None

    idx = 1
    while idx < len(tokens):
        token = tokens[idx]
        if token == "via" and idx + 1 < len(tokens):
            via = tokens[idx + 1]
            idx += 2
        elif token == "dev" and idx + 1 < len(tokens):
            dev = tokens[idx + 1]
            idx += 2
        elif token == "metric" and idx + 1 < len(tokens):
            value = tokens[idx + 1]
            try:
                metric = int(value)
            except ValueError:
                metric = None
            idx += 2
        else:
            idx += 1

    return RouteEntry(
        destination=destination,
        via=via,
        dev=dev,
        metric=metric,
        raw=line,
    )


def collect_routes(interface: str) -> list[RouteEntry]:
    """Return route entries that use the WireGuard interface."""
    try:
        result = _run_command(["ip", "route", "show"])
    except FileNotFoundError:
        return []
    except subprocess.TimeoutExpired:
        return []

    if result.returncode != 0:
        return []

    routes: list[RouteEntry] = []
    for line in result.stdout.splitlines():
        if f" dev {interface}" not in line:
            continue
        routes.append(_parse_route_line(line.strip()))
    return routes


def _parse_size_to_bytes(token: str) -> int | None:
    """Convert WireGuard transfer size into bytes."""
    units = {
        "B": 1,
        "KiB": 1024,
        "MiB": 1024**2,
        "GiB": 1024**3,
        "TiB": 1024**4,
    }
    parts = token.split()
    if len(parts) < 2:
        return None
    try:
        value = float(parts[0])
    except ValueError:
        return None
    factor = units.get(parts[1])
    if factor is None:
        return None
    return int(math.floor(value * factor))


def _parse_transfer_fields(raw: str) -> tuple[int | None, int | None]:
    rx = tx = None
    pieces = raw.split(",")
    if pieces:
        first = pieces[0].replace("received", "").strip()
        rx = _parse_size_to_bytes(first)
    if len(pieces) > 1:
        second = pieces[1].replace("sent", "").strip()
        tx = _parse_size_to_bytes(second)
    return rx, tx


def _parse_wireguard_output(interface: str, output: str) -> WireGuardOverview:
    overview = WireGuardOverview(interface=interface)
    lines = output.splitlines()
    current_peer: dict[str, object] | None = None

    for raw_line in lines:
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("interface:"):
            continue
        if line.startswith("public key:"):
            overview.public_key = line.split(":", 1)[1].strip()
        elif line.startswith("listening port:"):
            value = line.split(":", 1)[1].strip()
            try:
                overview.listen_port = int(value)
            except ValueError:
                overview.listen_port = None
        elif line.startswith("peer:"):
            if current_peer:
                overview.peers.append(VpnPeer(**current_peer))  # type: ignore[arg-type]
            current_peer = {
                "public_key": line.split(":", 1)[1].strip(),
                "allowed_ips": [],
            }
        elif line.startswith("endpoint:") and current_peer is not None:
            current_peer["endpoint"] = line.split(":", 1)[1].strip() or None
        elif line.startswith("allowed ips:") and current_peer is not None:
            ips_raw = line.split(":", 1)[1].strip()
            current_peer["allowed_ips"] = [ip.strip() for ip in ips_raw.split(",") if ip.strip()]
        elif line.startswith("latest handshake:") and current_peer is not None:
            current_peer["latest_handshake"] = line.split(":", 1)[1].strip()
        elif line.startswith("transfer:") and current_peer is not None:
            rx, tx = _parse_transfer_fields(line.split(":", 1)[1].strip())
            current_peer["transfer_rx_bytes"] = rx
            current_peer["transfer_tx_bytes"] = tx
        elif line.startswith("persistent keepalive:") and current_peer is not None:
            current_peer["persistent_keepalive"] = line.split(":", 1)[1].strip()

    if current_peer:
        overview.peers.append(VpnPeer(**current_peer))  # type: ignore[arg-type]

    return overview


def collect_wireguard_overview(interface: str) -> WireGuardOverview:
    """Gather WireGuard/AWG peer information via `wg show`."""
    try:
        result = _run_command(["wg", "show", interface])
    except FileNotFoundError:
        return WireGuardOverview(
            interface=interface,
            error="'wg' binary not found inside container.",
        )
    except subprocess.TimeoutExpired:
        return WireGuardOverview(
            interface=interface,
            error="Timed out while waiting for 'wg show'.",
        )

    if result.returncode != 0:
        return WireGuardOverview(
            interface=interface,
            error=result.stderr.strip() or f"'wg show' failed ({result.returncode}).",
        )

    return _parse_wireguard_output(interface, result.stdout or "")


def _check_port_accessible(host: str, port: int, timeout: float = 1.0) -> bool:
    """Check if a TCP port is accessible by attempting to connect."""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((host, port))
        sock.close()
        return result == 0
    except (socket.error, OSError):
        return False


def _check_hysteria_process_running() -> bool:
    """Check if hysteria process is running via ps/pgrep."""
    try:
        # Try pgrep first (more reliable)
        result = _run_command(["pgrep", "-f", "hysteria"])
        if result.returncode == 0 and result.stdout.strip():
            return True
    except FileNotFoundError:
        pass

    # Fallback to ps aux | grep
    try:
        result = _run_command(["ps", "aux"])
        if result.returncode == 0:
            for line in result.stdout.splitlines():
                if "hysteria" in line.lower() and "grep" not in line.lower():
                    return True
    except FileNotFoundError:
        pass

    return False


def collect_hysteria2_status(
    socks5_port: int,
    http_port: int,
    server: str | None = None,
) -> Hysteria2Status:
    """
    Collect Hysteria2 proxy status.

    Checks:
    1. Process running (via pgrep/ps)
    2. SOCKS5 port accessible (localhost socket connect)
    3. HTTP port accessible (localhost socket connect)

    Args:
        socks5_port: Local SOCKS5 proxy port
        http_port: Local HTTP proxy port
        server: Optional server address for display

    Returns:
        Hysteria2Status with diagnostics
    """
    is_running = _check_hysteria_process_running()
    socks5_accessible = False
    http_accessible = False
    error = None

    if not is_running:
        error = "Hysteria process not running"
    else:
        # Only check ports if process is running
        socks5_accessible = _check_port_accessible("127.0.0.1", socks5_port)
        http_accessible = _check_port_accessible("127.0.0.1", http_port)

        if not socks5_accessible and not http_accessible:
            error = f"Neither SOCKS5 port {socks5_port} nor HTTP port {http_port} are accessible"
        elif not socks5_accessible:
            error = f"SOCKS5 port {socks5_port} not accessible"
        elif not http_accessible:
            error = f"HTTP port {http_port} not accessible"

    return Hysteria2Status(
        server=server,
        socks5_port=socks5_port,
        http_port=http_port,
        is_running=is_running,
        socks5_accessible=socks5_accessible,
        http_accessible=http_accessible,
        error=error,
    )


async def perform_gemini_probe(domain: str, timeout: float = PROBE_TIMEOUT) -> GeminiProbeResult:
    """Issue HTTPS probe against Gemini endpoint."""
    url = f"https://{domain}/"
    start = time.perf_counter()
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.get(url, headers={"User-Agent": "tsmuk-vpn-health/1.0"})
    except httpx.RequestError as exc:
        return GeminiProbeResult(
            domain=domain,
            status=GeminiProbeStatus.FAIL,
            error=str(exc),
        )

    latency_ms = (time.perf_counter() - start) * 1000
    status = GeminiProbeStatus.OK if response.status_code < 500 else GeminiProbeStatus.FAIL

    return GeminiProbeResult(
        domain=domain,
        status=status,
        http_status=response.status_code,
        latency_ms=latency_ms,
        error=None if status is GeminiProbeStatus.OK else f"HTTP {response.status_code}",
    )


async def gather_vpn_health(
    *,
    interface: str | None = None,
    probe_domain: str | None = None,
) -> VpnHealthResponse:
    """
    Aggregate diagnostics for the `/api/vpn/health` endpoint.

    Supports WireGuard, AWG, and Hysteria2 VPN types.
    """
    domain = probe_domain or (
        settings.vpn_domains_list[0]
        if settings.vpn_domains_list
        else "generativelanguage.googleapis.com"
    )

    # Handle disabled VPN
    if not settings.vpn_enabled:
        probe_result = GeminiProbeResult(
            domain=domain, status=GeminiProbeStatus.SKIPPED, error="VPN disabled."
        )

        # Return minimal response with appropriate defaults based on VPN type
        if settings.vpn_type == "hysteria2":
            hysteria2 = Hysteria2Status(
                socks5_port=settings.hysteria2_socks5_port,
                http_port=settings.hysteria2_http_port,
                is_running=False,
                socks5_accessible=False,
                http_accessible=False,
                error="VPN disabled in configuration.",
            )
            return VpnHealthResponse(
                status=VpnHealthStatus.DISABLED,
                vpn_type=VpnType.HYSTERIA2,
                hysteria2=hysteria2,
                probe=probe_result,
                details=["VPN disabled in configuration."],
            )
        else:
            # WireGuard/AWG fallback
            iface = interface or settings.wg_interface
            interface_status = InterfaceStatus(
                name=iface, is_up=False, error="VPN disabled in configuration."
            )
            wireguard = WireGuardOverview(interface=iface, error="VPN disabled in configuration.")
            return VpnHealthResponse(
                status=VpnHealthStatus.DISABLED,
                vpn_type=VpnType.WIREGUARD,
                interface=interface_status,
                wireguard=wireguard,
                routes=[],
                probe=probe_result,
                details=["VPN disabled in configuration."],
            )

    # Determine VPN type and collect diagnostics
    vpn_type = VpnType(settings.vpn_type)

    if vpn_type == VpnType.HYSTERIA2:
        # Hysteria2: Check process and proxy ports
        server = None
        if settings.hysteria2_uri:
            # Extract server from URI (hysteria2://password@server:port/...)
            try:
                uri_parts = settings.hysteria2_uri.split("@")
                if len(uri_parts) > 1:
                    server = uri_parts[1].split("/")[0]
            except Exception:
                pass

        hysteria2_task = asyncio.to_thread(
            collect_hysteria2_status,
            settings.hysteria2_socks5_port,
            settings.hysteria2_http_port,
            server,
        )
        hysteria2 = await hysteria2_task

        # Perform Gemini probe
        if not settings.allow_external_network:
            probe_result = GeminiProbeResult(
                domain=domain,
                status=GeminiProbeStatus.SKIPPED,
                error="External network access disabled.",
            )
        else:
            probe_result = await perform_gemini_probe(domain)

        # Determine health status
        details: list[str] = []
        status = VpnHealthStatus.HEALTHY

        if hysteria2.error:
            details.append(hysteria2.error)
            if not hysteria2.is_running:
                status = VpnHealthStatus.DEGRADED
            elif not hysteria2.socks5_accessible and not hysteria2.http_accessible:
                status = VpnHealthStatus.DEGRADED

        if probe_result.status is GeminiProbeStatus.FAIL:
            status = VpnHealthStatus.DEGRADED
            details.append(probe_result.error or "Gemini probe failed.")
        elif probe_result.status is GeminiProbeStatus.SKIPPED:
            details.append(probe_result.error or "Gemini probe skipped.")

        return VpnHealthResponse(
            status=status,
            vpn_type=VpnType.HYSTERIA2,
            hysteria2=hysteria2,
            probe=probe_result,
            details=details,
        )

    else:
        # WireGuard/AWG: Check interface and peers
        iface = interface or settings.wg_interface

        interface_task = asyncio.to_thread(collect_interface_status, iface)
        wireguard_task = asyncio.to_thread(collect_wireguard_overview, iface)
        routes_task = asyncio.to_thread(collect_routes, iface)

        interface_status, wireguard, routes = await asyncio.gather(
            interface_task, wireguard_task, routes_task
        )

        # Perform Gemini probe
        if not settings.allow_external_network:
            probe_result = GeminiProbeResult(
                domain=domain,
                status=GeminiProbeStatus.SKIPPED,
                error="External network access disabled.",
            )
        else:
            probe_result = await perform_gemini_probe(domain)

        # Determine health status
        details: list[str] = []
        status = VpnHealthStatus.HEALTHY

        if interface_status.error:
            details.append(interface_status.error)
            status = VpnHealthStatus.DEGRADED
        elif not interface_status.is_up:
            details.append("WireGuard interface is down.")
            status = VpnHealthStatus.DEGRADED

        if wireguard.error:
            details.append(wireguard.error)
            status = VpnHealthStatus.DEGRADED

        if probe_result.status is GeminiProbeStatus.FAIL:
            status = VpnHealthStatus.DEGRADED
            details.append(probe_result.error or "Gemini probe failed.")
        elif probe_result.status is GeminiProbeStatus.SKIPPED:
            details.append(probe_result.error or "Gemini probe skipped.")

        return VpnHealthResponse(
            status=status,
            vpn_type=vpn_type,
            interface=interface_status,
            wireguard=wireguard,
            routes=routes,
            probe=probe_result,
            details=details,
        )
