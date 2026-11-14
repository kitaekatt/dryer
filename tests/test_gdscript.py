from pathlib import Path

from dryer.discover import iter_source_files, language_of
from dryer.scan import find_duplicates, scan_files

LEFT = """\
extends Node

func alpha(xs):
\tvar ys = filter(xs, odd)
\tys.append(inc)
\tfor y in ys:
\t\tprint("seen")
\treturn map(ys, inc)
"""

RIGHT = """\
extends Control

func beta(items):
\tvar kept = filter(items, even)
\tkept.append(dec)
\tfor k in kept:
\t\tprint("other")
\treturn map(kept, dec)
"""

NEAR_MISS = """\
extends Control

func gamma(items):
\tvar kept = select(items, even)
\tkept.erase(dec)
\twhile kept.size() > 3:
\t\tkept.pop_back()
\treturn reduce(kept, dec)
"""


def write(root: Path, name: str, text: str) -> None:
    (root / name).write_text(text, encoding="utf-8")


def run(root: Path, threshold: float):
    files = iter_source_files([root])
    entries, warnings = scan_files(files, root, min_lines=1, min_nodes=1)
    assert warnings == []
    return find_duplicates(entries, threshold=threshold)


def test_gd_extension_is_gdscript():
    assert language_of("player.gd") == "gdscript"


def test_renamed_gdscript_functions_are_reported(tmp_path):
    write(tmp_path, "left.gd", LEFT)
    write(tmp_path, "right.gd", RIGHT)
    found = run(tmp_path, 0.99)
    assert [(i.language, i.left.file, i.right.file, i.score) for i in found] == [
        ("gdscript", "left.gd", "right.gd", 1.0)
    ]


def test_a_different_gdscript_body_is_not_reported(tmp_path):
    write(tmp_path, "left.gd", LEFT)
    write(tmp_path, "near.gd", NEAR_MISS)
    assert run(tmp_path, 0.9) == []


def test_a_different_method_name_lowers_the_score(tmp_path):
    write(tmp_path, "a.gd", "func a(xs):\n\txs.append(1)\n")
    write(tmp_path, "b.gd", "func b(items):\n\titems.erase(1)\n")
    found = run(tmp_path, 0.0)
    assert len(found) == 1
    assert found[0].score < 1.0


def test_inner_class_methods_are_compared(tmp_path):
    write(tmp_path, "a.gd", "class A:\n\tfunc a(xs):\n\t\treturn filter(xs, odd)\n")
    write(tmp_path, "b.gd", "func b(items):\n\treturn filter(items, even)\n")
    found = run(tmp_path, 0.99)
    assert len(found) == 1
    assert found[0].score == 1.0
