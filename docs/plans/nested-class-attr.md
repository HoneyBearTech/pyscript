# Plan: nested-class-attr

## What Sean asked for
"start on the nested class annotation fix": the last remaining case from #875.

## What we found
Checked on upstream's latest code and on #902's branch; both behave the same.
- A class defined inside another class's body is stored in the outer class as pyscript's internal placeholder (`EvalLocalVar`), not as the class itself. So once the outer class is built, `Outer.Inner` is the placeholder:
  - `Outer.Inner | None` fails with the same `TypeError` as #875. This applies anywhere, for example in another class's type hints: `y: Outer.Inner | None = None`.
  - `type(Outer.Inner()) is Outer.Inner` and `isinstance(Outer.Inner(), Outer.Inner)` give `False` (Python: `True`).
- These already work: `x: Inner | None` written inside the outer class's own body, methods and dataclasses using the nested class, and `list[Inner]`.
- **Must keep working:** today a method can use the nested class by its bare name (`def make(self): return Inner.v` gives `4`). Real Python raises `NameError` there, but scripts may rely on it, so the fix must not change it.

## What we'll change
1. **`custom_components/pyscript/eval.py`, `ast_classdef`:** just before the outer class object is created, replace each defined placeholder in the class's namespace with the value it holds, so the class's attributes are the real nested classes. The placeholders themselves stay valid, so methods that already hold one keep working. A namespace from a custom metaclass that can't be walked is left as it is. *Check:* the tests below.
2. **Tests in `tests/test_unit_eval.py`**, each checked against real Python:
   - `Outer.Inner | None`, at module level and in another class's type hints;
   - `type(Outer.Inner()) is Outer.Inner` and `isinstance`;
   - a dataclass with a nested dataclass;
   - two levels of nesting.
   One test also pins today's behaviour of a method using the nested class by its bare name, so it can't break silently.
   *Check:* the new tests fail on upstream's current code and pass with step 1.
3. **All project checks** on Python 3.14, as CI runs them: `pytest`, `ruff check`, `ruff format --check`, `pylint`, `mypy`, and `codespell`.
4. **Upstream PR.** After your final approval, one commit goes on a clean branch cut from upstream `master`, with a prefilled link for you to open the PR ("Refs #875"). The PR text notes the overlap with #902 and #906.

## Contribution rules that apply
- `docs/contributing.rst` and `tests/README.md`: dev setup from `tests/requirements_test.txt`, pre-commit hooks, `pytest`, PRs from a fork.
- Pre-commit runs ruff (check and format, line length 109), codespell, pylint and mypy. CI (`validate.yml`, Python 3.14) runs hassfest, ruff, pytest with coverage, pylint and mypy.
- No PR template; we follow the maintainer's habits: one small fix per PR, with tests. Commits are signed off.

## Who's on it
Engineer, Security Officer and Auditor. Research is done (above); QA is skipped as too small for this job (the Auditor runs the tests). No second security review: nothing security-related is touched.

## Risks
- **Overlap:** #902 and #906 both also change `ast_classdef`. Each is a small, separate edit, but whichever merges later needs a small update; we'll do it.
- **Custom metaclasses** whose class namespace isn't a plain dictionary: handled by leaving those alone, and tested.

## Out of scope
- Making methods stop seeing nested classes by bare name (a Python difference, but changing it could break scripts).
- The module name shown when printing a nested type hint (`custom_components.pyscript.eval.Inner` instead of `Outer.Inner`), which is only cosmetic.
