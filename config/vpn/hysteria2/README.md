# Hysteria2 VPN Configuration

Hysteria2 is a high-performance proxy powered by a customized QUIC protocol, designed for bypassing network restrictions and accessing blocked APIs (e.g., Google Gemini API). Unlike WireGuard/OpenVPN, Hysteria2 runs as a userspace SOCKS5/HTTP proxy rather than creating kernel network interfaces.

## Overview

This project uses Hysteria2 as the primary VPN solution for accessing external APIs that may be geo-restricted or blocked. The system automatically:

- Parses connection URI and generates YAML configuration
- Starts Hysteria2 client as a background daemon
- Exposes SOCKS5 proxy on `127.0.0.1:1080`
- Exposes HTTP proxy on `127.0.0.1:8080`
- Routes application traffic (Gemini API calls) through the proxy

### Why Hysteria2?

- **No root required**: Runs in userspace, no kernel modules needed
- **Better performance on lossy networks**: QUIC-based protocol handles packet loss better than TCP-based VPNs
- **Censorship resistant**: Traffic appears as standard HTTPS/HTTP3
- **Simpler setup**: Just a URI - no complex config files
- **Cross-platform**: Works on Linux, macOS, Windows with the same binary

## Quick Start

### Docker (Recommended)

1. Edit `.env` file in project root:

```bash
VPN_ENABLED=1
VPN_TYPE=hysteria2
HYSTERIA2_URI=hysteria2://SenpaiCat2407@vpn.vibe-labs.ru:8443/?sni=vpn.vibe-labs.ru
HYSTERIA2_SOCKS5_PORT=1080
HYSTERIA2_HTTP_PORT=8080
```

2. Start services:

```bash
docker-compose up -d
```

3. Verify connection:

```bash
curl http://localhost:9187/api/vpn/health
```

The application will automatically start Hysteria2 and route Gemini API traffic through it.

## Environment Variables

### Hysteria2-Specific

| Variable | Default | Description |
|----------|---------|-------------|
| `VPN_ENABLED` | `0` | Enable VPN |
| `VPN_TYPE` | `hysteria2` | Set VPN type to Hysteria2 |
| `HYSTERIA2_URI` | - | Connection URI (required) |
| `HYSTERIA2_SOCKS5_PORT` | `1080` | Local SOCKS5 proxy port |
| `HYSTERIA2_HTTP_PORT` | `8080` | Local HTTP proxy port |
| `HYSTERIA2_CONFIG_PATH` | `/tmp/hysteria2.yaml` | Generated config file path |

### URI Format

```
hysteria2://PASSWORD@SERVER:PORT/?sni=HOSTNAME
```

Example:
```
hysteria2://SenpaiCat2407@vpn.vibe-labs.ru:8443/?sni=vpn.vibe-labs.ru
```

Components:
- `PASSWORD` — Authentication password for the Hysteria2 server
- `SERVER` — Server hostname or IP address
- `PORT` — Server port (default: 443)
- `sni` — TLS Server Name Indication (usually same as server)

## Generated Configuration

The bootstrap script generates a YAML config like this:

```yaml
server: vpn.vibe-labs.ru:8443
auth: SenpaiCat2407
tls:
  sni: vpn.vibe-labs.ru
  insecure: false
socks5:
  listen: 127.0.0.1:1080
http:
  listen: 127.0.0.1:8080
```

## How It Differs from WireGuard/OpenVPN

| Feature | WireGuard/OpenVPN | Hysteria2 |
|---------|-------------------|-----------|
| Network Layer | Kernel (TUN/TAP) | Userspace |
| Interface | `wg0`, `tun0` | None (proxy) |
| Routing | `ip route` | SOCKS5/HTTP proxy |
| Root Required | Yes | No |
| Protocol | WireGuard/OpenVPN | QUIC-based |
| Performance | Excellent | Excellent (optimized for unreliable networks) |

## Integration with Application

The application's HTTP clients (httpx, aiohttp) should be configured to use the proxy:

```python
import httpx

# Using SOCKS5 proxy
async with httpx.AsyncClient(proxy="socks5://127.0.0.1:1080") as client:
    response = await client.get("https://generativelanguage.googleapis.com/")

# Using HTTP proxy
async with httpx.AsyncClient(proxy="http://127.0.0.1:8080") as client:
    response = await client.get("https://generativelanguage.googleapis.com/")
```

## Verification

Check Hysteria2 status via health endpoint:

```bash
curl http://localhost:9187/api/vpn/health
```

Response example:
```json
{
  "status": "healthy",
  "vpn_type": "hysteria2",
  "hysteria2": {
    "server": "vpn.vibe-labs.ru:8443",
    "socks5_port": 1080,
    "http_port": 8080,
    "is_running": true,
    "socks5_accessible": true,
    "http_accessible": true
  },
  "probe": {
    "domain": "generativelanguage.googleapis.com",
    "status": "ok",
    "latency_ms": 150.5
  }
}
```

Manual verification:

```bash
# Check if process is running
ps aux | grep hysteria

# Test SOCKS5 proxy
curl --socks5 127.0.0.1:1080 https://generativelanguage.googleapis.com/

# Test HTTP proxy
curl -x http://127.0.0.1:8080 https://generativelanguage.googleapis.com/
```

## Installing Hysteria2 Client

### Docker (Already Included)

The project's Docker image (`Dockerfile.multistage`) already includes Hysteria2 client for both AMD64 and ARM64 architectures. No additional installation needed.

### Linux (Manual Installation)

For development outside Docker:

```bash
# Download latest release (AMD64)
wget -O /usr/local/bin/hysteria \
  https://github.com/apernet/hysteria/releases/latest/download/hysteria-linux-amd64
chmod +x /usr/local/bin/hysteria

# Or for ARM64
wget -O /usr/local/bin/hysteria \
  https://github.com/apernet/hysteria/releases/latest/download/hysteria-linux-arm64
chmod +x /usr/local/bin/hysteria

# Verify installation
hysteria version
```

### macOS

```bash
# Using Homebrew
brew install hysteria

# Or download binary directly
curl -Lo /usr/local/bin/hysteria \
  https://github.com/apernet/hysteria/releases/latest/download/hysteria-darwin-amd64
chmod +x /usr/local/bin/hysteria

# For Apple Silicon (M1/M2)
curl -Lo /usr/local/bin/hysteria \
  https://github.com/apernet/hysteria/releases/latest/download/hysteria-darwin-arm64
chmod +x /usr/local/bin/hysteria

# Verify installation
hysteria version
```

### Windows

1. Download binary from [GitHub Releases](https://github.com/apernet/hysteria/releases/latest):
   - `hysteria-windows-amd64.exe` (64-bit)
   - `hysteria-windows-386.exe` (32-bit)

2. Rename to `hysteria.exe` and add to PATH

3. Verify installation:
```cmd
hysteria version
```

## Migration from OpenVPN

1. Update `.env`:
   ```bash
   VPN_TYPE=hysteria2
   HYSTERIA2_URI=hysteria2://PASSWORD@server:port/?sni=hostname
   ```

2. Remove OpenVPN-specific settings (no longer needed):
   ```bash
   # OPENVPN_CONFIG_PATH=  # Not needed for Hysteria2
   # OPENVPN_INTERFACE=    # Not needed for Hysteria2
   ```

3. Routing settings (`VPN_ROUTE_MODE`, `VPN_ROUTE_DOMAINS`, etc.) are **not used** with Hysteria2 since traffic is routed via proxy, not kernel routes.

4. Update application HTTP clients to use the proxy (if not already configured).

## Advantages of Hysteria2

- **No root required**: Runs in userspace, no kernel modules needed
- **Better performance on lossy networks**: QUIC-based protocol handles packet loss better
- **Censorship resistant**: Traffic looks like standard HTTPS/HTTP3
- **Simpler setup**: Just a URI, no config files to manage
- **Cross-platform**: Works on any platform with the Hysteria2 binary

## Troubleshooting

### Connection Refused

```bash
# Check if Hysteria2 is running
ps aux | grep hysteria

# Check logs
cat /var/log/hysteria2.log
```

### TLS Errors

Ensure SNI is correctly set in the URI:
```
hysteria2://password@server:port/?sni=correct-hostname
```

### Firewall Issues

Hysteria2 uses UDP. Ensure UDP port is open on the server.

## Security Notes

- Never commit the `HYSTERIA2_URI` with real credentials to version control
- Use environment variables or secrets management for production
- The generated config file (`/tmp/hysteria2.yaml`) contains credentials

## References

- [Hysteria2 Official Documentation](https://v2.hysteria.network/)
- [Hysteria2 Client Configuration](https://v2.hysteria.network/docs/getting-started/Client/)
- [Full Client Config Reference](https://v2.hysteria.network/docs/advanced/Full-Client-Config/)
