# Plan: comp-scope

**What Sean asked for:** "Let's do the maintainer's suggested follow-up on #919 as a separate PR".

The maintainer's words on #919: "A possible follow-up: the new comprehension scoping only applies in functions with an inner function or lambda, so the same code can behave differently depending on that. It would be good to use it in every function eventually."

## What we found
- **Why some functions behave differently.** Since #919, a function with an inner function, class or lambda keeps each of its variables in a shared box, so an inner function can share it. `EvalFunc.has_closure` marks those functions. Only those get the new handling of comprehension and generator expression loop variables (`shares_locals()` in `eval.py`). Other functions keep their variables as plain values and use the old handling.
- **The difference shows up only with a generator expression** that is used later, or used by a comprehension that reuses one of its names. Plain comprehensions already match Python in every function (16 scripts checked).
- **How many differ.** In a function without an inner function, 22 of the 27 comparison scripts that #919 runs only with an inner function differ from Python, including the 5 examples in our #919 reply. For example:
  ```python
  def f():
      x = 0
      g = ((x := x + 1) for _ in range(3))
      r = [x for x in g]
      return r, x   # pyscript ([1, 2, 3], 0), Python ([1, 2, 3], 3)
  ```
- **Making every function use the shared boxes** (`has_closure` always true) fixes all 27 scripts. The other 5 already match Python and stay as checks that nothing breaks.
  - The full suite then passes, apart from one expected error message. Reading a local variable before it has a value (including one that hides a built-in, like `len`) now gives `UnboundLocalError` ("local variable 'x' referenced before assignment"), as Python does, instead of `NameError`. `UnboundLocalError` is a kind of `NameError`, so code that catches `NameError` still works.
  - `locals()`, `eval()`, `exec()`, `global`, `nonlocal`, `del`, recursion, `*args`/`**kwargs` and error positions are unchanged.
  - The cost is one small box per local variable on each call, plus one extra step per read or write. Quiet measurements (20 alternating runs each, plan review) gave: arithmetic loop +7%, local reads and writes +9%, a comprehension +7%, and **many calls to a small function +14.5%**.
- **A narrower rule** fixes the same 27 scripts. It keeps today's rule (an inner function or lambda) and also gives shared boxes to every function that contains a generator expression. Functions without one measured within noise of master. But it keeps a rule about which functions are special, which is what the maintainer wants to remove.
- **`eval()` and `exec()` must stay as they are.** Code they run has no running pyscript function, and its variables are a plain dictionary. Turning the new handling on there breaks a case that works today: with separate locals, `exec('g=((x:=x+1) for _ in range(3)); r=[x for x in g]', {'x': 0}, ns)` would give `[1, 1, 1]` instead of Python's `[1, 2, 3]`.
- **Module level and class bodies** have the same kind of difference. The maintainer asked about functions only, so these stay as they are.
- **Contribution rules.** The project has no `CONTRIBUTING.md`. We follow the maintainer's habits: one focused commit per PR, `pre-commit run --all-files` (ruff, ruff format, codespell, pylint, mypy) and the full test suite pass, docs updated in `docs/reference.rst`, and a sign-off line on the commit.

## What we'll change
One commit on current master (`dece34a`).

1. **Every function uses the shared variables.** In `eval.py`, remove `has_closure` and `check_for_closure()`. Every local variable of a function becomes an `EvalLocalVar` in `resolve_nonlocals()`. `shares_locals()` keeps its "a pyscript function is running" test (`self.in_local_scope() and self.curr_func is not None`) and drops only the `has_closure` part, so `eval()` and `exec()` are unchanged. The code should get smaller, not bigger.
   *Check:* the 7 `SHARED_COMPREHENSION_SCOPE_TESTS` and the 15 `GENEXP_WALRUS_SCOPE_TESTS` also run in plain functions, with no inner function added, and match CPython. So do the 5 examples from the #919 reply. The 22 that fail on master pass; the 5 that already pass keep passing.
2. **Tests.**
   - Run those lists both as written and with `with_inner_function()`, so both kinds of function are covered.
   - Add the 5 reply examples as comparison scripts. The fifth raises `ZeroDivisionError` in Python, so the script catches it and returns it as its result.
   - Update the expected message in `test_eval_exceptions` (a function that reads a local variable before it has a value) to the new `UnboundLocalError` wording.
   - Add comparison scripts for reading a local before it has a value: one plain, and one that hides a built-in like `len`.
   - Add the `exec()` case above as a comparison script, so `eval()` and `exec()` stay as they are.
   - Call the comparison helper once with a list of scripts, never once per case: a failing case would stall the run.
   *Check:* full suite and pre-commit pass. Each new test fails on master.
3. **Speed.**
   - First try cheap ways to make the shared variables faster, without changing behaviour. For example, give `EvalLocalVar` fixed attribute slots (`__slots__`), and create it without the keyword-argument dictionary.
   - Then measure master against the change on quiet runs, with nothing else running. Cover four workloads: a loop doing arithmetic on locals, many local reads and writes, many calls to a small function, and a comprehension. Use one warm-up and at least 20 alternating runs per workload.
   *Check:* the numbers go in the PR description.
   - **Rule we follow,** applied to each workload's median:
     - If every one is under 10% slower, we keep "every function".
     - If any is 10% or more, the Engineer switches to the narrower rule. That rule keeps today's inner-function-or-lambda test and adds functions containing a generator expression.
   - The PR description gives the numbers for both, so the maintainer can choose.
4. **Docs.** In `docs/reference.rst`, the generator expression limits end with "...unless it was made in a function that has an inner function or lambda". That changes so the limit applies only at module level and in class bodies, which keep the old behaviour. With the narrower rule, it says "unless it was made in a function". Lines keep the paragraph's wrapping (about 100 characters).
   *Check:* `sphinx-build -W -b html docs <temporary folder>` passes, and no new line is longer than about 100 characters.
5. **Drafts.** A PR description in the layout of our earlier upstream PRs:
   - what was different, and why;
   - what changed;
   - testing, with the speed numbers;
   - the module-level and class-body differences left as they are.

   It credits the maintainer's suggestion on #919.

## Who's on it
CEO, Researcher (done), Engineer, QA, Security Officer, Auditor, plan review, plain-English check.

## Risks
- **Speed.** Every function call now makes a box per local variable. The plan review measured +14.5% on many calls to a small function. Step 3 tries to bring that down; if it can't, the narrower rule is used.
- **Error messages.** Some messages change from `NameError` to Python's `UnboundLocalError` wording. Scripts that catch `NameError` still work.
- **Hidden reliance on plain values.** Other code (`locals()`, `eval()`/`exec()`, the error report, `super()`, Jupyter) might rely on a plain function's variables being plain values. The checked cases all work, and QA and the Auditor will look for more.

## Out of scope
- Module-level and class-body comprehension differences.
- Any other change to how generator expressions run.

## Record
**2026-11-23. Built and checked.** The finished change is `team/comp-scope-pr`. It's one signed-off commit, `d4e8fe0` "use the new comprehension scoping in every function", on upstream master `933e177`. That's two commits after the planned base `dece34a`, because #921 and a docs line wrap landed upstream.

**What shipped**
- **Every function keeps its locals in `EvalLocalVar` cells.** `has_closure` and `check_for_closure()` are removed. `shares_locals()` keeps the "a function is running" test, so `eval()` and `exec()` are unchanged.
- **Speed-ups:**
  - `EvalLocalVar` has `__slots__` and takes its value as a positional argument;
  - `ast_name()` reads the cell once;
  - a function's own locals are marked `None` in `local_sym_table`, so `call()` no longer raises and catches an exception per empty cell.
- **`get_names_set()`** no longer counts comprehension loop variables as the function's own. This fixes `len` after `[len for len in ...]`, and a module-level global read after a comprehension. The global case was already wrong on master.
- **`ast_annassign()`** handles a function's own `__annotations__`.
- **Error types.** An empty variable read in a generator expression gives `NameError` for the function's variables and `UnboundLocalError` for the generator's own loop variables, as in Python. This uses `EvalLoopVar`, a subclass that records its generator expression, plus a per-generator identity, `genexp_id`. Several of these cases were already wrong on master.
- **Size:** `eval.py` adds 61 lines and removes 46.
- **Docs:** the generator expression limitation now applies only at module level and in class bodies.

**Speed**, measured over 3 processes with 20 alternating runs each:

| Workload | Change vs master |
|---|---|
| arithmetic loop | -0.6 to +2.0% |
| local reads and writes | +0.6 to +1.5% |
| calls to a small function | +6.5 to +8.8% |
| a comprehension | -1.3 to +1.8% |
| deep recursion, plain function | up to +13.6% (900 levels, 10 locals) |
| deep recursion, function with an inner function | 1.7 to 6.7 times as fast |

**Checks:** 335 tests, pre-commit and the docs build with warnings treated as errors all pass. The commit merges cleanly with master.
- **Research:** found 22 of 27 scripts differ in plain functions, and compared three options.
- **Plan review:** found three problems, all folded in before Gate A:
  - `exec()` would change;
  - the docs must name class bodies;
  - not all the new tests fail on master.
- **QA:** pass. Its corrections to the drafts were made.
- **Security:** fix round 1 fixed its should-fix, that deep recursion was up to 8 times slower because of the per-call exception. Its final check of `d4e8fe0` is clear.
- **Audit:** four rounds, each finding a must-fix:
  - **Round 1:** comprehension targets hid built-ins and globals, and a function's own `__annotations__` broke.
  - **Round 2:** a generator expression read of an empty enclosing variable gave `UnboundLocalError` instead of `NameError`.
  - **Round 3:** the generator's own loop variables gave `NameError`.
  - **Round 4:** two generator expressions sharing one iterator were confused.

  The owner approved rounds 3 and 4 beyond the usual two. The final narrow check approved. The remaining differences were all there on master too, and go in the PR's Note.

**Open for Gate B:** the plan's 10% rule was set for the four main workloads, and those are all under 10%. Deep recursion in plain functions, added to the measurements later, reaches about 14%. The PR states this, and shows the narrower rule's numbers as an alternative.
- Plain-English check: it confirmed every count and all 12 speed rows. It found wording that claimed too much, all fixed:
  - that every function now matches Python, when known differences remain;
  - that the narrower rule costs nothing, when one recursion row was up to about 6% slower and it leaves two error-type cases unfixed;
  - that deep recursion is rare in scripts, which wasn't measured.

  The upstream description's narrower-rule sentence now gives the measured exception.
