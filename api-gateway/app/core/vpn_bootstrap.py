from __future__ import annotations

import os
import shutil
import socket
import subprocess
import time
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path


class VpnBootstrapError(RuntimeError):
    """Raised when VPN bootstrap fails."""


# Legacy alias for backward compatibility
WireGuardBootstrapError = VpnBootstrapError


@dataclass
class DefaultRoute:
    gateway: str
    dev: str
    metric: str | None = None


def _log(message: str) -> None:
    print(f"[vpn] {message}", flush=True)


def _is_truthy(value: str | None) -> bool:
    if value is None:
        return False
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _require_binary(name: str) -> None:
    if shutil.which(name) is None:
        raise WireGuardBootstrapError(
            f"'{name}' binary not found. Install wireguard-tools inside the container."
        )


def _check_sysctl_param(param: str, expected_value: str = "1") -> bool:
    """
    Check if sysctl parameter is set to expected value.
    
    Returns True if parameter exists and equals expected_value, False otherwise.
    """
    try:
        result = subprocess.run(
            ["sysctl", "-n", param],
            capture_output=True,
            text=True,
            timeout=2.0,
        )
        if result.returncode == 0:
            current_value = result.stdout.strip()
            return current_value == expected_value
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        pass
    return False


def _run_or_raise(cmd: Sequence[str]) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        stderr = result.stderr.strip()
        stdout = result.stdout.strip()
        details = stderr or stdout or f"exit code {result.returncode}"
        raise WireGuardBootstrapError(f"Command '{' '.join(cmd)}' failed: {details}")
    return result


def _run_with_sysctl_fallback(
    cmd: Sequence[str],
    sysctl_param: str = "net.ipv4.conf.all.src_valid_mark",
    expected_value: str = "1",
) -> subprocess.CompletedProcess[str]:
    """
    Run command with fallback handling for sysctl permission errors.
    
    If command fails with sysctl permission denied error, check if the sysctl
    parameter is already set to the expected value. If so, log a warning and
    continue. Otherwise, raise an error.
    
    This is useful when Docker sets sysctl parameters via docker-compose.yml,
    but wg-quick still tries to set them and gets permission denied.
    """
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode == 0:
        return result
    
    # Check if error is related to sysctl permission denied
    stderr = result.stderr.strip().lower()
    stdout = result.stdout.strip().lower()
    error_text = (stderr + " " + stdout).lower()
    
    # Check for sysctl permission errors - look for common patterns
    has_sysctl_keyword = "sysctl" in error_text
    has_permission_error = (
        "permission denied" in error_text
        or "operation not permitted" in error_text
        or "eacces" in error_text  # EACCES error code
    )
    # Check if sysctl parameter is mentioned (with dots or spaces)
    param_mentioned = (
        sysctl_param.lower() in error_text
        or sysctl_param.replace(".", " ").lower() in error_text
        or "src_valid_mark" in error_text
    )
    
    is_sysctl_error = has_sysctl_keyword and has_permission_error and param_mentioned
    
    if is_sysctl_error:
        _log(
            f"Command '{' '.join(cmd)}' failed with sysctl permission error. "
            f"Checking if parameter '{sysctl_param}' is already set..."
        )
        
        if _check_sysctl_param(sysctl_param, expected_value):
            _log(
                f"Parameter '{sysctl_param}' is already set to '{expected_value}' "
                f"(likely set by Docker). Continuing despite sysctl error."
            )
            # Return success since the parameter is already correctly set
            return subprocess.CompletedProcess(cmd, 0, result.stdout, result.stderr)
        else:
            current_value = "unknown"
            try:
                check_result = subprocess.run(
                    ["sysctl", "-n", sysctl_param],
                    capture_output=True,
                    text=True,
                    timeout=2.0,
                )
                if check_result.returncode == 0:
                    current_value = check_result.stdout.strip()
            except Exception:
                pass
            
            raise WireGuardBootstrapError(
                f"Command '{' '.join(cmd)}' failed with sysctl permission error. "
                f"Parameter '{sysctl_param}' is set to '{current_value}' "
                f"(expected '{expected_value}'). Cannot proceed."
            )
    
    # Not a sysctl error, raise normally
    details = result.stderr.strip() or result.stdout.strip() or f"exit code {result.returncode}"
    raise WireGuardBootstrapError(f"Command '{' '.join(cmd)}' failed: {details}")


def _run_ignore(cmd: Sequence[str]) -> None:
    subprocess.run(cmd, capture_output=True, text=True)


def _setup_wireguard_manually(config_path: Path, interface: str) -> None:
    """
    Set up WireGuard interface manually by parsing config and running commands.
    This is a fallback when wg-quick fails due to sysctl issues.
    """
    import configparser
    
    config = configparser.ConfigParser()
    config.read(config_path)
    
    if "Interface" not in config:
        raise WireGuardBootstrapError("Config file missing [Interface] section")
    
    interface_section = config["Interface"]
    peer_section = config["Peer"] if "Peer" in config else {}
    
    # Create interface
    _run_ignore(["ip", "link", "add", interface, "type", "wireguard"])
    
    # Configure WireGuard using wg set commands
    if "PrivateKey" in interface_section:
        import subprocess as sp
        proc = sp.Popen(
            ["wg", "set", interface, "private-key", "/dev/stdin"],
            stdin=sp.PIPE,
            text=True,
        )
        proc.communicate(input=interface_section["PrivateKey"])
        if proc.returncode != 0:
            raise WireGuardBootstrapError(f"Failed to set private key: returncode {proc.returncode}")
    
    if "Address" in interface_section:
        address = interface_section["Address"]
        _run_ignore(["ip", "address", "add", address, "dev", interface])
    
    if peer_section:
        if "PublicKey" not in peer_section:
            raise WireGuardBootstrapError("Peer PublicKey is required")
        
        public_key = peer_section["PublicKey"]
        peer_cmd = ["wg", "set", interface, "peer", public_key]
        
        if "PresharedKey" in peer_section:
            import subprocess as sp
            proc = sp.Popen(
                ["wg", "set", interface, "peer", public_key, "preshared-key", "/dev/stdin"],
                stdin=sp.PIPE,
                text=True,
            )
            proc.communicate(input=peer_section["PresharedKey"])
            if proc.returncode != 0:
                raise WireGuardBootstrapError(f"Failed to set preshared key: returncode {proc.returncode}")
        
        if "Endpoint" in peer_section:
            _run_ignore(["wg", "set", interface, "peer", public_key, "endpoint", peer_section["Endpoint"]])
        
        if "AllowedIPs" in peer_section:
            allowed_ips = peer_section["AllowedIPs"]
            _run_ignore(["wg", "set", interface, "peer", public_key, "allowed-ips", allowed_ips])
        
        if "PersistentKeepalive" in peer_section:
            _run_ignore(["wg", "set", interface, "peer", public_key, "persistent-keepalive", peer_section["PersistentKeepalive"]])
    
    # Set MTU and bring interface up
    _run_ignore(["ip", "link", "set", "mtu", "1420", "up", "dev", interface])
    
    # Add routes if AllowedIPs is specified
    if peer_section and "AllowedIPs" in peer_section:
        allowed_ips = peer_section["AllowedIPs"].split(",")
        for ip in allowed_ips:
            ip = ip.strip()
            if ip == "0.0.0.0/0":
                _run_ignore(["ip", "route", "add", "0.0.0.0/0", "dev", interface])
            elif ip:
                _run_ignore(["ip", "route", "add", ip, "dev", interface])


def _interface_up(interface: str) -> bool:
    result = subprocess.run(
        ["ip", "link", "show", "dev", interface],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return False

    output = result.stdout or ""
    if "state UP" in output:
        return True

    if "<" in output and ">" in output:
        flags = output.split("<", 1)[1].split(">", 1)[0]
        flag_set = {flag.strip() for flag in flags.split(",")}
        return "UP" in flag_set or "LOWER_UP" in flag_set

    return False


def _wait_for_interface(interface: str, timeout: float, poll_interval: float) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if _interface_up(interface):
            return
        time.sleep(poll_interval)
    raise WireGuardBootstrapError(
        f"VPN interface '{interface}' did not become available within {timeout:.1f}s"
    )


def _wait_for_port(host: str, port: int, timeout: float, poll_interval: float) -> None:
    """
    Wait for a port to become available (listening).

    Used for checking when proxy services (SOCKS5/HTTP) are ready.
    """
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1.0)
            sock.connect((host, port))
            sock.close()
            return
        except (socket.error, socket.timeout, OSError):
            time.sleep(poll_interval)
    raise VpnBootstrapError(
        f"Port {host}:{port} did not become available within {timeout:.1f}s"
    )


def _parse_hysteria2_uri(uri: str) -> dict[str, str]:
    """
    Parse Hysteria2 URI format: hysteria2://password@server:port/?sni=hostname

    Returns:
        dict with keys: password, server, port, sni

    Raises:
        VpnBootstrapError: If URI format is invalid
    """
    from urllib.parse import urlparse, parse_qs

    if not uri.startswith("hysteria2://"):
        raise VpnBootstrapError(
            f"Invalid Hysteria2 URI: must start with 'hysteria2://', got: {uri[:20]}..."
        )

    try:
        parsed = urlparse(uri)

        # Extract password (username field in URI)
        password = parsed.username
        if not password:
            raise VpnBootstrapError("Hysteria2 URI missing password (format: hysteria2://password@server:port)")

        # Extract server (hostname)
        server = parsed.hostname
        if not server:
            raise VpnBootstrapError("Hysteria2 URI missing server hostname")

        # Extract port
        port = parsed.port
        if not port:
            raise VpnBootstrapError("Hysteria2 URI missing port")

        # Extract SNI from query params
        query_params = parse_qs(parsed.query)
        sni = query_params.get("sni", [server])[0]  # Default to server if SNI not specified

        return {
            "password": password,
            "server": server,
            "port": str(port),
            "sni": sni,
        }
    except Exception as exc:
        if isinstance(exc, VpnBootstrapError):
            raise
        raise VpnBootstrapError(f"Failed to parse Hysteria2 URI: {exc}") from exc


def _parse_csv(raw: str | None) -> list[str]:
    if not raw:
        return []
    return [item.strip() for item in raw.split(",") if item.strip()]


def _get_default_route() -> DefaultRoute | None:
    result = subprocess.run(
        ["ip", "route", "show", "default"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return None
    line = (result.stdout or "").strip().splitlines()
    if not line:
        return None
    tokens = line[0].split()
    gateway = None
    dev = None
    metric = None
    for idx, token in enumerate(tokens):
        if token == "via" and idx + 1 < len(tokens):
            gateway = tokens[idx + 1]
        elif token == "dev" and idx + 1 < len(tokens):
            dev = tokens[idx + 1]
        elif token == "metric" and idx + 1 < len(tokens):
            metric = tokens[idx + 1]
    if gateway and dev:
        return DefaultRoute(gateway=gateway, dev=dev, metric=metric)
    return None


def _restore_default_route(route: DefaultRoute) -> None:
    cmd = ["ip", "route", "replace", "default", "via", route.gateway, "dev", route.dev]
    if route.metric:
        cmd.extend(["metric", route.metric])
    _run_or_raise(cmd)


def _remove_default_route_via_interface(interface: str) -> None:
    _run_ignore(["ip", "route", "del", "default", "dev", interface])


def _ensure_route_via_gateway(target: str, route: DefaultRoute) -> None:
    cmd = ["ip", "route", "replace", target, "via", route.gateway, "dev", route.dev]
    _run_or_raise(cmd)


def _ensure_route_via_interface(target: str, interface: str) -> None:
    cmd = ["ip", "route", "replace", target, "dev", interface]
    _run_or_raise(cmd)


def _resolve_domains(domains: Iterable[str]) -> list[str]:
    """
    Resolve domains to IPv4 addresses with multiple attempts to catch all possible IPs.
    
    Google services use Anycast and may return different IPs on each DNS query.
    We make multiple resolution attempts to collect all possible addresses.
    
    For Google API domains, returns known CIDR blocks for more reliable routing.
    """
    domain_list = list(domains)
    has_google_domain = any(
        "generativelanguage.googleapis.com" in d or "googleapis.com" in d
        for d in domain_list
    )
    
    # Known Google Cloud Platform CIDR blocks for Google APIs
    # These are common IP ranges used by Google APIs (AS15169)
    if has_google_domain:
        _log(
            "Google API domain detected - using CIDR blocks for reliable routing "
            "(covers all possible Google API IPs)"
        )
        return [
            "142.250.0.0/15",  # Google AS15169 (142.250.0.0 - 142.251.255.255)
            "172.217.0.0/16",  # Google AS15169 (172.217.0.0 - 172.217.255.255)
            "216.58.192.0/19",  # Google AS15169 (216.58.192.0 - 216.58.223.255)
        ]
    
    # For non-Google domains, resolve individual IPs with multiple attempts
    addresses: list[str] = []
    seen: set[str] = set()
    
    for domain in domain_list:
        # Make multiple DNS queries to catch all possible IPs (Anycast)
        resolved_ips: set[str] = set()
        for attempt in range(3):  # 3 attempts to get different IPs
            try:
                infos = socket.getaddrinfo(domain, None, proto=socket.IPPROTO_TCP)
                for info in infos:
                    ip = info[4][0]
                    if ":" in ip:
                        continue  # skip IPv6 for now
                    resolved_ips.add(ip)
            except socket.gaierror as exc:  # pragma: no cover - depends on DNS
                if attempt == 2:  # Last attempt failed
                    raise WireGuardBootstrapError(
                        f"Failed to resolve domain '{domain}': {exc}"
                    ) from exc
                # Continue to next attempt
                continue
        
        # Add all resolved IPs
        for ip in resolved_ips:
            if ip not in seen:
                addresses.append(ip)
                seen.add(ip)
    
    if not addresses:
        raise WireGuardBootstrapError(
            f"DNS lookup for {', '.join(domain_list)} returned no IPv4 addresses."
        )
    return addresses


def configure_split_tunnel(
    interface: str,
    env: Mapping[str, str],
    default_route: DefaultRoute | None,
) -> None:
    route_mode = env.get("VPN_ROUTE_MODE", "domains").strip().lower()
    if route_mode not in {"all", "domains", "cidr"}:
        raise WireGuardBootstrapError("VPN_ROUTE_MODE must be one of: all, domains, cidr.")

    bypass_cidrs = _parse_csv(env.get("VPN_BYPASS_CIDRS"))

    if route_mode == "all":
        _log("Routing mode 'all' – entire outbound traffic locked to VPN.")
        if bypass_cidrs:
            if default_route is None:
                raise WireGuardBootstrapError(
                    "Cannot add bypass CIDRs without baseline default route."
                )
            for cidr in bypass_cidrs:
                _log(f"Adding bypass CIDR via original gateway: {cidr}")
                _ensure_route_via_gateway(cidr, default_route)
        return

    if default_route is None:
        raise WireGuardBootstrapError(
            "Split-tunnel mode requires detecting the original default route."
        )

    if route_mode == "domains":
        domains = _parse_csv(env.get("VPN_ROUTE_DOMAINS"))
        if not domains:
            raise WireGuardBootstrapError(
                "VPN_ROUTE_DOMAINS must be provided when VPN_ROUTE_MODE=domains."
            )
        resolved = _resolve_domains(domains)
        # Check if resolved items are already CIDRs (contain '/') or individual IPs
        targets = []
        for item in resolved:
            if "/" in item:
                # Already a CIDR block
                targets.append(item)
            else:
                # Individual IP, add /32
                targets.append(f"{item}/32")
    else:
        cidrs = _parse_csv(env.get("VPN_ROUTE_CIDRS"))
        if not cidrs:
            raise WireGuardBootstrapError(
                "VPN_ROUTE_CIDRS must be provided when VPN_ROUTE_MODE=cidr."
            )
        targets = cidrs

    _remove_default_route_via_interface(interface)
    _restore_default_route(default_route)
    _log(
        "Default route restored to original gateway; only selected destinations "
        f"will use VPN ({interface})."
    )

    for target in targets:
        _log(f"Routing {target} via {interface}")
        _ensure_route_via_interface(target, interface)

    for cidr in bypass_cidrs:
        _log(f"Ensuring bypass CIDR stays on original gateway: {cidr}")
        _ensure_route_via_gateway(cidr, default_route)


def _validate_awg_config(config_path: Path) -> None:
    """
    Validate AWG config file for required obfuscation parameters.
    
    AWG requires: Jc, Jmin, Jmax, S1, S2, H1, H2, H3, H4 in [Interface] section.
    """
    required_params = {"Jc", "Jmin", "Jmax", "S1", "S2", "H1", "H2", "H3", "H4"}
    found_params: set[str] = set()
    in_interface = False
    
    try:
        with config_path.open() as f:
            for line in f:
                line = line.strip()
                if line.startswith("[Interface]"):
                    in_interface = True
                elif line.startswith("[") and not line.startswith("[Interface"):
                    in_interface = False
                elif in_interface and "=" in line:
                    key = line.split("=")[0].strip()
                    if key in required_params:
                        found_params.add(key)
    except Exception as exc:
        raise WireGuardBootstrapError(f"Failed to read AWG config: {exc}") from exc
    
    missing = required_params - found_params
    if missing:
        raise WireGuardBootstrapError(
            f"AWG config missing required obfuscation parameters: {', '.join(sorted(missing))}"
        )


def ensure_awg_up(
    config_path: str,
    interface: str,
    *,
    timeout: float = 15.0,
    poll_interval: float = 0.5,
) -> None:
    """
    Bring AWG (AmneziaWG) interface up using the provided config file.
    
    AWG uses the same protocol as WireGuard but with obfuscation parameters.
    For full obfuscation support, a specialized AWG client is required.
    """
    # Try to use amneziawg client if available, fallback to wg-quick
    awg_client = shutil.which("amneziawg")
    if awg_client:
        _require_binary("amneziawg")
        _require_binary("ip")
        _log("Using amneziawg client for AWG obfuscation support.")
    else:
        _require_binary("wg-quick")
        _require_binary("ip")
        _log("Warning: amneziawg client not found, using wg-quick (obfuscation may not work).")

    cfg = Path(config_path)
    if not cfg.exists():
        raise WireGuardBootstrapError(f"AWG config not found: {cfg}")

    # Validate AWG-specific parameters
    _validate_awg_config(cfg)

    _log(f"Ensuring AWG interface '{interface}' is up (config={cfg})")

    if _interface_up(interface):
        _log(f"AWG interface '{interface}' already up – skipping.")
        return

    if awg_client:
        # Use amneziawg client if available
        _run_with_sysctl_fallback([awg_client, "up", str(cfg)])
    else:
        # Fallback to wg-quick (obfuscation parameters will be ignored)
        # Create a temporary config without AWG-specific parameters for wg-quick
        import tempfile
        awg_params = {"Jc", "Jmin", "Jmax", "S1", "S2", "H1", "H2", "H3", "H4"}
        temp_cfg = Path(tempfile.mkdtemp()) / "wg0.conf"
        with cfg.open() as src, temp_cfg.open("w") as dst:
            in_interface = False
            for line in src:
                if line.strip().startswith("[Interface]"):
                    in_interface = True
                    dst.write(line)
                elif line.strip().startswith("[Peer]"):
                    in_interface = False
                    dst.write(line)
                elif in_interface:
                    # Skip AWG-specific parameters
                    key = line.split("=")[0].strip() if "=" in line else ""
                    if key not in awg_params:
                        dst.write(line)
                else:
                    dst.write(line)
        try:
            # Try to run wg-quick, but check if interface actually came up
            _log(f"Running wg-quick up on temporary config: {temp_cfg}")
            result = _run_with_sysctl_fallback(["wg-quick", "up", str(temp_cfg)])
            _log(f"wg-quick command completed (returncode handled by fallback)")
            # Even if command "succeeded" (sysctl error was ignored), check if interface is up
            interface_status = _interface_up(interface)
            _log(f"Interface {interface} status after wg-quick: {'UP' if interface_status else 'DOWN/NOT EXISTS'}")
            if not interface_status:
                # Interface didn't come up, try manual setup
                _log("wg-quick completed but interface is not up. Attempting manual setup...")
                # Check if interface exists at all
                check_result = subprocess.run(
                    ["ip", "link", "show", "dev", interface],
                    capture_output=True,
                    text=True,
                )
                if check_result.returncode == 0:
                    _log(f"Interface {interface} exists, bringing it up manually...")
                    _run_ignore(["ip", "link", "set", "up", "dev", interface])
                    # Check again
                    if not _interface_up(interface):
                        _log("Failed to bring interface up manually. Trying full manual setup...")
                        _setup_wireguard_manually(temp_cfg, interface)
                else:
                    # Interface doesn't exist, wg-quick must have failed completely
                    # Try to parse config and set up manually
                    _log("Interface doesn't exist. Attempting manual WireGuard setup...")
                    _setup_wireguard_manually(temp_cfg, interface)
        finally:
            # Clean up temp file
            if temp_cfg.exists():
                temp_cfg.unlink()
                temp_cfg.parent.rmdir()

    _wait_for_interface(interface, timeout, poll_interval)
    _log(f"AWG interface '{interface}' is up.")


def ensure_wireguard_up(
    config_path: str,
    interface: str,
    *,
    timeout: float = 15.0,
    poll_interval: float = 0.5,
) -> None:
    """
    Bring WireGuard interface up using the provided config file.
    """
    _require_binary("wg-quick")
    _require_binary("ip")

    cfg = Path(config_path)
    if not cfg.exists():
        raise WireGuardBootstrapError(f"WireGuard config not found: {cfg}")

    _log(f"Ensuring WireGuard interface '{interface}' is up (config={cfg})")

    if _interface_up(interface):
        _log(f"WireGuard interface '{interface}' already up – skipping wg-quick.")
        return

    _run_with_sysctl_fallback(["wg-quick", "up", str(cfg)])
    _wait_for_interface(interface, timeout, poll_interval)
    _log(f"WireGuard interface '{interface}' is up.")


def ensure_openvpn_up(
    config_path: str,
    interface: str = "tun0",
    *,
    timeout: float = 15.0,
    poll_interval: float = 0.5,
) -> None:
    """
    Bring OpenVPN interface up using the provided config file.
    
    OpenVPN uses TUN interface (usually tun0) and requires --route-nopull
    for split-tunnel mode (routes are configured manually via configure_split_tunnel).
    """
    _require_binary("openvpn")
    _require_binary("ip")

    cfg = Path(config_path)
    if not cfg.exists():
        raise WireGuardBootstrapError(f"OpenVPN config not found: {cfg}")

    _log(f"Ensuring OpenVPN interface '{interface}' is up (config={cfg})")

    if _interface_up(interface):
        _log(f"OpenVPN interface '{interface}' already up – skipping.")
        return

    # Create PID directory if it doesn't exist
    pid_dir = Path("/var/run/openvpn")
    if not pid_dir.exists():
        try:
            pid_dir.mkdir(parents=True, exist_ok=True)
        except OSError:
            # If we can't create the directory, skip PID file
            pass

    # Launch OpenVPN in daemon mode with --route-nopull for split-tunnel
    # This prevents OpenVPN from automatically changing the default route
    # We'll configure routes manually via configure_split_tunnel
    openvpn_cmd = [
        "openvpn",
        "--config", str(cfg),
        "--daemon", "openvpn",
        "--route-nopull",  # Don't apply routes from server (we'll set them manually)
        "--dev", interface,
    ]
    
    # Add PID file if directory exists
    if pid_dir.exists():
        openvpn_cmd.extend(["--writepid", str(pid_dir / f"{interface}.pid")])
    
    # Try to start OpenVPN - if it's already running, the interface should come up
    try:
        _run_or_raise(openvpn_cmd)
    except WireGuardBootstrapError as exc:
        # If OpenVPN is already running, it may return an error, but interface might still come up
        _log(f"OpenVPN start command returned error (may already be running): {exc}")
        # Wait a bit and check if interface came up anyway
        time.sleep(1.0)
        if _interface_up(interface):
            _log(f"OpenVPN interface '{interface}' is up despite start error.")
            return
        # If interface didn't come up, re-raise the error
        raise

    _wait_for_interface(interface, timeout, poll_interval)
    _log(f"OpenVPN interface '{interface}' is up.")


def ensure_hysteria2_up(
    uri: str,
    socks5_port: int,
    http_port: int,
    config_path: str,
    *,
    timeout: float = 15.0,
    poll_interval: float = 0.5,
) -> None:
    """
    Bring Hysteria2 client up using the provided URI.

    Hysteria2 uses a YAML config file and runs as a proxy (SOCKS5/HTTP),
    not as a kernel network interface like WireGuard/OpenVPN.

    Args:
        uri: Hysteria2 connection URI (hysteria2://password@server:port/?sni=hostname)
        socks5_port: Local SOCKS5 proxy port (default 1080)
        http_port: Local HTTP proxy port (default 8080)
        config_path: Path to generate YAML config file
        timeout: Maximum time to wait for proxy to become available
        poll_interval: Time between port availability checks
    """
    _require_binary("hysteria")

    _log(f"Starting Hysteria2 client (SOCKS5={socks5_port}, HTTP={http_port})")

    # Parse URI to extract connection parameters
    try:
        params = _parse_hysteria2_uri(uri)
    except VpnBootstrapError as exc:
        raise VpnBootstrapError(f"Invalid Hysteria2 URI: {exc}") from exc

    server_addr = f"{params['server']}:{params['port']}"
    _log(f"Connecting to Hysteria2 server: {server_addr} (SNI={params['sni']})")

    # Generate YAML config file
    config_content = f"""server: {server_addr}
auth: {params['password']}
tls:
  sni: {params['sni']}
  insecure: false
socks5:
  listen: 127.0.0.1:{socks5_port}
http:
  listen: 127.0.0.1:{http_port}
"""

    config_file = Path(config_path)
    try:
        config_file.parent.mkdir(parents=True, exist_ok=True)
        config_file.write_text(config_content)
        _log(f"Generated Hysteria2 config: {config_path}")
    except Exception as exc:
        raise VpnBootstrapError(f"Failed to write Hysteria2 config: {exc}") from exc

    # Check if Hysteria2 is already running by testing SOCKS5 port
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1.0)
        sock.connect(("127.0.0.1", socks5_port))
        sock.close()
        _log(f"Hysteria2 SOCKS5 port {socks5_port} already listening - assuming client is running.")
        return
    except (socket.error, socket.timeout, OSError):
        # Port not available, need to start client
        pass

    # Start Hysteria2 client in background
    hysteria_cmd = [
        "hysteria",
        "client",
        "-c", str(config_path),
    ]

    _log(f"Starting Hysteria2 client: {' '.join(hysteria_cmd)}")

    try:
        # Start as background process (daemon mode)
        # Hysteria2 doesn't have a built-in daemon mode, so we use subprocess
        process = subprocess.Popen(
            hysteria_cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,  # Detach from parent
        )

        # Give it a moment to start
        time.sleep(0.5)

        # Check if process is still running
        if process.poll() is not None:
            raise VpnBootstrapError(
                f"Hysteria2 client exited immediately with code {process.returncode}"
            )

        _log(f"Hysteria2 client started (PID={process.pid})")

    except FileNotFoundError as exc:
        raise VpnBootstrapError(
            "'hysteria' binary not found. Install hysteria2 client in the container."
        ) from exc
    except Exception as exc:
        raise VpnBootstrapError(f"Failed to start Hysteria2 client: {exc}") from exc

    # Wait for SOCKS5 port to become available
    _log(f"Waiting for SOCKS5 port {socks5_port} to become available...")
    _wait_for_port("127.0.0.1", socks5_port, timeout, poll_interval)
    _log(f"Hysteria2 client is ready (SOCKS5={socks5_port}, HTTP={http_port})")


def bootstrap_from_env(
    env: Mapping[str, str] | None = None,
    *,
    timeout: float = 15.0,
    poll_interval: float = 0.5,
) -> bool:
    """
    Bootstrap WireGuard, AWG, OpenVPN, or Hysteria2 using environment variables.

    Returns True when VPN enforcement executed, False when skipped.
    """
    data = env or os.environ
    if not _is_truthy(data.get("VPN_ENABLED", "0")):
        _log("VPN disabled; skipping VPN bootstrap.")
        return False

    vpn_type = data.get("VPN_TYPE", "wireguard").lower()
    if vpn_type not in {"wireguard", "awg", "openvpn", "hysteria2"}:
        raise WireGuardBootstrapError(
            f"Unsupported VPN_TYPE '{vpn_type}'. Use 'wireguard', 'awg', 'openvpn', or 'hysteria2'."
        )

    # Handle Hysteria2 separately (proxy-based, not interface-based)
    if vpn_type == "hysteria2":
        hysteria2_uri = data.get("HYSTERIA2_URI")
        if not hysteria2_uri:
            raise WireGuardBootstrapError("HYSTERIA2_URI is required when VPN_TYPE=hysteria2.")

        socks5_port = int(data.get("HYSTERIA2_SOCKS5_PORT", "1080"))
        http_port = int(data.get("HYSTERIA2_HTTP_PORT", "8080"))
        config_path = data.get("HYSTERIA2_CONFIG_PATH", "/tmp/hysteria2.yaml")

        _log(f"Starting VPN bootstrap (type=hysteria2, SOCKS5={socks5_port}, HTTP={http_port})")

        ensure_hysteria2_up(
            hysteria2_uri,
            socks5_port,
            http_port,
            config_path,
            timeout=timeout,
            poll_interval=poll_interval,
        )

        # Hysteria2 uses proxy mode, not kernel routes - skip split tunnel configuration
        _log("Hysteria2 uses proxy mode (SOCKS5/HTTP) - skipping route configuration.")
        _log(f"Configure applications to use SOCKS5 proxy at 127.0.0.1:{socks5_port}")
        return True

    # Get config path and interface based on VPN type (WireGuard/AWG/OpenVPN)
    if vpn_type == "openvpn":
        config_path = data.get("OPENVPN_CONFIG_PATH")
        interface = data.get("OPENVPN_INTERFACE", "tun0")
        if not config_path:
            raise WireGuardBootstrapError("OPENVPN_CONFIG_PATH is required when VPN_TYPE=openvpn.")
    else:
        config_path = data.get("WG_CONFIG_PATH")
        interface = data.get("WG_INTERFACE", "wg0" if vpn_type == "wireguard" else "awg0")
        if not config_path:
            raise WireGuardBootstrapError("WG_CONFIG_PATH is required when VPN_ENABLED=1.")

    _log(f"Starting VPN bootstrap (type={vpn_type}, interface={interface}, config={config_path})")

    # Check sysctl parameter before starting (only for WireGuard/AWG)
    if vpn_type not in {"openvpn", "hysteria2"}:
        sysctl_param = "net.ipv4.conf.all.src_valid_mark"
        if _check_sysctl_param(sysctl_param, "1"):
            _log(f"Sysctl parameter '{sysctl_param}' is already set to '1' (likely by Docker)")
        else:
            _log(f"Warning: sysctl parameter '{sysctl_param}' is not set to '1'")

    default_route = _get_default_route()

    if vpn_type == "awg":
        ensure_awg_up(
            config_path,
            interface,
            timeout=timeout,
            poll_interval=poll_interval,
        )
    elif vpn_type == "openvpn":
        ensure_openvpn_up(
            config_path,
            interface,
            timeout=timeout,
            poll_interval=poll_interval,
        )
    else:
        ensure_wireguard_up(
            config_path,
            interface,
            timeout=timeout,
            poll_interval=poll_interval,
        )

    configure_split_tunnel(interface, data, default_route)
    return True


def main() -> int:
    try:
        ran = bootstrap_from_env()
        if ran:
            _log("VPN bootstrap completed successfully.")
        return 0
    except WireGuardBootstrapError as exc:
        _log(f"VPN bootstrap failed: {exc}")
        return 1
    except Exception as exc:  # pragma: no cover - safety net
        _log(f"Unexpected VPN bootstrap error: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
