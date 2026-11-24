# Plan: issue-925

**What Sean asked for:** "yes", meaning fix upstream issue #925.

#925 (reported by dmamelin, after #924 merged): an inner function can pick up a variable from whichever function called its maker, instead of the variable Python would use. The issue's example returns `"caller"` where Python returns `"global"`, and it does so silently.

## What we found
- **The cause.** `EvalFunc.resolve_nonlocals()` in `eval.py` runs when a `def` is evaluated, and decides which outside variables the new function shares.
  - It searches the symbol tables of every function currently running (`sym_table_stack`, the call chain), and takes the first one that keeps the name as a shared variable (`EvalLocalVar`).
  - Python only looks in the functions the new function is *written* inside.
- **It's older than #924.** Before #924, only functions with an inner function, lambda or class kept shared variables, so only those callers leaked. #924 made every function keep them, so now any caller leaks. On the code before #924 (`933e177`), the issue's script also fails if the caller contains a lambda.
- **The research compared 30 scripts with Python, each run two ways.** It covered:
  - defs one and two levels deep, and classes and nested classes in functions;
  - decorators, recursion, and two callers deep;
  - a caller's parameter hiding a built-in like `len`, and a name defined nowhere except in the caller;
  - `eval("make()")`, `exec`, and `nonlocal` (one and two levels deep);
  - and controls that must keep working.

  On today's master, 15 of them differ from Python in both forms. Lambdas, comprehensions and generator expressions look only in the function they're written in, so they go wrong only when that function picked up a caller's variable first. The plan check confirmed this with three more scripts.
- **A first prototype of the fix passes all of them.** It is a small change to `eval.py` (about 17 lines added and 8 removed), and the full suite passes with it. The one exception, a default value of a def nested two levels deep, fails the same way on every version: it's an older, separate gap.
- **But the plan check found that the prototype breaks working code.** It found 8 scripts that match Python today but not with the prototype. Each has a class inside a middle function, whose body assigns, or declares `global`, the same name its methods read. Its example:

  ```python
  x = 'global'
  def outer():
      x = 'outer'
      def mid():
          class C:
              x = 'class'
              def read(self):
                  return x
          return C().read()
      return mid()
  result = outer()   # Python: 'outer'; prototype: 'global'
  ```

  In Python, a method skips its class body when it looks up a name, so it reads `outer`'s `x`. But `get_names_set()` treats a class body like a function: a name the class assigns hides the same name its methods need. So `mid` never shares `x`, and only the call-chain search found it. The breaking cases are a plain read, a `nonlocal` write, a decorator wrapper, nested classes, a comprehension or generator expression in the method, and a trigger-decorated method.

## What we'll change
1. **Search only where the function is written.** In `resolve_nonlocals()`, search only the table of the function that contains the `def`, instead of the whole call chain. Class bodies don't count, as in Python: the search looks through them to the enclosing function. This needs a small list of the class-body tables in progress, kept by `ast_classdef`.
   - This relies on each function sharing every outside name that anything nested inside it reads. Then the enclosing function's own table holds everything a nested `def` can need. Step 2 makes that true.
   - *Check:* every script below matches CPython, as written and with an inner function.
2. **Pass every needed name through middle functions.** Fix `get_names_set()` so that a function shares every outside name its nested functions need, in two places where it misses some today:
   - **`nonlocal` in a nested def.** `get_names_set()` ignores `nonlocal x` in a nested def when that def assigns `x`. So `nonlocal` two levels deep only worked because of the leak. Count such names as needed from outside.
   - **Class bodies.** A name that a class body assigns, or declares `global`, mustn't hide the same name that its methods, or anything inside them, read from outside. In Python, methods skip the class body. The class body's own reads of names it assigns stay the class's own.

   If this turns out to need more than a small change to `get_names_set()`, the Engineer may instead record, when each function is defined, the tables of the functions it is written inside, and search those. This would also handle any case the name collection misses. The cost is that a closure keeps those functions' tables alive. The Engineer will report which approach was used and why.
   - *Check:* the two-level `nonlocal` script and all 8 scripts the plan check found still match CPython.
3. **Tests.** Add a new comparison test in `tests/test_unit_eval.py` that runs the scripts once, as a list, both as written and with `with_inner_function()`, against CPython. The list includes:
   - the issue's script, and the lambda variant from the reply on #925;
   - every research script that differs today;
   - the controls (a function reading its own enclosing variable, one level and two levels up, with a caller using the same name; a class variable with the same name; a closure called later from a different caller);
   - `nonlocal` one and two levels deep, with the caller having the same name;
   - the plan check's 16 scripts: the 8 class cases above must keep matching, and the three lambda, comprehension and generator-expression cases through a middle function must now match, and a parameter-shadowing control must keep matching. The other 4 cases (a lambda or `nonlocal` in a class body that shadows the name, a lambda as a default value, or a lambda in a class's base list) already differ on master. They go in the test if the fix also makes them match; otherwise they're listed in the PR's Note;
   - controls with a closure called after its outer function has returned.

   *Check:* the new test fails on today's master and passes with the fix, and the full suite and `pre-commit run --all-files` pass.
4. **Speed.** The search now looks only at the tables of the functions the `def` is written in (and through any class bodies between), instead of the whole call chain. So it should be no slower. To confirm, time defining a function inside a function at a few call depths, and a method inside nested classes, against master.
5. **Docs.** No change to `docs/reference.rst` is expected, because this restores Python's behaviour, and the docs don't describe the old one. Confirm that nothing there says otherwise.
6. **Deliver.** One signed-off commit on current upstream master (`148e2d3`), in the style of #919 and #924, with "Fixes #925". After Gate B it goes on the fork as a new branch for Sean to open upstream. Drafts:
   - the upstream PR title and description, in the layout of Sean's earlier PRs, which lists what's left (the default-value gap);
   - a short follow-up on #925 that links the PR.

## Who's on it
CEO, Researcher, Plan Checker, Engineer, QA, Security Officer, Auditor and the plain-English check.

## Risks
- **Code that relied on the leak.** Anything that only worked because a function picked up a caller's variable will now get the module variable, or a `NameError`, as Python does. Some correct-looking code relied on it too: the two-level `nonlocal` case and the 8 class cases (step 2). There may be more of these, so the Auditor will look for further ones.
- **`eval`/`exec`.** A `def` inside `eval`/`exec` code will no longer pick up the calling function's variables by accident. That's Python's behaviour too: code run by `exec` with a separate locals dict can't share them.

## Out of scope
- A default value of a def nested inside another nested def that reads the outer function's variable. This fails the same way before and after #924, and it'll be listed in the PR's Note.
- The plan check's cases that already differ on master, unless the fix also makes them match (see step 3).
- Module-level and class-body comprehension scoping.
