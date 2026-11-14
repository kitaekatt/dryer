import pytest

from dryer.discover import iter_source_files, language_of
from dryer.scan import find_duplicates, scan_files

LEFT = """\
export function alpha(xs) {
  const ys = filter(xs, odd);
  ys.push(inc);
  for (const y of ys) {
    console.log("seen", y.total);
  }
  return map(ys, inc);
}
"""

RIGHT = """\
function beta(items) {
  const kept = filter(items, even);
  kept.push(dec);
  for (const k of kept) {
    console.log("other", k.count);
  }
  return map(kept, dec);
}
"""

NEAR_MISS = """\
function gamma(items) {
  const kept = select(items, even);
  kept.unshift(dec);
  while (kept.length > 3) {
    console.warn("other");
    kept.pop();
  }
  return reduce(kept, dec);
}
"""


def run(root, threshold):
    entries, warnings = scan_files(iter_source_files([root]), root, min_lines=1, min_nodes=1)
    assert warnings == []
    return find_duplicates(entries, threshold=threshold)


@pytest.mark.parametrize("name", ["a.js", "a.jsx", "a.mjs", "a.cjs"])
def test_javascript_extensions(name):
    assert language_of(name) == "javascript"


def test_renamed_javascript_functions_are_reported(tmp_path):
    (tmp_path / "left.js").write_text(LEFT)
    (tmp_path / "right.mjs").write_text(RIGHT)
    found = run(tmp_path, 0.99)
    assert [(i.language, i.left.file, i.right.file, i.score) for i in found] == [
        ("javascript", "left.js", "right.mjs", 1.0)
    ]


def test_jsx_components_and_class_methods_are_compared(tmp_path):
    (tmp_path / "a.jsx").write_text(
        "export const Alpha = (props) => {\n  const v = use(props.a);\n"
        "  return <div className=\"x\">{v}</div>;\n};\n"
    )
    (tmp_path / "b.jsx").write_text(
        "export const Beta = (p) => {\n  const w = use(p.b);\n"
        "  return <div className=\"y\">{w}</div>;\n};\n"
    )
    (tmp_path / "c.cjs").write_text("class K {\n  m(xs) { return filter(xs, odd); }\n}\n")
    (tmp_path / "d.cjs").write_text("class L {\n  n(ys) { return filter(ys, even); }\n}\n")
    found = run(tmp_path, 0.99)
    assert sorted((i.left.file, i.right.file) for i in found) == [
        ("a.jsx", "b.jsx"),
        ("c.cjs", "d.cjs"),
    ]


def test_a_different_javascript_body_is_not_reported(tmp_path):
    (tmp_path / "left.js").write_text(LEFT)
    (tmp_path / "near.js").write_text(NEAR_MISS)
    assert run(tmp_path, 0.9) == []


def test_a_different_method_name_lowers_the_score(tmp_path):
    (tmp_path / "a.js").write_text("function a(xs) { return xs.filter(odd); }\n")
    (tmp_path / "b.js").write_text("function b(items) { return items.select(even); }\n")
    found = run(tmp_path, 0.0)
    assert len(found) == 1
    assert found[0].score < 1.0


def test_callbacks_stay_inside_the_enclosing_function(tmp_path):
    (tmp_path / "a.js").write_text("function a(xs) { return xs.map(function (q) { return q; }); }\n")
    (tmp_path / "b.js").write_text("function b(ys) { return ys.map(function (r) { return r; }); }\n")
    found = run(tmp_path, 0.99)
    assert len(found) == 1


def test_javascript_test_files_are_skipped(tmp_path):
    (tmp_path / "a.test.js").write_text(LEFT)
    (tmp_path / "b.spec.mjs").write_text(RIGHT)
    assert iter_source_files([tmp_path]) == []
