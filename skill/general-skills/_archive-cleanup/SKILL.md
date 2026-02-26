---
name: archive-cleanup
description: Automatically archive old documents from active/ to archive/ based on age and relevance rules.
metadata: {"openclaw":{"emoji":"📦","requires":{"bins":["bash"]},"primaryEnv":"ARCHIVE_AGE_DAYS"}}
---

# Archive Cleanup Skill

Archive old documents to keep active workspace clean.

## Commands

- Run archive check:
  - `bash {baseDir}/scripts/archive-cleanup.sh`

## Environment

- `ARCHIVE_AGE_DAYS`: Days before archiving (default: 30)
