# Issue tracker: GitHub

Issues and specs live in GitHub Issues for
morre95/MyWirelessAndroidAutoDongle. Use the gh CLI.

## Conventions

Run commands from this repository. For operations outside it,
pass --repo morre95/MyWirelessAndroidAutoDongle.

- Create: gh issue create --title "..." --body-file <file>
- Read: gh issue view <number> --json number,title,body,labels,comments
- List: gh issue list --state open --json number,title,body,labels
- Comment: gh issue comment <number> --body-file <file>
- Add labels: gh issue edit <number> --add-label "..."
- Remove labels: gh issue edit <number> --remove-label "..."
- Close: gh issue close <number>

For multiline bodies, write the exact text to a temporary file
and pass it with --body-file.

For parent/child issues, use GitHub sub-issues when available.
Otherwise put "Part of #<parent>" in the child's body and link
the child in the parent's task list.

## Pull requests as a triage surface

**PRs as a request surface: no.**

## Skill terminology

"Publish to the issue tracker" means create a GitHub issue.
"Fetch the relevant ticket" means read the referenced issue.
