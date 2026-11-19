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
    out = generator_path(_concept(cid), Path("/b"))
    assert out == Path("/b", *cid.split("/")[:-1], cid.split("/")[-1] + ".md")


@pytest.mark.parametrize("cid", DOTTED_IDS)
def test_update_path_matches_generator(cid):
    assert update_path(cid, Path("/b")) == generator_path(_concept(cid), Path("/b"))


def test_plain_ids_unchanged():
    assert generator_path(_concept("src/app/run"), Path("/b")) == Path("/b/src/app/run.md")


def test_dotted_ids_never_share_a_path():
    paths = {generator_path(_concept(cid), Path("/b")) for cid in DOTTED_IDS}
    assert len(paths) == len(DOTTED_IDS)


def test_path_round_trips_to_concept_id():
    # Readers (lookup, update, sqlite) recover the id with rel.with_suffix("").
    for cid in DOTTED_IDS:
        rel = generator_path(_concept(cid), Path("/b")).relative_to("/b")
        assert str(rel.with_suffix("")) == cid


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
