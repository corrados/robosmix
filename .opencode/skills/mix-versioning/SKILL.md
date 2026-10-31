---
name: mix-versioning
description: Use when implementing or changing history, commits, branches, checkouts, feedback nodes, artifact storage, store schema versions, or migrations in Robosmix.
---

# Mix Versioning

Read `docs/PLAN.md` section 4 before changing the store or data model.

## Model

- `Commit` is immutable and has zero or more parent commits. History is a DAG.
- `Branch` is a named pointer to a commit; creating a flavor creates a branch.
- `Feedback` belongs to a commit; acting on it appends a child commit.
- `Artifact` is a content-addressed blob referenced by hash.
- The working state is derived from the checked-out commit, never edited in
  place.

## Invariants

1. Never rewrite, delete, or mutate a commit or artifact.
2. A commit references the plan, recipe, agent/model version, analysis inputs,
   and render artifacts used to create it.
3. Content addressing uses the hash of bytes, not filenames or timestamps.
4. Store paths are relative to the project root; reject escaping paths and
   symlinks that leave the store.
5. Every commit has a message and creation metadata; messages are user-editable
   in new commits only.

## Branch and checkout semantics

- `checkout <commit>` may move to a detached state; `--branch <name>` creates a
  branch at that commit.
- New commits advance the current branch; they never move another branch.
- Merging is not required initially; if added, record both parents and do not
  lose either side's artifacts.
- Deleting a branch only removes the pointer; unreachable commits remain until
  an explicit, documented garbage collection.

## Store implementation

- Use SQLite for the index and a content-addressed blob directory for payloads.
- Wrap writes in a transaction; write blobs before the metadata that references
  them.
- Include a `schema_version` in the store and run forward-only migrations.
- Use atomic rename for blob writes and temp-file cleanup on failure.
- Test concurrent readers and a simulated crash between blob and metadata
  writes.

## CLI behavior

- `history` shows the DAG with short hashes, branches, metrics, and messages.
- `diff` reports plan and metric differences without modifying state.
- `compare` resolves artifacts and reports objective differences.
- All commands are safe to re-run; they never duplicate commits.
