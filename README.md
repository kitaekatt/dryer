# dryer

dryer finds candidate duplicate code in Clojure, Java, Go, TypeScript, Rust, and Python. One run detects the language of each source file, normalizes that language's forms, and reports pairs whose structure is close enough to review.

Clojure follows [dry4clj](https://github.com/unclebob/dry4clj). The other languages use the same idea on the functions and methods [crapper](https://github.com/unclebob/crapper) and [mutator](https://github.com/unclebob/mutator) already treat as one unit. A form is only compared with forms written in the same language.

The score is Jaccard similarity of structural fingerprints:

```text
score = shared fingerprints / all fingerprints seen in either form
```

A score of `1.0` means the normalized structures have the same fingerprint set. The default `--threshold 0.82` reports candidates close enough to be worth review.

These two functions score `1.0`. The names, locals, predicates, and mapped functions differ, and those incidental symbols normalize away. A default run still skips them: they are three lines, and the default minimum is four.

```clojure
(defn alpha [xs]
  (let [ys (filter odd? xs)]
    (map inc ys)))

(defn beta [items]
  (let [kept (filter even? items)]
    (map dec kept)))
```

The same shape in the other languages scores `1.0` too: the called function or method stays, and the locals do not.

```java
int alpha(int[] xs) {
  int[] ys = filter(xs, odd);
  return map(ys, inc);
}
```

```python
def beta(items):
    kept = filter(items, even)
    return map(kept, dec)
```

What stays is the call or method name, the operator, and the shape of the tree. What drops out is the local name, the field name, the literal, and the keyword. A Clojure keyword call `(:kind m)` and `(:id row)` is the same shape. So is `order.total` and `row.amount`.

## Run

```bash
./dryer
```

The first run creates `.venv` and installs the tool. From a project root it walks the tree, skips `test`, `spec`, `vendor`, `node_modules`, and `target`, and writes two results:

- a report on stdout, closest match first
- `.metrics/dry.edn`, replaced on every successful analysis

```bash
./dryer src/demo src/ui          # these files and trees
./dryer --changed                # git additions and edits
./dryer billing                  # path fragment
./dryer --threshold 0.9 src
./dryer --edn --min-lines 3 src
./dryer --exclude bootstrap_guard.py --exclude 'generated/*'
```

```text
--threshold N    Minimum structural similarity score, default 0.82
--min-lines N    Minimum source lines in a candidate form, default 4
--min-nodes N    Minimum normalized syntax nodes, default 20
--exclude GLOB   Leave out matching files, may be repeated
--group-identical  Report identical forms (score 1.00) once as a group
--format F       text or edn, default text
--edn            Same as --format edn
--text           Same as --format text
```

Normalized syntax nodes are the structural pieces left after incidental names and literals are replaced. `--min-nodes` drops forms smaller than that before comparison.

`--exclude` takes a glob that is matched against each file's path relative to the project root (`--root`, default the current directory) and against its bare file name, so `--exclude bootstrap_guard.py` leaves out that file in every directory and `--exclude 'generated/*'` leaves out a tree. `*` also matches `/`. A pattern must match the whole path or the whole name. It applies to files named on the command line too. Use it for a file that is copied on purpose, such as a vendored helper. Quote the pattern so the shell does not expand it.

`--group-identical` reports forms with identical structure (score `1.00`) once per set instead of once per pair, so `N` copies of a form give one candidate, not `N*(N-1)/2`. Candidates below `1.00` are unchanged, and so is a set of exactly two. A group lists every copy in text output (`DUPLICATE score=1.00 copies=3`), and in EDN the first two copies are `:left` and `:right` and the rest are in `:others`, a key present only for a group of three or more.

Default text output for the invoice and receipt from dry4clj. They differ by one extra binding:

```text
DUPLICATE score=0.89
  src/billing/invoice.clj:3-13
  src/billing/receipt.clj:3-14
```

`.metrics/dry.edn` is the same report dry4clj prints as EDN, with the language added:

```clojure
{:candidates
 [{:score 0.890909090909
   :language "clojure"
   :left {:file "src/billing/invoice.clj", :start-line 3, :end-line 13}
   :right {:file "src/billing/receipt.clj", :start-line 3, :end-line 14}
   :left-nodes 158
   :right-nodes 166}]}
```

## What each language compares

| Language | Candidate | Left out |
| --- | --- | --- |
| Clojure | every top-level form except `ns` | reader-conditional branches other than `:clj` |
| Java | methods with a body | constructors, abstract methods, methods inside anonymous or local classes |
| Go | functions and methods with a body | function literals stay inside the enclosing function |
| TypeScript | functions, methods, and top-level arrow functions | callbacks nested inside another function |
| Rust | functions and methods with a body | functions inside `mod tests`, and closures |
| Python | functions and methods | functions nested inside another function |
| GDScript (`.gd`) | functions, constructors, and inner-class methods | lambdas, which stay inside the enclosing function |
| C++ (`.cpp` `.cc` `.cxx` `.hpp` `.hh` `.h`) | functions, methods, constructors, and destructors with a body | lambdas, `= default` and `= delete` members, and classes defined inside a function |

Clojure reader conditionals keep the `:clj` branch, as dry4clj does. Syntax-quote is kept as a `syntax-quote` form rather than expanded.

A missing or unreadable Clojure form is reported on stderr. Forms read before it are still compared. The run exits `0` after a report, `1` on a usage error, and `2` on an unknown `--format`.

## Development

```bash
python3 -m venv .venv
.venv/bin/pip install -e '.[dev]'
.venv/bin/pytest
```
