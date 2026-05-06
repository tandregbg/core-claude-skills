---
name: md2pdf
description: Convert markdown files to styled PDFs. Supports Mermaid diagrams, tables, professional typography. Individual or combined output.
user-invocable: true
argument-hint: <file.md> [file2.md ...] [--combined output.pdf] [--css custom.css] [-o output_dir] [--outbox NAME] [--vault PATH] [--subject TEXT]
---

# PDF Export Skill

Convert markdown documents to professionally styled PDFs using weasyprint.

## Usage

```
/md2pdf path/to/document.md
/md2pdf doc1.md doc2.md doc3.md
/md2pdf doc1.md doc2.md --combined package.pdf
/md2pdf doc.md --css ~/my-brand.css -o ~/Desktop
/md2pdf doc1.md doc2.md --outbox erik-lindgren_bravo --subject "Sammanfattning"
```

## How it works

1. Translate any ` ```markmap ` fenced blocks into Mermaid mindmap blocks (heading levels + bullets become indentation)
2. Normalize lazy lists -- insert a blank line before a list that follows a paragraph (matches GFM/Obsidian behavior, since Python-markdown is strict CommonMark)
3. Extract Mermaid code blocks from raw markdown, render to PNG via `mmdc` (high-res, scale 3x)
4. Parse remaining markdown to HTML (Python `markdown` library), with `pymdownx.tasklist` enabled when available so `- [ ] ` / `- [x] ` become real checkboxes
5. Inject rendered Mermaid PNGs back into the HTML
6. Apply CSS styling (default: `style.css` in this skill directory)
7. Render to PDF via weasyprint

Note: Mermaid is rendered as PNG, not SVG, because Mermaid SVGs use `foreignObject` for text labels which weasyprint cannot render.

## Mindmap support

Author mindmaps using a fenced ` ```markmap ` block. The skill converts it to a Mermaid mindmap automatically before rendering:

````markdown
```markmap
# Root
## Branch A
- Leaf A1
- Leaf A2
## Branch B
- Leaf B1
  - Sub-leaf
```
````

Rules:
- `#` heading is the root (depth 0). `##` is depth 1, `###` is depth 2, etc.
- Bullets (`-` / `*`) under a heading inherit the heading's depth and add their own indent (each two spaces / tab = one extra level).
- Mermaid's mindmap renderer is used, so `mmdc` must be installed for the diagram to render. Without `mmdc` the block falls back to a plain code listing.

### Limit depth per block

Pass `depth=N` as a fence attribute to prune nodes deeper than N. Depth 0 is the root, so `depth=2` keeps the root + two levels of branches and drops everything deeper.

````markdown
```markmap depth=2
# Root
## Branch A
- Leaf A1     (kept — depth 2)
  - Drilldown (dropped — depth 3)
## Branch B
- Leaf B1     (kept)
```
````

Use a small depth (1-2) for an executive overview and omit the attribute (or use a higher value) for a detailed map.

## Execution

Run the converter script:

```bash
python3 ~/.claude/skills/md2pdf/md2pdf.py <args>
```

### Arguments

| Arg | Description |
|-----|-------------|
| `files` | One or more `.md` files to convert |
| `-o`, `--output-dir` | Output directory (default: current dir) |
| `--combined NAME.pdf` | Merge all files into one PDF |
| `--css FILE` | Custom CSS (default: built-in professional style) |
| `--outbox NAME` | Package PDFs into `<vault>/_outbox/YYMMDD-NAME/` with `_manifest.md` + email stub. NAME follows the contact convention (`förnamn-efternamn_organisation`). |
| `--vault PATH` | Vault root for `--outbox` mode (default: walk up from cwd looking for `_outbox/` or `_contacts/`, then `$OBSIDIAN_VAULT`). |
| `--subject TEXT` | Pre-fill the email subject line in `--outbox` mode. |

### Examples

Single file:
```bash
python3 ~/.claude/skills/md2pdf/md2pdf.py report.md -o ~/Desktop
```

Multiple files, individual PDFs:
```bash
python3 ~/.claude/skills/md2pdf/md2pdf.py summary.md strategy.md diagram.md -o ./export
```

Combined document:
```bash
python3 ~/.claude/skills/md2pdf/md2pdf.py summary.md strategy.md --combined full-report.pdf -o ~/Desktop
```

Custom styling:
```bash
python3 ~/.claude/skills/md2pdf/md2pdf.py doc.md --css ~/brand/style.css
```

Outbox mode (auto-package for sending):
```bash
python3 ~/.claude/skills/md2pdf/md2pdf.py nulaege.md strategi.md --outbox erik-lindgren_bravo --subject "Sammanfattning från mötet"
```

Outbox mode produces:
```
<vault>/_outbox/YYMMDD-erik-lindgren_bravo/
├── _manifest.md                                  # status, kanal, kontakt, projekt, Innehåll-tabell
├── 260415-erik-lindgren_bravo-mejl.txt     # ämne ifyllt, bilagor listade, body tom
├── nulaege.pdf
└── strategi.pdf
```

The manifest and email stub are skeletons. After generating, you MUST fill in:

1. **Email body** (`mejl.txt`): Write a complete email with context — what's attached and why, key decisions or outcomes, open questions, and what's expected from the recipient. Never leave the body as `<!-- fyll i meddelandetext -->`. **IMPORTANT: The email file must be plain text only — no markdown syntax.** Do not use `##`, `**`, `---`, backticks, or any other markdown formatting. Use UPPERCASE for section headings, plain dashes/numbers for lists, and spaces for alignment. The text is copied directly into a mail client where markdown renders as ugly raw syntax.
2. **Manifest**: Fill in Beskrivning/Målgrupp cells and Syfte. Remove references to internal-only documents that should not be sent to the recipient.
3. **Bilaga-listan**: Verify that only recipient-appropriate files are listed — remove internal CRs, question logs with internal IDs, or other non-customer-facing documents.

After sending, flip `**Status:** ej skickad` to `skickad` in the manifest. Combining `--outbox` with `--combined paket.pdf` produces a single PDF inside the outbox folder instead of one per source file.

## Dependencies

- **weasyprint** (Python) -- HTML/CSS to PDF
- **markdown** (Python) -- Markdown to HTML
- **pymdown-extensions** (Python, optional) -- Renders `- [ ]` / `- [x]` task lists as proper checkboxes (without it the checkboxes show up as literal `[ ]` text after the bullet)
- **mmdc** (npm: `@mermaid-js/mermaid-cli`) -- Mermaid diagram rendering, **required for mindmap and mermaid blocks** (optional only if neither block type is used)

### Install (first-time setup)

```bash
# Python deps
pip install weasyprint markdown pymdown-extensions

# Mermaid CLI (required for ```mermaid and ```markmap blocks)
npm install -g @mermaid-js/mermaid-cli
```

Verify:
```bash
mmdc --version    # should print a version
weasyprint --version
```

If `mmdc` is missing, mermaid/markmap blocks will fall back to a plain code listing in the PDF (no diagram rendered) -- the build still succeeds.

## Customization

Override the default `style.css` with `--css`. The CSS uses `@page` rules for print layout (A4, margins, page numbers). See `style.css` in this directory for the full default template.

## Integration with other skills

This skill pairs well with:
- `/ops` -- generate meeting summaries, then export as PDF
- `/preparation` -- create meeting prep docs, export for print/sharing
- `/transcript` -- process transcripts, deliver as PDF

Workflow: generate markdown with the source skill, then `/md2pdf` to export.
