# Plan: rebase-916

## What Sean asked for
"go ahead and rebase #916 onto master"

## What we found
- Upstream master is now `13af32c`, after #917 (generator expressions) and #912 (`del obj.attr`) were merged.
- #916 (`fix-class-init-super-891`, `ae58351`) now conflicts, but only in `tests/test_unit_eval.py`. #916 and #917 both added tests at the end of that file, so there are three conflicting spots, all where the new tests meet. `eval.py` and `docs/reference.rst` merge cleanly.
- Nobody has asked for this yet; it's a heads-up rebase, so the maintainer can merge #916 without asking.

## What we'll change
1. **Rebase #916 onto upstream master** (`13af32c`).
   - In `tests/test_unit_eval.py`, keep every upstream test unchanged, including #917's generator expression tests, and put #916's tests after them.
   - Code and docs come over unchanged.
   - It stays one commit, with the same message and sign-off.
   *Check:* the range-diff against `ae58351` shows only where the tests sit, and no upstream test line is removed.
2. **Check #916 and #917 together.** Both are now in the same interpreter, so we try them in combination and compare with real Python:
   - `super()` and `Base.__init__` used inside generator expressions in methods;
   - generator expressions inside `__init__` and in class bodies;
   - classes created inside generator expression elements.
   If something breaks only because both changes are present, we fix it in the same commit and tell you in the report.
   *Check:* the combinations match Python, or the report explains any difference.
3. **Checks:** the full test suite, the pre-commit checks (ruff, codespell, yamllint, pylint, mypy) and the docs build (`sphinx-build -W`), on Python 3.14 as upstream CI uses.
4. **Update the PR.** After your final approval, the team replaces `fix-class-init-super-891` with the rebased commit. It uses a guarded force push that only goes through if the branch still holds `ae58351`. This is the first time the team does this itself. If it's still refused, you'll get the one-line command instead. If the description needs anything, you'll get the full new text. You'll also get a short reply to paste. This plan file doesn't go upstream.

## Contribution rules that apply
- `docs/contributing.rst` and `tests/README.md`: run the tests and pre-commit hooks; PRs come from a fork. There's no CONTRIBUTING.md or PR template.
- We follow the maintainer's habits: a focused rebase with no unrelated changes, and every commit signed off.

## Who's on it
Engineer, Security Officer and Auditor. This is a small job: research and QA are skipped (the Auditor and Engineer run the tests), and so is the plan check. No second security review, because nothing security-related is touched.

## Risks
- **Upstream moves again before the push.** We check right before pushing, and redo the rebase if needed.
- **#918 depends on #916,** and #910 and #911 also add tests at the end of the same file. Whichever merges next may need another small rebase.

## Out of scope
- Any change to #916 beyond the rebase and anything step 2 forces.
- #918, which stays as it is until #916 merges, as Sean decided.

---

## Record (2026-11-21)

**Status:** built and checked, with nothing open. Not yet sent to #916.

**What's ready:** `team/rebase-916-891`, one commit `32c18f1` on upstream master `06f8eba`. While we worked, master moved twice: to `13af32c` (#917, #912), then to `06f8eba` (#910). The plan's "upstream moves" step covered both.
- `tests/test_unit_eval.py`: upstream's tests are unchanged, including those from #917 and #910, and #916's come after them.
- **One fix that exists only because #916 and #917 are both in:** inside a generator expression's element, a zero-argument `super()` used the method's `self`. Python uses the generator's own first argument, its outermost iterator, so pyscript could silently call a parent method on the wrong object.
  - Now it matches Python: `genexp_iter` is set in `ast_generatorexp`, saved and cleared around function calls, and used by `super_args`.
  - Two new scripts in #916's CPython-compared test cover an element, a condition, the outermost iterable, nested generator expressions and a plain function.
- Apart from that fix, the code and docs are the same as `ae58351`.

**Checks (Python 3.14, shared test setup):**
- The full suite has 222 tests, and all pass. The pre-commit checks and the docs build pass.
- Comparisons with Python matched for `super()` and `Base.__init__` inside generator expressions, generator expressions in `__init__` and class bodies, classes created in elements, and #910's wrapped methods and `__init__` with `super()`.

**Review rounds:**
- Security: clear.
- Audit round 1: one must-fix (the `super()` case above). It was fixed by the Engineer.
- Audit round 2: approved.

**Pre-existing, left alone:**
- A class body's own generator expression using `super()` gives `RuntimeError` where Python gives `TypeError`. That's rare, and it was the same before this job.
- `lambda: C(10)` with a pyscript class that has an `__init__` fails. It does on plain master too, and it's noted for a later batch.
- A generator expression element that waits still raises #917's clear error.

**Skipped:** research and QA (the Engineer and the Auditor ran the full suite), and the plan check (small job).
