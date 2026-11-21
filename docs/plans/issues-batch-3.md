# Plan: issues-batch-3

## What Sean asked for
"let's get the next batch, make sure they are high value"

## What we found
The small, still-broken bug issues were used up by the first two batches. The highest-value items left are real gaps in pyscript's Python support, which users keep hitting:
- **Classes:** these are the most-reported interpreter limit, with about 22 threads since 2020. The maintainer agrees that "classes in pyscript are weak". On upstream's latest code (`c20990b`), compared with real Python 3.14:
  - `super().__init__()` and `super().method()` fail with `RuntimeError: super(): __class__ cell not found`. That also breaks custom exceptions and `dict` subclasses.
  - `Base.__init__(self, x)` and `super(C, self).__init__(x)` fail with `TypeError`.
  - A subclass without its own `__init__` doesn't use its parent's, so `C(1)` fails (#891).
  - `@property` and `@classmethod` on pyscript methods fail with `TypeError: 'EvalFunc' object is not callable`.
- **Generator expressions (#564, also #834):** `any(x > 3 for x in values)`, `"".join(... for ...)` and `next(... for ..., None)` fail with "not implemented ast ast_generatorexp". The maintainer wrote "any implementations would be most welcome".
- Working versions of all three fixes have been tried, and they pass the whole test suite. Every case that went wrong with #891 in batch 1 is now covered by a test that matches real Python: custom exceptions keeping their message, `logging.Handler` and `threading.Thread` subclasses, `str` and namedtuple bases, and a parent `__init__` that uses `super()`.

## What we'll change
Three upstream PRs, each cut from upstream `master`, with tests compared against real Python and a docs update in the "Language Limitations" section.

1. **Classes: inherited `__init__`, `Base.__init__` and `super()`** (`custom_components/pyscript/eval.py`, `tests/test_unit_eval.py`, `docs/reference.rst`). Closes #891.
   - Each method remembers the class it was defined in, so `super()` without arguments works.
   - A class without `__init__` uses the first `__init__` along its parents, as Python does.
   - Objects are created the way Python's `type.__call__` does it: `__new__` first, with the constructor's arguments when a parent class written in Python needs them, then the pyscript `__init__`.
   - *Check:* about 40 cases, each compared with real Python:
     - every case that broke in batch 1;
     - diamond inheritance, metaclasses, a pyscript `__new__`, and `@pyscript_compile` `__init__`s;
     - an `__init__` that returns a value (`TypeError`, as in Python).
   - The new tests fail on today's code, and the whole existing suite still passes.
2. **Generator expressions** (`eval.py`, `tests/test_unit_eval.py`, `docs/reference.rst`). Closes #564.
   - `(x for x in y)` gives a real lazy iterator. `any()` stops at the first match, and an endless source like `itertools.count()` is fine with `next()`.
   - If an element has to wait for something (for example `task.sleep`), it raises a clear error that says to use a list comprehension instead. `yield` and generator functions stay unsupported.
   - *Check:* about 25 cases, each compared with real Python:
     - `sum`, `any` and `all`, `join`, `next`, and nested generators;
     - closures, a walrus inside the generator, inside a class, and errors raised inside a generator;
     - the error message when an element has to wait.
   - The tests also cover generator expressions inside trigger and service functions.
3. **`@property` and `@classmethod` on pyscript methods** (`eval.py`, `tests/test_unit_eval.py`, `docs/reference.rst`).
   - Property getters and setters (including `obj.prop += 1`) work.
   - Class methods work when called through the class, an instance or a subclass.
   - A read-only property still raises `AttributeError`.
   - *Check:* about 17 cases compared with real Python, and the docs list what still doesn't work, such as `getattr(obj, "prop")` and `functools.cached_property`.
4. **All project checks** on Python 3.14 for each PR on its own: `pytest`, `ruff check`, `ruff format --check`, `pylint`, `mypy`, `codespell`, and a strict docs build.
5. **Upstream PRs.** After your final approval, each fix goes on its own clean branch from upstream `master`, with a prefilled link for you to open it. Items 1 and 3 change the same few lines of `call_func`. So we'll suggest merging item 1 first, and we'll rebase item 3 as soon as it's merged.

## Contribution rules that apply
- The project has `docs/contributing.rst` and `tests/README.md`, and no CONTRIBUTING.md or PR template. Their rules:
  - Set up the dev environment from `tests/requirements_test.txt`.
  - Run the pre-commit hooks: ruff check and format, codespell, check-json, yamllint, pylint and mypy.
  - Run `pytest`, and send PRs from a fork.
- CI (`validate.yml`, Python 3.14) runs hassfest, ruff, pytest with coverage, pylint and mypy.
- The maintainer's habits: one fix per PR, with tests and docs when behaviour changes. Titles name the fix and the issue. Commits are signed off.

## Who's on it
Three Engineers in parallel, one per item, each on their own branch. Then QA, the Security Officer and the Auditor, with the Auditor looking hardest at item 1. Research is done (above). There's no second security review, because no security-related code is touched.

## Risks
- **Item 1 changes how every pyscript class creates its objects.** That's the biggest risk in this batch. It's why it has about 40 tests compared with real Python, including every case that broke before, and the audit will focus on it.
- **Item 2 runs each element right away, without waiting.** An element that has to wait gets a clear error, not a hang.
- **Overlap:** item 1 also conflicts with open upstream PR #896 (methods as triggers). Whichever merges second needs a small update; we'd do it. Items 1 and 3 overlap as described above.
- **Bigger PRs than before** (about 100–140 lines of code each for items 1 and 2), so the maintainer's review may take longer.

## Out of scope
- Other special methods (`__str__`, `__len__`, `__iter__` and so on) and pyscript functions used as `sort` keys or `map` callbacks. These can't work because pyscript methods are async, and the docs already say so.
- #635 and #436 (services missing at startup and shutdown): this code is being rewritten in the maintainer's open PR #899, so we're waiting for that.
- #855 (the Jupyter kernel listens on all network addresses): a small fix, but it's security-related and of lower value. It can be its own job if you want it.
- #877 and #885 (restoring saved states): still need a design decision from the maintainer.
