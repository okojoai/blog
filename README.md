# okojoai/blog

Multi-platform blog article management repository. Articles are managed in Git, reviewed via Pull Requests, and automatically published to each platform on merge.

## Supported Platforms

| Platform | Status | Publishing Method |
|---|---|---|
| [Hatena Blog](https://tech-blog.okojo.ai) | Active | Auto-publish via GitHub Actions (blogsync + AtomPub API) |
| Zenn | Planned | GitHub integration |
| WordPress | Planned | REST API |
| note | Planned | Manual (no public API) |

## Repository Structure

```
blog/
├── hatena/                           # Hatena Blog
│   ├── entries/                      #   Published articles
│   │   └── tech-blog.okojo.ai/      #     Organized by blog domain
│   ├── draft_entries/                #   Draft articles
│   ├── blogsync.yaml                 #   blogsync configuration
│   └── draft.template                #   Template for new drafts
├── .github/
│   ├── workflows/                    # CI/CD workflows
│   │   ├── hatena-initialize.yaml    #   Initial sync from Hatena Blog
│   │   ├── hatena-create-draft.yaml  #   Create new draft → PR
│   │   ├── hatena-push.yaml          #   Publish on PR merge
│   │   ├── hatena-push-draft.yaml    #   Sync draft on PR merge
│   │   ├── hatena-push-when-publishing.yaml  # Draft → Published
│   │   ├── hatena-pull.yaml          #   Pull published entries
│   │   └── hatena-pull-draft.yaml    #   Pull specific draft
│   ├── CODEOWNERS                    # Review assignment
│   └── PULL_REQUEST_TEMPLATE/
│       └── draft.md                  # PR template for drafts
├── CONTRIBUTING.md                   # Contribution guidelines
└── .gitignore
```

## Quick Start for Contributors

### 1. Create a New Article

Go to **Actions** tab > **[hatena] create draft** > **Run workflow** and enter the article title.

A draft PR will be created automatically.

### 2. Write the Article

Edit the Markdown file in the PR branch. Articles use YAML frontmatter:

```markdown
---
Title: Your Article Title
Category:
- tech
- python
Draft: true
---

Article body in Markdown...
```

### 3. Request Review

Push your changes and request a review from @okojoalg.

### 4. Publish

After approval, remove `Draft: true` from the frontmatter and merge the PR. The article will be published automatically.

## Workflow Reference

### Automatic Triggers (on PR merge to main)

| Workflow | Trigger Path | Action |
|---|---|---|
| `hatena-push` | `hatena/entries/**` | Push changes to Hatena Blog |
| `hatena-push-draft` | `hatena/draft_entries/**` | Sync draft changes to Hatena Blog |
| `hatena-push-when-publishing` | `hatena/draft_entries/**` | Publish draft (when `Draft: true` is removed) |

### Manual Triggers (workflow_dispatch)

| Workflow | Input | Action |
|---|---|---|
| `hatena-initialize` | `is_draft_included` (bool) | Sync all existing articles from Hatena Blog |
| `hatena-create-draft` | `title` (string) | Create a new draft and open a PR |
| `hatena-pull` | - | Pull published articles from Hatena Blog |
| `hatena-pull-draft` | `title` (string) | Pull a specific draft by title |

### Skip Publishing

Add the `skip-push` label to a PR to prevent auto-publishing on merge. Useful for syncing from Hatena Blog without round-tripping.

## Branch Protection Rules

| Rule | Setting |
|---|---|
| PR required | All users (no bypass, including admins) |
| Review required | 1 approval from CODEOWNERS (@okojoalg) |
| Stale review dismissal | Enabled (new push invalidates approval) |
| Branch deletion | Blocked |
| Force push | Blocked |

## For Administrators

### Initial Setup

The following GitHub settings are required:

**Repository Variables** (Settings > Secrets and variables > Actions > Variables):

| Variable | Value |
|---|---|
| `BLOG_DOMAIN` | `tech-blog.okojo.ai` |

**Repository Secrets** (Settings > Secrets and variables > Actions > Secrets):

| Secret | Source |
|---|---|
| `OWNER_API_KEY` | Hatena Blog > Settings > Advanced > AtomPub |

**Other Settings**:
- Actions > General > Workflow permissions: **Read and write permissions**
- Actions > General > Allow GitHub Actions to create and approve pull requests: **Enabled**
- General > Pull Requests > Allow auto-merge: **Enabled**

### Adding a New Platform

1. Create a new directory at the repository root (e.g., `zenn/`, `wordpress/`)
2. Add platform-specific workflows in `.github/workflows/` with prefix (e.g., `zenn-*.yaml`)
3. Add necessary secrets/variables for the platform's API
4. Update `CONTRIBUTING.md` with the platform's article format and workflow
5. Workflow path triggers should scope to the platform directory (e.g., `zenn/**`)

### blogsync Configuration

`hatena/blogsync.yaml` maps the blog domain to the Hatena account:

```yaml
tech-blog.okojo.ai:
  username: okojoai
default:
  local_root: entries
```

Workflows run with `working-directory: hatena`, so `local_root: entries` resolves to `hatena/entries/`.

## Images

Image files are blocked by `.gitignore`. Use external hosting:

- **Hatena Blog**: Upload to [Hatena Fotolife](https://f.hatena.ne.jp/)
- Reference via URL: `![alt text](https://cdn-ak.f.st-hatena.com/...)`

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for detailed guidelines on article format, review criteria, and branch naming conventions.
