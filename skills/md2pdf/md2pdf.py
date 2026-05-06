#!/usr/bin/env python3
"""Convert markdown files to styled PDFs via weasyprint.

Usage:
    python3 md2pdf.py input.md [input2.md ...] [-o output_dir] [--combined output.pdf] [--css style.css]

Features:
    - Markdown → HTML → PDF via weasyprint
    - Mermaid diagram rendering via mmdc (auto-detected)
    - Professional default styling (overridable with --css)
    - Combined multi-file output or individual PDFs
"""

import argparse
import datetime
import hashlib
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


def _bootstrap_homebrew_paths() -> None:
    """Make Homebrew binaries and libraries discoverable before heavy imports.

    weasyprint loads native libraries (libgobject, pango, harfbuzz, ...) at
    import time via ctypes. When this script runs in a non-interactive shell
    (SSH session, cron, Claude Code on a fresh shell) without /opt/homebrew on
    PATH and DYLD_FALLBACK_LIBRARY_PATH, the dlopen calls fail. Likewise mmdc
    is a shell wrapper that needs /opt/homebrew/bin to find `node`.

    We extend PATH and DYLD_FALLBACK_LIBRARY_PATH defensively so the rest of
    the script can stay platform-agnostic. Idempotent: existing entries are
    not duplicated.
    """
    bin_dirs = ["/opt/homebrew/bin", "/usr/local/bin"]
    lib_dirs = ["/opt/homebrew/lib", "/usr/local/lib"]

    def _prepend(env_key: str, dirs: list[str]) -> None:
        existing = os.environ.get(env_key, "")
        parts = existing.split(os.pathsep) if existing else []
        for d in dirs:
            if Path(d).is_dir() and d not in parts:
                parts.insert(0, d)
        if parts:
            os.environ[env_key] = os.pathsep.join(parts)

    _prepend("PATH", bin_dirs)
    _prepend("DYLD_FALLBACK_LIBRARY_PATH", lib_dirs)


_bootstrap_homebrew_paths()

import markdown  # noqa: E402  (must come after PATH bootstrap)
from weasyprint import HTML  # noqa: E402  (loads native libs on import)

SCRIPT_DIR = Path(__file__).parent
DEFAULT_CSS = SCRIPT_DIR / "style.css"


def convert_markmap_to_mermaid(text: str) -> str:
    """Translate ```markmap fenced blocks into ```mermaid mindmap blocks.

    Markmap uses heading levels (#, ##, ###) and bullet lists to express
    hierarchy. Mermaid's mindmap syntax uses indentation. We convert headings
    to indent levels and preserve bullet indentation.

    Optional fence attributes:
        ```markmap depth=2          -- prune nodes deeper than depth 2
        ```markmap depth=3 ...      -- multiple attrs space-separated

    Depth counting: the root (single `#` heading) is depth 0. `##` is depth 1,
    a bullet directly under `##` is depth 2, etc. depth=N keeps everything at
    depth <= N and drops deeper nodes.

    Conversion rules:
    - First-level heading (# X)   -> root node (zero indent in mermaid)
    - Second-level heading (## X) -> 1 level deep
    - Third-level heading (### X) -> 2 levels deep, etc.
    - Bullets (- X / * X) inherit parent heading level + their own indent
    """
    pattern = re.compile(r'(?m)^```markmap([^\n]*)\n(.*?)^```\s*$', re.DOTALL)

    def parse_attrs(attr_str: str) -> dict:
        attrs = {}
        for token in attr_str.strip().split():
            if "=" in token:
                k, v = token.split("=", 1)
                attrs[k.strip()] = v.strip()
        return attrs

    def translate_block(match: re.Match) -> str:
        attr_str = match.group(1)
        body = match.group(2)
        attrs = parse_attrs(attr_str)
        max_depth = None
        if "depth" in attrs:
            try:
                max_depth = int(attrs["depth"])
            except ValueError:
                max_depth = None

        out_lines = ["mindmap"]
        heading_depth = 0  # last seen heading level (1-based, where 1 = #)
        for raw_line in body.splitlines():
            line = raw_line.rstrip()
            if not line.strip():
                continue

            heading_match = re.match(r'^(#+)\s+(.*)$', line)
            if heading_match:
                hashes, content = heading_match.groups()
                heading_depth = len(hashes)
                node_depth = heading_depth - 1  # # = depth 0 (root)
                if max_depth is not None and node_depth > max_depth:
                    continue
                indent = "  " * heading_depth
                out_lines.append(f"{indent}{content.strip()}")
                continue

            bullet_match = re.match(r'^(\s*)[-*]\s+(.*)$', line)
            if bullet_match:
                leading_ws, content = bullet_match.groups()
                # Each two spaces (or tab) of bullet indent = one extra depth
                ws_units = leading_ws.replace("\t", "  ")
                bullet_depth = len(ws_units) // 2 + 1
                total_depth = heading_depth + bullet_depth
                node_depth = total_depth - 1
                if max_depth is not None and node_depth > max_depth:
                    continue
                indent = "  " * total_depth
                out_lines.append(f"{indent}{content.strip()}")
                continue

            # Plain text inside markmap block: treat as bullet at current depth+1
            total_depth = heading_depth + 1
            node_depth = total_depth - 1
            if max_depth is not None and node_depth > max_depth:
                continue
            indent = "  " * total_depth
            out_lines.append(f"{indent}{line.strip()}")

        return "```mermaid\n" + "\n".join(out_lines) + "\n```"

    return pattern.sub(translate_block, text)


def normalize_lazy_lists(text: str) -> str:
    """Insert a blank line before a list that follows a paragraph without one.

    Python-markdown follows strict CommonMark and requires a blank line between
    a paragraph and a list. GitHub Flavored Markdown and Obsidian are lazier:
    they treat ``Some text:\n- item`` as a list. This pre-processor matches the
    lazy behavior so authoring stays natural.

    Skips:
    - Lines inside fenced code blocks (```...```)
    - Already-blank-separated lists (no-op)
    - List items immediately after another list item or list-continuation line
    """
    lines = text.split("\n")
    out: list[str] = []
    in_fence = False
    fence_marker = ""
    list_start = re.compile(r'^(\s*)(?:[-*+]\s+|\d+\.\s+)')

    for i, line in enumerate(lines):
        stripped = line.strip()

        # Track fenced code blocks (``` or ~~~)
        if not in_fence and (stripped.startswith("```") or stripped.startswith("~~~")):
            in_fence = True
            fence_marker = stripped[:3]
            out.append(line)
            continue
        if in_fence:
            if stripped.startswith(fence_marker):
                in_fence = False
            out.append(line)
            continue

        m = list_start.match(line)
        if m and out:
            prev = out[-1]
            prev_stripped = prev.strip()
            # Only insert if previous non-empty line is a paragraph (not blank,
            # not heading, not another list item, not a separator/code)
            if prev_stripped and not list_start.match(prev) and not prev_stripped.startswith("#"):
                out.append("")

        out.append(line)

    return "\n".join(out)


def find_mmdc() -> str | None:
    """Locate the mmdc binary, even when not on PATH.

    Order of search:
    1. `mmdc` on the current PATH (covers interactive shells with full PATH)
    2. Common Homebrew install locations (covers SSH/non-interactive shells
       on macOS where /opt/homebrew/bin or /usr/local/bin aren't in PATH)
    3. Common Linux install locations
    4. nvm-managed node directories under ~/.nvm/versions/node/
    """
    found = shutil.which("mmdc")
    if found:
        return found

    candidates = [
        "/opt/homebrew/bin/mmdc",       # Apple Silicon Homebrew
        "/usr/local/bin/mmdc",          # Intel Mac Homebrew / older Linux
        "/usr/bin/mmdc",                # system-wide Linux package
        str(Path.home() / ".npm-global" / "bin" / "mmdc"),
        str(Path.home() / "node_modules" / ".bin" / "mmdc"),
    ]
    for path in candidates:
        if Path(path).is_file():
            return path

    # nvm: pick the highest-versioned node install with mmdc
    nvm_root = Path.home() / ".nvm" / "versions" / "node"
    if nvm_root.is_dir():
        for node_dir in sorted(nvm_root.iterdir(), reverse=True):
            candidate = node_dir / "bin" / "mmdc"
            if candidate.is_file():
                return str(candidate)

    return None


def extract_mermaid_blocks(text: str, work_dir: Path) -> tuple[str, dict[str, str]]:
    """Extract mermaid code blocks from markdown, render to PNG, return placeholders.

    Uses PNG output because Mermaid SVGs use foreignObject for text labels,
    which weasyprint cannot render.
    """
    mmdc = find_mmdc()
    placeholders = {}

    pattern = re.compile(r'(?m)^```mermaid\s*\n(.*?)^```\s*$', re.DOTALL)

    def replace_with_placeholder(match):
        diagram_src = match.group(1).strip()
        digest = hashlib.md5(diagram_src.encode()).hexdigest()[:8]
        placeholder = f'MERMAID_PLACEHOLDER_{digest}'

        if mmdc:
            mmd_file = work_dir / f"mermaid_{digest}.mmd"
            png_file = work_dir / f"mermaid_{digest}.png"
            mmd_file.write_text(diagram_src)
            result = subprocess.run(
                [mmdc, "-i", str(mmd_file), "-o", str(png_file),
                 "-b", "white", "--quiet", "-s", "3"],
                capture_output=True,
                timeout=30,
            )
            if result.returncode == 0 and png_file.exists():
                import base64
                png_b64 = base64.b64encode(png_file.read_bytes()).decode()
                placeholders[placeholder] = (
                    f'<div class="mermaid-diagram">'
                    f'<img src="data:image/png;base64,{png_b64}" />'
                    f'</div>'
                )
            else:
                stderr = result.stderr.decode() if result.stderr else "unknown error"
                print(f"  Warning: mmdc failed for diagram {digest}: {stderr}", file=sys.stderr)
                placeholders[placeholder] = f'<pre><code>{diagram_src}</code></pre>'
        else:
            placeholders[placeholder] = f'<pre><code>{diagram_src}</code></pre>'

        return f'\n\n{placeholder}\n\n'

    text = pattern.sub(replace_with_placeholder, text)
    return text, placeholders


def restore_mermaid_placeholders(html: str, placeholders: dict[str, str]) -> str:
    """Replace placeholder strings in HTML with rendered diagram content."""
    for placeholder, svg_html in placeholders.items():
        html = html.replace(f'<p>{placeholder}</p>', svg_html)
        html = html.replace(placeholder, svg_html)
    return html


def md_to_html(md_path: Path, work_dir: Path) -> str:
    """Convert a markdown file to HTML string."""
    text = md_path.read_text(encoding="utf-8")

    # Strip YAML frontmatter
    if text.startswith("---"):
        end = text.find("---", 3)
        if end != -1:
            text = text[end + 3:].lstrip()

    # Translate ```markmap blocks into ```mermaid mindmap blocks first
    text = convert_markmap_to_mermaid(text)

    # Normalize lazy lists (insert blank line before a list that follows a paragraph)
    text = normalize_lazy_lists(text)

    # Extract and render mermaid blocks before markdown processing
    text, mermaid_placeholders = extract_mermaid_blocks(text, work_dir)

    extensions = [
        "tables",
        "fenced_code",
        "codehilite",
        "toc",
        "smarty",
        "md_in_html",
    ]
    # Add pymdown extensions when installed:
    #  - tasklist: renders - [ ] / - [x] as proper checkboxes
    #  - magiclink: autolinks bare URLs and email addresses
    try:
        import pymdownx  # noqa: F401
        extensions.append("pymdownx.tasklist")
        extensions.append("pymdownx.magiclink")
    except ImportError:
        pass

    extension_configs = {
        "codehilite": {"css_class": "highlight", "guess_lang": False},
        "pymdownx.tasklist": {"custom_checkbox": True, "clickable_checkbox": False},
    }
    html = markdown.markdown(text, extensions=extensions, extension_configs=extension_configs)

    # Restore mermaid diagrams
    html = restore_mermaid_placeholders(html, mermaid_placeholders)

    # Wrap heading + following content in <section> to prevent orphaned headings
    html = wrap_heading_sections(html)

    return html


def wrap_heading_sections(html: str) -> str:
    """Wrap each heading and its following content in a <section> element.

    This allows CSS `break-inside: avoid` to keep short heading groups together,
    preventing orphaned headings at the bottom of pages.
    """
    # Split on h2/h3/h4 boundaries (not h1 — that's the document title)
    pattern = re.compile(r'(<h[234][^>]*>)')
    parts = pattern.split(html)

    if len(parts) <= 1:
        return html

    result = []
    # parts[0] is everything before the first heading
    result.append(parts[0])

    i = 1
    while i < len(parts):
        heading_tag = parts[i]
        content = parts[i + 1] if i + 1 < len(parts) else ""

        # Get content up to the next heading of same or higher level
        content_before_next = content.split('<h')[0] if '<h' in content else content
        stripped = content_before_next.strip()

        # Always wrap — weasyprint will break the section across pages if needed,
        # but will try to keep it together when it fits
        if len(stripped) < 3000:
            result.append(f'<section class="heading-group">{heading_tag}{content}</section>')
        else:
            result.append(f'{heading_tag}{content}')

        i += 2

    return "".join(result)


def wrap_html(body: str, title: str, css_path: Path) -> str:
    """Wrap HTML body in a full document with CSS."""
    css = css_path.read_text(encoding="utf-8")
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <title>{title}</title>
    <style>{css}</style>
</head>
<body>
    <article>
        {body}
    </article>
</body>
</html>"""


def convert_file(md_path: Path, output_path: Path, css_path: Path, work_dir: Path):
    """Convert a single markdown file to PDF."""
    html_body = md_to_html(md_path, work_dir)

    title = md_path.stem.replace("-", " ").replace("_", " ").title()
    full_html = wrap_html(html_body, title, css_path)

    HTML(string=full_html, base_url=str(md_path.parent)).write_pdf(str(output_path))


def convert_combined(md_paths: list[Path], output_path: Path, css_path: Path, work_dir: Path):
    """Convert multiple markdown files into a single combined PDF."""
    sections = []
    for md_path in md_paths:
        html_body = md_to_html(md_path, work_dir)
        sections.append(html_body)

    combined_body = '\n<div class="page-break"></div>\n'.join(sections)
    full_html = wrap_html(combined_body, "Document Package", css_path)

    HTML(string=full_html, base_url=str(md_paths[0].parent)).write_pdf(str(output_path))


def resolve_vault(explicit: str | None) -> Path:
    """Resolve the Obsidian vault root.

    Priority: explicit --vault > walk up from cwd looking for _outbox/ or
    _contacts/ markers > $OBSIDIAN_VAULT env var > error.
    """
    if explicit:
        p = Path(explicit).expanduser().resolve()
        if not p.is_dir():
            print(f"Error: --vault path is not a directory: {p}", file=sys.stderr)
            sys.exit(1)
        return p

    cwd = Path.cwd().resolve()
    for candidate in [cwd, *cwd.parents]:
        if (candidate / "_outbox").is_dir() or (candidate / "_contacts").is_dir():
            return candidate

    env_vault = os.environ.get("OBSIDIAN_VAULT")
    if env_vault:
        p = Path(env_vault).expanduser().resolve()
        if p.is_dir():
            return p

    print(
        "Error: vault root not detected. Pass --vault PATH, run from inside a "
        "vault containing _outbox/ or _contacts/, or set $OBSIDIAN_VAULT.",
        file=sys.stderr,
    )
    sys.exit(1)


def parse_recipient(slug: str) -> tuple[str, str, str]:
    """Split 'forname-efternamn_organisation' into (display_name, org, full_slug).

    Falls back gracefully if no underscore present.
    """
    if "_" in slug:
        name_part, org_part = slug.split("_", 1)
    else:
        name_part, org_part = slug, ""
    display_name = " ".join(w.capitalize() for w in name_part.split("-"))
    return display_name, org_part, slug


def build_manifest(
    date_str: str,
    slug: str,
    pdf_filenames: list[str],
    email_filename: str,
    subject: str | None,
) -> str:
    """Render the _manifest.md skeleton matching the _outbox/README.md convention."""
    display_name, org, _ = parse_recipient(slug)
    org_label = org.capitalize() if org else ""
    title = f"# {date_str} -- {display_name}"
    if org_label:
        title += f" ({org_label})"

    rows = [
        f"| {email_filename} | Mejltext | Kopiera till mailklient | <!-- fyll i -->|"
    ]
    for fname in pdf_filenames:
        rows.append(f"| {fname} | Bilaga | <!-- fyll i beskrivning --> | <!-- fyll i --> |")

    projekt_line = f"**Projekt:** [[{org}]]" if org else "**Projekt:** <!-- fyll i -->"
    subject_line = subject if subject else "<!-- fyll i ämne -->"

    return f"""{title}

**Status:** ej skickad
**Kanal:** mejl
**Kontakt:** [[{slug}]]
{projekt_line}

---

## Innehåll

| Fil | Typ | Beskrivning | Målgrupp |
|-----|-----|-------------|----------|
{chr(10).join(rows)}

## Skicka

1. Öppna `{email_filename}`, kopiera texten till mailklient
2. Bifoga PDF:erna ovan
3. Skicka, sätt sedan **Status:** skickad ovan

**Ämne:** {subject_line}

## Syfte

<!-- fyll i: vad vill du uppnå med detta utskick? -->

## Svar förväntas på

- [ ] <!-- fyll i förväntat svar/åtgärd -->
"""


def build_email_stub(
    slug: str,
    pdf_filenames: list[str],
    subject: str | None,
) -> str:
    """Render the YYMMDD-NAME-mejl.txt skeleton."""
    subject_line = subject if subject else "<!-- fyll i ämne -->"
    bilagor = "\n".join(f"- {f}" for f in pdf_filenames)
    return f"""Ämne: {subject_line}

---

Hej <!-- fyll i förnamn -->,

Jag bifogar {len(pdf_filenames)} dokument:

{bilagor}

<!-- fyll i meddelandetext -->

/Alex
"""


def main():
    parser = argparse.ArgumentParser(description="Convert markdown to styled PDF")
    parser.add_argument("files", nargs="+", help="Markdown files to convert")
    parser.add_argument("-o", "--output-dir", default=".", help="Output directory for PDFs")
    parser.add_argument("--combined", help="Combine all files into a single PDF with this name")
    parser.add_argument("--css", help="Custom CSS file (default: built-in style)")
    parser.add_argument("--outbox", metavar="NAME", help="Package PDFs into <vault>/_outbox/YYMMDD-NAME/ with manifest and email stub. NAME follows the contact convention (e.g. erik-lindgren_bravo).")
    parser.add_argument("--vault", help="Vault root (default: detect from cwd or $OBSIDIAN_VAULT)")
    parser.add_argument("--subject", help="Email subject line for the .txt stub (outbox mode)")
    args = parser.parse_args()

    css_path = Path(args.css) if args.css else DEFAULT_CSS
    if not css_path.exists():
        print(f"Error: CSS file not found: {css_path}", file=sys.stderr)
        sys.exit(1)

    md_paths = [Path(f) for f in args.files]
    for p in md_paths:
        if not p.exists():
            print(f"Error: File not found: {p}", file=sys.stderr)
            sys.exit(1)

    if args.outbox:
        vault = resolve_vault(args.vault)
        date_str = datetime.date.today().strftime("%y%m%d")
        outbox_dir = vault / "_outbox" / f"{date_str}-{args.outbox}"
        outbox_dir.mkdir(parents=True, exist_ok=True)

        contacts_check = vault / "_contacts" / args.outbox
        if not contacts_check.is_dir():
            print(
                f"Warning: _contacts/{args.outbox}/ not found in vault. "
                "Continuing -- but the wikilink in the manifest will be unresolved.",
                file=sys.stderr,
            )

        with tempfile.TemporaryDirectory() as tmp:
            work_dir = Path(tmp)

            if args.combined:
                pdf_name = args.combined
                if not pdf_name.lower().endswith(".pdf"):
                    pdf_name += ".pdf"
                out = outbox_dir / pdf_name
                print(f"Generating combined PDF: {out}")
                convert_combined(md_paths, out, css_path, work_dir)
                print(f"  ✓ {out}")
                pdf_filenames = [pdf_name]
            else:
                pdf_filenames = []
                for md_path in md_paths:
                    pdf_name = md_path.stem + ".pdf"
                    out = outbox_dir / pdf_name
                    print(f"Converting: {md_path.name}")
                    convert_file(md_path, out, css_path, work_dir)
                    print(f"  ✓ {out}")
                    pdf_filenames.append(pdf_name)

        email_filename = f"{date_str}-{args.outbox}-mejl.txt"
        manifest_path = outbox_dir / "_manifest.md"
        email_path = outbox_dir / email_filename

        manifest_path.write_text(
            build_manifest(date_str, args.outbox, pdf_filenames, email_filename, args.subject),
            encoding="utf-8",
        )
        print(f"  ✓ {manifest_path}")

        email_path.write_text(
            build_email_stub(args.outbox, pdf_filenames, args.subject),
            encoding="utf-8",
        )
        print(f"  ✓ {email_path}")
        print(f"\nOutbox folder: {outbox_dir}")
        return

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory() as tmp:
        work_dir = Path(tmp)

        if args.combined:
            out = output_dir / args.combined
            print(f"Generating combined PDF: {out}")
            convert_combined(md_paths, out, css_path, work_dir)
            print(f"  ✓ {out}")
        else:
            for md_path in md_paths:
                out = output_dir / (md_path.stem + ".pdf")
                print(f"Converting: {md_path.name}")
                convert_file(md_path, out, css_path, work_dir)
                print(f"  ✓ {out}")


if __name__ == "__main__":
    main()
