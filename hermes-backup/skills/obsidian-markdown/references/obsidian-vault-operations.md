# Obsidian Vault Operations

> Absorbed from the `obsidian` skill (2026-08-14). Covers filesystem-first vault operations: reading notes, listing notes, searching, creating, appending, and wikilinks. The main `obsidian-markdown` skill covers Obsidian-flavored markdown syntax (wikilinks, embeds, callouts, frontmatter, tags). This file covers the vault-level workflow.

## Vault Path Resolution

Use a known or resolved vault path before calling file tools.

The documented vault-path convention is the `OBSIDIAN_VAULT_PATH` environment variable, for example from `~/.hermes/.env`. If it is unset, use `~/Documents/Obsidian Vault`.

File tools do not expand shell variables. Do not pass paths containing `$OBSIDIAN_VAULT_PATH` to `read_file`, `write_file`, `patch`, or `search_files`; resolve the vault path first and pass a concrete absolute path. Vault paths may contain spaces, which is another reason to prefer file tools over shell commands.

If the vault path is unknown, `terminal` is acceptable for resolving `OBSIDIAN_VAULT_PATH` or checking whether the fallback path exists. Once the path is known, switch back to file tools.

## Read a Note

Use `read_file` with the resolved absolute path to the note. Prefer this over `cat` because it provides line numbers and pagination.

## List Notes

Use `search_files` with `target: "files"` and the resolved vault path. Prefer this over `find` or `ls`.

- To list all markdown notes, use `pattern: "*.md"` under the vault path.
- To list a subfolder, search under that subfolder's absolute path.

## Search

Use `search_files` for both filename and content searches. Prefer this over `grep`, `find`, or `ls`.

- For filenames, use `search_files` with `target: "files"` and a filename `pattern`.
- For note contents, use `search_files` with `target: "content"`, the content regex as `pattern`, and `file_glob: "*.md"` when you want to restrict matches to markdown notes.

## Create a Note

Use `write_file` with the resolved absolute path and the full markdown content. Prefer this over shell heredocs or `echo` because it avoids shell quoting issues and returns structured results.

When creating a note in Obsidian, prefer the `obsidian-markdown` skill's formatting (frontmatter, wikilinks, callouts) over plain markdown.

## Append to a Note

Prefer a native file-tool workflow when it is not awkward:

- Read the target note with `read_file`.
- Use `patch` for an anchored append when there is stable context, such as adding a section after an existing heading or appending before a known trailing block.
- Use `write_file` when rewriting the whole note is clearer than constructing a fragile patch.

For an anchored append with `patch`, replace the anchor with the anchor plus the new content.

For a simple append with no stable context, `terminal` is acceptable if it is the clearest safe option.

## Targeted Edits

Use `patch` for focused note changes when the current content gives you stable context. Prefer this over shell text rewriting.

## Wikilinks

Obsidian links notes with `[[Note Name]]` syntax. When creating notes, use these to link related content. See `obsidian-markdown` skill for full wikilink syntax including display text, heading anchors, and block IDs.

## Relationship to `obsidian-markdown`

- **`obsidian-markdown`** — Obsidian Flavored Markdown syntax (wikilinks, embeds, callouts, frontmatter, tags, comments, math, Mermaid diagrams, footnotes). Use when writing or editing `.md` content.
- **This file** — Vault-level workflow (path resolution, reading, listing, searching, creating, appending). Use when navigating or managing the vault as a filesystem.

Load both skills when doing full Obsidian vault work: `skill_view(name='obsidian-markdown')` for syntax, this file for vault operations.
