# MCP

Configure local MCP servers in `~/.agent-h/mcp.toml`:

```bash
agent-h mcp add filesystem 'stdio:npx -y @modelcontextprotocol/server-filesystem .'
agent-h mcp list
agent-h mcp remove filesystem
```

Enabled servers are loaded on session start. Failed servers are recorded but do not block the session.
