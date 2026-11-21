# Plan: issues-batch-2

## What Sean asked for
"look at issues in custom-components/pyscript find me 5 of the most important ones and start fixing them"

## What we found
We went through all 138 open issues and checked each likely bug on upstream's latest `master` (`309a3ff`).
- Most are feature requests, how-to questions, Home Assistant or install problems, or already fixed. About 25 are already fixed on `master` (for example #512, #538, #761, #792, #819 and the blocking-call warnings #608, #612, #619 and #620). Others are covered by open upstream PRs (#899, #896, #907, #908, #869).
- **Only two open issues are real, still-broken bugs that a small fix can solve.** We reproduced both:
  - **#808:** a decorator written with `functools.wraps` loses its own body. Its `try`/`except` never runs, so the error it should catch gets through.
  - **#726:** in an app with subfolders, a correct relative import (`from .a import foo` in `subfolder/b.py`) fails. A reload can also unload part of the app.
- We also found one bug while checking that has no issue yet: `del obj.attr` on a normal object fails with `NameError`, because pyscript treats it as deleting a Home Assistant state.
- Two issues ask for clearer docs, and the maintainer agreed in the threads: logging for apps and scripts (#821, #520, #265), and `watch=` firing only when a value changes (#864).

So the five are two bug fixes, one small bug fix without an issue, and two docs fixes. Generator expressions (#564) are **left out** (see "Out of scope"). We can add them if you want them.

## What we'll change
Each item becomes its own small upstream PR, cut from upstream `master`, with its tests.

1. **#808: decorators that use `functools.wraps`** (`custom_components/pyscript/eval.py`, `tests/test_unit_eval.py`).
   - Before calling a user decorator, pyscript will hand it a wrapped copy of the function. That way `wraps` can't overwrite pyscript's own fields on the decorator's inner function.
   - If the decorator returns the function unchanged, it is unwrapped again.
   - *Check:* new tests cover a `wraps` decorator that catches an error, one that passes arguments through, stacked decorators, one that returns the function unchanged, and that `__wrapped__` is set. Each test fails on today's code and passes with the fix, and each result matches real Python.
2. **#726: relative imports inside an app's subfolders** (`custom_components/pyscript/global_ctx.py`, `tests/test_apps_modules.py`).
   - A module imported as `subfolder.b` will resolve its own relative imports from `subfolder/`, as Python does. Today it uses the app's top folder.
   - This is a one-line change.
   - *Check:* new tests cover the issue's exact example, and confirm that a reload unloads nothing it shouldn't. The PR text will say plainly that scripts using today's workaround (`from .subfolder.a` inside `subfolder/b.py`) need to switch to the normal form.
3. **`del obj.attr` on normal objects** (`custom_components/pyscript/eval.py`, `tests/test_unit_eval.py`).
   - Only names that refer to Home Assistant states (`domain.entity`, `domain.entity.attr`) will be deleted as states.
   - Attributes of normal objects, including `del self.x` in a method, will be deleted like in Python.
   - *Check:* tests cover objects, `self` in methods, a missing attribute (`AttributeError`, as in Python), and the existing state-deletion tests still pass.
4. **Docs: logging** (`docs/reference.rst`, maybe `docs/tutorial.rst`), for #821, #520 and #265.
   - The docs will give the logger names for apps (`custom_components.pyscript.apps.<app>`), scripts and modules.
   - They will add one full `logger:` example: quiet by default, one app at info, one script at debug.
   - *Check:* the docs build cleanly with the project's Sphinx setup, and the logger names match the code.
5. **Docs: `@state_trigger` and repeated values** (`docs/reference.rst`), for #864.
   - The docs will say that `watch=` and trigger expressions fire only when a value changes, so a sensor that repeats the same value doesn't fire them.
   - They will show the workaround from the issue (`watch=["sensor.x.last_updated"]`).
   - *Check:* the docs build cleanly, and the behaviour matches the code (`trigger.py`).
6. **All project checks** on Python 3.14, as CI runs them: `pytest`, `ruff check`, `ruff format --check`, `pylint`, `mypy`, and the pre-commit hooks (including codespell).
7. **Upstream PRs.** After your final approval, each fix goes on its own clean branch from upstream `master`, with a prefilled link for you to open the PR. Each PR description uses "Closes #N" (or no issue for item 3), then what was broken, why, what changed, and testing.

## Contribution rules that apply
- The project has `docs/contributing.rst` and `tests/README.md`, and no CONTRIBUTING.md or PR template. Their rules:
  - Set up the dev environment from `tests/requirements_test.txt`.
  - Run the pre-commit hooks: ruff check and format, codespell, check-json, yamllint, pylint and mypy.
  - Run `pytest`, and send PRs from a fork.
- CI (`validate.yml`, Python 3.14) runs hassfest, ruff, pytest with coverage, pylint and mypy.
- The maintainer's habits: one small fix per PR, with its tests and with a docs change when behaviour changes. Titles name the fix and the issue number. Commits are signed off.

## Who's on it
Three Engineers on separate files, working in parallel:
- one Engineer for items 1 and 3 (`eval.py`, separate parts);
- one for item 2 (`global_ctx.py`);
- one for items 4 and 5 (docs).

After that, QA, the Security Officer and the Auditor review the work. Research is done (above). There's no second security review, because no security-related code is touched.

## Risks
- **#808** changes how every user decorator gets its function. The whole test suite passes with a first version of the fix, and the Auditor will look closely at this item.
- **#726** changes behaviour for anyone using today's workaround. This is stated in the PR text.
- **Overlap with open upstream PRs:** #907 and #909 also touch `eval.py`. Whichever merges later may need a small update; we'd do it.

## Out of scope
- **#564, generator expressions** (for example `sum(x for x in y)`). A 4-line version works, but it builds the whole list first. So `any(...)` doesn't stop early, and an endless generator would freeze Home Assistant. The maintainer called a full version "quite hard". This is a feature that needs his buy-in, not a bug fix.
- Issues that need the maintainer's design: #891, #877 and #885, #831, #788 (stubs for `service.call`), and #855 (Jupyter listen address).
- Commenting on the issues that are already fixed on `master`. This stays on the roadmap, if you want it.

---

## Record (2026-11-21)

**Status:** built and checked, with no open problems. Not yet sent upstream.

**What shipped on this branch:** five commits, each one meant to become its own upstream PR. Each one applies on its own to upstream `master` (`309a3ff`) and passes the tests there.
- `181956e` keep a decorator's wrapper body when it uses functools.wraps (#808): `eval.py` +42/−15, 6 new test cases.
- `75137bc` delete object attributes in del instead of treating them as states: `eval.py` +16/−4, 5 new test cases.
- `d16e990` document the logger names for scripts, apps and modules (#821, #520, #265): docs only.
- `cf83267` document that state triggers only fire when a value changes (#864): docs only.
- `c53ef6c` fix relative imports inside an app's subfolders (#726): `global_ctx.py` +4/−1, 1 new test.

**Checks:** all 207 tests, ruff, pylint, mypy, codespell and a strict Sphinx docs build pass on Python 3.14. hassfest only runs on GitHub. The new tests fail on upstream's code without the fixes, and every new case matches real Python.

**Review rounds:**
- QA: passed.
- Security: clear.
- Audit:
  - **Must-fix, fixed:** the #726 package check compared the end of the file path with `/__init__.py`. On Windows that would treat an app's `__init__.py` as a plain module. It now uses `os.path.basename`. The fix was checked by rerunning the tests, ruff, mypy and pylint.
  - **Should-fix, not changed:** after `del mod.Foo` (a class defined in another pyscript module), `hasattr(mod, "Foo")` stays True. The class is kept as an empty placeholder so that the module's own functions see it as deleted, and pyscript already does the same for a module-level `del Foo`. This is a rare case and is a known limit.

**Decisions:**
- The #808 fix keeps the function object a decorator returns, and doesn't unwrap it as the first version did. A decorator that stores the function (a registry) keeps a working one, and attributes like `__wrapped__` survive. `remove_func()` had no other users, so it was removed.
- #726 needed a second small change beyond the first idea. A plain module's relative imports now start from its package, not from itself, which removes the phantom contexts. Scripts that use the old workaround (`from .subfolder.a` inside `subfolder/b.py`) must switch to `from .a`. The PR text says so.
- Unchanged: relative imports from a plain file inside a `modules/` package still aren't supported, as before.
- The plan check and the plain-English check were skipped: their reviewer's monthly quota is used up.
