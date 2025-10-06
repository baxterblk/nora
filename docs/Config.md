# Configuration Guide

## Overview

NORA uses a YAML configuration file located at `~/.nora/config.yaml` to manage settings for Ollama connections, model preferences, and environment profiles.

## Quick Start

### View Current Configuration

```bash
nora config show
```

Output:
```json
{
  "model": "deepseek-coder:6.7b",
  "ollama": {
    "url": "http://localhost:11434",
    "verify_ssl": false
  },
  "profiles": {}
}
```

### Update Settings

```bash
# Change default model
nora config set model llama3.2:3b

# Change Ollama URL
nora config set ollama.url http://remote-server:11434

# Enable SSL verification
nora config set ollama.verify_ssl true
```

### Test Connection

```bash
nora config test
```

Output:
```
✓ Connected to http://localhost:11434
✓ Ollama version: 0.1.0
```

## Configuration File Structure

### Default Configuration

When you first run NORA, it creates `~/.nora/config.yaml`:

```yaml
model: deepseek-coder:6.7b
ollama:
  url: http://localhost:11434
  verify_ssl: false
profiles: {}
```

### Configuration Keys

#### `model` (string)
The default Ollama model to use for all commands.

**Examples:**
- `deepseek-coder:6.7b` - Code-focused model
- `llama3.2:3b` - General-purpose lightweight model
- `codellama:7b` - Larger code model
- `mistral:latest` - Latest Mistral model

**Override at runtime:**
```bash
nora chat --model llama3.2:3b
nora agent greeter --model codellama:7b
```

#### `ollama.url` (string)
The base URL for the Ollama API.

**Local:**
```yaml
ollama:
  url: http://localhost:11434
```

**Remote:**
```yaml
ollama:
  url: http://192.168.1.100:11434
  url: https://ollama.example.com
```

**Important:** Do not include trailing slashes.

#### `ollama.verify_ssl` (boolean)
Whether to verify SSL certificates when connecting to Ollama.

**Local/Self-Signed:**
```yaml
ollama:
  verify_ssl: false  # Ignore SSL errors
```

**Production:**
```yaml
ollama:
  verify_ssl: true   # Enforce valid SSL
```

#### `ollama.compatibility` (string)
Ollama API endpoint compatibility mode for older server versions.

**Default (Modern Ollama):**
```yaml
ollama:
  compatibility: chat  # Use /api/chat (Ollama v0.3.9+)
```

**Legacy Mode (Older Ollama):**
```yaml
ollama:
  compatibility: generate  # Use /api/generate (Ollama < v0.3.9)
```

**When to Use:**

- **`chat` mode** (default): Use for Ollama v0.3.9 and newer
  - Supports full conversation history with message roles
  - Better context management
  - Preferred for all modern installations

- **`generate` mode**: Use for Ollama versions before v0.3.9
  - Uses legacy `/api/generate` endpoint
  - Converts messages to flat prompt format
  - Required for older server versions

**Check Your Ollama Version:**

```bash
curl http://localhost:11434/api/version
```

If the version is < 0.3.9, switch to generate mode:

```bash
nora config set ollama.compatibility generate
nora config test
```

**Automatic Fallback:**

NORA automatically detects when `/api/chat` is unavailable (404 error) and falls back to `/api/generate` with a warning:

```
⚠️ Ollama server missing /api/chat — falling back to /api/generate compatibility mode.
⚠️ Consider upgrading Ollama or run: nora config set ollama.compatibility generate
```

This fallback happens once per session. To avoid the warning, explicitly set the compatibility mode.

**Example Configuration:**

```yaml
# For older Ollama servers
model: deepseek-coder:6.7b
ollama:
  url: http://localhost:11434
  verify_ssl: false
  compatibility: generate
```

#### `profiles` (object)
Named configuration presets for different environments.

## Profiles

### What Are Profiles?

Profiles allow you to quickly switch between different Ollama configurations (local dev, remote server, production, etc.) without manually editing the config file.

### Creating Profiles

Edit `~/.nora/config.yaml`:

```yaml
model: deepseek-coder:6.7b
ollama:
  url: http://localhost:11434
  verify_ssl: false

profiles:
  # Local development with lighter model
  dev:
    model: llama3.2:3b
    ollama:
      url: http://localhost:11434
      verify_ssl: false

  # Remote GPU server with larger models
  gpu-server:
    model: codellama:13b
    ollama:
      url: http://192.168.50.10:11434
      verify_ssl: false

  # Production environment
  production:
    model: deepseek-coder:6.7b
    ollama:
      url: https://ollama.example.com
      verify_ssl: true

  # Experimental models
  experimental:
    model: mistral:latest
    ollama:
      url: http://localhost:11434
      verify_ssl: false
```

### Using Profiles

#### List Available Profiles

```bash
nora config show
```

Look for the `profiles` section in the JSON output.

#### Switch Profiles

```bash
nora config use gpu-server
```

Output:
```
✓ Switched to profile: gpu-server
```

This updates your active configuration:
```yaml
model: codellama:13b
ollama:
  url: http://192.168.50.10:11434
  verify_ssl: false
```

#### Switch Back to Default

```bash
nora config use default
```

### Profile Inheritance

Profiles only need to specify the keys they want to override:

```yaml
model: deepseek-coder:6.7b
ollama:
  url: http://localhost:11434
  verify_ssl: false

profiles:
  # Only override model, inherit ollama settings
  lightweight:
    model: llama3.2:3b

  # Only override URL, inherit model and verify_ssl
  remote:
    ollama:
      url: http://192.168.1.100:11434
```

## Remote Ollama Setup

### Prerequisites

1. **Ollama installed** on the remote server
2. **Network access** to the Ollama API port (default: 11434)
3. **Firewall rules** allowing TCP connections on port 11434

### Option 1: Direct Connection (Local Network)

#### Step 1: Configure Ollama Server

On the remote server, set Ollama to listen on all interfaces:

**Linux (systemd):**

Edit `/etc/systemd/system/ollama.service`:

```ini
[Service]
Environment="OLLAMA_HOST=0.0.0.0:11434"
```

Restart Ollama:
```bash
sudo systemctl daemon-reload
sudo systemctl restart ollama
```

**macOS/Windows:**

Set environment variable before starting Ollama:
```bash
export OLLAMA_HOST=0.0.0.0:11434
ollama serve
```

#### Step 2: Test Connection

From your local machine:

```bash
curl http://REMOTE_IP:11434/api/version
```

Expected response:
```json
{"version": "0.1.0"}
```

#### Step 3: Configure NORA

```bash
nora config set ollama.url http://REMOTE_IP:11434
nora config test
```

### Option 2: SSH Tunnel (Secure)

For remote servers not on your local network, use an SSH tunnel:

#### Step 1: Create SSH Tunnel

```bash
ssh -L 11434:localhost:11434 user@remote-server -N
```

This forwards local port 11434 to the remote server's Ollama instance.

#### Step 2: Configure NORA

```bash
nora config set ollama.url http://localhost:11434
nora config test
```

NORA will connect to localhost:11434, which tunnels to the remote server.

#### Step 3: Keep Tunnel Alive

**Option A: Use autossh**

```bash
autossh -M 0 -L 11434:localhost:11434 user@remote-server -N
```

**Option B: SSH config keepalive**

Add to `~/.ssh/config`:

```
Host remote-server
    ServerAliveInterval 60
    ServerAliveCountMax 3
```

### Option 3: HTTPS with Reverse Proxy (Production)

For public-facing Ollama instances, use a reverse proxy with SSL:

#### Step 1: Install Nginx/Caddy

**Caddy example** (`Caddyfile`):

```
ollama.example.com {
    reverse_proxy localhost:11434
}
```

Start Caddy (auto-provisions SSL):
```bash
caddy run
```

#### Step 2: Configure NORA

```bash
nora config set ollama.url https://ollama.example.com
nora config set ollama.verify_ssl true
nora config test
```

### Option 4: Profile-Based Setup

For multiple remote servers, use profiles:

```yaml
model: deepseek-coder:6.7b
ollama:
  url: http://localhost:11434
  verify_ssl: false

profiles:
  home-server:
    ollama:
      url: http://192.168.1.100:11434

  work-server:
    ollama:
      url: https://ollama.work.local
      verify_ssl: true

  cloud-gpu:
    model: codellama:13b
    ollama:
      url: https://ollama.example.com
      verify_ssl: true
```

**Usage:**
```bash
# Use home server
nora config use home-server
nora chat

# Switch to work server
nora config use work-server
nora chat

# Switch to cloud GPU for heavy workloads
nora config use cloud-gpu
nora run "complex code generation task"
```

## Advanced Configuration

### Custom Configuration Path

Override the default config location:

```bash
export NORA_CONFIG_PATH=/path/to/custom/config.yaml
nora chat
```

Or edit `nora/core/config.py` to change the default:

```python
class ConfigManager:
    def __init__(self, path: str = "/custom/path/config.yaml") -> None:
        # ...
```

### Programmatic Configuration

For scripts or automation:

```python
from nora.core import ConfigManager

config = ConfigManager()

# Update settings
config.set("model", "llama3.2:3b")
config.set("ollama.url", "http://remote:11434")
config.save()

# Test connection
success, result = config.test_connection()
if success:
    print(f"Connected: {result}")
else:
    print(f"Failed: {result}")
```

### Environment Variables (Future Feature)

Planned for v0.4.0:

```bash
export NORA_MODEL=llama3.2:3b
export NORA_OLLAMA_URL=http://remote:11434
nora chat
```

## Troubleshooting

### Connection Refused

**Symptom:**
```
✗ Connection failed: Connection refused
```

**Causes:**
- Ollama not running
- Wrong URL/port
- Firewall blocking

**Solutions:**
```bash
# Check if Ollama is running
curl http://localhost:11434/api/version

# Start Ollama
ollama serve

# Check firewall (Linux)
sudo ufw allow 11434

# Check Ollama is listening on the right interface
sudo netstat -tlnp | grep 11434
```

### SSL Verification Errors

**Symptom:**
```
✗ Connection failed: SSL: CERTIFICATE_VERIFY_FAILED
```

**Causes:**
- Self-signed certificate
- Expired certificate
- Certificate hostname mismatch

**Solutions:**

**Option A: Disable SSL verification** (local/dev only)
```bash
nora config set ollama.verify_ssl false
```

**Option B: Add certificate to trust store** (production)
```bash
# Linux
sudo cp cert.crt /usr/local/share/ca-certificates/
sudo update-ca-certificates

# macOS
sudo security add-trusted-cert -d -r trustRoot -k /Library/Keychains/System.keychain cert.crt
```

### Timeout Errors

**Symptom:**
```
✗ Connection failed: Request timeout
```

**Causes:**
- Slow network
- Large model loading
- Server overloaded

**Solutions:**

Edit `nora/core/config.py` to increase timeout:

```python
def test_connection(self) -> Tuple[bool, Any]:
    # ...
    r = requests.get(f"{url}/api/version", timeout=30, verify=verify)
    #                                              ^^^ increase from 5
```

### Model Not Found

**Symptom:**
```
Error: model 'codellama:13b' not found
```

**Cause:**
Model not pulled on the Ollama server.

**Solution:**

On the Ollama server:
```bash
ollama pull codellama:13b
ollama list  # Verify it's available
```

Then test from NORA:
```bash
nora config test
nora chat --model codellama:13b
```

## Security Considerations

### Local Development

- ✅ Use `verify_ssl: false` for self-signed certs
- ✅ Bind Ollama to `127.0.0.1:11434` (localhost only)
- ✅ Keep config file permissions: `chmod 600 ~/.nora/config.yaml`

### Remote Servers (Local Network)

- ✅ Use SSH tunneling instead of direct exposure
- ✅ Configure firewall rules to allow only trusted IPs
- ⚠️ Consider using VPN for access

### Production (Public Internet)

- ✅ Always use HTTPS with valid certificates
- ✅ Set `verify_ssl: true`
- ✅ Implement authentication (reverse proxy with auth)
- ✅ Use rate limiting to prevent abuse
- ✅ Monitor logs for suspicious activity

**Example Nginx config with auth:**

```nginx
server {
    listen 443 ssl;
    server_name ollama.example.com;

    ssl_certificate /etc/letsencrypt/live/ollama.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/ollama.example.com/privkey.pem;

    auth_basic "Ollama API";
    auth_basic_user_file /etc/nginx/.htpasswd;

    location / {
        proxy_pass http://localhost:11434;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }
}
```

Then configure NORA with basic auth in the URL:
```bash
nora config set ollama.url https://user:pass@ollama.example.com
```

## Best Practices

1. **Use profiles** for different environments
2. **Test connections** after config changes
3. **Enable SSL verification** in production
4. **Keep config files secure** (don't commit to git)
5. **Document custom profiles** in project README
6. **Use SSH tunnels** for remote access when possible
7. **Monitor Ollama logs** for errors
8. **Keep Ollama updated** for latest features/fixes

## Example Configurations

### Solo Developer (Local Only)

```yaml
model: deepseek-coder:6.7b
ollama:
  url: http://localhost:11434
  verify_ssl: false
profiles: {}
```

### Team with Shared GPU Server

```yaml
model: codellama:7b
ollama:
  url: http://10.0.0.50:11434
  verify_ssl: false

profiles:
  local:
    model: llama3.2:3b
    ollama:
      url: http://localhost:11434

  gpu-server:
    model: codellama:13b
    ollama:
      url: http://10.0.0.50:11434

  experimental:
    model: mistral:latest
    ollama:
      url: http://10.0.0.50:11434
```

### Production with Multiple Regions

```yaml
model: deepseek-coder:6.7b
ollama:
  url: https://ollama-us.example.com
  verify_ssl: true

profiles:
  us-east:
    ollama:
      url: https://ollama-us.example.com
      verify_ssl: true

  eu-west:
    ollama:
      url: https://ollama-eu.example.com
      verify_ssl: true

  asia-pacific:
    ollama:
      url: https://ollama-ap.example.com
      verify_ssl: true

  development:
    model: llama3.2:3b
    ollama:
      url: http://localhost:11434
      verify_ssl: false
```

## Configuration Migration

### From v0.2.x to v0.3.x

NORA v0.3.0 is backwards compatible with v0.2.x configs. No changes needed.

### Future (v0.4.x)

Planned changes:
- **Environment variable overrides**: `NORA_MODEL`, `NORA_OLLAMA_URL`
- **Encrypted secrets**: For API keys and credentials
- **Plugin-specific config**: Per-agent settings
- **Context settings**: Configure context window limits

See [ROADMAP.md](../ROADMAP.md) for details.

---

**Next Steps:**
- Set up your configuration: `nora config set model llama3.2:3b`
- Test connection: `nora config test`
- Create profiles for different environments
- Read [Overview.md](./Overview.md) for architecture details
- Check [Agents.md](./Agents.md) for plugin development
