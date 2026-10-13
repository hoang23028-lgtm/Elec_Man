"""Check repository documentation links and prevent stale canonical filenames."""

import re
import sys
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]


def check_links(root: Path = ROOT) -> list[str]:
    failures = []
    documents = [root / "README.md", *sorted((root / "docs").rglob("*.md"))]
    documents += sorted((root / "design-system").rglob("*.md"))
    for document in documents:
        content = document.read_text(encoding="utf-8-sig")
        # Code snippets can deliberately show illustrative paths, not actual links.
        content = re.sub(r"^```.*?^```\s*$", "", content, flags=re.M | re.S)
        for match in re.finditer(r"\]\(([^)\n]+)\)", content):
            target = match[1].strip().strip("<>")
            parsed = urlsplit(target)
            if parsed.scheme or not parsed.path or target.startswith("//"):
                continue
            path = (document.parent / unquote(parsed.path)).resolve()
            if not path.is_relative_to(root.resolve()) or not path.exists():
                failures.append(
                    f"{document.relative_to(root)}: missing/escaping link {target}"
                )
    return failures


def main() -> int:
    failures = check_links()
    for failure in failures:
        print(failure, file=sys.stderr)
    print(f"Documentation links: {'failed' if failures else 'passed'}")
    return bool(failures)


if __name__ == "__main__":
    raise SystemExit(main())
