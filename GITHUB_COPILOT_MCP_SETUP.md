# GitHub Copilot MCP Setup Guide

This guide explains how to connect the `mcp-quant-brain` (mcp-quant-brain) server to **GitHub Copilot** in Visual Studio Code.

## Prerequisites
- **VS Code 1.99+** (or the latest version)
- **GitHub Copilot Extension** installed and logged in.
- **Agent Mode Enabled**: Ensure you are in the "Copilot Chat" sidebar and using a recent model that supports tools.

## STEP 1: Copy the Configuration
Copy the JSON block below. You will need to paste this into your VS Code MCP configuration.

```json
{
  "mcpServers": {
    "mcp-quant-brain": {
      "command": "C:\\Users\\PaarthGala\\Coding\\mcp-quant-brain\\.venv\\Scripts\\python.exe",
      "args": [
        "C:\\Users\\PaarthGala\\Coding\\mcp-quant-brain\\main.py"
      ],
      "env": {
        "YFINANCE_CACHE": "True",
        "DEFAULT_MARKET": "US"
      }
    }
  }
}
```

> [!IMPORTANT]
> Ensure the paths above match your actual local installation folder.

## STEP 2: Open the Config in VS Code
1. Open Visual Studio Code.
2. Open the **Command Palette** (`Ctrl+Shift+P` or `Cmd+Shift+P`).
3. Type **"MCP: Open User Configuration"** and press Enter.
4. If the file is empty, paste the JSON above (ensuring it's valid JSON). If it already has servers, add `mcp-quant-brain` to the `mcpServers` object.
5. Save the file.

## STEP 3: Verify and Use
1. Open the **Command Palette** again and type **"MCP: List Servers"**.
2. Verify that `mcp-quant-brain` is listed and status is "Healthy" or "Running".
3. Open **Copilot Chat**.
4. Ask a financial question: 
   > "Analyze NVDA and TSLA using the generate_optimized_verdict tool."

## Troubleshooting
- **Serialization Errors**: If you see `int64` errors, restart the MCP server using the **"MCP: Restart Server"** command in VS Code.
- **Path Errors**: Ensure the `python.exe` path points to the `.venv` inside the project directory.
