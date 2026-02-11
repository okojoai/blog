# okojoai/blog

マルチプラットフォーム対応のブログ記事管理リポジトリ。記事を Git で管理し、Pull Request でレビュー後、マージ時に各プラットフォームへ自動投稿します。

## 対応プラットフォーム

| プラットフォーム | ステータス | 投稿方法 |
|---|---|---|
| [Hatena Blog](https://tech-blog.okojo.ai) | 稼働中 | GitHub Actions で自動投稿（blogsync + AtomPub API） |
| Zenn | 予定 | GitHub 連携 |
| WordPress | 予定 | REST API |
| note | 予定 | 手動（公開 API なし） |

## リポジトリ構成

```
blog/
├── hatena/                           # はてなブログ
│   ├── entries/                      #   公開記事
│   │   └── tech-blog.okojo.ai/      #     ブログドメイン別に整理
│   ├── draft_entries/                #   下書き
│   ├── scripts/                      #   自動化スクリプト
│   │   └── generate-article.py      #     arXiv 論文から記事を自動生成
│   ├── prompts/                      #   プロンプトテンプレート
│   │   └── arxiv-review.md           #     論文レビュー用プロンプト
│   ├── blogsync.yaml                 #   blogsync 設定
│   └── draft.template                #   下書きテンプレート
├── .github/
│   ├── workflows/                    # CI/CD ワークフロー
│   │   ├── hatena-auto-generate.yaml #   arXiv 論文から記事を自動生成（月〜金）
│   │   ├── hatena-initialize.yaml    #   はてなブログから初期同期
│   │   ├── hatena-create-draft.yaml  #   新規下書き作成 → PR
│   │   ├── hatena-push.yaml          #   マージ時に自動投稿
│   │   ├── hatena-push-draft.yaml    #   マージ時に下書き同期
│   │   ├── hatena-push-when-publishing.yaml  # 下書き → 公開
│   │   ├── hatena-pull.yaml          #   公開記事を取得
│   │   └── hatena-pull-draft.yaml    #   特定の下書きを取得
│   ├── CODEOWNERS                    # レビュー担当の割り当て
│   └── PULL_REQUEST_TEMPLATE/
│       └── draft.md                  # 下書き PR 用テンプレート
├── CONTRIBUTING.md                   # 投稿ガイドライン
└── .gitignore
```

## 寄稿者向けクイックスタート

### 1. 新しい記事を作成する

**Actions** タブ > **[hatena] create draft** > **Run workflow** でタイトルを入力。

Draft PR が自動作成されます。

### 2. 記事を書く

PR ブランチで Markdown ファイルを編集します。YAML フロントマター形式：

```markdown
---
Title: 記事タイトル
Category:
- tech
- python
Draft: true
---

記事本文を Markdown で記述...
```

### 3. レビューを依頼する

変更をプッシュし、@okojoalg にレビューを依頼してください。

### 4. 公開する

承認後、フロントマターから `Draft: true` を削除してマージすると、自動的にはてなブログに公開されます。

## ワークフロー一覧

### 自動トリガー（main への PR マージ時）

| ワークフロー | トリガーパス | 動作 |
|---|---|---|
| `hatena-push` | `hatena/entries/**` | はてなブログに変更を反映 |
| `hatena-push-draft` | `hatena/draft_entries/**` | 下書きの変更をはてなブログに同期 |
| `hatena-push-when-publishing` | `hatena/draft_entries/**` | 下書きを公開（`Draft: true` 削除時） |

### スケジュール実行

| ワークフロー | スケジュール | 動作 |
|---|---|---|
| `hatena-auto-generate` | 月〜金 AM 10:00 JST | arXiv 論文から記事を自動生成して PR 作成 |

### 手動トリガー（workflow_dispatch）

| ワークフロー | 入力 | 動作 |
|---|---|---|
| `hatena-initialize` | `is_draft_included` (bool) | はてなブログの既存記事を一括同期 |
| `hatena-create-draft` | `title` (string) | 新規下書きを作成して PR を開く |
| `hatena-pull` | - | はてなブログから公開記事を取得 |
| `hatena-pull-draft` | `title` (string) | タイトルで特定の下書きを取得 |
| `hatena-auto-generate` | `category` (string, 任意) | arXiv カテゴリを指定して記事生成 |

### 投稿のスキップ

PR に `skip-push` ラベルを付けると、マージ時の自動投稿をスキップします。はてなブログからの同期 PR で往復投稿を防ぐために使います。

## ブランチ保護ルール

| ルール | 設定 |
|---|---|
| PR 必須 | 全ユーザー対象（管理者含むバイパスなし） |
| レビュー必須 | CODEOWNERS（@okojoalg）の承認 1 件以上 |
| stale レビューの自動却下 | 有効（新しいプッシュで承認が無効化） |
| ブランチ削除禁止 | 有効 |
| Force push 禁止 | 有効 |

## 管理者向け

### 初期セットアップ

以下の GitHub 設定が必要です：

**Repository Variables**（Settings > Secrets and variables > Actions > Variables）：

| 変数名 | 値 |
|---|---|
| `BLOG_DOMAIN` | `tech-blog.okojo.ai` |

**Repository Secrets**（Settings > Secrets and variables > Actions > Secrets）：

| シークレット | 取得元 |
|---|---|
| `OWNER_API_KEY` | はてなブログ > 設定 > 詳細設定 > AtomPub |
| `ANTHROPIC_API_KEY` | [Anthropic Console](https://console.anthropic.com/) |

**その他の設定**：
- Actions > General > Workflow permissions: **Read and write permissions**
- Actions > General > Allow GitHub Actions to create and approve pull requests: **有効**
- General > Pull Requests > Allow auto-merge: **有効**

### 新しいプラットフォームの追加

1. リポジトリルートに新しいディレクトリを作成（例: `zenn/`, `wordpress/`）
2. `.github/workflows/` にプレフィックス付きワークフローを追加（例: `zenn-*.yaml`）
3. プラットフォームの API 用シークレット/変数を追加
4. `CONTRIBUTING.md` にそのプラットフォームの記事形式とワークフローを追記
5. ワークフローの paths トリガーをプラットフォームディレクトリに限定（例: `zenn/**`）

### blogsync 設定

`hatena/blogsync.yaml` でブログドメインとはてなアカウントを紐付けます：

```yaml
tech-blog.okojo.ai:
  username: okojoai
default:
  local_root: entries
```

ワークフローは `working-directory: hatena` で実行されるため、`local_root: entries` は `hatena/entries/` に解決されます。

## 画像について

画像ファイルは `.gitignore` でブロックされています。外部ホスティングを使用してください：

- **はてなブログ**: [はてなフォトライフ](https://f.hatena.ne.jp/)にアップロード
- Markdown での参照: `![代替テキスト](https://cdn-ak.f.st-hatena.com/...)`

## 投稿ガイドライン

記事のフォーマット、レビュー基準、ブランチ命名規則の詳細は [CONTRIBUTING.md](CONTRIBUTING.md) を参照してください。
