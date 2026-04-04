# Transcript Skill

Skill for processing and summarizing transcriptions from calls, meetings, or voice recordings.

## Usage

```
/transcript [transcription content or file path]
```

Or simply invoke `/transcript` and paste the transcription content.

## What It Does

1. **Creates a structured summary** of the transcription
2. **Asks where to save** the file (context-aware)
3. **Updates CHANGELOG.md** if requested and available

## Summary Format

The skill creates summaries with:

- **Heading**: `# Summary: YYMMDD Samtal [Participants] - [Topic]`
- **Introduction**: Date and context
- **Sections**: One `##` section per distinct topic area
- **Bullet points**: Key facts, decisions, technical details
- **Next steps**: Action items when applicable

### Example Output

```markdown
# Summary: 260205 Samtal Alex-Bob - Project Planning

#### Introduction
Recording from 2026-02-05. Discussion about infrastructure and deployment.

---

## Infrastructure decisions

- Evaluating Glesys and Bahnhof for server hosting
- Two IP addresses needed for blade configuration
- IP-Tables for firewall management

---

## Next steps

- Get quote from Glesys
- Compare with Bahnhof pricing
```

## File Organization

The skill is context-aware and adapts to the current directory structure:

### Participant Folders
If a `_contacts/` directory exists, the skill suggests saving to the matching contact folder:
- `_contacts/bob-lindgren/`
- `_contacts/sara-holm/`
- `_contacts/hank/`

### CHANGELOG Integration
The skill always updates or creates a `CHANGELOG.md` in the target folder. If none exists, one is created automatically with entries for all existing files:

```markdown
- **YYMMDD: Participant(s)** - One sentence summary. *(keyword1, keyword2, max 15)* -> [filename.md]
```

## Filename Convention

Output files follow the format:
```
YYMMDD-participant-topic-description.md
```

Examples:
- `260205-samtal-alex-hank-infrastruktur-serveralternativ.md`
- `260201-samtal-alex-sara-AI-workshop-planering.md`

## Content Rules

The skill:
- **Preserves** technical terminology and key terms
- **Excludes** personal reflections, sensitive information
- **Prioritizes** concrete facts, business ideas, projects
- **Maintains** the original language (Swedish/English)

## Typical Workflow

1. Record a call/meeting (e.g., with Deep Thought)
2. Get the transcription
3. Run `/transcript` with the content
4. Review the generated summary
5. Specify save location (or accept suggestion)
6. Optionally update CHANGELOG

## Tips

- Include metadata from Deep Thought (date, title, suggested filename) for better context
- Mention the participant or project name if not obvious from the content
- For project-specific transcripts, mention the project (e.g., "Bravo", "fundraiser-run")
