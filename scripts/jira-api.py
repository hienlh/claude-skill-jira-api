#!/usr/bin/env python3
"""Jira REST API client - replacement for jira CLI with full API support."""

import argparse
import json
import os
import sys
import urllib.request
import urllib.error
import urllib.parse
import base64
from pathlib import Path

# Load .env from skill directory
ENV_PATH = Path(__file__).parent.parent / ".env"


def load_env():
    """Load environment variables from .env file."""
    if ENV_PATH.exists():
        for line in ENV_PATH.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, value = line.partition("=")
                os.environ.setdefault(key.strip(), value.strip())


load_env()

BASE_URL = os.environ.get("JIRA_BASE_URL", "").rstrip("/")
EMAIL = os.environ.get("JIRA_EMAIL", "")
API_TOKEN = os.environ.get("JIRA_API_TOKEN", "")
PROJECT = os.environ.get("JIRA_PROJECT", "NX")


def get_auth_header():
    """Get base64 encoded auth header."""
    credentials = base64.b64encode(f"{EMAIL}:{API_TOKEN}".encode()).decode()
    return f"Basic {credentials}"


def api_request(method, path, data=None, files=None):
    """Make authenticated Jira API request."""
    url = f"{BASE_URL}/rest/api/3/{path}"
    headers = {"Authorization": get_auth_header()}

    if files:
        # Multipart upload for attachments
        boundary = "----FormBoundary7MA4YWxkTrZu0gW"
        headers["X-Atlassian-Token"] = "no-check"
        headers["Content-Type"] = f"multipart/form-data; boundary={boundary}"

        body = b""
        for filepath in files:
            filename = os.path.basename(filepath)
            with open(filepath, "rb") as f:
                file_data = f.read()
            body += f"--{boundary}\r\n".encode()
            body += f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'.encode()
            body += b"Content-Type: application/octet-stream\r\n\r\n"
            body += file_data
            body += b"\r\n"
        body += f"--{boundary}--\r\n".encode()

        req = urllib.request.Request(url, data=body, headers=headers, method=method)
    elif data is not None:
        headers["Content-Type"] = "application/json"
        body = json.dumps(data).encode("utf-8")
        req = urllib.request.Request(url, data=body, headers=headers, method=method)
    else:
        req = urllib.request.Request(url, headers=headers, method=method)

    try:
        with urllib.request.urlopen(req) as resp:
            if resp.status == 204:
                return None
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8")
        try:
            error_json = json.loads(error_body)
            print(f"❌ API Error ({e.code}): {json.dumps(error_json, indent=2)}", file=sys.stderr)
        except json.JSONDecodeError:
            print(f"❌ API Error ({e.code}): {error_body}", file=sys.stderr)
        sys.exit(1)


def format_issue(issue, verbose=False):
    """Format issue for display."""
    fields = issue["fields"]
    key = issue["key"]
    summary = fields.get("summary", "")
    status = fields.get("status", {}).get("name", "")
    priority = fields.get("priority", {}).get("name", "")
    issue_type = fields.get("issuetype", {}).get("name", "")
    assignee = fields.get("assignee", {})
    assignee_name = assignee.get("displayName", "Unassigned") if assignee else "Unassigned"
    reporter = fields.get("reporter", {})
    reporter_name = reporter.get("displayName", "") if reporter else ""
    created = fields.get("created", "")[:10]
    updated = fields.get("updated", "")[:10]
    labels = fields.get("labels", [])
    duedate = fields.get("duedate", "")

    lines = []
    lines.append(f"  ⭐ {issue_type}  {'🚧' if status != 'Done' else '✅'} {status}  ⌛ {duedate or '-'}  👷 {assignee_name}  🔑️ {key}  🚀 {priority}")
    lines.append("")
    lines.append(f"  # {summary}")
    lines.append("")
    lines.append(f"  ⏱️  {created}  🔎 {reporter_name}  🏷️  {', '.join(labels) if labels else 'None'}")

    if verbose:
        desc = fields.get("description", None)
        if desc:
            lines.append("")
            lines.append("  ------------------------ Description ------------------------")
            lines.append("")
            lines.append(f"  {extract_text_from_adf(desc)}")

        # Comments count
        comment_data = fields.get("comment", {})
        total_comments = comment_data.get("total", 0) if isinstance(comment_data, dict) else 0
        lines.append("")
        lines.append(f"  💬 {total_comments} comments")

        # Linked issues
        links = fields.get("issuelinks", [])
        if links:
            lines.append("")
            lines.append("  ------------------------ Linked Issues ------------------------")
            for link in links:
                link_type = link.get("type", {}).get("outward", link.get("type", {}).get("name", ""))
                linked = link.get("outwardIssue") or link.get("inwardIssue")
                if linked:
                    lk = linked["key"]
                    ls = linked["fields"]["summary"]
                    lst = linked["fields"]["status"]["name"]
                    lines.append(f"  {link_type.upper()}: {lk} {ls} • {lst}")

    lines.append("")
    lines.append(f"  View: {BASE_URL}/browse/{key}")
    return "\n".join(lines)


def extract_text_from_adf(doc):
    """Extract plain text from Atlassian Document Format."""
    if doc is None:
        return ""
    if isinstance(doc, str):
        return doc

    texts = []

    def walk(node):
        if isinstance(node, dict):
            if node.get("type") == "text":
                texts.append(node.get("text", ""))
            elif node.get("type") == "hardBreak":
                texts.append("\n")
            for child in node.get("content", []):
                walk(child)
        elif isinstance(node, list):
            for item in node:
                walk(item)

    walk(doc)
    return "".join(texts)


# ── Commands ──


def cmd_view(args):
    """View issue details."""
    issue = api_request("GET", f"issue/{args.issue}?expand=renderedFields")
    print(format_issue(issue, verbose=True))


def cmd_list(args):
    """List issues with JQL."""
    jql = args.jql or f'project={PROJECT} ORDER BY updated DESC'
    params = urllib.parse.urlencode({
        "jql": jql,
        "maxResults": args.limit,
        "fields": "summary,status,priority,issuetype,assignee,updated,duedate",
    })
    result = api_request("GET", f"search/jql?{params}")
    total = result.get("total", 0)
    issues = result.get("issues", [])

    print(f"  Showing {len(issues)} of {total} issues\n")
    for issue in issues:
        f = issue["fields"]
        key = issue["key"]
        status = f.get("status", {}).get("name", "")
        summary = f.get("summary", "")
        assignee = f.get("assignee", {})
        aname = assignee.get("displayName", "-") if assignee else "-"
        priority = f.get("priority", {}).get("name", "")
        print(f"  {key:<10} {status:<15} {priority:<8} {aname:<20} {summary[:60]}")


def cmd_create(args):
    """Create a new issue."""
    data = {
        "fields": {
            "project": {"key": args.project or PROJECT},
            "summary": args.summary,
            "issuetype": {"name": args.type},
        }
    }
    if args.body:
        data["fields"]["description"] = {
            "type": "doc",
            "version": 1,
            "content": _wiki_to_adf(args.body),
        }
    if args.priority:
        data["fields"]["priority"] = {"name": args.priority}
    if args.assignee:
        data["fields"]["assignee"] = {"id": args.assignee}
    if args.labels:
        data["fields"]["labels"] = args.labels

    result = api_request("POST", "issue", data)
    key = result["key"]
    print(f"✅ Issue created: {key}")
    print(f"   {BASE_URL}/browse/{key}")


def cmd_edit(args):
    """Edit an existing issue."""
    data = {"fields": {}}
    if args.summary:
        data["fields"]["summary"] = args.summary
    if args.priority:
        data["fields"]["priority"] = {"name": args.priority}
    if args.assignee:
        data["fields"]["assignee"] = {"id": args.assignee}
    if args.labels:
        data["fields"]["labels"] = args.labels

    if not data["fields"]:
        print("❌ No fields to update", file=sys.stderr)
        sys.exit(1)

    api_request("PUT", f"issue/{args.issue}", data)
    print(f"✅ Issue {args.issue} updated")


def cmd_move(args):
    """Transition issue to a new status."""
    # Get available transitions
    result = api_request("GET", f"issue/{args.issue}/transitions")
    transitions = result.get("transitions", [])

    target = args.status.lower()
    matched = None
    for t in transitions:
        if t["name"].lower() == target or t["to"]["name"].lower() == target:
            matched = t
            break

    if not matched:
        # Fuzzy match
        for t in transitions:
            if target in t["name"].lower() or target in t["to"]["name"].lower():
                matched = t
                break

    if not matched:
        available = [f"{t['name']} → {t['to']['name']}" for t in transitions]
        print(f"❌ Status '{args.status}' not found. Available transitions:", file=sys.stderr)
        for a in available:
            print(f"   - {a}", file=sys.stderr)
        sys.exit(1)

    api_request("POST", f"issue/{args.issue}/transitions", {"transition": {"id": matched["id"]}})
    print(f"✅ {args.issue} → {matched['to']['name']}")


def _parse_inline_markup(text):
    """Parse Jira wiki inline markup into ADF inline nodes.

    Supports: *bold*, {{code}}, [text|url], ~strikethrough~, +underline+
    """
    import re
    nodes = []
    # Pattern: *bold*, {{code}}, [text|url] or [url], ~strike~, +underline+
    pattern = re.compile(
        r'\{\{(.+?)\}\}'       # {{code}}
        r'|\[([^|\]]+)\|([^\]]+)\]'  # [text|url]
        r'|\[([^\]]+)\]'       # [url] (plain link)
        r'|\*(.+?)\*'          # *bold*
        r'|~(.+?)~'            # ~strikethrough~
        r'|\+(.+?)\+'          # +underline+
    )
    last_end = 0
    for m in pattern.finditer(text):
        # Add preceding plain text
        if m.start() > last_end:
            nodes.append({"type": "text", "text": text[last_end:m.start()]})
        if m.group(1) is not None:  # {{code}}
            nodes.append({"type": "text", "text": m.group(1), "marks": [{"type": "code"}]})
        elif m.group(2) is not None:  # [text|url]
            nodes.append({"type": "text", "text": m.group(2), "marks": [{"type": "link", "attrs": {"href": m.group(3)}}]})
        elif m.group(4) is not None:  # [url]
            nodes.append({"type": "text", "text": m.group(4), "marks": [{"type": "link", "attrs": {"href": m.group(4)}}]})
        elif m.group(5) is not None:  # *bold*
            nodes.append({"type": "text", "text": m.group(5), "marks": [{"type": "strong"}]})
        elif m.group(6) is not None:  # ~strike~
            nodes.append({"type": "text", "text": m.group(6), "marks": [{"type": "strike"}]})
        elif m.group(7) is not None:  # +underline+
            nodes.append({"type": "text", "text": m.group(7), "marks": [{"type": "underline"}]})
        last_end = m.end()
    # Trailing text
    if last_end < len(text):
        nodes.append({"type": "text", "text": text[last_end:]})
    return nodes if nodes else [{"type": "text", "text": text}]


def _wiki_to_adf(body_text):
    """Convert Jira wiki markup to ADF (Atlassian Document Format) nodes.

    Supports: h1-h6 headings, bullet lists (* item), numbered lists (# item),
    horizontal rules (----), inline markup (*bold*, {{code}}, [text|url]).
    """
    import re
    content_nodes = []
    lines = body_text.split("\n")
    i = 0
    while i < len(lines):
        line = lines[i]

        # Heading: h1. to h6.
        heading_match = re.match(r'^h([1-6])\.\s*(.*)', line)
        if heading_match:
            level = int(heading_match.group(1))
            text = heading_match.group(2).strip()
            content_nodes.append({
                "type": "heading",
                "attrs": {"level": level},
                "content": _parse_inline_markup(text),
            })
            i += 1
            continue

        # Horizontal rule: ----
        if line.strip().startswith('----'):
            content_nodes.append({"type": "rule"})
            i += 1
            continue

        # Bullet list: * item (collect consecutive lines)
        if re.match(r'^\*\s+', line):
            list_items = []
            while i < len(lines) and re.match(r'^\*\s+', lines[i]):
                item_text = re.sub(r'^\*\s+', '', lines[i])
                list_items.append({
                    "type": "listItem",
                    "content": [{"type": "paragraph", "content": _parse_inline_markup(item_text)}],
                })
                i += 1
            content_nodes.append({"type": "bulletList", "content": list_items})
            continue

        # Numbered list: # item (collect consecutive lines)
        if re.match(r'^#\s+', line):
            list_items = []
            while i < len(lines) and re.match(r'^#\s+', lines[i]):
                item_text = re.sub(r'^#\s+', '', lines[i])
                list_items.append({
                    "type": "listItem",
                    "content": [{"type": "paragraph", "content": _parse_inline_markup(item_text)}],
                })
                i += 1
            content_nodes.append({"type": "orderedList", "content": list_items})
            continue

        # Empty line → skip (don't create empty paragraphs)
        if not line.strip():
            i += 1
            continue

        # Regular paragraph with inline markup
        content_nodes.append({
            "type": "paragraph",
            "content": _parse_inline_markup(line),
        })
        i += 1

    return content_nodes


def cmd_comment_add(args):
    """Add comment to issue. Supports Jira wiki markup in body text."""
    content_nodes = _wiki_to_adf(args.body)

    data = {
        "body": {
            "type": "doc",
            "version": 1,
            "content": content_nodes,
        }
    }
    api_request("POST", f"issue/{args.issue}/comment", data)
    print(f"✅ Comment added to {args.issue}")


def cmd_comment_list(args):
    """List comments on issue."""
    result = api_request("GET", f"issue/{args.issue}/comment?maxResults={args.limit}&orderBy=-created")
    comments = result.get("comments", [])
    total = result.get("total", 0)

    print(f"  {total} comments on {args.issue}\n")
    for c in comments:
        cid = c.get("id", "")
        author = c.get("author", {}).get("displayName", "Unknown")
        created = c.get("created", "")[:19].replace("T", " ")
        body_text = extract_text_from_adf(c.get("body", ""))
        print(f"  [{created}] {author} (id: {cid}):")
        for line in body_text.split("\n")[:5]:
            print(f"    {line}")
        if len(body_text.split("\n")) > 5:
            print(f"    ... ({len(body_text.split(chr(10)))} lines)")
        print()


def cmd_comment_edit(args):
    """Edit an existing comment."""
    content_nodes = []
    for line in args.body.split("\n"):
        content_nodes.append({
            "type": "paragraph",
            "content": [{"type": "text", "text": line}] if line else [],
        })

    data = {
        "body": {
            "type": "doc",
            "version": 1,
            "content": content_nodes,
        }
    }
    api_request("PUT", f"issue/{args.issue}/comment/{args.comment_id}", data)
    print(f"✅ Comment {args.comment_id} updated on {args.issue}")


def cmd_comment_delete(args):
    """Delete a comment."""
    api_request("DELETE", f"issue/{args.issue}/comment/{args.comment_id}")
    print(f"✅ Comment {args.comment_id} deleted from {args.issue}")


def cmd_attach(args):
    """Add attachments to issue."""
    files = args.files
    for f in files:
        if not os.path.exists(f):
            print(f"❌ File not found: {f}", file=sys.stderr)
            sys.exit(1)

    result = api_request("POST", f"issue/{args.issue}/attachments", files=files)
    if result:
        for att in result:
            print(f"✅ Attached: {att.get('filename')} ({att.get('size', 0)} bytes)")


def cmd_transitions(args):
    """List available transitions for an issue."""
    result = api_request("GET", f"issue/{args.issue}/transitions")
    transitions = result.get("transitions", [])
    print(f"  Available transitions for {args.issue}:\n")
    for t in transitions:
        print(f"  {t['id']:<6} {t['name']:<25} → {t['to']['name']}")


def cmd_search(args):
    """Search issues with text query."""
    jql = f'project={args.project or PROJECT} AND text ~ "{args.query}" ORDER BY updated DESC'
    params = urllib.parse.urlencode({
        "jql": jql,
        "maxResults": args.limit,
        "fields": "summary,status,priority,issuetype,assignee",
    })
    result = api_request("GET", f"search/jql?{params}")
    total = result.get("total", 0)
    issues = result.get("issues", [])

    print(f"  Found {total} issues matching '{args.query}'\n")
    for issue in issues:
        f = issue["fields"]
        key = issue["key"]
        status = f.get("status", {}).get("name", "")
        summary = f.get("summary", "")
        print(f"  {key:<10} {status:<15} {summary[:70]}")


def cmd_assign(args):
    """Assign issue to user."""
    if args.user == "me":
        # Get current user
        me = api_request("GET", "myself")
        account_id = me["accountId"]
    elif args.user == "none":
        account_id = None
    else:
        account_id = args.user

    api_request("PUT", f"issue/{args.issue}/assignee", {"accountId": account_id})
    print(f"✅ {args.issue} assigned to {args.user}")


def cmd_delete(args):
    """Delete an issue."""
    api_request("DELETE", f"issue/{args.issue}")
    print(f"✅ {args.issue} deleted")


def cmd_worklog_add(args):
    """Add worklog entry to issue."""
    data = {
        "timeSpent": args.time,
    }
    if args.comment:
        data["comment"] = {
            "type": "doc",
            "version": 1,
            "content": _wiki_to_adf(args.comment),
        }
    api_request("POST", f"issue/{args.issue}/worklog", data)
    print(f"✅ Worklog added to {args.issue}: {args.time}")


def cmd_worklog_list(args):
    """List worklogs on issue."""
    result = api_request("GET", f"issue/{args.issue}/worklog")
    worklogs = result.get("worklogs", [])
    total = result.get("total", 0)

    print(f"  {total} worklogs on {args.issue}\n")
    for w in worklogs:
        author = w.get("author", {}).get("displayName", "Unknown")
        started = w.get("started", "")[:10]
        time_spent = w.get("timeSpent", "")
        print(f"  [{started}] {author}: {time_spent}")


def cmd_user_search(args):
    """Search for users."""
    params = urllib.parse.urlencode({"query": args.query, "maxResults": args.limit})
    result = api_request("GET", f"user/search?{params}")

    print(f"  Users matching '{args.query}':\n")
    for u in result:
        name = u.get("displayName", "")
        email = u.get("emailAddress", "")
        account_id = u.get("accountId", "")
        active = "Active" if u.get("active") else "Inactive"
        print(f"  {name:<30} {email:<35} {active:<10} {account_id}")


def cmd_link(args):
    """Link two issues."""
    data = {
        "type": {"name": args.type},
        "inwardIssue": {"key": args.inward},
        "outwardIssue": {"key": args.outward},
    }
    api_request("POST", "issueLink", data)
    print(f"✅ Linked {args.inward} ←[{args.type}]→ {args.outward}")


def cmd_sprint(args):
    """List issues in current sprint."""
    # Get board sprints
    params = urllib.parse.urlencode({"state": "active"})
    result = api_request("GET", f"board/{args.board}/sprint?{params}")
    sprints = result.get("values", [])

    if not sprints:
        print("  No active sprint found")
        return

    sprint = sprints[0]
    print(f"  Sprint: {sprint['name']} (ID: {sprint['id']})\n")

    # Get sprint issues
    sprint_issues = api_request("GET", f"sprint/{sprint['id']}/issue?maxResults={args.limit}")
    issues = sprint_issues.get("issues", [])

    for issue in issues:
        f = issue["fields"]
        key = issue["key"]
        status = f.get("status", {}).get("name", "")
        summary = f.get("summary", "")
        assignee = f.get("assignee", {})
        aname = assignee.get("displayName", "-") if assignee else "-"
        print(f"  {key:<10} {status:<15} {aname:<20} {summary[:50]}")


def cmd_open(args):
    """Print browser URL for issue."""
    url = f"{BASE_URL}/browse/{args.issue}"
    print(url)
    os.system(f"open '{url}' 2>/dev/null || xdg-open '{url}' 2>/dev/null || echo '{url}'")


def main():
    parser = argparse.ArgumentParser(description="Jira REST API client")
    sub = parser.add_subparsers(dest="command", help="Commands")

    # view
    p = sub.add_parser("view", help="View issue details")
    p.add_argument("issue", help="Issue key (e.g. NX-1234)")

    # list
    p = sub.add_parser("list", help="List issues")
    p.add_argument("-q", "--jql", help="JQL query")
    p.add_argument("-l", "--limit", type=int, default=20, help="Max results")

    # create
    p = sub.add_parser("create", help="Create issue")
    p.add_argument("-s", "--summary", required=True, help="Summary")
    p.add_argument("-t", "--type", default="Task", help="Issue type")
    p.add_argument("-b", "--body", help="Description")
    p.add_argument("-p", "--project", help="Project key")
    p.add_argument("--priority", help="Priority name")
    p.add_argument("--assignee", help="Assignee account ID")
    p.add_argument("--labels", nargs="+", help="Labels")

    # edit
    p = sub.add_parser("edit", help="Edit issue")
    p.add_argument("issue", help="Issue key")
    p.add_argument("-s", "--summary", help="New summary")
    p.add_argument("--priority", help="Priority")
    p.add_argument("--assignee", help="Assignee account ID")
    p.add_argument("--labels", nargs="+", help="Labels")

    # move
    p = sub.add_parser("move", help="Transition issue")
    p.add_argument("issue", help="Issue key")
    p.add_argument("status", help="Target status name")

    # comment add
    p = sub.add_parser("comment-add", help="Add comment")
    p.add_argument("issue", help="Issue key")
    p.add_argument("body", help="Comment body")

    # comment list
    p = sub.add_parser("comment-list", help="List comments")
    p.add_argument("issue", help="Issue key")
    p.add_argument("-l", "--limit", type=int, default=10, help="Max results")

    # comment-edit
    p = sub.add_parser("comment-edit", help="Edit comment")
    p.add_argument("issue", help="Issue key")
    p.add_argument("comment_id", help="Comment ID (from comment-list)")
    p.add_argument("body", help="New comment body")

    # comment-delete
    p = sub.add_parser("comment-delete", help="Delete comment")
    p.add_argument("issue", help="Issue key")
    p.add_argument("comment_id", help="Comment ID")

    # attach
    p = sub.add_parser("attach", help="Add attachments")
    p.add_argument("issue", help="Issue key")
    p.add_argument("files", nargs="+", help="File paths to attach")

    # transitions
    p = sub.add_parser("transitions", help="List available transitions")
    p.add_argument("issue", help="Issue key")

    # search
    p = sub.add_parser("search", help="Search issues by text")
    p.add_argument("query", help="Search text")
    p.add_argument("-p", "--project", help="Project key")
    p.add_argument("-l", "--limit", type=int, default=20, help="Max results")

    # assign
    p = sub.add_parser("assign", help="Assign issue")
    p.add_argument("issue", help="Issue key")
    p.add_argument("user", help="Account ID, 'me', or 'none'")

    # delete
    p = sub.add_parser("delete", help="Delete issue")
    p.add_argument("issue", help="Issue key")

    # worklog-add
    p = sub.add_parser("worklog-add", help="Add worklog")
    p.add_argument("issue", help="Issue key")
    p.add_argument("time", help="Time spent (e.g. '2h', '30m', '1d')")
    p.add_argument("-c", "--comment", help="Worklog comment")

    # worklog-list
    p = sub.add_parser("worklog-list", help="List worklogs")
    p.add_argument("issue", help="Issue key")

    # user-search
    p = sub.add_parser("user-search", help="Search users")
    p.add_argument("query", help="Search query")
    p.add_argument("-l", "--limit", type=int, default=10, help="Max results")

    # link
    p = sub.add_parser("link", help="Link two issues")
    p.add_argument("inward", help="Inward issue key")
    p.add_argument("outward", help="Outward issue key")
    p.add_argument("-t", "--type", default="Relates", help="Link type (Relates, Blocks, Clones, etc.)")

    # sprint
    p = sub.add_parser("sprint", help="List current sprint issues")
    p.add_argument("board", help="Board ID")
    p.add_argument("-l", "--limit", type=int, default=50, help="Max results")

    # open
    p = sub.add_parser("open", help="Open issue in browser")
    p.add_argument("issue", help="Issue key")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    if not BASE_URL or not EMAIL or not API_TOKEN:
        print("❌ Missing JIRA_BASE_URL, JIRA_EMAIL, or JIRA_API_TOKEN in .env", file=sys.stderr)
        sys.exit(1)

    cmd_map = {
        "view": cmd_view,
        "list": cmd_list,
        "create": cmd_create,
        "edit": cmd_edit,
        "move": cmd_move,
        "comment-add": cmd_comment_add,
        "comment-edit": cmd_comment_edit,
        "comment-delete": cmd_comment_delete,
        "comment-list": cmd_comment_list,
        "attach": cmd_attach,
        "transitions": cmd_transitions,
        "search": cmd_search,
        "assign": cmd_assign,
        "delete": cmd_delete,
        "worklog-add": cmd_worklog_add,
        "worklog-list": cmd_worklog_list,
        "user-search": cmd_user_search,
        "link": cmd_link,
        "sprint": cmd_sprint,
        "open": cmd_open,
    }

    cmd_map[args.command](args)


if __name__ == "__main__":
    main()
