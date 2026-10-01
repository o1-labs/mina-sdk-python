"""Conformance to the specification in spec/ (a copy of o1-labs/mina-sdk-spec
at the tag in spec/VERSION): the query strings of mina_sdk.daemon.queries are
exactly the documents of spec/operations.graphql, up to white space, and every
document has one. mina-sdk-spec's CI validates the documents against the
daemon's schema.
"""

from __future__ import annotations

import re
from pathlib import Path

from mina_sdk.daemon import queries

ROOT = Path(__file__).resolve().parent.parent


def _tokenize(doc: str) -> list[str]:
    return re.findall(r"[A-Za-z0-9_$]+|[(){}:!,\[\]]", re.sub(r"#[^\n]*", "", doc))


def _operations(doc: str) -> dict[str, list[str]]:
    """The operations of a document, by name, as tokens."""
    toks = _tokenize(doc)
    ops: dict[str, list[str]] = {}
    i = 0
    while i < len(toks):
        name, start = toks[i + 1], i
        depth, seen_body = 0, False
        while True:
            if toks[i] == "{":
                depth += 1
                seen_body = True
            elif toks[i] == "}":
                depth -= 1
            i += 1
            if seen_body and depth == 0:
                break
        assert name not in ops, f"operation {name} twice"
        ops[name] = toks[start:i]
    return ops


def _assert_documents_are_the_spec(spec_file: str, documents: list[str]) -> None:
    spec = _operations((ROOT / spec_file).read_text())
    covered = []
    for doc in documents:
        ops = _operations(doc)
        assert len(ops) == 1, f"one named operation per query string:\n{doc}"
        ((name, toks),) = ops.items()
        assert name in spec, f"{name} is not in {spec_file}"
        assert toks == spec[name], f"{name} differs from {spec_file}"
        covered.append(name)
    assert sorted(covered) == sorted(spec), f"every operation of {spec_file} has one query string"


def test_daemon_queries_are_the_spec_documents():
    _assert_documents_are_the_spec("spec/operations.graphql", queries.ALL_DOCUMENTS)


def test_checker_catches_a_changed_document():
    changed = [d.replace("workIds", "workIdz") for d in queries.ALL_DOCUMENTS]
    try:
        _assert_documents_are_the_spec("spec/operations.graphql", changed)
    except AssertionError as e:
        assert "SnarkPool differs" in str(e)
    else:
        raise AssertionError("a changed document was not found")
