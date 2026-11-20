# Plan: global-path-875

## What Sean asked for
Act on the maintainer's review of upstream PR custom-components/pyscript#902 (the #875 fix): they approved it, and asked whether we want to also fix the `global` path in the same PR or leave it for a follow-up.

## What we found
- The maintainer's three suggested changes fix every `global` case in their comment, but they bring back a problem we removed from #875 earlier: after `from mod import Foo`, a function doing `global Foo; Foo = Other` (or `del Foo`) changes `mod`'s own `Foo`, for every script that imports `mod`. This happens because `from mod import Foo` copies the module's internal wrapper object, so both scripts share one box.
- The same sharing already causes a bug on master today, even without `global`: after `from mod import Foo`, a plain top-level `Foo = Other` or `del Foo` in the importing script changes `mod`'s `Foo`.
- The maintainer's changes also make one case they mention worse: after `global Foo; del Foo`, defining `Foo` again raises `NameError` in functions defined earlier.
- Two small extra changes fix both: `from mod import ...` takes the value out of the wrapper (as real Python does), and a class definition reuses the existing wrapper instead of making a new one. With them, all 202 existing tests pass and about 40 test cases behave like real Python. That covers the maintainer's cases, cross-module imports, closures, and `del` followed by a redefinition.

## Recommendation: leave #902 as it is and send this as a follow-up PR
The change is bigger than the maintainer's sketch and changes import behaviour slightly (see Risks), so it deserves its own review. #902 is already approved and can merge now. One fix per PR also matches the project's habits.
(If Sean prefers adding it to #902, comment so on this PR; the work is the same, only the delivery changes.)

## What we'll change
1. **Reply on #902 (Sean posts it).** A short thank-you comment for Sean to post from his account: "please merge as is; the global path follows in a separate PR". It also explains the cross-module catch in their suggestion. *Check:* text reviewed for tone and accuracy before Sean posts it. The PR's description also ends with an empty "Known limits" heading; we'll give Sean one line to fill it in.
2. **`custom_components/pyscript/eval.py`, five small edits:**
   - assigning through `global` updates the existing wrapper instead of replacing it;
   - deleting through `global` marks the wrapper undefined instead of removing it;
   - reading through `global` returns the class, not the wrapper;
   - `from mod import X` and `from mod import *` copy the value, not the wrapper;
   - a class definition reuses an existing wrapper for its name, and keeps the old class visible until the new one is finished (as Python does).
   *Check:* full test suite.
3. **Tests in `tests/test_unit_eval.py`** (or a nearby test file if module imports need it). They cover each case in the maintainer's comment (`|`, `is`, setting an attribute, rebinding, `del`, `del` then redefine), closures, and the cross-module cases (`from mod import Foo` / `import *`, then a rebind or `del` in the importer; a second script still sees the original). Each test is checked against what real Python gives. *Check:* the new tests fail on the current branch and pass with step 2.
4. **All project checks** on Python 3.14, as CI runs them: `pytest`, `ruff check`, `ruff format --check`, `pylint` and `mypy` on `custom_components/pyscript/*.py tests/*.py`, plus codespell from pre-commit.
5. **Upstream PR.** A clean branch on the fork, cut from the #902 branch, holding only the code and test commits (no plan or notes). We also write a prefilled link for Sean to open the upstream PR from his account. Its title and description explain the change, credit the maintainer's suggestion, name the import behaviour change, list the known limits, say it builds on #902, and say "Refs #875". After #902 merges, the branch is rebased onto upstream `master`.

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
- **The maintainer may prefer their smaller version.** The PR text will show the failing cross-module case, so they can judge.

## Out of scope (stated as known limits in the upstream PR)
- `import mod` then `mod.Foo | None` or `mod.Foo = Other` (attribute access on a module still hands out the wrapper).
- A lambda or `@pyscript_compile` function reading a module-level class that is later rebound.
- `global Zed; del Zed` on a name that was never defined doesn't raise `NameError`.
- No change to #902 itself, beyond the description line for Sean.
