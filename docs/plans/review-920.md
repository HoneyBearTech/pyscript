# Plan: review-920

**What Sean asked for:** "yes", meaning rework #920 the way the maintainer suggests.

The maintainer's review of #920, in full: "Thanks @HoneyBearTech, this is thorough, and catching `StopIteration` is worth fixing. But it's a big change for it: about 270 new lines in `eval.py`, with catches in 18 places, and it adds a rule every future coroutine that runs native code must follow, which is easy to break later. Python already keeps the original exception: the converted `RuntimeError` has the `StopIteration` as its `__cause__`, and passes unchanged through our outer coroutines. So could we unwrap it only where it matters: when matching and binding `except` clauses, what `with` passes to `__exit__`, the uncaught error report, and a generator expression element (which should give `RuntimeError("generator raised StopIteration")`)? I tried the first two on master in about 20 lines, and they pass 41 of your 57 comparison scripts, including `except StopIteration`, `.value`, `except Exception as e`, `contextlib.suppress` and a function that raises it to its caller. The rest are mostly `sys.exception()`/`__context__` inside a handler, and telling a genuine `RuntimeError("coroutine raised StopIteration")` from a native coroutine apart from the converted one. I think those are fine as documented limitations in exchange for a much smaller change."

## What we found
- #920 is one commit, `c89c40b`, on the fork's `fix-stopiteration` branch, on `5820c4f`. It clashes with master `a7a9541` at the end of `tests/test_unit_eval.py`, and with #919 in 6 places in `eval.py`.
- Its approach: catch a `StopIteration` at every place pyscript's own coroutines meet it, and carry it in a private `EvalStopIteration` exception. That's what makes it big, and every future coroutine that calls native code has to follow the same rule.
- When a `StopIteration` leaves a coroutine, Python replaces it with `RuntimeError("coroutine raised StopIteration")` and keeps the original as the new error's `__cause__`. That `RuntimeError` then passes unchanged through pyscript's outer coroutines. So the original can be recovered where a script can see it.
- On master, the places a script sees an exception are:
  - `ast_try`, which matches and binds `except` clauses;
  - `with_items`, which passes the exception to `__exit__`;
  - the uncaught error report (`EvalExceptionFormatter`, used for the log and for Jupyter);
  - `genexp_loop`, where an element's error leaves a generator expression.

## What we'll change
"CPython comparison scripts" means the same short examples run in ordinary Python and in pyscript, with the results compared. "Unwrap" means recovering the original `StopIteration` that Python keeps inside the `RuntimeError` it replaced it with.

Plan review tried the maintainer's two-place version on master. 41 of the 57 old scripts pass, which matches his count. Adding the generator expression change brings it to 44.

1. **Start again from master.** #920 stays the same PR, but its code is rebuilt from scratch: one new commit on master `a7a9541` replaces `c89c40b`. It keeps none of the old approach, so there's no `EvalStopIteration` and no catches spread through the interpreter. It does keep the old commit's comparison scripts.
2. **One small helper, used in a few places.** The helper recognises a replaced `StopIteration`. That's a `RuntimeError` whose message is Python's (`"coroutine raised StopIteration"` or `"async generator raised StopIteration"`) and whose `__cause__` is a `StopIteration`. It returns that `StopIteration`, and any other exception comes back unchanged. The exception objects themselves are never changed.
   - **`except` clauses (`ast_try`).** Match each clause against the unwrapped exception, and bind the unwrapped one to the `as` name. So `except StopIteration`, `except Exception as e`, `except BaseException as e`, `e.value` and a subclass of `StopIteration` all work as in Python, and `except RuntimeError` doesn't catch it. If no clause matches, the original error continues unchanged. The interpreter's outer catch stays as it is, so cancelling a task works as before.
   - **`with` (`with_items`).** Pass the unwrapped exception's type, value and traceback to `__exit__` and `__aexit__`. So `contextlib.suppress(StopIteration)` works. If `__exit__` doesn't suppress it, the original error continues. Cancelling still works as before.
   - **The uncaught error report (`EvalExceptionFormatter`).** Show `StopIteration` with the script's own lines and function names. Those lines are kept on Python's `RuntimeError`, not on the `StopIteration`, so the report takes them from there. The report must also cope with an exception chain that loops back on itself, which a script's `raise e` inside `except StopIteration as e` can create. Without that, the report itself fails with `RecursionError`.
   - **Jupyter (`jupyter_kernel.py`).** It uses the same report for the traceback, but takes the error's name and message straight from the caught error, so those come from the unwrapped exception too.
   - **Generator expressions (`genexp_loop`).** A `StopIteration` from an element, a filter (`if`) or an inner iterable gives `RuntimeError("generator raised StopIteration")`, with the `StopIteration` as its cause and context, as in Python. It doesn't quietly end the generator expression. The normal end of the loop and the outermost iterable work as before.
   - *Check:* the full suite passes. Each place has CPython comparison scripts or, for the report and Jupyter, tests of the actual logged message and Jupyter reply. These must fail on master without the change. The new tests also cover:
     - an uncaught `raise e`;
     - a `RuntimeError` with Python's message but no `StopIteration` cause, which must stay a `RuntimeError`;
     - a native generator's error, which must stay unchanged;
     - an `__exit__` that raises `StopIteration` itself, and one whose result raises it when tested for true or false;
     - awaiting another pyscript function, a native coroutine awaiting one, and `task.create`, which logs the error.
3. **The comparison scripts.** Run each of the old commit's 57 `STOP_ITERATION_TESTS` and its uncaught-report tests against the new code.
   - Every script that matches Python stays as a CPython comparison script. Plan review expects 44, including the #918 setter and deleter scripts, which pass without any special handling.
   - Each script that doesn't match Python is listed with its reason. Plan review found two groups:
     - **Inside a handler or `finally`, `sys.exception()`, `sys.exc_info()` and the implicit `__context__` show Python's `RuntimeError`.** This also affects an `except` clause's type expression. A bare `raise` and `raise e` still work.
     - **A genuine `RuntimeError("coroutine raised StopIteration")` from native code, or from a native task, looks like a `StopIteration`.** That also covers a script that builds the same chain itself.

     Each group becomes a documented limit. A short test checks what pyscript actually does there, so a later change can't alter it without anyone noticing.
   - *Check:* the counts in the description and reply match the code.
4. **Docs.** Master has no `StopIteration` item yet, so add one to Language Limitations:
   - `StopIteration` can be caught with `except` and suppressed by a `with`, as in Python;
   - then each limit from step 3, in one short sentence.

   Nothing else is copied from the old branch's docs.
   - *Check:* the docs build with warnings treated as errors (`sphinx-build -W -b html docs <folder>`) passes, and every sentence matches a test.
5. **Reply and description.** The team writes:
   - a reply that starts with "Thanks @craigbarratt" and answers his points in order: the size, the four places, the scripts (how many still match Python and which limits are now documented), and what changed and where;
   - a new #920 description in the layout of the earlier upstream PRs. It reports the real, measured overlap with #919.

   After Sean approves the finished work on GitHub (Gate B), the team replaces `fix-stopiteration` on the fork, because this is a new commit on a new base. The push is guarded: it only replaces the branch if nobody has changed it since `c89c40b`. Sean then pastes the description and posts the reply.
   - *Check:* on Python 3.14, the full test suite (`pytest`), the formatting, style, lint and type checks (`pre-commit run --all-files`) and the docs build all pass. The branch merges into master with no clashes, and the team measures where it still clashes with #919, in the code, tests and docs.

## Who's on it
CEO, Engineer, QA, Security Officer, Auditor, plan review, plain-English check. The Researcher was skipped: the maintainer's comment and the code give the facts.

## Risks
- Checking the message text of the `RuntimeError` relies on Python's wording. The tests run on the Python versions the project supports, so a wording change would show up as a failing test.
- A script that raises `RuntimeError("coroutine raised StopIteration") from StopIteration()` itself would also be unwrapped. That's very unlikely, and it falls under the documented limit about a genuine `RuntimeError`.
- Some cases the old #920 handled become documented limits. The maintainer accepts that in exchange for a much smaller change.
- This machine's safety check has blocked some branch replacements before. If it blocks the delivery push, Sean may need to allow it.

## Out of scope
- `StopAsyncIteration`, `except*` (pyscript doesn't support it yet), and the cases listed as limits.
- #919, which is ready to merge.

## Record
**2026-11-22. Built and checked.** The finished change is `team/review-920-pr`: one new signed-off commit, `0470f71` "let StopIteration be caught in try/except", on master `a7a9541`. It replaces `c89c40b`. After Gate B it goes on the fork's `fix-stopiteration` with a guarded push from `c89c40b`.

**What shipped**
- **The helper.** `unwrap_stop_iteration()` recovers the `StopIteration`. It only does so when the error is exactly a `RuntimeError` whose only argument is the string `"coroutine raised StopIteration"` and whose `__cause__` is a `StopIteration`.
- **Where it's used:**
  - `ast_try` matches and binds `except` clauses with it;
  - `with_items` uses it for `__exit__` and `__aexit__`;
  - `genexp_loop` uses it for an element, a filter or an inner iterable. That re-raises from the generator, so Python gives `RuntimeError("generator raised StopIteration")`. It keeps the script frames, using `BaseException`'s own traceback descriptor and method;
  - `EvalExceptionFormatter` uses it to show the `StopIteration` with the replacement's script frames and the `StopIteration`'s own native frames;
  - the Jupyter kernel uses it for `ename` and `evalue`.
- **The formatter.** It's cycle-safe, and for `raise X from exc` it searches the context chain for the replacement.
- **Deliberate deviation from the plan:** the async-generator message isn't unwrapped. pyscript has no async generators of its own, so that message only comes from native code, where the error is genuine.
- **Size:** `eval.py` adds 67 lines and removes 17, of which 50 added lines are code. The old version added 648 and removed 424.
- **Docs:** one new Language Limitations item, with four limits:
  - handler state (`sys.exception()`, `sys.exc_info()`, `__context__`);
  - a genuine native `RuntimeError` with the same message, or a pyscript `async def` that raises it, caught as `StopIteration`;
  - native code awaiting a pyscript function gets the `RuntimeError`;
  - a saved exception raised from after its handler has ended loses its script line in the report.

**Scripts:** 44 of the 57 old scripts match Python: the maintainer's 41, plus 17, 38 and 47 (the generator expression ones). There are 5 new scripts, so 49 comparison scripts in all, and 43 of them fail on master. The other 13 are documented limits, checked by `test_stop_iteration_limits`:
- handler state: scripts 9, 10, 19, 20, 21 and 34;
- a genuine `RuntimeError`: scripts 18, 22–26 and 57.

**Checks:** 232 tests, pre-commit and the docs build with warnings treated as errors all pass on Python 3.14. It merges into master with no clashes. With #919, the only clash is the "keep both" tests at the end of the test file, and with both kept, 235 tests pass.
- **Plan review:** it found four gaps, all folded in before Gate A:
  - the report lost the script frames;
  - an uncaught `raise e` crashed the report with `RecursionError`;
  - Jupyter's error fields;
  - the limit groups were wrong. #918's setters need nothing.
- **QA:** pass. Two description fixes were made.
- **Security:** clear.
- **Audit:**
  - **Round 1:** one must-fix, generator expression conversion dropped the failing function's frames. One should-fix, `raise X from exc` lost the cause's line when another exception came in between. Both were fixed; the saved-exception case became a documented limit.
  - **Round 2:** one must-fix, `with_traceback()` dispatched to a subclass override. Fixed with `BaseException`-level access, plus comparison script 49.
  - The re-check approved, with no findings.
- **Before Gate B:** the team fetched #920's comments again. Nothing new.
- Plain-English check: it confirmed every count. It found that the summaries were hard for a non-coder to read, so they now use plainer wording and say what the four limits mean. The old version's size is now labelled as its own commit's changes.
- After Gate B: #919 was merged upstream (`0149ea9`), so #920 now clashed with master in the test file. The commit was moved onto the new master as `8d5b6b0`, keeping both sets of tests. The code, docs and Jupyter test changes are identical to the approved `0470f71`. On the new master, 235 tests, pre-commit and the docs build pass. The upstream description and reply were updated to match, and the owner was asked to approve again before #920's branch is updated.
