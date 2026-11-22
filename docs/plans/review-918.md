# Plan: review-918

**What Sean asked for:** "let's work 918"

## What we found
- The maintainer reviewed #918 (support `@property` and `@classmethod` on pyscript class methods) and said it works well. He asked for four things:
  1. rebase onto master now that #916 has merged;
  2. make `del a.x` call a pyscript `@x.deleter`, the same way the setter works, with a test;
  3. update the docs: since #910, `getattr(a, "x")` on a pyscript property returns a coroutine instead of raising, and `hasattr` returns True;
  4. add a test for `super()` inside a classmethod.
- #918 is one commit, `b24ab7d`, on the fork's `fix-property-classmethod` branch. It now clashes with master `029e522` in `eval.py`. #915 removed `unwrap_defined`, the `ModuleType` import and the module branch in `ast_attribute`, and #916 changed nearby code. The tests at the end of `tests/test_unit_eval.py` also clash.
- On master, `del a.x` goes through `EvalAttrSet.delattr()` (`eval.py`). That is plain Python `delattr`, which calls a pyscript deleter without awaiting it, so the deleter never runs. #918's setter avoids this with `setattr_async`, which finds the property with `pyscript_property()` and awaits a pyscript `fset`.
- Zero-argument `super()` already accepts a class as its first argument on master, so it works inside a classmethod once #918's classmethod support is in. A trial during plan review matched Python for a chain of three classes and for a classmethod called on an instance.
- Checked on master: `getattr(a, "x")` on a pyscript property gives a coroutine (a pending operation, not the value), and `hasattr(a, "x")` is True. The built-in `setattr()` and `delattr()` return `None` without running the pyscript setter or deleter, and Python warns that a coroutine was never awaited.
- The docs' Language Limitations still say `getattr()`/`hasattr()` on a pyscript property raise an error, and that a property deleter doesn't work.

## What we'll change
1. **Rebase.** Reapply #918's commit on top of master `029e522`, and resolve the clashes. It stays one commit, signed off.
   - *Check:* the full test suite, the formatting, style, lint and type checks, and the docs build pass, and every #918 test still passes.
2. **Deleter.** Add `delattr_async` next to `setattr_async`. It looks up the property the same way, using `pyscript_property(obj, attr, "__delattr__")`, and when the property's deleter is a pyscript function it awaits it. Otherwise it does what `del a.x` does today. `ast_delete` uses it only for object attributes. Deleting a state variable, like `del pyscript.x`, is unchanged.
   - *Check:* new scripts run in CPython and in pyscript, with every result compared:
     - the deleter runs, with its side effects;
     - a property with no deleter raises the same `AttributeError` as Python;
     - `property(fget, fset, fdel)`;
     - a deleter inherited from a base class;
     - a deleter that raises; in `del a.x, b[0]`, `b[0]` must then not be deleted;
     - `del a.x, b[0]` deletes in order;
     - a class with its own `__delattr__`, and a native descriptor with `__delete__` (both keep working as in Python);
     - a native property's deleter;
     - deleting a plain attribute;
     - and no "never awaited" warning when a pyscript deleter runs.
   - A pyscript deleter on a subclass of `property`, or in a class with its own `__delattr__`, still won't run, as with the setter. The docs list that.
3. **`super()` in a classmethod.** Add CPython comparison scripts for both `super().make()` and `super(C, cls).make()` inside a classmethod, including a chain of three classes and a classmethod called on an instance. No interpreter change is expected. If a script doesn't match Python, the Engineer fixes it and says so in the record.
   - *Check:* the scripts match CPython, and they fail if #918's classmethod support is removed.
4. **Docs.** In Language Limitations (`docs/reference.rst`):
   - add the deleter (`@x.deleter`, and `del obj.prop`) to what works;
   - remove it from what doesn't;
   - replace the `getattr()`/`hasattr()` sentence with what really happens:
     - `getattr(a, "x")` on a pyscript property gives a coroutine, not the value, and `hasattr(a, "x")` is True;
     - the built-in `setattr()` and `delattr()` don't run a pyscript setter or deleter;
     - so in pyscript code, use `a.x`, `a.x = value` and `del a.x`;
   - keep the subclass-of-`property` and own `__getattribute__`/`__setattr__`/`__delattr__` limits.
   - *Check:* `sphinx-build -W` passes, and each sentence matches a test or a check run on the branch.
5. **Description and reply.** The team prepares a new #918 description and a reply to the maintainer. The reply starts with "Thanks @craigbarratt" and answers his four points in order, saying exactly what changed and where. After Sean's final approval on GitHub (Gate B), the team updates `fix-property-classmethod` on the fork with a lease-guarded force push, which the rebase needs. Then Sean pastes the new description and posts the reply.

## Who's on it
CEO, Engineer, QA, Security Officer, Auditor, plan review, plain-English check. The Researcher was skipped: the maintainer's comment and the code give the facts.

## Risks
- My open batch-4 PRs (lambdas, `StopIteration`, trigger blanks) also change `eval.py` and the end of the test file. Whichever of them merges after #918 needs a small rebase. Those PRs are being updated for #916 right now, separately.
- The force push replaces #918's commit. It's lease-guarded and only after Gate B.

## Out of scope
- `functools.cached_property`, `super().prop`, and pyscript properties in classes that override `__getattribute__`/`__setattr__`. They stay listed as limitations, unless step 2 or 3 changes one of them.
- Making `getattr()`, `setattr()` or `delattr()` from native code call a pyscript property. That would need a different design.

---

## Record (2026-11-22)

**Status:** built and checked. Nothing open. Nothing has been sent upstream yet.

**What's ready:** `team/review-918-pr`, commit `8b9cdfa`. It's one commit, "support @property and @classmethod on pyscript class methods", on upstream master `029e522`. After approval it replaces `b24ab7d` on the fork's `fix-property-classmethod` branch, which is #918's branch.

**What changed, by the maintainer's points:**
1. **Rebase:** onto `029e522`. `unwrap_defined`, the `ModuleType` import and #918's module branch in `ast_attribute` are dropped, as #915 removed them. The property lookup now comes after #916's `__init__` check, and the classmethod case in `call_func` comes before #916's `super()` handling. All 31 earlier comparison scripts are unchanged and pass.
2. **Deleter:** `EvalAttrSet.delattr_async` awaits a pyscript deleter. `ast_delete` uses it for object attributes, and deleting a state variable is unchanged. The new `test_property_deleter_match_python` compares 12 scripts with CPython and checks that there's no "never awaited" warning. 7 of them fail without the change. The other 5 check behaviour that must stay the same.
3. **Docs:** the `@property` item in Language Limitations now says:
   - the deleter works;
   - `getattr()` gives a coroutine and `hasattr()` is True;
   - the built-in `setattr()` and `delattr()` don't run the pyscript code;
   - use `obj.prop`, `obj.prop = value` and `del obj.prop` instead.
   Every sentence was tried on the branch.
4. **`super()` in a classmethod:** the new `test_classmethod_super_match_python` compares 6 scripts with CPython. No interpreter change was needed. All 6 fail without #918's classmethod support.

**Checks:**
- Full suite: 228 passed.
- pre-commit: all hooks pass, and no files are left modified.
- `sphinx-build -W`: passes.
- Speed: about 2% slower than master on an attribute-load microbenchmark, which is within noise.
- QA: passed every plan step, and checked that both new tests fail without their change.
- Security: clear.
- Audit: approved in round 1, with 36 further probes against CPython. No fix rounds were needed.

**Deviations from the plan:** none.

**Still documented as limits:**
- a pyscript getter, setter or deleter on a `property` subclass, or in a class with its own `__getattribute__`, `__setattr__` or `__delattr__`;
- `functools.cached_property`;
- `super().prop`;
- the built-in `getattr()`, `setattr()` and `delattr()`.

**Overlaps:** #919 (lambdas) and #920 (`StopIteration`) also change `eval.py`. #919, #920 and #921 add tests at the end of `tests/test_unit_eval.py`. Whichever merges later needs a small rebase.

**Skipped:**
- the Researcher, because the maintainer's comment gave the facts;
- the second security review, because nothing security-related changed.
