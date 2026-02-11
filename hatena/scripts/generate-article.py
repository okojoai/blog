"""arXiv 論文から Hatena Blog 記事を自動生成するスクリプト.

Usage:
    python generate-article.py --category cs.CV --output /tmp/article.md
    python generate-article.py --category cs.AI --entries-dir ../entries --drafts-dir ../draft_entries
"""

from __future__ import annotations

import argparse
import json
import os
import random
import sys
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from typing import TypedDict
from urllib.error import HTTPError
from urllib.request import Request, urlopen

ARXIV_API_URL = "https://export.arxiv.org/api/query"
ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"
CLAUDE_MODEL = "claude-sonnet-4-5-20250929"
SCORING_MODEL = "claude-haiku-4-5-20251001"
MAX_TOKENS = 8192
FETCH_COUNT = 20

# arXiv Atom namespace
ATOM_NS = "{http://www.w3.org/2005/Atom}"
ARXIV_NS = "{http://arxiv.org/schemas/atom}"

# 曜日別カテゴリマッピング (0=月, 4=金)
WEEKDAY_CATEGORIES: dict[int, list[str]] = {
    0: ["cs.CV"],
    1: ["cs.CV"],
    2: ["cs.AI"],
    3: ["cs.LG"],
    4: ["cs.CV", "cs.AI", "cs.LG", "cs.CL"],
}


class Paper(TypedDict):
    """arXiv 論文のメタ情報."""

    arxiv_id: str
    title: str
    authors: list[str]
    abstract: str
    categories: list[str]
    published: str
    url: str
    pdf_url: str


def fetch_arxiv_papers(category: str, max_results: int = 10) -> list[Paper]:
    """arXiv API から最新論文を取得する.

    Args:
        category: arXiv カテゴリ (e.g., "cs.CV")
        max_results: 取得する最大件数

    Returns:
        論文のリスト（新しい順）
    """
    query = f"cat:{category}"
    params = (
        f"search_query={query}"
        f"&sortBy=submittedDate"
        f"&sortOrder=descending"
        f"&max_results={max_results}"
    )
    url = f"{ARXIV_API_URL}?{params}"

    req = Request(url)
    with urlopen(req, timeout=30) as resp:
        xml_data = resp.read()

    root = ET.fromstring(xml_data)
    papers: list[Paper] = []

    for entry in root.findall(f"{ATOM_NS}entry"):
        arxiv_id_full = entry.findtext(f"{ATOM_NS}id", "")
        arxiv_id = arxiv_id_full.split("/abs/")[-1] if "/abs/" in arxiv_id_full else arxiv_id_full

        title_text = entry.findtext(f"{ATOM_NS}title", "")
        title = " ".join(title_text.split())

        authors = [
            author.findtext(f"{ATOM_NS}name", "")
            for author in entry.findall(f"{ATOM_NS}author")
        ]

        abstract_text = entry.findtext(f"{ATOM_NS}summary", "")
        abstract = " ".join(abstract_text.split())

        categories = [
            cat.get("term", "")
            for cat in entry.findall(f"{ATOM_NS}category")
        ]

        published = entry.findtext(f"{ATOM_NS}published", "")

        pdf_url = ""
        for link in entry.findall(f"{ATOM_NS}link"):
            if link.get("title") == "pdf":
                pdf_url = link.get("href", "")

        papers.append(
            Paper(
                arxiv_id=arxiv_id,
                title=title,
                authors=authors,
                abstract=abstract,
                categories=categories,
                published=published,
                url=f"https://arxiv.org/abs/{arxiv_id}",
                pdf_url=pdf_url or f"https://arxiv.org/pdf/{arxiv_id}",
            )
        )

    return papers


def find_existing_arxiv_ids(entries_dir: Path, drafts_dir: Path) -> set[str]:
    """既存の記事から arXiv ID を抽出して重複チェック用のセットを返す.

    Args:
        entries_dir: 公開記事ディレクトリ
        drafts_dir: 下書きディレクトリ

    Returns:
        既に記事化済みの arXiv ID のセット
    """
    existing_ids: set[str] = set()

    for directory in [entries_dir, drafts_dir]:
        if not directory.exists():
            continue
        for md_file in directory.rglob("*.md"):
            content = md_file.read_text(encoding="utf-8")
            # arXiv URL パターンから ID を抽出
            for line in content.splitlines():
                if "arxiv.org/abs/" in line:
                    # https://arxiv.org/abs/2401.12345 or similar
                    parts = line.split("arxiv.org/abs/")
                    if len(parts) > 1:
                        aid = parts[1].split(")")[0].split("]")[0].split(" ")[0].strip()
                        if aid:
                            existing_ids.add(aid)

    return existing_ids


SCORING_PROMPT = """\
You are an expert tech blog editor at an AI/CV startup.
Score each paper on how suitable it is for an engaging, insightful tech blog post.

Scoring criteria (each 1-10):
- **novelty**: How novel and groundbreaking is the approach?
- **practical**: How useful is this for engineers in production? (edge deployment, real datasets, etc.)
- **excitement**: How likely are engineers to share this and say "this is cool"?

Return ONLY a JSON array (no markdown fences) with objects containing:
- "index": the paper's index number (0-based)
- "novelty": score 1-10
- "practical": score 1-10
- "excitement": score 1-10
- "total": sum of the three scores
- "reason": one-sentence explanation in Japanese

Papers:
"""


def _call_claude_api(
    api_key: str,
    model: str,
    user_message: str,
    max_tokens: int,
) -> str:
    """Claude API を呼び出してテキストレスポンスを返す.

    Args:
        api_key: Anthropic API キー
        model: モデル名
        user_message: ユーザーメッセージ
        max_tokens: 最大トークン数

    Returns:
        レスポンステキスト
    """
    payload = json.dumps({
        "model": model,
        "max_tokens": max_tokens,
        "messages": [
            {"role": "user", "content": user_message},
        ],
    }).encode("utf-8")

    req = Request(
        ANTHROPIC_API_URL,
        data=payload,
        headers={
            "Content-Type": "application/json",
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
        },
        method="POST",
    )

    with urlopen(req, timeout=120) as resp:
        result = json.loads(resp.read())

    if result.get("type") == "error":
        error_msg = result.get("error", {}).get("message", "Unknown error")
        raise RuntimeError(f"Claude API error: {error_msg}")

    content_blocks = result.get("content", [])
    text_parts = [block["text"] for block in content_blocks if block.get("type") == "text"]
    text = "\n".join(text_parts)

    if not text.strip():
        raise RuntimeError("Claude API returned empty content")

    return text


def score_papers(papers: list[Paper], api_key: str) -> list[dict[str, int | str]]:
    """Claude API で論文リストをスコアリングし、スコア順にソートして返す.

    Args:
        papers: スコアリング対象の論文リスト
        api_key: Anthropic API キー

    Returns:
        スコア情報のリスト（total降順）
    """
    paper_summaries = []
    for i, p in enumerate(papers):
        paper_summaries.append(
            f"[{i}] {p['title']}\n"
            f"    Categories: {', '.join(p['categories'])}\n"
            f"    Abstract: {p['abstract'][:500]}"
        )

    user_message = SCORING_PROMPT + "\n\n".join(paper_summaries)

    print(f"Scoring {len(papers)} papers with {SCORING_MODEL}...")
    raw = _call_claude_api(api_key, SCORING_MODEL, user_message, max_tokens=4096)

    # JSON 配列をパース（マークダウンフェンスが付いている場合も対処）
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("\n", 1)[1]
        cleaned = cleaned.rsplit("```", 1)[0]

    scores: list[dict[str, int | str]] = json.loads(cleaned)
    scores.sort(key=lambda s: s.get("total", 0), reverse=True)
    return scores


def generate_article_with_claude(
    paper: Paper,
    prompt_template: str,
    api_key: str,
    related_papers: list[Paper] | None = None,
) -> str:
    """Claude API を使って論文レビュー記事を生成する.

    Args:
        paper: 論文メタ情報
        prompt_template: プロンプトテンプレート
        api_key: Anthropic API キー
        related_papers: 比較表で参照可能な関連論文リスト

    Returns:
        生成された記事本文（Markdown）
    """
    paper_info = (
        f"**Title**: {paper['title']}\n"
        f"**Authors**: {', '.join(paper['authors'])}\n"
        f"**arXiv ID**: {paper['arxiv_id']}\n"
        f"**Categories**: {', '.join(paper['categories'])}\n"
        f"**Published**: {paper['published']}\n"
        f"**URL**: {paper['url']}\n"
        f"**PDF**: {paper['pdf_url']}\n\n"
        f"**Abstract**:\n{paper['abstract']}"
    )

    related_section = ""
    if related_papers:
        lines = ["\n\n# Related Papers (use these for comparison table)"]
        for rp in related_papers:
            lines.append(
                f"- [{rp['title']}]({rp['url']}) "
                f"({', '.join(rp['categories'][:3])}): "
                f"{rp['abstract'][:200]}..."
            )
        related_section = "\n".join(lines)

    user_message = f"{prompt_template}\n{paper_info}{related_section}"
    return _call_claude_api(api_key, CLAUDE_MODEL, user_message, MAX_TOKENS)


def build_frontmatter(paper: Paper, category_label: str) -> str:
    """はてなブログ用の frontmatter を生成する.

    Args:
        paper: 論文メタ情報
        category_label: メインカテゴリラベル

    Returns:
        YAML frontmatter 文字列
    """
    # タイトルから日本語記事タイトルを構築
    title = f"【論文読み】{paper['title']}"
    categories = ["論文読み", category_label]

    # カテゴリ行の構築
    cat_lines = "\n".join(f"- {c}" for c in categories)

    return f"""---
Title: "{title}"
Category:
{cat_lines}
Draft: true
---"""


def build_footer(paper: Paper) -> str:
    """記事のフッター（原論文リンク）を生成する.

    Args:
        paper: 論文メタ情報

    Returns:
        フッター文字列
    """
    return (
        "\n---\n"
        f"> **原論文**: [{paper['title']}]({paper['url']})\n"
    )


def get_category_for_today(override: str | None = None) -> str:
    """今日の曜日に基づいてカテゴリを返す.

    Args:
        override: 指定された場合はそのカテゴリを使用

    Returns:
        arXiv カテゴリ文字列
    """
    if override:
        return override

    weekday = datetime.now(tz=timezone.utc).weekday()
    candidates = WEEKDAY_CATEGORIES.get(weekday, ["cs.CV"])
    return random.choice(candidates)


CATEGORY_LABELS: dict[str, str] = {
    "cs.CV": "Computer Vision",
    "cs.AI": "Artificial Intelligence",
    "cs.LG": "Machine Learning",
    "cs.CL": "Natural Language Processing",
}


def main() -> None:
    """メインエントリーポイント."""
    parser = argparse.ArgumentParser(description="Generate a blog article from an arXiv paper")
    parser.add_argument("--category", type=str, default=None, help="arXiv category (default: auto by weekday)")
    parser.add_argument("--output", type=str, required=True, help="Output markdown file path")
    parser.add_argument("--prompt-file", type=str, default=None, help="Path to prompt template file")
    parser.add_argument("--entries-dir", type=str, default=None, help="Published entries directory")
    parser.add_argument("--drafts-dir", type=str, default=None, help="Draft entries directory")
    parser.add_argument("--metadata-file", type=str, default=None, help="Write metadata (arxiv_id, title, category) for CI")
    args = parser.parse_args()

    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        print("Error: ANTHROPIC_API_KEY is required", file=sys.stderr)
        sys.exit(1)

    # プロンプトテンプレートの読み込み
    script_dir = Path(__file__).parent
    prompt_path = Path(args.prompt_file) if args.prompt_file else script_dir.parent / "prompts" / "arxiv-review.md"
    prompt_template = prompt_path.read_text(encoding="utf-8")

    # カテゴリ選定
    category = get_category_for_today(args.category)
    category_label = CATEGORY_LABELS.get(category, category)
    print(f"Category: {category} ({category_label})")

    # arXiv から論文取得（20件）
    print("Fetching papers from arXiv...")
    try:
        papers = fetch_arxiv_papers(category, max_results=FETCH_COUNT)
    except HTTPError as e:
        print(f"Error fetching from arXiv: {e}", file=sys.stderr)
        sys.exit(1)

    if not papers:
        print("No papers found", file=sys.stderr)
        sys.exit(1)

    print(f"Found {len(papers)} papers")

    # 既存記事の arXiv ID を取得して重複排除
    entries_dir = Path(args.entries_dir) if args.entries_dir else script_dir.parent / "entries"
    drafts_dir = Path(args.drafts_dir) if args.drafts_dir else script_dir.parent / "draft_entries"
    existing_ids = find_existing_arxiv_ids(entries_dir, drafts_dir)

    if existing_ids:
        print(f"Excluding {len(existing_ids)} already-covered papers")

    candidates = [p for p in papers if p["arxiv_id"] not in existing_ids]
    if not candidates:
        print("All recent papers have already been covered", file=sys.stderr)
        sys.exit(1)

    # Claude でスコアリングし、最もスコアの高い論文を選定
    try:
        scores = score_papers(candidates, api_key)
    except (HTTPError, RuntimeError, json.JSONDecodeError) as e:
        print(f"Scoring failed, falling back to latest paper: {e}", file=sys.stderr)
        scores = [{"index": 0, "total": 0, "reason": "fallback"}]

    best = scores[0]
    best_index = int(best.get("index", 0))
    if best_index < 0 or best_index >= len(candidates):
        best_index = 0

    paper = candidates[best_index]
    score_total = best.get("total", "?")
    score_reason = best.get("reason", "")
    print(f"Selected (score={score_total}): {paper['title']} ({paper['arxiv_id']})")
    if score_reason:
        print(f"  Reason: {score_reason}")

    # 関連論文 = 選定された論文以外の候補
    related_papers = [p for p in candidates if p["arxiv_id"] != paper["arxiv_id"]]

    # Claude API で記事生成
    print(f"Generating article with {len(related_papers)} related papers as context...")
    try:
        article_body = generate_article_with_claude(
            paper, prompt_template, api_key, related_papers=related_papers,
        )
    except HTTPError as e:
        print(f"Error calling Claude API: {e}", file=sys.stderr)
        sys.exit(1)

    # 記事の組み立て
    footer = build_footer(paper)
    body_only = f"{article_body}\n{footer}"
    frontmatter = build_frontmatter(paper, category_label)
    full_article = f"{frontmatter}\n\n{body_only}"

    # blogsync 用: 本文のみ（frontmatter なし）
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(body_only, encoding="utf-8")
    print(f"Body written to: {output_path}")

    # git コミット用: frontmatter 付き完全版
    full_path = output_path.with_suffix(".full.md")
    full_path.write_text(full_article, encoding="utf-8")
    print(f"Full article written to: {full_path}")

    # メタデータ出力（CI 用）
    if args.metadata_file:
        meta_path = Path(args.metadata_file)
        meta_path.write_text(
            f"arxiv_id={paper['arxiv_id']}\n"
            f"title={paper['title']}\n"
            f"category={category}\n"
            f"score={score_total}\n",
            encoding="utf-8",
        )
        print(f"Metadata written to: {meta_path}")


if __name__ == "__main__":
    main()
