# Plan: nested-class-rebase

## What Sean asked for
Follow up on upstream [custom-components/pyscript#907](https://github.com/custom-components/pyscript/pull/907), the nested class fix.

## What we found
- The maintainer approved #907 and asked for two things:
  1. **Rebase onto current `master`.** GitHub shows #907 as conflicting. Only `tests/test_unit_eval.py` conflicts: the #906 tests were also added at the end of that file. The `eval.py` change still applies cleanly.
  2. **One docstring:** `test_nested_class_bare_name_in_method` pins behaviour that differs from real Python (#902 lists it as a known limit). Its docstring should say it documents current behaviour, not the intended one.
- Since that review, two more PRs merged upstream (#908 and #909). We tried the rebase on top of them too: the same file conflicts, in the same way (both sides only add tests at the end of the file).
- The maintainer also checked more cases against real Python and found the fix covers them. No code change was asked for.

## What we'll change
1. **Rebase the fix commit onto upstream's latest `master`.** Keep both the new upstream tests and ours in `tests/test_unit_eval.py`; nothing else changes. *Check:* the `eval.py` change is the same as in #907, and every upstream test is still there.
2. **Update the docstring** of `test_nested_class_bare_name_in_method` to say it pins current pyscript behaviour, which differs from Python (a known limit listed in #902), so nobody mistakes it for the intended behaviour. *Check:* the reviewer's wording request is met; the test is unchanged otherwise.
3. **All project checks** on Python 3.14, as CI runs them: `pytest`, `ruff check`, `ruff format --check`, `pylint`, `mypy`, `codespell`. *Check:* all pass; the new tests still fail without the `eval.py` change.
4. **Update #907.** After your final approval, the rebased commit replaces the old one on the fork branch `fix-nested-class-attr`, which #907 uses. Rebasing means replacing the branch's history (a "force push"); that's what the maintainer asked for, and only #907 uses that branch. You'll also get a short reply to paste on #907, because the app can't write on the upstream repo.

## Contribution rules that apply
- `docs/contributing.rst` and `tests/README.md`: dev setup from `tests/requirements_test.txt`, pre-commit hooks, `pytest`, PRs from a fork.
- Pre-commit runs ruff (check and format, line length 109), codespell, pylint and mypy. CI (`validate.yml`, Python 3.14) runs hassfest, ruff, pytest with coverage, pylint and mypy.
- No PR template; we follow the maintainer's habits: one small fix per PR, with tests. Commits are signed off.

## Who's on it
Engineer, Security Officer and Auditor. Research and the plan check are skipped: this is a small, mechanical follow-up and we already did the trial rebase. QA is skipped too (the Auditor runs the tests). No second security review: nothing security-related is touched.

## Risks
- **Upstream moves again** before we push. We'll check right before pushing and redo the rebase if needed.
- **The maintainer re-reviews.** A new commit on #907 may need their approval again; they asked for it, so that's expected.

## Out of scope
- Any change to how the fix works.
- Making methods stop seeing nested classes by bare name (a Python difference, but changing it could break scripts).
