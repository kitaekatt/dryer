import pytest

from dryer.discover import iter_source_files, language_of
from dryer.scan import find_duplicates, scan_files

LEFT = """\
#include <vector>

int Board::alpha(std::vector<int> xs) {
  auto ys = filter(xs, odd);
  ys.push_back(7);
  for (int i = 0; i < 3; ++i) {
    std::sort(ys.begin(), ys.end());
  }
  return map(ys, inc);
}
"""

RIGHT = """\
int Panel::beta(std::vector<int> items) {
  auto kept = filter(items, even);
  kept.push_back(9);
  for (int k = 0; k < 8; ++k) {
    std::sort(kept.begin(), kept.end());
  }
  return map(kept, dec);
}
"""

NEAR_MISS = """\
int Panel::gamma(std::vector<int> items) {
  auto kept = select(items, even);
  kept.emplace_back(9);
  while (!kept.empty()) {
    std::stable_sort(kept.begin(), kept.end());
    kept.pop_back();
  }
  return reduce(kept, dec);
}
"""


def run(root, threshold):
    entries, warnings = scan_files(iter_source_files([root]), root, min_lines=1, min_nodes=1)
    assert warnings == []
    return find_duplicates(entries, threshold=threshold)


@pytest.mark.parametrize(
    "name", ["a.cpp", "a.h", "a.hpp", "a.cc", "a.cxx", "a.hh"]
)
def test_cpp_extensions(name):
    assert language_of(name) == "cpp"


def test_renamed_cpp_functions_are_reported(tmp_path):
    (tmp_path / "left.cpp").write_text(LEFT)
    (tmp_path / "right.cc").write_text(RIGHT)
    found = run(tmp_path, 0.99)
    assert [(i.language, i.left.file, i.right.file, i.score) for i in found] == [
        ("cpp", "left.cpp", "right.cc", 1.0)
    ]


def test_header_class_methods_are_compared(tmp_path):
    (tmp_path / "a.hpp").write_text(
        "class A {\n public:\n  int a(int xs) { return filter(xs, odd); }\n};\n"
    )
    (tmp_path / "b.h").write_text("int b(int items) { return filter(items, even); }\n")
    found = run(tmp_path, 0.99)
    assert len(found) == 1
    assert found[0].score == 1.0


def test_a_different_cpp_body_is_not_reported(tmp_path):
    (tmp_path / "left.cpp").write_text(LEFT)
    (tmp_path / "near.cpp").write_text(NEAR_MISS)
    assert run(tmp_path, 0.9) == []


def test_a_qualified_callee_name_stays(tmp_path):
    (tmp_path / "a.cpp").write_text("void a() { std::sort(v); }\n")
    (tmp_path / "b.cpp").write_text("void b() { std::stable_sort(v); }\n")
    found = run(tmp_path, 0.0)
    assert len(found) == 1
    assert found[0].score < 1.0


def test_lambdas_stay_inside_the_enclosing_function(tmp_path):
    (tmp_path / "a.cpp").write_text(
        "void a() { auto f = [](int q) { return q + 1; }; use(f); }\n"
    )
    (tmp_path / "b.cpp").write_text(
        "void b() { auto g = [](int r) { return r + 1; }; use(g); }\n"
    )
    found = run(tmp_path, 0.99)
    assert len(found) == 1
    assert (found[0].left.start_line, found[0].left.end_line) == (1, 1)
