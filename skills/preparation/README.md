# preparation

**Version:** 1.0.1

Create structured meeting preparation documents from contact history.

> **Note:** This skill is for **1-on-1 meetings** with contacts in `_contacts/` folders. For **team meetings** in project folders, use `/ops prepare` instead.

## Usage

```
/preparation david                    # Prepare for call with David, today
/preparation david tomorrow           # Prepare for tomorrow's call
/preparation erik sandberg 260219    # Specific contact + date
/preparation bob l 260220           # Partial name match + date
```

## What It Does

1. Finds the matching contact folder inside `_contacts/`
2. Reads recent transcripts, previous preparations, and CHANGELOG
3. Extracts open action items, unresolved threads, and relationship context
4. Asks the user for additional context (meeting purpose, new information)
5. Generates a structured preparation document with talking points and agenda

## Output

- File: `YYMMDD-förberedelse-[context].md` saved in the contact folder
- Optional: CHANGELOG.md entry in the contact folder
- Automatically discovered by `/daily-dashboard` on the target date

## Document Structure

- **Kontext** -- recent history and current situation
- **Numbered topic sections** -- key discussion areas with background and questions
- **Öppna åtgärdspunkter** -- open action items split by person
- **Föreslagna samtalsämnen** -- prioritized agenda
- **Bakgrund** -- relationship summary

## Post-Meeting

After the meeting, the preparation can be updated with `[UTFALL]` annotations, new action items, and reflections -- turning it into a complete meeting record.

## Integration

- Works with any vault using `_contacts/` folder conventions
- Files picked up by `/daily-dashboard` via filename pattern matching
- Complements `/transcript` for the full meeting lifecycle: prepare -> meet -> transcribe

## See Also

| Skill | Use for | Context |
|-------|---------|---------|
| `/preparation` | 1-on-1 meetings | `_contacts/` folders |
| `/ops prepare` | Team standups, war rooms | `_projects/` folders |

---

## Changelog

### v1.0.1 (2026-03-11)

- Added note clarifying scope (1-on-1 vs team meetings)
- Added "See Also" section with `/ops prepare` reference

### v1.0.0

Initial release.
