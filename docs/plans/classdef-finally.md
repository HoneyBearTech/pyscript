# Plan: classdef-finally

## What Sean asked for
"start on the class body try/finally fix": the small follow-up found while working on #902.

## What we found
- When a class body raises an error, pyscript never leaves the class's scope (`ast_classdef` in `custom_components/pyscript/eval.py`). It switches into the class's namespace before running the body and switches back only after the body finishes normally.
- Checked on upstream's latest code: with `try: class Foo: raise ValueError ... except ValueError: pass` at the top of a script, a later `x = 5` is stored inside the failed class, not in the script. Real Python stores it in the script.
- Inside a function, the same error leaves pyscript's internal scope stack one entry too long. Upstream issue search found no existing report.
- #902's second commit (not merged yet) changes the same few lines. Whichever PR merges second needs a small, mechanical update.

## What we'll change
1. **`custom_components/pyscript/eval.py`, `ast_classdef`:** wrap the loop that runs the class body in `try`/`finally`, so pyscript always returns to the outer scope, even when the body raises. *Check:* new tests below.
2. **Tests in `tests/test_unit_eval.py`**, each checked against real Python:
   - a class body that raises, caught by `try`/`except` at module level, then later assignments land in the script;
   - the same inside a function, with the function's later locals and return value correct;
   - a nested class whose body raises;
   - an error from a class body that isn't caught: it still reaches the caller, and the next script run is unaffected.
   *Check:* the new tests fail on upstream's current code and pass with step 1.
3. **All project checks** on Python 3.14, as CI runs them: `pytest`, `ruff check`, `ruff format --check`, `pylint`, `mypy`, and `codespell`.
4. **Upstream PR.** After your final approval, one commit goes on a clean branch cut from upstream `master`, holding only the fix and its tests (no plan or notes). You get a prefilled link to open the PR from your account. The PR text mentions that it touches the same lines as #902.

## Contribution rules that apply
- `docs/contributing.rst` and `tests/README.md`: dev setup from `tests/requirements_test.txt`, pre-commit hooks, `pytest`, PRs from a fork.
- Pre-commit runs ruff (check and format, line length 109), codespell, pylint and mypy. CI (`validate.yml`, Python 3.14) runs hassfest, ruff, pytest with coverage, pylint and mypy.
- No PR template; we follow the maintainer's habits: one small fix per PR, with tests. Commits are signed off.

## Who's on it
Engineer, Security Officer and Auditor. Skipped as too small for them: research (done while planning), QA (the Auditor runs the tests), and the plan check (its reviewer's monthly quota is used up). No second security review: nothing security-related is touched.

## Risks
- **Conflict with #902:** both change `ast_classdef`. If #902 merges first, we update this branch (a few lines); if this merges first, #902 gets the same small update.
- **Behaviour change:** only code where a class body raises and the error is caught behaves differently, and it now behaves like Python.

## Out of scope
- A class redefined with a body that raises losing its old value: #902's second commit already fixes that.
- Any other class-body behaviour.

---

## Record (2026-11-20)

**Status:** built and checked, with no open problems. Not yet sent upstream.

**What shipped on this branch:** one commit, `restore the scope when a class body raises` (`5aa2e0b`). It wraps the class-body loop in `ast_classdef` in `try`/`finally` (+9/−7) and adds two tests (+103) compared against CPython 3.14. It applies cleanly to upstream `master` (`8131a78`), and all 204 tests, ruff, pylint, mypy and codespell pass.

**Checks:** the Security Officer reported it clear, and the Auditor approved with no findings. The audit also confirmed that the scope is restored for `return`/`break` in a class body and for task cancellation. Plan check, QA and plain-English check were skipped (job too small; the reviewer's quota was used up).

**Decisions:**
- Cut from upstream `master`, not from #902's branch, so the fix can merge on its own. Whichever of the two merges second needs a small update.
- The class name left bound to an undefined placeholder after a failed body is left alone: #902's second commit handles redefinition, and a first definition already gives NameError, as Python does.
