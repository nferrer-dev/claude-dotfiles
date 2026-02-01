---
name: connect-apps
description: Connect Claude to 1000+ external applications via Composio Tool Router. Use when Claude needs to actually execute actions in external apps like Gmail, Slack, GitHub, Notion, Jira, etc. Requires composio-toolrouter plugin and free API key.
---

# Connect Apps

Enables Claude to integrate with 1000+ external applications and execute real actions.

## Setup

1. Install plugin: `claude plugin install composio-toolrouter`
2. Run setup: `/setup` (from the connect-apps-plugin commands)
3. Get free API key from https://platform.composio.dev
4. Test: Ask Claude to perform an action (e.g., "Send an email to test@example.com")

## Capabilities

- **Email**: Send via Gmail, Outlook, SendGrid
- **Dev Tools**: Create issues in GitHub, GitLab, Jira, Linear
- **Messaging**: Post to Slack, Discord, Teams, Telegram
- **Docs**: Update Notion, Google Docs, Confluence
- **Data**: Manage Sheets, Airtable, PostgreSQL

## How It Works

1. You request an action (e.g., "Send email to john@example.com about the meeting")
2. Composio Tool Router identifies the right tool
3. First use: OAuth authorization prompt (one-time per service)
4. Action executes and results are returned

## Troubleshooting

- **Plugin not found**: Verify installation with `claude plugin list`
- **Auth errors**: Complete OAuth flow when prompted
- **Permission denied**: Check permissions in the target app
