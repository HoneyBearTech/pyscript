# Plan: issues-batch-4

## What Sean asked for
"find more open issues in pyscript to fix"

## What we found
- **Few small bugs are left.** We checked all 125 open issues against upstream master `06f8eba` and read about 60 threads closely. Most are questions, setup problems, feature ideas that need the maintainer's design, or bugs already fixed on master. Only #905 is new since our last search, and it's the maintainer's own issue with his own plan, so we leave it to him.
- **#725 (lambdas): the most useful fix left.** A `lambda` inside a pyscript function can't see that function's own variables or parameters. For example, `sorted(items, key=lambda i: d[i])` or `filter(lambda v: v > value, items)` inside a trigger function fails with `NameError`. At the top level of a script the same code works, which is what the reporter saw. We confirmed it on master.
  - **Cause:** pyscript turns a lambda into native Python code (`ast_lambda` in `eval.py`), and that code only looks names up in the script's globals.
  - **A second problem nearby:** a lambda's default value (`lambda v=x: v`) can come out as one of pyscript's internal placeholder objects instead of the value.
- **`StopIteration` can't be caught (no issue yet).** `try: next(it) except StopIteration: ...` doesn't work in pyscript, even in the simplest script. The error arrives as `RuntimeError: coroutine raised StopIteration`, so `except StopIteration` never matches. We confirmed it on master and found no issue for it.
  - **Cause:** pyscript runs each statement inside Python's async machinery. Python turns a `StopIteration` that escapes there into a `RuntimeError`.
- **#617 (leading space in trigger expressions).** A trigger whose expression starts with a space or a new line, such as `@state_trigger(""" pyscript.a == 'x'""")`, fails with `IndentationError`, and the trigger is never created. Trigger expressions are parsed in about ten places: the current decorators, the older ("legacy") decorators, and `task.wait_until`. All of them need the same fix.
- **#433 (docs).** The docs say a state trigger's `value` and `old_value` "include the state attributes too". Users, and even the thread, keep guessing wrong about how to get an attribute's old value. It does work: `old_value.brightness` gives the old attribute and `value.brightness` the new one. The docs just don't say so.
- **Already fixed on master:** about 10 open issues, with evidence: #796, #834, #864, #821, #265, #520, #729, #875, #440 and #631. A comment on each would let the maintainer close them.

## What we'll change
Each fix is its own upstream PR, on its own branch cut from upstream master, so they can be merged in any order.

1. **#725: lambdas see the variables of the function they're written in** (branch `fix-lambda-closure-725`).
   - **How it will behave:** like Python, the lambda reads a variable's current value each time it runs, not a copy taken when it was made. So if the function changes `limit` after creating `lambda v: v > limit`, the lambda sees the new `limit`, as in Python.
   - **How:** in `eval.py`, the lambda stays native Python code, so it still works with `sorted`, `map` and other native functions. Pyscript already shares variables between a function and the functions defined inside it, and the fix extends that sharing to lambdas, so the lambda's reads go to those shared variables. The lambda's own parameters and globals work as today.
   - **Default values:** `lambda v=x: v` gets the value of `x`, never an internal object.
   - **One limit we'll document, not fix:** a lambda that uses a list comprehension's loop variable after the comprehension has finished, as in `fs = [lambda: i for i in range(3)]` followed by calling `fs[0]()`. In pyscript, comprehensions don't have their own scope; that's a known, documented difference that also applies to generator expressions. Fixing it means changing how all comprehensions work, so it's out of scope. In that case the lambda gives a clear `NameError` instead of a wrong value.
   - **If exact behaviour proves impossible:** the Engineer stops and reports. We won't quietly switch to taking copies; any change of approach comes back to you.
   - **Docs:** the lambda paragraph in `docs/reference.rst` says lambdas can now use the enclosing function's variables, and states the comprehension limit.
   *Check:* tests compared with real Python for:
   - parameters, locals and nested functions, plus a variable changed after the lambda is made;
   - a lambda returned from a function, and two separate calls of the same function;
   - a lambda parameter with the same name as an outer variable;
   - positional and keyword defaults;
   - `sorted(..., key=...)`, `max(..., key=...)`, `map(f, ...)` and `filter(f, ...)`, and the #725 example;
   - a deleted or not-yet-set variable.
   The full suite passes.
2. **`StopIteration` can be caught** (branch `fix-stopiteration`).
   - **How:** where pyscript calls native code (`next()`, an iterator's `__next__`, any library function) and where a script does `raise StopIteration`, a `StopIteration` is carried out of pyscript's async machinery inside an internal wrapper, so Python doesn't convert it. The `try`/`except` handling then matches the original `StopIteration`, with its value. The same applies to `with` blocks and `finally`.
   - **What stays the same:** `for` loops and the #917 generator expressions still end normally when their iterator runs out, and pyscript's own internal uses of `StopIteration` are untouched. A real `RuntimeError` that Python raises for its own reasons, such as a native generator that lets `StopIteration` escape, stays a `RuntimeError`.
   - **When nothing catches it:** an uncaught `StopIteration` is reported as `StopIteration`, with the script line, not as the confusing `coroutine raised StopIteration`.
   - **Docs:** a short line in Language Limitations isn't needed afterwards. If any difference from Python remains, it's listed there.
   *Check:* tests compared with real Python for:
   - `next()` with and without a default;
   - `except StopIteration`, `except (StopIteration, ValueError)`, `except Exception as exc` and the exception's `.value`;
   - a bare `raise` inside the handler, `finally`, and a `with` block whose `__exit__` sees the exception;
   - a function that raises it and a caller that catches it;
   - `for` loops and generator expressions, including `next()` on an empty iterator inside a generator expression's element;
   - the uncaught case.
3. **#617: trigger expressions can start with spaces or new lines** (branch `fix-trigger-expr-whitespace-617`).
   - **Where:** one small helper strips surrounding blanks (spaces, tabs, new lines) from a trigger expression before it's parsed. It's used in every place that parses one:
     - the current decorators' expressions, `decorators/base.py`;
     - the legacy decorators and `task.wait_until`, `trigger.py`;
     - `@state_trigger`, `@state_active`, and the filters of `@event_trigger`, `@mqtt_trigger` and `@webhook_trigger`.
   - **Not changed:**
     - `@time_trigger` and `@time_active` use their own time format, which already strips blanks;
     - pyscript's `eval()` keeps Python's exact rules;
     - ordinary script code keeps its strict indentation.
   - **Error messages:** for an expression that's really broken, the message shows the stripped expression, with the marker under the right spot.
   - **Docs:** one line in the state trigger section says expressions may span several lines in a triple-quoted string.
   *Check:* tests with a leading space, a leading new line, a tab, and a multi-line expression in brackets, for both the current and the legacy decorators and `task.wait_until`. A trigger with a stripped expression really fires, and a real syntax error still shows a clear message pointing at the right place.
4. **#433: explain how to read old and new attribute values** (branch `docs-attribute-old-value-433`).
   - In the state trigger section of `docs/reference.rst`, say:
     - `var_name` is always the entity;
     - `value` and `old_value` are its state;
     - an attribute's new and old values are `value.attr` and `old_value.attr`.
   - Add a short example that also handles the cases the docs already warn about: `old_value` is `None` when the entity is new, and an attribute may be missing.
   - This branch changes only that section.
   *Check:* the docs build has no warnings. We test the example against pyscript, including an update that changes only an attribute.
5. **Comments for issues already fixed** (optional; you post them). You get a short, ready-to-paste comment for each of the 10 issues, saying what fixed it (the PR or commit) and how it was checked, so the maintainer can close them.

**Checks on every branch:**
- the full test suite, the pre-commit checks (ruff, codespell, yamllint, pylint, mypy) and the docs build, on Python 3.14 as upstream CI uses, with the team's shared test setup;
- temporary local merges (thrown away afterwards; each branch is still sent on its own):
  - the four new fixes together, because the lambda and `StopIteration` fixes both change `eval.py` and its tests;
  - each fix with our open PRs #911, #916 and #918, so you know about clashes in advance.

**Opening the PRs:** after your final approval, the team pushes the four branches to your fork. You get, for each PR:
- a link that opens it with the title filled in;
- the full description, in the same layout as your earlier PRs.

This plan file doesn't go upstream.

## Contribution rules that apply
- `docs/contributing.rst` and `tests/README.md`: run the tests and pre-commit hooks; PRs come from a fork. There's no CONTRIBUTING.md or PR template.
- Pre-commit runs ruff, codespell, yamllint, pylint and mypy. Docs are reStructuredText built with Sphinx.
- We follow the maintainer's habits: one focused change per PR, tests compared with CPython, a docs update for any user-visible change, and every commit signed off.

## Who's on it
Three Engineers, each in their own copy of the repo:
- one on the lambda fix;
- one on `StopIteration`;
- one on the trigger-expression fix and the docs fix.

The lambda and `StopIteration` branches both change `eval.py`, its tests and `docs/reference.rst`, so the CEO checks them together and sorts out any clash. Then QA, a Security Officer and an Auditor check all four, followed by a plain-English check before the final approval. The Researcher and the plan check are done. No second security review, because nothing security-related is touched.

## Risks
- **The lambda fix changes how a common feature behaves.**
  - Code that accidentally relied on a lambda seeing a global with the same name as a local would now see the local, as in Python. The tests compare with Python for exactly these cases.
  - It's the biggest change in this batch. If exact behaviour proves too hard, it comes back to you rather than shipping a half-way version.
- **`StopIteration` touches error handling at the core of the interpreter.** The tests above cover every way it can be raised and caught. The #917 generator expressions get extra checks.
- **The fixes may clash with each other and with our open PRs.** #916, #918 and the lambda and `StopIteration` fixes all change `eval.py`. Whichever merges later may need a small rebase. The merge checks above tell you in advance.
- **Upstream moves while we work.** We check again right before pushing.

## Out of scope
- #905 (the maintainer's own plan), and #886 and #629 (they touch the service code that the open #899 is rewriting).
- `match-case`: the maintainer has said no to it.
- Feature requests that need the maintainer's design (#244, #431, #646, #568, #831, #877/#885, #788, #855).
- Inner `@pyscript_compile` functions seeing enclosing variables: the docs list that as a limit, and this plan covers lambdas only.
- Giving comprehensions their own scope (see step 1).
- A lambda calling a pyscript class that has an `__init__` (`lambda: C(10)`). That's a separate, older limit we found while checking #916; it could be a later fix.

---

## Record (2026-11-22)

**Status:** built and checked. Two very rare edge cases are still open; they're described below, and you decide on them. Nothing has been sent upstream yet.

**What's ready:** four branches, each one commit on upstream master `06f8eba`. Each merges cleanly with today's master, `08f10e5`, which now includes #911.

| Step | Branch | Commit | Upstream branch name |
|---|---|---|---|
| 1. #725 lambdas | `team/issues-batch-4-lambda` | `96d1324` | `fix-lambda-closure-725` |
| 2. `StopIteration` | `team/issues-batch-4-stopiteration` | `80b2f7e` | `fix-stopiteration` |
| 3. #617 trigger blanks | `team/issues-batch-4-trigger-ws` | `98f0544` | `fix-trigger-expr-whitespace-617` |
| 4. #433 docs | `team/issues-batch-4-attr-docs` | `29d933d` | `docs-attribute-old-value-433` |

**Changes from the plan:**
- **Lambdas:** the plan said a lambda made in a list comprehension, and called after the comprehension ended, would get a clear `NameError`. That limit turned out to be unnecessary, so it was dropped. Making lambdas work meant giving comprehension loop variables their own variable for each run in functions that share variables. With that in place, those lambdas behave exactly as in Python. Functions without an inner function or lambda keep master's behaviour.
- **`StopIteration`:** the first design recognised pyscript's own error by its message and traceback. The audit showed a script could fake or erase those, so it was replaced. Now a private marker is attached at the exact moment pyscript creates the error, and nothing a script does can fake or erase it.

**Checks (Python 3.14, shared test setup):**
- Every branch passes the full suite, pre-commit and `sphinx-build -W`.
- Lambda, trigger and docs merged together on today's master (which includes #911's new tests) pass 249 tests. `StopIteration`, trigger and lambda merged together pass 248. Lambda plus `StopIteration` passes 225. All are temporary merges.
- **Lambdas:** 63 scripts compared with Python (45 for lambdas and 18 for comprehensions, some run twice). No case that matches Python on master fails on the branch. That was checked across 197 comparisons.
- **`StopIteration`:** 48 scripts compared with Python. Master gets 37 of them wrong. `try` blocks run within a few percent of master's speed.
- **Trigger blanks:** tests for the current and legacy decorators and for `task.wait_until`. 399 expression pairs give the same parse as before.
- **Docs:** the example was run against pyscript for a new entity, an attribute-only update, an added attribute and a deletion.

**Review rounds:**
- **Security:** clear on all four.
- **Lambdas:** audit rounds 1 to 3, with two fix rounds. The rounds found an inner generator losing its variables, the `except` name staying set, `:=` writes being lost, and a lambda's own names leaking out. All were fixed.
- **`StopIteration`:** audit rounds 1 to 3, with two fix rounds. The rounds found argument comparison, native coroutines, handler expressions, a cleared traceback, and operator nodes. All were fixed.
- **Trigger blanks:** audit round 1 found a `# comment` swallowing the next entry. It was fixed and approved.
- **Docs:** approved in round 1.
- QA passed each branch.

**Open (both very rare; each fix round found a smaller case than the last):**
- **Lambdas:** in a nested function, a lambda that contains `__debug__` and also binds a name with `:=` or in a comprehension makes the enclosing function pick up an outer variable of that name. You can only see it through `eval()` or `locals()`.
- **`StopIteration`:** if a `with` block's `__exit__` returns an object whose `__bool__` raises `StopIteration`, the result is a `RuntimeError` instead of a `StopIteration`.

Both are listed in their PR descriptions. The `StopIteration` one, and a pyscript `async def` awaited through a native task, are also in the docs' Language Limitations, as the plan required.

**Found, not fixed (already on master):**
- With the current decorators, `task.wait_until` returns at once when its expressions name no state variable.
- `y: Any[int] = None` in a function raises an error (#796), though Python never evaluates local annotations.
- An empty trigger expression gives a bare `SyntaxError`.
- `except*` isn't supported, and `except BaseException` catches only `Exception`.
- Comprehension targets declared `nonlocal` or `global` behave differently from Python.

**Overlaps:**
- Lambda and `StopIteration` clash in 6 places in `eval.py`. Whichever merges second needs about an hour's rebase, which we've already tried out. #916 clashes with the lambda branch in one spot in `ast_generatorexp`.
- Lambda, `StopIteration`, trigger and #916 all add tests at the end of `tests/test_unit_eval.py`. Each of those clashes is a small "keep both".

**Issues already fixed:** 10 checked on master `08f10e5`.
- Already closed: #520, #729 and #875.
- Fixed or answered by the docs: #834, #821 and #265.
- Couldn't reproduce, so the comment asks the reporter to confirm: #440 and #631.
- Partly fixed: #796 and #864.

That makes 7 comments for you to post.

**Skipped:** a second security review, because nothing security-related changed.

### Update after #916 merged (2026-11-22)
Upstream merged #916 (`029e522`), so the lambda, `StopIteration` and trigger branches stopped merging cleanly. All four were moved onto `029e522` and checked again.

| Step | Commit | On the fork as |
|---|---|---|
| 1. #725 lambdas | `5581080` | `team/issues-batch-4-lambda-rebased` |
| 2. `StopIteration` | `b8c3717` | `team/issues-batch-4-stopiteration-rebased` |
| 3. #617 trigger blanks | `1e39bf5` | `team/issues-batch-4-trigger-ws` |
| 4. #433 docs | `13105aa` | `team/issues-batch-4-attr-docs` |

The new lambda and `StopIteration` versions are on new branch names, so nothing was overwritten. `team/issues-batch-4-base-916` points at `029e522`, for comparing.

- **Lambdas:** kept #916's generator-expression handling. 2 scripts added for `super()` in methods that use lambdas, so there are now 47. `super()` without arguments inside a lambda still doesn't work; the docs have listed that since #916.
- **`StopIteration`:** #916's object-creation code (`__new__`, `__init__`, a metaclass `__call__`, `super()`) is covered by the existing catch in `call_func`. 3 scripts added, so there are now 51.
- **Trigger and docs:** only the "keep both" test-file clash. No interaction with #916.
- **Checks:**
  - Each branch passes the full suite, pre-commit and `sphinx-build -W`. Lambdas and `StopIteration` pass 227 each, trigger 248, docs 225.
  - Lambdas, trigger and docs merged together pass 250.
  - The Auditors reviewed the lambda and `StopIteration` rebases and approved them, with nothing to fix.
