"""A dotted leaf in a concept_id must survive into its file name.

``Path.with_suffix(".md")`` replaces everything from the leaf's last dot, so
``_dependencies/maven/org.apache.flink:flink-avro`` was written as
``_dependencies/maven/org.apache.md`` and every Maven dependency sharing a
groupId prefix overwrote the previous one. Measured on DataSQRL/sqrl 0.12.4:
304 Maven dependency concepts collapsed into 35 files.
"""

from pathlib import Path

import pytest

from okf.generator import _concept_output_path as generator_path
from okf.parsers.base import Concept
from okf.update import _concept_output_path as update_path

DOTTED_IDS = [
    "_dependencies/maven/org.apache.flink:flink-avro",
    "_dependencies/maven/org.apache.flink:flink-table-planner_2.12",
    "_dependencies/maven/org.apache.flink:flink-table-planner_2.12_1",
    "documentation/docusaurus.config",
]


def _concept(cid: str) -> Concept:
    return Concept(concept_id=cid, type="Dependency", title=cid, description="", resource="")


@pytest.mark.parametrize("cid", DOTTED_IDS)
def test_generator_path_appends_md(cid):
    # The whole leaf survives (':' escaped as %3A, see below), then .md is appended.
    leaf = cid.split("/")[-1].replace(":", "%3A")
    out = generator_path(_concept(cid), Path("/b"))
    assert out == Path("/b", *cid.split("/")[:-1], leaf + ".md")


@pytest.mark.parametrize("cid", DOTTED_IDS)
def test_update_path_matches_generator(cid):
    assert update_path(cid, Path("/b")) == generator_path(_concept(cid), Path("/b"))


def test_plain_ids_unchanged():
    assert generator_path(_concept("src/app/run"), Path("/b")) == Path("/b/src/app/run.md")


def test_dotted_ids_never_share_a_path():
    paths = {generator_path(_concept(cid), Path("/b")) for cid in DOTTED_IDS}
    assert len(paths) == len(DOTTED_IDS)


def test_path_round_trips_to_concept_id():
    # Readers (lookup, pairs, update, sqlite, migrate) recover the id this way.
    from okf.bundle_paths import concept_id_from_path
    for cid in DOTTED_IDS:
        rel = generator_path(_concept(cid), Path("/b")).relative_to("/b")
        assert concept_id_from_path(rel) == cid


def test_maven_dependencies_all_written(tmp_path):
    """End to end: every dependency in a pom.xml gets its own file."""
    from okf.generator import _dedup_concept_ids, scan_codebase, write_bundle

    src = tmp_path / "repo"
    src.mkdir()
    deps = "".join(
        f"<dependency><groupId>{g}</groupId><artifactId>{a}</artifactId>"
        f"<version>1.0</version></dependency>"
        for g, a in [
            ("org.apache.flink", "flink-avro"),
            ("org.apache.flink", "flink-core"),
            ("org.apache.kafka", "kafka-clients"),
            ("org.junit", "junit-bom"),
        ]
    )
    (src / "pom.xml").write_text(
        f"<project><modelVersion>4.0.0</modelVersion><dependencies>{deps}</dependencies></project>"
    )
    concepts = _dedup_concept_ids(scan_codebase(src))
    dep_ids = {c.concept_id for c in concepts if c.type == "Dependency"}
    assert len(dep_ids) == 4, dep_ids

    bundle = tmp_path / "bundle"
    write_bundle(concepts=concepts, output_dir=bundle, bundle_name="repo",
                 log_entries=["test"], source_root=str(src))
    written = {
        line.split(":", 1)[1].strip().strip('"')
        for md in bundle.rglob("*.md")
        for line in md.read_text().splitlines()
        if line.startswith("concept_id:")
    }
    assert dep_ids <= written, dep_ids - written


# ---------------------------------------------------------------------------
# Characters a file name cannot hold on every filesystem
# ---------------------------------------------------------------------------
# A Maven or Gradle dependency id is groupId:artifactId. NTFS forbids ':' (and
# " * < > ? |), and actions/upload-artifact refuses to upload such a path, so
# the file name escapes them while the concept_id in frontmatter keeps them.

FORBIDDEN = '"*:<>?|'


def test_file_name_has_no_forbidden_characters():
    out = generator_path(_concept("_dependencies/gradle/com.google.code.gson:gson"), Path("/b"))
    assert out == Path("/b/_dependencies/gradle/com.google.code.gson%3Agson.md")
    assert not set(out.name) & set(FORBIDDEN)


@pytest.mark.parametrize("cid", [
    "_dependencies/maven/org.junit:junit-bom",
    "a/odd%name",                  # '%' itself escaped, so decoding is exact
    "a/already%3Aescaped",         # must not decode to "a/already:escaped"
    'a/every"*:<>?|char',
    "plain/id",
])
def test_path_round_trips_with_escapes(cid):
    from okf.bundle_paths import concept_id_from_path
    rel = generator_path(_concept(cid), Path("/b")).relative_to("/b")
    assert not set(str(rel)) & set(FORBIDDEN)
    assert concept_id_from_path(rel) == cid


def test_readers_recover_escaped_id(tmp_path):
    """lookup, pairs and update read the id back from the escaped file name."""
    from okf.generator import _dedup_concept_ids, scan_codebase, write_bundle
    from okf.lookup import load_bundle
    from okf.pairs import load_bundle as pairs_load
    from okf.update import _load_concepts_from_bundle

    src = tmp_path / "repo"
    src.mkdir()
    (src / "pom.xml").write_text(
        "<project><dependencies><dependency><groupId>org.junit</groupId>"
        "<artifactId>junit-bom</artifactId><version>5</version></dependency>"
        "</dependencies></project>"
    )
    bundle = tmp_path / "bundle"
    write_bundle(concepts=_dedup_concept_ids(scan_codebase(src)), output_dir=bundle,
                 bundle_name="repo", log_entries=["t"], source_root=str(src))
    cid = "_dependencies/maven/org.junit:junit-bom"
    assert (bundle / "_dependencies/maven/org.junit%3Ajunit-bom.md").is_file()
    assert cid in {c["concept_id"] for c in load_bundle(bundle)}
    assert cid in {c["concept_id"] for c in pairs_load(bundle)}
    assert cid in _load_concepts_from_bundle(bundle)


def test_dir_index_links_resolve_to_escaped_file(tmp_path):
    from okf.generator import render_dir_index
    c = _concept("_dependencies/maven/org.junit:junit-bom")
    out = render_dir_index("_dependencies/maven", [], [c], "repo", {c.concept_id: c})
    # The file is org.junit%3Ajunit-bom.md; as a link target '%' is itself escaped.
    assert "](org.junit%253Ajunit-bom.md)" in out
