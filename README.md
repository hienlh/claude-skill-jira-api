# Claude Skill: Jira API

> Manage Jira issues directly from Claude Code - view, create, edit, transition, comment, attach files, and more.

A Python-based Claude Code skill for interacting with Jira Cloud via REST API v3. No external dependencies - uses pure Python with urllib.

## Quick Install

```bash
npx skills add hienlh/claude-skill-jira-api
```

Or install globally without prompts:

```bash
npx skills add hienlh/claude-skill-jira-api -y -g
```

After install, configure your credentials (see [Authentication](#2-configure-authentication)).

## Features

- **View Issues** - Detailed issue view with description, comments, linked issues
- **Create/Edit/Delete** - Full issue lifecycle management
- **Transitions** - Move issues through workflow states
- **Comments** - Add and list comments with ADF support
- **Attachments** - Upload files (images, PDFs, etc.) to issues
- **Search** - JQL and text search across projects
- **Worklogs** - Track time spent on issues
- **Issue Links** - Link related issues (Relates, Blocks, Clones, etc.)
- **Sprint** - View current sprint issues
- **User Search** - Find users by name/email
- **Assign** - Assign issues to users

## Installation

### 1. Clone to your Claude skills directory

```bash
git clone https://github.com/hienlh/claude-skill-jira-api.git ~/.claude/skills/jira-api
```

### 2. Configure authentication

Generate an API token at: https://id.atlassian.com/manage-profile/security/api-tokens

Create `.env` file:

```bash
cp ~/.claude/skills/jira-api/.env.example ~/.claude/skills/jira-api/.env
# Edit .env with your credentials
```

```env
JIRA_BASE_URL=https://your-domain.atlassian.net
JIRA_EMAIL=your-email@example.com
JIRA_API_TOKEN=your-api-token
JIRA_PROJECT=YOUR_PROJECT_KEY
```

## Quick Start

```bash
JIRA="python3 ~/.claude/skills/jira-api/scripts/jira-api.py"

# View issue
$JIRA view NX-1234

# Create issue
$JIRA create -s "Bug: login fails" -t Bug -b "Steps to reproduce..."

# Transition status
$JIRA move NX-1234 "In Progress"

# Add comment
$JIRA comment-add NX-1234 "Fixed in PR #123"

# Attach screenshot
$JIRA attach NX-1234 screenshot.png

# Search
$JIRA search "pension bug"
```

## Commands Reference

| Command | Description | Example |
|---------|-------------|---------|
| `view` | View issue details | `view NX-1234` |
| `list` | List issues (JQL) | `list -q "status='In Progress'"` |
| `search` | Text search | `search "pension bug"` |
| `create` | Create issue | `create -s "Summary" -t Bug` |
| `edit` | Edit issue | `edit NX-1234 -s "New title"` |
| `delete` | Delete issue | `delete NX-1234` |
| `move` | Transition status | `move NX-1234 "Done"` |
| `transitions` | List available transitions | `transitions NX-1234` |
| `comment-add` | Add comment | `comment-add NX-1234 "body"` |
| `comment-list` | List comments | `comment-list NX-1234` |
| `attach` | Upload files | `attach NX-1234 file.png` |
| `assign` | Assign issue | `assign NX-1234 me` |
| `worklog-add` | Add worklog | `worklog-add NX-1234 2h` |
| `worklog-list` | List worklogs | `worklog-list NX-1234` |
| `user-search` | Find users | `user-search "victor"` |
| `link` | Link two issues | `link NX-1 NX-2 -t Blocks` |
| `sprint` | Sprint issues | `sprint 4` |
| `open` | Open in browser | `open NX-1234` |

## Options

| Option | Description |
|--------|-------------|
| `-s`, `--summary` | Issue summary |
| `-t`, `--type` | Issue type (Task, Bug, Story, etc.) |
| `-b`, `--body` | Description text |
| `-p`, `--project` | Project key (overrides .env) |
| `-q`, `--jql` | JQL query string |
| `-l`, `--limit` | Max results (default: 20) |
| `-c`, `--comment` | Worklog comment |
| `--priority` | Priority name |
| `--assignee` | Assignee account ID |
| `--labels` | Issue labels |

## API Reference

Based on Jira REST API v3:
- Swagger: https://dac-static.atlassian.com/cloud/jira/platform/swagger-v3.v3.json
- Docs: https://developer.atlassian.com/cloud/jira/platform/rest/v3/

## Requirements

- Python 3.6+
- No external dependencies (uses stdlib only)

## License

MIT License - See [LICENSE](LICENSE)

## Contributing

Contributions welcome! Please open an issue or PR.
