# proxy-brain — a fork of okf-generator

This repository is a **hard fork** of
[UmairBaig8/okf-generator](https://github.com/UmairBaig8/okf-generator), taken at:

| | |
|---|---|
| commit | `5fb73be73814ec75b5c5f48ccbbecf348ff277d3` |
| date | 2026-08-01 |
| version | `0.1.53` |

The full upstream history is preserved — 606 commits by Umair Baig (604),
Yiannis Gkoufas and apikodes — so `git log` and `git blame` continue to credit
the people who wrote each line. Only the repository's name differs.

## Licence

Upstream is **MIT**, and this fork remains MIT. `LICENSE` keeps its original
notice, `Copyright (c) 2026 Umair Baig`, unchanged. Work added after the fork
point is covered by the same licence; the attribution travels with the code.

## Relationship to the Open Knowledge Format

`okf-generator` produces **OKF v0.2** bundles, an extended dialect of the
[Open Knowledge Format v0.1](https://github.com/GoogleCloudPlatform/knowledge-catalog),
which is Google's Apache-2.0 specification and is **not** part of this fork.

This matters for naming. The format is OKF; this tool is one implementation of
it. Throughout the code, uppercase `OKF` refers to the format and lowercase
`okf` to the tool — notably `okf_version` in every generated concept's
frontmatter is the *format's* version, and is part of the on-disk contract that
existing bundles and their readers depend on.

## What has changed

**Nothing but the repository name.** The Python package is still `okf/`, the
console script is still `okf`, and the distribution is still `okf-generator`.
Renaming those is a separate decision: it would touch roughly 3,500 occurrences
across 211 files, would need a new PyPI name, and would break the `okf mcp`
invocations in any existing MCP client configuration.

## Why this fork exists

Upstream's last commit and last release were both 2026-08-01. Several defects
that cost real data were found independently while using it at scale, and some
are already filed upstream and unfixed:

- `Path.with_suffix(".md")` truncates a dotted leaf name, so
  `_dependencies/maven/org.apache.flink:flink-avro` is written as
  `org.apache.md` and silently overwrites its siblings. On two measured repos
  this accounted for 270 of 293 and 61 of 152 lost concepts.
- Two symbols whose names differ only in case collide on a case-insensitive
  filesystem, and which one survives is decided by thread scheduling — so a
  bundle is not reproducible, and differs between macOS and Linux.
- `okf generate --help` runs a full scan and writes a bundle instead of printing
  usage ([upstream #10](https://github.com/UmairBaig8/okf-generator/issues/10)).

None of these are visible from a generated bundle: an overwritten concept leaves
no trace, and the directory index still lists it under its untruncated name.

Forking is not a judgement on the upstream project, which is MIT precisely so
that it can be carried on. Patches that make sense upstream should be offered
there.
