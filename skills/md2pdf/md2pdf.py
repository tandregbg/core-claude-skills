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
import markdown
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from weasyprint import HTML

SCRIPT_DIR = Path(__file__).parent
DEFAULT_CSS = SCRIPT_DIR / "style.css"


def extract_mermaid_blocks(text: str, work_dir: Path) -> tuple[str, dict[str, str]]:
    """Extract mermaid code blocks from markdown, render to PNG, return placeholders.

    Uses PNG output because Mermaid SVGs use foreignObject for text labels,
    which weasyprint cannot render.
    """
    mmdc = shutil.which("mmdc")
    placeholders = {}

    pattern = re.compile(r'```mermaid\s*\n(.*?)```', re.DOTALL)

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
    extension_configs = {
        "codehilite": {"css_class": "highlight", "guess_lang": False},
    }
    html = markdown.markdown(text, extensions=extensions, extension_configs=extension_configs)

    # Restore mermaid diagrams
    html = restore_mermaid_placeholders(html, mermaid_placeholders)
    return html


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
