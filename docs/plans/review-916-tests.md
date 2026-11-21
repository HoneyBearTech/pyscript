# Plan: review-916-tests

## What Sean asked for
"yes, start the #916 job and leave #918"

That means answering the maintainer's review of upstream #916. #918 waits until #916 merges.

## What we found
- **The maintainer approved #916.** He compared another 17 scripts with Python and found no problems.
- **He asked for two more test scripts** in `CLASS_INIT_SUPER_SOURCES`, to cover two lines the tests don't reach yet:
  1. A method that uses `super()`, called from a generator expression's element, for example `list(self.g() for _ in range(2))`. This covers the line in `EvalFunc.call` that resets `genexp_iter`.
  2. A `__new__` that returns an object of another pyscript class that has an `__init__`. This checks that `__init__` runs only once.
- **#916 still merges cleanly** with the latest upstream master, `08f10e5`, which now includes #911. So no rebase is needed.

## What we'll change
1. **Add the two scripts** to `CLASS_INIT_SUPER_SOURCES` in `tests/test_unit_eval.py`.
   - They're added as one new commit on #916's branch, `fix-class-init-super-891`, on top of `32c18f1`. Nothing is rewritten.
   - Each script is run in real Python and in pyscript, and the results are compared, like the others in that list.
   - The first script covers the method being called from an element, from a condition, and from a nested generator expression.
   - The second script checks how many times each `__init__` runs, what `type()` the result has, and the case where the other class only inherits its `__init__`.
   - If a script shows that pyscript differs from Python, the fix goes in the same commit, and the report tells you about it.

   *Check:* the full test suite, the pre-commit checks and the docs build pass on Python 3.14. We also check that both lines really run: we remove each one in a throwaway copy, and the new tests must fail.
2. **After your final approval,** the team pushes the commit to `fix-class-init-super-891`. It's an ordinary push, with no force push. You get the reply to post on #916. It starts "Thanks @craigbarratt", answers both requests in order, and says exactly what was added and where.

This plan file doesn't go upstream.

## Contribution rules that apply
- `docs/contributing.rst` and `tests/README.md`: run the tests and pre-commit hooks.
- Tests are compared with CPython, as #916's own tests are. Every commit is signed off.

## Who's on it
- An Engineer.
- Then a Security Officer and an Auditor.
- A plain-English check before the final approval.

Skipped, because the job is small: research, QA and the plan check. The Engineer and the Auditor run the full test suite.

## Risks
- **A new script could find a real difference from Python.** If so, the fix goes in the same commit and is tested, and the report says so.
- **Master could move again before the push.** We check right before pushing. A new commit on top doesn't need a rebase unless a conflict appears.

## Out of scope
- #918: it waits until #916 merges, as you decided.
- The next batch's work (PR #12).
