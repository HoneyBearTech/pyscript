# Plan: review-924

**What Sean asked for:** "yes", meaning add the test the maintainer asked for on #924.

The maintainer's review of #924 (2026-11-23), in full: "Thanks @HoneyBearTech, this is a nice result: one rule for every function, and functions with an inner function or lambda get much faster in deep recursion. I compared about 25 more scripts with CPython, each as written and with an inner function: arguments and defaults, `except ... as e` unbinding, `del`, `for`/`with`/`import` targets, `locals()`, recursion, `global`, `nonlocal`, a local hiding `print`, comprehension variables not leaking, lambdas in comprehensions, nested comprehensions, `:=`, inner classes and functions. All of them match. I also timed small calls, a local loop, and recursion with 10 locals with and without an inner function at realistic depths, and got within noise of master (the inner-function case a few percent faster). One small request. Every mutation I tried was caught by the tests except one: if `EvalFunc.call()` doesn't reset `genexp_id`, nothing fails. This script catches it (it gives `NameError` instead of `UnboundLocalError`), so it would be worth adding to `FUNCTION_LOCALS_TESTS`:" followed by a script where `f()` calls `h()` from a generator expression, and `h()` reads its own local `z` before assigning it.

## What we found
- #924 is one commit, `d4e8fe0`, on the fork's `comprehension-scope-every-function` branch, on upstream master `933e177`.
- `EvalFunc.call()` saves `genexp_iter` and `genexp_id`, resets them to `None`, and restores them afterwards. That's so a function called from inside a generator expression doesn't think it's running in one.
- The tests miss it if `genexp_id` isn't reset. Then `h()`'s own empty local is read while `genexp_id` still belongs to `f()`'s generator expression, so it gives `NameError` instead of Python's `UnboundLocalError`.

## What we'll change
1. **Add the maintainer's script to `FUNCTION_LOCALS_TESTS`** in `tests/test_unit_eval.py`, as he wrote it. Like the others in that list, it runs as written and with an inner function, and is compared with CPython.
   *Check:*
   - the new script matches CPython on the current code;
   - with the `genexp_id` reset removed from `EvalFunc.call()`, it fails, in both kinds of function;
   - the full suite and pre-commit pass.
2. **Check the other resets in the same place.** Remove each of `call()`'s other save, reset and restore steps in turn (the `genexp_iter` reset, and each restore), and see whether a test catches each one. If one is missed, add a small comparison script that catches it.
   *Check:* each such removal makes at least one test fail.
3. **Deliver it as a second commit on #924**, signed off, with a normal push (no force) to `comprehension-scope-every-function`. That way the maintainer sees just the new test.
4. **Drafts:** a reply to the maintainer, starting "Thanks @craigbarratt". It answers his points in order and says exactly what was added and where. The PR description gets a line in Testing for the new script.

## Who's on it
CEO, Engineer, Security Officer, Auditor and the plain-English check. This is a trivial job (a test-only change), so there's no Researcher, plan review or QA.

## Risks
- None to behaviour: only tests change.

## Out of scope
- Any change to `eval.py`.

## Record
**2026-11-23. Built and checked.** The finished change is `team/review-924-pr`: one new signed-off commit, `527cfba` "test that a function called from a generator expression resets genexp_id", on #924's `d4e8fe0`. It changes `tests/test_unit_eval.py` only (+44). After Gate B it goes on the fork's `comprehension-scope-every-function` with a normal push.

**What shipped:** three scripts in `FUNCTION_LOCALS_TESTS`, which now has 23 scripts (46 runs):
- the maintainer's script, exactly as he wrote it;
- a free-variable read after a call from a generator expression's element;
- a `super()` script.

Each of five removals in `call()` (the `genexp_id` reset, the `genexp_iter` reset, both restores together, and each restore alone) now makes at least one script fail, as written and with an inner function. Before, only the maintainer's script caught one of them. The `genexp_iter` reset was caught only by a hang, and the three restores weren't caught at all.

**Checks:** 335 tests and pre-commit pass.
- **Security:** clear. It noted that upstream's own commit `933e177` carries a tool credit line. That commit isn't ours and isn't in our diff.
- **Audit:** approved. It redid the five removals independently, and all fail. Its one nit, that the description still said "one commit", is fixed in the description draft (text only).
- **Plan review and QA:** skipped, since this is a trivial test-only job.
- Plain-English check: it confirmed the counts (335 tests, 20 to 23 scripts, +44 lines). It found the five removals described as "five steps" and some jargon. Both are fixed in the owner's texts and here.
