#!/usr/bin/env python3

import os
import re
import sys
import argparse
import difflib
from pathlib import Path
from typing import List, Dict, Tuple, Optional, Set
from dataclasses import dataclass, field
from urllib.parse import urlparse, unquote
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError
from collections import defaultdict


@dataclass
class LinkIssue:
    file_path: str
    link_text: str
    link_target: str
    issue_type: str
    suggestion: Optional[str] = None
    auto_fix: bool = False


@dataclass
class FileChange:
    file_path: str
    original_content: str
    new_content: str
    issues_fixed: List[str] = field(default_factory=list)
    links_validated: int = 0
    links_fixed: int = 0


@dataclass
class VaultIndex:
    files_by_name: Dict[str, List[str]] = field(
        default_factory=lambda: defaultdict(list)
    )
    headings_by_file: Dict[str, List[Tuple[str, str]]] = field(default_factory=dict)
    all_files: Set[str] = field(default_factory=set)


class MarkdownFormatter:
    def __init__(self, base_dir: str, flags: Dict[str, bool]):
        self.base_dir = Path(base_dir)
        self.flags = flags
        self.vault_index = None
        self.url_cache = {}

    def collect_targets(self, paths: List[str]) -> List[Path]:
        targets = []
        for path_str in paths:
            path = (
                self.base_dir / path_str
                if not Path(path_str).is_absolute()
                else Path(path_str)
            )

            if path.is_file() and path.suffix == ".md":
                targets.append(path)
            elif path.is_dir():
                targets.extend(self._collect_markdown_files(path))
            else:
                print(f"Warning: {path} not found or not a markdown file")

        return sorted(set(targets))

    def _collect_markdown_files(self, directory: Path) -> List[Path]:
        markdown_files = []
        for root, dirs, files in os.walk(directory):
            dirs[:] = [d for d in dirs if not d.startswith(".") or d == ".claude"]

            for file in files:
                if file.endswith(".md"):
                    markdown_files.append(Path(root) / file)

        return markdown_files

    def build_vault_index(self, files: List[Path]) -> VaultIndex:
        index = VaultIndex()

        for file_path in files:
            rel_path = str(file_path.relative_to(self.base_dir))
            index.all_files.add(rel_path)

            file_name = file_path.stem
            index.files_by_name[file_name].append(rel_path)

            try:
                content = file_path.read_text(encoding="utf-8")
                headings = self._extract_headings(content)
                index.headings_by_file[rel_path] = headings
            except Exception as e:
                print(f"Warning: Could not read {file_path}: {e}")

        return index

    def _extract_headings(self, content: str) -> List[Tuple[str, str]]:
        headings = []
        for line in content.split("\n"):
            match = re.match(r"^(#{1,6})\s+(.+)$", line)
            if match:
                heading_text = match.group(2).strip()
                slug = self._create_slug(heading_text)
                headings.append((heading_text, slug))
        return headings

    def _create_slug(self, text: str) -> str:
        slug = text.lower()
        slug = re.sub(r"[^\w\s-]", "", slug)
        slug = re.sub(r"[-\s]+", "-", slug)
        return slug.strip("-")

    def process_file(self, file_path: Path) -> Optional[FileChange]:
        try:
            original_content = file_path.read_text(encoding="utf-8")
            new_content = original_content
            issues_fixed = []
            links_validated = 0
            links_fixed = 0

            if not self.flags.get("no_format", False):
                new_content, format_issues = self._fix_formatting(new_content)
                issues_fixed.extend(format_issues)

            if not self.flags.get("no_links", False):
                new_content, link_stats = self._validate_and_fix_links(
                    new_content, file_path
                )
                links_validated = link_stats["validated"]
                links_fixed = link_stats["fixed"]
                issues_fixed.extend(link_stats["issues"])

            if new_content != original_content:
                rel_path = str(file_path.relative_to(self.base_dir))
                return FileChange(
                    file_path=rel_path,
                    original_content=original_content,
                    new_content=new_content,
                    issues_fixed=issues_fixed,
                    links_validated=links_validated,
                    links_fixed=links_fixed,
                )

            return None

        except Exception as e:
            print(f"Error processing {file_path}: {e}")
            return None

    def _fix_formatting(self, content: str) -> Tuple[str, List[str]]:
        issues = []
        lines = content.split("\n")
        new_lines = []
        i = 0

        while i < len(lines):
            line = lines[i]

            heading_match = re.match(r"^(#{1,6})(\s*)(.*)$", line)
            if heading_match:
                hashes = heading_match.group(1)
                space = heading_match.group(2)
                text = heading_match.group(3)

                if new_lines and new_lines[-1].strip():
                    new_lines.append("")
                    issues.append("Added blank line before heading")

                if not space or space != " ":
                    line = f"{hashes} {text}"
                    issues.append("Fixed heading spacing")

                new_lines.append(line.rstrip())

                if (
                    i + 1 < len(lines)
                    and lines[i + 1].strip()
                    and not re.match(r"^#{1,6}\s", lines[i + 1])
                ):
                    new_lines.append("")
                    issues.append("Added blank line after heading")

            elif re.match(r"^[\s]*[-*+]\s", line):
                indent_match = re.match(r"^(\s*)[-*+]\s", line)
                if indent_match:
                    indent = indent_match.group(1)
                    if len(indent) % 2 != 0:
                        new_indent = " " * ((len(indent) // 2 + 1) * 2)
                        line = new_indent + line.lstrip()
                        issues.append("Fixed list indentation")

                    line = re.sub(r"^(\s*)[-*+]\s", r"\1- ", line)

                new_lines.append(line.rstrip())

            elif line.startswith("```"):
                new_lines.append(line.rstrip())
                i += 1
                while i < len(lines) and not lines[i].startswith("```"):
                    new_lines.append(lines[i].rstrip())
                    i += 1
                if i < len(lines):
                    new_lines.append(lines[i].rstrip())

            else:
                new_lines.append(line.rstrip())

            i += 1

        while new_lines and not new_lines[-1]:
            new_lines.pop()

        new_lines.append("")

        result = "\n".join(new_lines)

        result = re.sub(r"\n{3,}", "\n\n", result)

        return result, list(set(issues))

    def _validate_and_fix_links(
        self, content: str, file_path: Path
    ) -> Tuple[str, Dict]:
        stats = {"validated": 0, "fixed": 0, "issues": []}

        markdown_link_pattern = r"\[([^\]]+)\]\(([^)]+)\)"
        wikilink_pattern = r"\[\[([^\]]+)\]\]"

        def replace_markdown_link(match):
            text = match.group(1)
            url = match.group(2)
            stats["validated"] += 1

            if url.startswith("http://") or url.startswith("https://"):
                new_url = self._validate_external_url(url)
                if new_url != url:
                    stats["fixed"] += 1
                    stats["issues"].append(f"Updated URL: {url} -> {new_url}")
                    return f"[{text}]({new_url})"

            elif not url.startswith("#"):
                fixed_url = self._validate_internal_link(url, file_path)
                if fixed_url != url:
                    stats["fixed"] += 1
                    stats["issues"].append(f"Fixed internal link: {url} -> {fixed_url}")
                    return f"[{text}]({fixed_url})"

            return match.group(0)

        def replace_wikilink(match):
            link_content = match.group(1)
            stats["validated"] += 1

            if "|" in link_content:
                target, alias = link_content.split("|", 1)
            else:
                target = link_content
                alias = None

            if "#" in target:
                note, heading = target.split("#", 1)
            else:
                note = target
                heading = None

            resolved = self._resolve_wikilink(note.strip(), file_path)
            if resolved and resolved != note.strip():
                stats["fixed"] += 1
                new_target = resolved
                if heading:
                    new_target += f"#{heading}"
                if alias:
                    new_target += f"|{alias}"
                stats["issues"].append(
                    f"Resolved wikilink: [[{link_content}]] -> [[{new_target}]]"
                )
                return f"[[{new_target}]]"

            return match.group(0)

        if not self.flags.get("internal_only", False):
            content = re.sub(markdown_link_pattern, replace_markdown_link, content)

        if not self.flags.get("external_only", False):
            content = re.sub(wikilink_pattern, replace_wikilink, content)

        return content, stats

    def _validate_external_url(self, url: str) -> str:
        if url in self.url_cache:
            return self.url_cache[url]

        try:
            url = url.strip()

            if url.startswith("http://"):
                https_url = url.replace("http://", "https://", 1)
                try:
                    req = Request(
                        https_url, method="HEAD", headers={"User-Agent": "Mozilla/5.0"}
                    )
                    with urlopen(req, timeout=5) as response:
                        if response.status < 400:
                            self.url_cache[url] = https_url
                            return https_url
                except:
                    pass

            req = Request(url, method="HEAD", headers={"User-Agent": "Mozilla/5.0"})
            with urlopen(req, timeout=5) as response:
                final_url = response.geturl()
                if final_url != url:
                    self.url_cache[url] = final_url
                    return final_url

            self.url_cache[url] = url
            return url

        except Exception:
            self.url_cache[url] = url
            return url

    def _validate_internal_link(self, link: str, current_file: Path) -> str:
        link = link.strip()

        if "#" in link:
            file_part, anchor = link.split("#", 1)
        else:
            file_part = link
            anchor = None

        if not file_part:
            return link

        current_dir = current_file.parent
        target_path = (current_dir / file_part).resolve()

        try:
            rel_to_base = target_path.relative_to(self.base_dir)
            if str(rel_to_base) in self.vault_index.all_files:
                return link
        except ValueError:
            pass

        if not file_part.endswith(".md"):
            new_link = file_part + ".md"
            if anchor:
                new_link += f"#{anchor}"
            return new_link

        return link

    def _resolve_wikilink(self, note_name: str, current_file: Path) -> Optional[str]:
        if not self.vault_index:
            return None

        if note_name in self.vault_index.files_by_name:
            matches = self.vault_index.files_by_name[note_name]
            if len(matches) == 1:
                return matches[0].replace(".md", "")

        return None

    def show_diff(self, change: FileChange) -> None:
        print(f"\n{'=' * 80}")
        print(f"File: {change.file_path}")
        print(f"{'=' * 80}")

        if change.issues_fixed:
            print("\nIssues Fixed:")
            for issue in change.issues_fixed:
                print(f"  ✓ {issue}")

        if change.links_validated > 0:
            print(
                f"\nLinks: {change.links_validated} validated, {change.links_fixed} fixed"
            )

        print("\nDiff:")
        diff = difflib.unified_diff(
            change.original_content.splitlines(keepends=True),
            change.new_content.splitlines(keepends=True),
            fromfile=f"a/{change.file_path}",
            tofile=f"b/{change.file_path}",
            lineterm="",
        )

        for line in diff:
            if line.startswith("+") and not line.startswith("+++"):
                print(f"\033[32m{line}\033[0m", end="")
            elif line.startswith("-") and not line.startswith("---"):
                print(f"\033[31m{line}\033[0m", end="")
            else:
                print(line, end="")

    def apply_changes(self, changes: List[FileChange]) -> None:
        for change in changes:
            file_path = self.base_dir / change.file_path
            file_path.write_text(change.new_content, encoding="utf-8")
            print(f"✓ Applied changes to {change.file_path}")


def main():
    parser = argparse.ArgumentParser(description="Format markdown files")
    parser.add_argument("paths", nargs="*", help="Files or directories to process")
    parser.add_argument(
        "--dry-run", action="store_true", help="Preview changes without applying"
    )
    parser.add_argument("--no-format", action="store_true", help="Skip formatting")
    parser.add_argument("--no-links", action="store_true", help="Skip link validation")
    parser.add_argument(
        "--external-only", action="store_true", help="Only check external URLs"
    )
    parser.add_argument(
        "--internal-only", action="store_true", help="Only check internal links"
    )
    parser.add_argument("--base-dir", help="Base directory for vault")
    parser.add_argument(
        "--yes",
        "-y",
        action="store_true",
        help="Auto-apply changes without confirmation",
    )

    args = parser.parse_args()

    if not args.paths:
        print("Error: No paths specified")
        sys.exit(1)

    base_dir = args.base_dir or os.getcwd()

    flags = {
        "dry_run": args.dry_run,
        "no_format": args.no_format,
        "no_links": args.no_links,
        "external_only": args.external_only,
        "internal_only": args.internal_only,
        "yes": args.yes,
    }

    formatter = MarkdownFormatter(base_dir, flags)

    print("Collecting files...")
    targets = formatter.collect_targets(args.paths)

    if not targets:
        print("No markdown files found")
        sys.exit(0)

    print(f"Found {len(targets)} markdown file(s)")

    if not flags["no_links"]:
        print("Building vault index...")
        formatter.vault_index = formatter.build_vault_index(targets)

    print("Processing files...")
    changes = []
    for target in targets:
        change = formatter.process_file(target)
        if change:
            changes.append(change)

    if not changes:
        print("\n✓ No changes needed")
        sys.exit(0)

    print(f"\n{len(changes)} file(s) with changes")

    for change in changes:
        formatter.show_diff(change)

    if flags["dry_run"]:
        print("\n[DRY RUN] No changes applied")
        sys.exit(0)

    # Auto-apply if --yes flag
    if flags.get("yes", False):
        formatter.apply_changes(changes)
        print(f"\n✓ Successfully processed {len(changes)} file(s)")
        sys.exit(0)

    # Otherwise, prompt for confirmation
    print("\n" + "=" * 80)
    response = input("Apply these changes? (y/n): ").strip().lower()

    if response == "y":
        formatter.apply_changes(changes)
        print(f"\n✓ Successfully processed {len(changes)} file(s)")
    else:
        print("\nChanges not applied")


if __name__ == "__main__":
    main()
