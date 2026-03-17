# Jira REST API v3 Reference

Swagger: https://dac-static.atlassian.com/cloud/jira/platform/swagger-v3.v3.json
Docs: https://developer.atlassian.com/cloud/jira/platform/rest/v3/

## Implemented

| Command | Endpoint | Method |
|---------|----------|--------|
| view | `/rest/api/3/issue/{key}` | GET |
| list | `/rest/api/3/search/jql` | GET |
| search | `/rest/api/3/search/jql` | GET |
| create | `/rest/api/3/issue` | POST |
| edit | `/rest/api/3/issue/{key}` | PUT |
| delete | `/rest/api/3/issue/{key}` | DELETE |
| move | `/rest/api/3/issue/{key}/transitions` | POST |
| transitions | `/rest/api/3/issue/{key}/transitions` | GET |
| comment-add | `/rest/api/3/issue/{key}/comment` | POST |
| comment-list | `/rest/api/3/issue/{key}/comment` | GET |
| attach | `/rest/api/3/issue/{key}/attachments` | POST |
| assign | `/rest/api/3/issue/{key}/assignee` | PUT |
| worklog-add | `/rest/api/3/issue/{key}/worklog` | POST |
| worklog-list | `/rest/api/3/issue/{key}/worklog` | GET |
| user-search | `/rest/api/3/user/search` | GET |
| link | `/rest/api/3/issueLink` | POST |
| sprint | `/rest/api/3/board/{id}/sprint` + `/rest/api/3/sprint/{id}/issue` | GET |

## Not Yet Implemented (add as needed)

- `DELETE /rest/api/3/attachment/{id}` — Delete attachment
- `PUT /rest/api/3/issue/{key}/comment/{id}` — Update comment
- `DELETE /rest/api/3/issue/{key}/comment/{id}` — Delete comment
- `PUT /rest/api/3/issue/{key}/worklog/{id}` — Update worklog
- `GET /rest/api/3/project` — List projects
- `GET /rest/api/3/priority` — List priorities
- `GET /rest/api/3/status` — List statuses
- `GET /rest/api/3/issuetype` — List issue types
- `GET /rest/api/3/board` — List boards
- `POST /rest/api/3/issue/{key}/watchers` — Add watcher
- `GET /rest/api/3/filter` — List saved filters
- `POST /rest/api/3/issues/bulk` — Bulk fetch issues
