# 🌐 Universal MCP Configuration Guide

This guide provides the configuration snippets required to connect the `mcp-quant-brain` server to your favorite AI IDE agents and clients.

## 🛠️ Global Parameters

- **Python Executable**: `c:/Users/PaarthGala/Coding/mcp-quant-brain/.venv/Scripts/python.exe`
- **Main Script**: `c:/Users/PaarthGala/Coding/mcp-quant-brain/main.py`

---

## 1. Claude Desktop (Windows)

**File Path**: `%APPDATA%\Claude\claude_desktop_config.json`

Add the following to your `mcpServers` object:

```json
{
  "mcpServers": {
    "mcp-quant-brain": {
      "command": "c:/Users/PaarthGala/Coding/mcp-quant-brain/.venv/Scripts/python.exe",
      "args": ["c:/Users/PaarthGala/Coding/mcp-quant-brain/main.py"],
      "env": {
        "YFINANCE_CACHE": "True",
        "DEFAULT_MARKET": "US"
      }
    }
  }
}
```

---

## 2. Windsurf (Windows)

**File Path**: `%USERPROFILE%\.codeium\windsurf\mcp_config.json`

Add the following to your `mcpServers` object:

```json
{
  "mcpServers": {
    "mcp-quant-brain": {
      "command": "c:/Users/PaarthGala/Coding/mcp-quant-brain/.venv/Scripts/python.exe",
      "args": ["c:/Users/PaarthGala/Coding/mcp-quant-brain/main.py"],
      "env": {
        "YFINANCE_CACHE": "True",
        "DEFAULT_MARKET": "US"
      }
    }
  }
}
```

---

## 3. Roo Code / Cline (VS Code)

**Global Path**: `%APPDATA%\Code\User\globalStorage\rooveterinaryinc.roo-cline\settings\mcp_settings.json`  
**Project Path**: `.roo/mcp.json`

Add the following configuration:

```json
{
  "mcpServers": {
    "mcp-quant-brain": {
      "command": "c:/Users/PaarthGala/Coding/mcp-quant-brain/.venv/Scripts/python.exe",
      "args": ["c:/Users/PaarthGala/Coding/mcp-quant-brain/main.py"],
      "env": {
        "YFINANCE_CACHE": "True",
        "DEFAULT_MARKET": "US"
      },
      "disabled": false
    }
  }
}
```

---

## 4. Cursor

Cursor allows you to add MCP servers via the GUI:

1. Open **Cursor Settings** (`Ctrl + Shift + J`).
2. Go to **General** -> **MCP**.
3. Click **+ Add New MCP Server**.
4. Set the name to `mcp-quant-brain`.
5. Set the type to `command`.
6. Use the following command string:
   ```text
   c:/Users/PaarthGala/Coding/mcp-quant-brain/.venv/Scripts/python.exe c:/Users/PaarthGala/Coding/mcp-quant-brain/main.py
   ```

---

## 5. Other Clients (Standard Configuration)

For any client that supports the MCP protocol via `stdio`, use:

- **Command**: `c:/Users/PaarthGala/Coding/mcp-quant-brain/.venv/Scripts/python.exe`
- **Arguments**: `["c:/Users/PaarthGala/Coding/mcp-quant-brain/main.py"]`
- **Environment**:
  - `YFINANCE_CACHE`: `True`
  - `DEFAULT_MARKET`: `US`

---

---

> [!IMPORTANT]
> This server uses the standard `mcp-python-sdk`. It is optimized for `stdio` transport and does not pollute `stdout` with banners or logs, making it compatible with all modern MCP clients.
