# Plan: global-path-875

## What Sean asked for
Act on the maintainer's review of upstream PR custom-components/pyscript#902 (the #875 fix): they approved it, and asked whether we want to also fix the `global` path in the same PR or leave it for a follow-up.

## What we found
- The maintainer's three suggested changes fix every `global` case in their comment, but they bring back a problem we removed from #875 earlier: after `from mod import Foo`, a function doing `global Foo; Foo = Other` (or `del Foo`) changes `mod`'s own `Foo`, for every script that imports `mod`. This happens because `from mod import Foo` copies the module's internal wrapper object, so both scripts share one box.
- The same sharing already causes a bug on master today, even without `global`: after `from mod import Foo`, a plain top-level `Foo = Other` or `del Foo` in the importing script changes `mod`'s `Foo`.
- The maintainer's changes also make one case they mention worse: after `global Foo; del Foo`, defining `Foo` again raises `NameError` in functions defined earlier.
- Two small extra changes fix both: `from mod import ...` takes the value out of the wrapper (as real Python does), and a class definition reuses the existing wrapper instead of making a new one. With them, all 202 existing tests pass and about 40 test cases behave like real Python. That covers the maintainer's cases, cross-module imports, closures, and `del` followed by a redefinition.

## Decision: add it to #902
Sean chose to add the `global` fix to #902 itself, as the maintainer offered, rather than send a separate PR. The new commits go on top of the existing #902 commit, so the maintainer reviews only what's new.

## What we'll change
1. **Reply on #902 (Sean posts it, after the new commits are pushed).** A short comment for Sean to post from his account. It thanks the maintainer, says the `global` path is now included, and explains why it has two changes beyond their sketch: the cross-module catch, and redefinition after `del`. It also points out the change to import behaviour. We'll also give Sean an updated description for #902 (the current one ends with an empty "Known limits" heading). *Check:* text reviewed for tone and accuracy before Sean posts it.
2. **`custom_components/pyscript/eval.py`, five small edits:**
   - assigning through `global` updates the existing wrapper instead of replacing it;
   - deleting through `global` marks the wrapper undefined instead of removing it;
   - reading through `global` returns the class, not the wrapper;
   - `from mod import X` and `from mod import *` copy the value, not the wrapper;
   - a class definition reuses an existing wrapper for its name, and keeps the old class visible until the new one is finished (as Python does).
   *Check:* full test suite.
3. **Tests in `tests/test_unit_eval.py`** (or a nearby test file if module imports need it). They cover each case in the maintainer's comment (`|`, `is`, setting an attribute, rebinding, `del`, `del` then redefine), closures, and the cross-module cases (`from mod import Foo` / `import *`, then a rebind or `del` in the importer; a second script still sees the original). Each test is checked against what real Python gives. *Check:* the new tests fail on the current branch and pass with step 2.
4. **All project checks** on Python 3.14, as CI runs them: `pytest`, `ruff check`, `ruff format --check`, `pylint` and `mypy` on `custom_components/pyscript/*.py tests/*.py`, plus codespell from pre-commit.
5. **Update #902.** After the final approval here, push only the code and test commits (no plan or notes) onto the #902 branch (`fix-class-annotation-union-875` on the fork). This updates upstream #902 directly. The existing #902 commit is kept as it is, with no history rewrite or force-push. The commit message credits the maintainer's suggestion, names the import behaviour change, and lists the known limits.

## Contribution rules that apply
- `docs/contributing.rst` points to `tests/README.md`: a dev setup from `tests/requirements_test.txt`, pre-commit hooks, and `pytest`. PRs come from a fork.
- Pre-commit runs ruff (check and format, line length 109), codespell, check-json, yamllint, pylint and mypy. CI (`validate.yml`, Python 3.14) runs hassfest, ruff, pytest with coverage, pylint and mypy.
- No PR template exists. We follow the maintainer's observed habits: small focused PRs, a clear description, and tests for every fix.
- Commits signed off (`git commit -s`), authored as Sean, written as solo work.

## Who's on it
Engineer (code and tests), QA (tests and plan check), Security Officer (leaks and risky code), Auditor (independent review of the logic), and a plain-English check of the report. No second security review: the change doesn't touch credentials, shell commands, the network, setup scripts, CI or dependencies.

## Risks
- **Import behaviour change.** Today `from mod import Foo` keeps following later changes to `Foo` inside `mod`, because both share the wrapper. After this change it takes a snapshot, as Python does. An app that relied on the old behaviour would stop seeing those updates. Code using `mod.Foo` is not affected. This will be stated plainly in the upstream PR.
- **Redefining a class.** The wrapper is reused, so while the new class body runs, the name still means the old class, and if the body fails the old class stays. Real Python does the same. A first-time definition works as it does today. Tests will cover both.
- **The maintainer may prefer their smaller version.** The reply will show the failing cross-module case, so they can judge.
- **#902's approval goes stale.** New commits mean the maintainer reviews again before merging. #902 is wider than it was, which they invited.

## Out of scope (stated as known limits in the upstream PR)
- `import mod` then `mod.Foo | None` or `mod.Foo = Other` (attribute access on a module still hands out the wrapper).
- A lambda or `@pyscript_compile` function reading a module-level class that is later rebound.
- `global Zed; del Zed` on a name that was never defined doesn't raise `NameError`.
- No change to the existing #902 commit.

---

## Record (2026-11-20)

**Status:** built and checked, with no open problems. Not yet pushed to #902.

**What shipped on this branch:** one commit, `update module-level names in place when assigned or deleted through global (#875)`. It changes `eval.py` (+109/−23) and adds tests (+825). It applies cleanly on its own onto #902's commit, and all 204 tests, ruff, pylint, mypy and codespell pass on Python 3.14.

**Decisions:**
- Add the `global` fix to #902 instead of a separate PR (Sean, on this PR).
- A read through `global` leaves an undefined wrapper wrapped, as in the maintainer's sketch, so a class defined through `global` can still name itself in its type hints. Rejected: raising NameError there, which broke code that works today.
- Unwrap on every binding (assignment, imports) and on module attribute reads, so no binding shares another module's wrapper. Rejected: an "owner" field on the wrapper (bigger change, and it left existing leaks).
- Class bodies bind in the class namespace, even inside a function that declares the name `global`.
- Imports inside a function are local to it, as in Python.

**Review rounds:**
- Round 1: the audit found two must-fix regressions: aliases through `mod.Foo` still shared the wrapper, and imports inside a function broke closures. Both fixed.
- Round 2: the audit found class-body import and alias problems and a wrong exception type. All fixed.
- Round 3 (extra round, Sean commented "fix"): the audit found that `global x` written inside a class body was ignored, and that a nested class failed with a custom `__prepare__` mapping. Both are fixed. The final audit found no new problems; it asked for one more known limit in the commit message (a `@pyscript_compile` function defined in a class body under `global`, which upstream already has), and that was added.

**Rejected or deferred findings:**
- `global Zed; del Zed` on a never-defined name doesn't raise. Unchanged from upstream, listed as a known limit.
- `hasattr(mod, "Foo")` after mod deletes `Foo` returns True. Added to the `getattr(mod, ...)` known limit.
- Star import inside a function is accepted. Unchanged from upstream.
- A class body that raises doesn't restore pyscript's scope stack. Unchanged from upstream; worth its own small PR.
- Plan check and plain-English check were skipped (the reviewer's monthly quota was used up).
