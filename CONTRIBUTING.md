# Contributing Guide

## Overview

This repository manages blog articles for multiple platforms.
Each platform has its own directory under the repository root.

```
blog/
├── hatena/          # Hatena Blog
│   ├── entries/     # Published articles
│   ├── draft_entries/ # Drafts
│   ├── blogsync.yaml
│   └── draft.template
├── zenn/            # (future)
├── wordpress/       # (future)
└── note/            # (future)
```

All articles go through a PR-based review flow before publishing.

## Posting Flow (Hatena Blog)

```
1. GitHub Actions > "[hatena] create draft" to create a new draft
2. A PR is automatically created with the draft
3. Edit the article in the PR branch
4. Request review from the repository owner (@okojoalg)
5. Remove "Draft: true" from frontmatter when ready to publish
6. Merge the PR after approval
7. The article is automatically published to Hatena Blog
```

## Branch Naming

Use the following format:

```
article/<platform>/<short-description>
```

Examples:
- `article/hatena/setup-guide`
- `article/hatena/python-tips`

## Article Format (Hatena Blog)

Articles use Markdown with YAML frontmatter:

```markdown
---
Title: Article title here
Category:
- category1
- category2
Draft: true
---

Article body in Markdown...
```

### Required Fields

| Field | Description |
|---|---|
| `Title` | Article title (required) |
| `Draft` | `true` for draft, remove to publish |

### Optional Fields

| Field | Description |
|---|---|
| `Category` | List of categories |
| `CustomPath` | Custom URL path |

## Images

- **Do NOT commit image files** to this repository (blocked by `.gitignore`)
- Upload images to Hatena Fotolife or external hosting services
- Reference images by URL in Markdown: `![alt](https://example.com/image.png)`

## Review Criteria

Reviewers will check the following before approving:

- [ ] Title is clear and descriptive
- [ ] Categories are set appropriately
- [ ] No typos or grammatical errors
- [ ] Images use external URLs (no local file references)
- [ ] Links are valid and accessible
- [ ] Code blocks have language specifiers
- [ ] Content is accurate and well-structured

## Pulling Existing Articles

To sync published articles from Hatena Blog to this repository:

1. Run `[hatena] pull published entries` from Actions tab
2. A PR will be created with updated articles
3. Merge the PR (this does **not** re-publish to Hatena Blog)

## Notes

- Direct pushes to `main` are not allowed
- All changes require a PR with owner approval
- PRs with the `skip-push` label will not trigger publishing
