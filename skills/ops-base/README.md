# Operations Base Framework

Shared operational standards referenced by domain-specific ops-skills.

## Purpose

Provides consistent foundation for:
- Meeting documentation formats
- Task management and prioritization
- Workflow processes
- Archive policies
- Cross-referencing standards

## Not User-Invocable

This is a base module. Use `/ops` instead -- the unified, config-driven meeting processing skill.

## What's Included

### Meeting Documentation
Two-tier format (Concise Operational / Detailed Strategic) with standardized structures.

### Task Management
- Priority levels: P0 (critical) to P3 (research)
- Status indicators: BLOCKED, IN PROGRESS, ON TRACK, TODO, PLANNED, COMPLETE
- Task document lifecycle

### Documentation Structure
Standard directory organization and naming conventions.

### Workflow Processes
Meeting workflow steps and CHANGELOG format.

### Archive Policy
Rules for archiving meetings, tasks, and resources.

### Cross-Referencing
Link standards for consistent document navigation.

## Directory Structure

```
meetings/
  operational/
  strategic/
  technical/
tasks/
  active/
  .archive/
resources/
transcripts/
CHANGELOG.md
```

## Priority Levels

| Level | Description | Timeline |
|-------|-------------|----------|
| P0 | Critical blocker | Immediate |
| P1 | High priority | This week |
| P2 | Important | Within 2 weeks |
| P3 | Research/exploration | Flexible |

## Naming Conventions

| Type | Format |
|------|--------|
| Meetings | `YYMMDD-Topic-Type.md` |
| Tasks | `YYMMDD-Topic-tasks.md` |
| Resources | `descriptive-name.md` |
