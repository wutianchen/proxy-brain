# Ideas

Where to take the core of slim-okf-generator once `serve` and `mcp` move into
[proxied-brain](https://github.com/wutianchen/proxied-brain).

The core is one function: **a source tree in, a correct, pinned, citable set of
concepts out.** Each idea below either makes that output trustworthy, or removes
a correction proxied-brain currently has to make after the fact. They are drawn
from proxied-brain's glossary (`terminology.md`), its measurement of what okf
loses (`docs/research/okf-concept-gap.md`), and the okf-to-locator conversion it
already had to write (`proxied_brain/okf.py`, proxied-brain #166).

## 1. Make the output correct

**Fix the three path collisions.** On DataSQRL/sqrl 0.12.4, okf reported 8,655
concepts and wrote 8,362. On traefik it reported 13,300 and wrote 13,148. Every
missing concept was parsed, rendered, and then overwritten by another, with no
warning. There are three causes:

| cause | sqrl | traefik | status |
|---|---:|---:|---|
| `Path.with_suffix(".md")` cuts a dotted leaf name short | 270 | 61 | **fixed** |
| names differing only in case collide on a case-insensitive filesystem (macOS, Windows) | 15 | 81 | open |
| a directory's `index.md` overwrites a concept with the same path | 8 | 10 | open |

**Refuse to write two concepts to one path.** Each cause above is a small fix.
The lasting fix is a check in the writer: if two `concept_id`s map to the same
file, fail loudly. Then the next collision is a loud error instead of a silent
loss.

**Write a manifest that proves the bundle is complete.** Emit `_manifest.json`
mapping every `concept_id` to its path, with the counts. proxied-brain found the
gap "cannot be computed from the bundle on disk", so today it re-runs okf's scan
to find out what should be there. With a manifest, checking a bundle means
reading one file.

**Make the output reproducible.** The same commit should produce a byte-identical
bundle on macOS and Linux:

- nothing that depends on thread timing (today, which case-colliding concept
  survives depends on which thread wrote last);
- no timestamps in the output;
- a deterministic order for the `_N` suffixes added to duplicate ids.

Back it with a golden test that runs in CI on both operating systems.

## 2. Emit what proxied-brain consumes

**Pin to the exact commit.** The bundle currently records `git:branch:HEAD`,
which is the ref okf failed to resolve. Resolve the commit SHA and the GitHub
owner/repo instead, and give every concept a
`gh:<owner>/<repo>@<sha>:<path>#L<a>-L<b>` address. Most of
`proxied_brain/okf.py` then becomes unnecessary.

**Suggest a quote for each concept.** In proxied-brain the quote is "the only
field anything proves": it is what makes drift detectable. The generator already
has the parse tree, so it can propose a line that:

- appears exactly once in the file,
- is under ~80 characters,
- is not trivial (`}`, `import (`).

The signature line is usually that line. Every generated concept would then be
drift-checkable from the day it is generated, where today each arrives as an
unread entry with no quote.

**Give dependencies a real address.** `Dependency` and `Resource` concepts get
no locator (53 and 7 on sqrl), because "the whole `pom.xml`" says nothing about
any one dependency. The manifest scanner already parses those files, so it can
record the lines of each `<dependency>` block or `FROM` instruction, and they
become ranged locators like any other concept.

**Add a machine-readable output mode.** `okf generate --format jsonl` would
stream one JSON object per concept and skip markdown. Reading okf's markdown
back costs proxied-brain 2.07s, against 0.06s to build its whole index. When the
consumer is a program, the markdown step is pure overhead.

## 3. Support releases and overlays

**Keep concept ids stable across releases.** A proxied-brain overlay replaces a
base entry by `id`, so a function must keep its id from one release to the
next. Today the `_N` suffix depends on scan order and can shift between
releases. Distinguishing overloads by a short hash of the signature would keep
ids stable.

**Generate an overlay directly.** `okf diff` compares two bundles that already
exist. `okf generate --since <ref>` would emit only the concepts added, changed
or removed between two commits, with an explicit marker for removals. That is
proxied-brain's overlay model, where later releases carry only what changed, and
it gives refresh a list of what to re-check.

## 4. Index documentation, not only code

proxied-brain also indexes documentation (`doc:` sources). A markdown and HTML
parser could turn each heading section into a concept, anchored by the
heading's fragment plus a quote. Same model, applied to docs.

## 5. Live up to "slim"

**Cut what is not core.** Candidates: `visualize`, `dashboard`, `ask`, `agent`,
`pairs`, `enrich`, and the bundled web templates. That trims the dependency
list and roughly halves the ~11k lines in `okf/`.

**Make the language grammars optional.** Each tree-sitter grammar could become
an install extra, e.g. `slim-okf-generator[go,java]`. Today `tree-sitter-kotlin`
forces a Rust toolchain into the release workflow just to build.

## Suggested order

| # | Work | Why this position |
|---|---|---|
| 1 | remaining collision fixes, the collision check, the manifest | stops the data loss; everything else builds on it |
| 2 | commit pinning and `gh:` addresses | removes most of proxied-brain's conversion code |
| 3 | stable ids and the reproducibility test | overlays depend on them |
| 4 | suggested quotes, dependency line ranges | makes generated concepts checkable for drift |
| 5 | slimming down | easier once the core is tested |
| 6 | JSONL output, `--since` overlays, the docs parser | new capability |
