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
