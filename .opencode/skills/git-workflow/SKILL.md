---
name: git-workflow
description: Use at the end of every completed Robosmix task, before reporting done, to stage all intended changes, commit them, and push to the configured upstream.
---

# Git Workflow

Every completed task must end with the intended changes committed and pushed.
Do not report a task as done while its changes are only in the working tree.

## Finishing checklist

1. Run the required checks from `AGENTS.md`.
2. Inspect `git status`, `git diff`, and recent `git log` entries.
3. Stage all intended changes. Normally this is the entire task diff, but verify
   first that it contains no unrelated files.
4. Never commit audio, model caches, secrets, generated deliverables, or local
   environment files.
5. Write a concise commit message in the repository's existing style.
6. Commit and push to the configured upstream.
7. Confirm `git status` is clean and the branch is not ahead of its upstream.

## Push rules

- Push the current branch to its configured upstream with `git push`.
- If the branch has no upstream, confirm the correct remote and set it with
  `git push -u <remote> HEAD`.
- Do not force-push, rewrite history, or create empty commits unless explicitly
  asked.
- If checks, commit, or push fail, leave the work intact and report the failure
  clearly instead of claiming completion.

## No changes

If the task produced no changes, do not create an empty commit. Confirm the
working tree is clean and report that there was nothing to commit.
