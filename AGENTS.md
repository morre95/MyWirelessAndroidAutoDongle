# Agent instructions

## Context7

Use Context7 for current library, framework, SDK, API, CLI, and cloud-service documentation, including setup and library-specific debugging.
Start with resolve-library-id unless an exact library ID is supplied.
Select the best relevant match, then use query-docs with the full question.
Do not use Context7 for general programming concepts, business-logic debugging, code review, standalone scripts, or refactoring.

## Agent skills

### Issue tracker

Track issues and specs in GitHub Issues for morre95/MyWirelessAndroidAutoDongle. Before tracker operations, read `docs/agents/issue-tracker.md`.

### Triage labels

Use the five standard triage labels. Before triaging or changing labels, read `docs/agents/triage-labels.md`.

### Domain docs

Use a single-context layout: root `GLOSSARY.md` and `docs/adr/`. Before exploring the codebase, read `docs/agents/domain.md`.
