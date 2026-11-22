# Plan: review-919

**What Sean asked for:** "Do the requested change to 919 and update it for the current master"

The maintainer approved #919, with one request: "`loop_scope.keep_writes()` in `genexp_loop` isn't covered by the tests. Removing it doesn't fail any, and a walrus in a generator expression run by a later comprehension that reuses the name still works without it. Could you add a test that needs it, or drop it if it isn't needed?"

He also suggested a possible follow-up: "the new comprehension scoping only applies in functions with an inner function or lambda, so the same code can behave differently depending on that. It would be good to use it in every function eventually."

## What we found
- #919 is one commit, `cddf148`, on the fork's `fix-lambda-closure-725` branch, on `5820c4f`. Since #923 merged, master is `a7a9541`. #919 now clashes with master only at the end of `tests/test_unit_eval.py`, where both add tests. `eval.py` and the docs merge cleanly.
- `keep_writes()` (`LoopScope`, `eval.py`) is called in `genexp_loop` when a generator expression's element runs while a later comprehension's loop variables are in place. That happens when the generator expression is used inside a comprehension that started after it was made. To run the element, `genexp_loop` puts back the bindings the later comprehension hid. Afterwards, `keep_writes()` keeps anything the element assigned to them, for example with `:=`, before the comprehension's own bindings come back.
- In a function with an inner function or lambda, each local variable has a fixed *binding*, the entry in the function's table of names. The binding holds the value in a *cell*. `keep_writes()` only acts when a binding itself is created, replaced or removed. Assignment (including `:=`, which assigns inside an expression) and `del` only change or empty the cell. A variable that has no value yet already has its binding and an empty cell, made before the code runs. Nested comprehensions and generator expressions swap in temporary bindings, but always put the old ones back when they finish. So `keep_writes()` is probably never needed. Plan review tried many cases and found none that needs it.
- Plan review found a separate, existing difference from Python. In a function *without* an inner function or lambda, a `:=` inside a generator expression that a later comprehension runs, where that comprehension's loop variable has the same name, is lost: `x = 0; g = ((x := x + 1) for _ in range(3)); r = [x for x in g]` leaves `x` at 0, while Python gives 3. It's the same with or without `keep_writes()`. It's exactly the case of the maintainer's suggested follow-up (the new scoping in every function).

## What we'll change
"CPython comparison scripts" means the same short examples run in ordinary Python and in pyscript, with the results compared.

1. **Update #919 for the current master.** Reapply its commit on top of `a7a9541`. In `tests/test_unit_eval.py`, keep both complete sets of tests at the end: each list of scripts with the test function that runs it. It stays one commit, with its message unchanged.
   - *Check:* the full suite passes, and all of #919's earlier scripts still match Python.
2. **Settle `keep_writes()`.** Run each case below three ways: in Python, in pyscript as it is, and in pyscript with `keep_writes()` removed. Each case is a `:=` in a generator expression's element, where a later comprehension's loop variable has the same name:
   - the name has no value yet when the element runs;
   - it already has a value;
   - the name is deleted and then assigned again;
   - a lambda in the function reads the name afterwards;
   - a lambda whose default value uses `:=`;
   - nested comprehensions and generator expressions that reuse the name, several elements, and an element that raises;
   - each in a function with an inner lambda and one without.

   Then:
   - **If at least one case matches Python only with `keep_writes()`,** keep it, and add the cases as CPython comparison scripts. At least one of them must fail when `keep_writes()` is removed.
   - **If none does,** remove `keep_writes()` and its call. Add the cases that already match Python as scripts that check the behaviour stays the same. The reply explains why it isn't needed: as found above, bindings are only ever swapped back, never left replaced.
   - **Cases that differ from Python with and without it** (like the one plan review found) aren't caused by `keep_writes()`. They're listed in the reply as examples for the follow-up, not fixed here.

   Either way, this is a second signed-off commit on top of step 1's, so the maintainer can see what changed since his review.
   - *Check:* the full suite passes, and the new scripts match Python.
3. **The follow-up he suggested** (the new scoping in every function) isn't done here, because he called it a possible follow-up. The reply thanks him for it, gives the existing differences found in step 2 as examples of why it's worth doing, and says it would be a separate PR.
4. **Reply and description.** The team writes:
   - a reply that starts with "Thanks @craigbarratt" and says what we found about `keep_writes()`, what changed and where, and the new test names;
   - an updated #919 description: rebased on master, plus step 2's result and the new script count.

   After Sean approves the finished work on GitHub (Gate B), the team replaces #919's branch on the fork, because the update onto the new master needs that. The push is guarded: it stops if anyone has changed the branch since `cddf148`. Sean then pastes the description and posts the reply.
   - *Check:* on Python 3.14, the full test suite (`pytest`), the formatting, style, lint and type checks (`pre-commit run --all-files`), and the docs build with warnings treated as errors all pass. The branch merges into master with no clashes, and GitHub shows #919 as mergeable (no clashing changes).

## Who's on it
CEO, Engineer, QA, Security Officer, Auditor, plan review, plain-English check. The Researcher was skipped: the maintainer's comment and the code give the facts.

## Risks
- #920 (`StopIteration`) also clashes with master, and it clashes with #919 in 6 places in `eval.py`. Once #919 merges, #920 needs about an hour's rebase. That's a separate job.
- This machine's safety check has blocked some branch replacements before. If it blocks the delivery push, Sean may need to allow it.

## Out of scope
- The maintainer's suggested follow-up: the new comprehension scoping in every function.
- Updating #920.

## Record
**2026-11-22. Built and checked.** The finished change is `team/review-919-pr`, two signed-off commits on master `a7a9541`:
- `8355e0e`, "let lambdas use the enclosing function's variables (#725)": #919's commit `cddf148` reapplied, with its changes and message unchanged. The only clash was at the end of `tests/test_unit_eval.py`. Both sets of tests are kept, each with its own test function.
- `30defb9`, "remove LoopScope.keep_writes(), which nothing needs".

After Gate B, it replaces `fix-lambda-closure-725` on the fork with a guarded push, from `cddf148`.

**What we found about `keep_writes()`:** nothing needs it, so the plan's "remove" branch was taken.
- In a function that shares its variables, every name the function binds already has its binding when the function is called. That includes `:=` targets and comprehension loop names.
- Assignment and `del` only change the value inside that binding.
- Nested comprehensions and generator expressions always put back the bindings they replace.
- The Engineer ran 21 cases three ways: in Python, in pyscript as it is, and in pyscript without `keep_writes()`. They were run in functions with an inner function and, where the case allows it, without one. No case changed when it was removed.
- With `keep_writes()` made to fail whenever it changes anything, the full suite still passed (231 tests). The CEO and the Auditor each confirmed this separately. The Auditor also ran 155 more cases, with no difference.
- The 15 cases that match Python are now `GENEXP_WALRUS_SCOPE_TESTS`, run by `test_genexp_walrus_scopes_match_python`. They pass with and without `keep_writes()`.

**Existing differences, left for the maintainer's suggested follow-up:** in a function without an inner function or lambda, a generator expression run by a comprehension that reuses a name sees the comprehension's loop variable, and a `:=` to that name is lost. All but the `global` case differ from Python, with or without `keep_writes()`. The reply gives five examples.

**Checks:**
- 232 tests, pre-commit and the docs build with warnings treated as errors all pass on Python 3.14, and the branch merges into master with no clashes.
- 94 scripts are compared with Python: 50 lambda scripts, 29 comprehension-scope scripts and 15 new ones.
- **Plan review:** it found an existing difference in functions without an inner lambda, and said "no value yet" doesn't mean a binding is created. Both were folded into the plan before Gate A.
- **QA:** pass, with two notes. One claim, the suite run with the failing check, was confirmed by the CEO. The other, plain-function cases not being committed tests, is now stated in the drafts.
- **Security:** clear.
- **Audit:** approve. It found two wording fixes in the drafts:
  - the 15 scripts are 14 `:=` scripts plus 1 `nonlocal` script;
  - the old `default_value()` example needs an inner function to show the old failure.

  Both were fixed in one round, with no code change.
