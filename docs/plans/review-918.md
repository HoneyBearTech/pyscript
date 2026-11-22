# Plan: review-918

**What Sean asked for:** "let's work 918"

## What we found
- The maintainer reviewed #918 (support `@property` and `@classmethod` on pyscript class methods) and said it works well. He asked for four things:
  1. rebase onto master now that #916 has merged;
  2. make `del a.x` call a pyscript `@x.deleter`, the same way the setter works, with a test;
  3. update the docs: since #910, `getattr(a, "x")` on a pyscript property returns a coroutine instead of raising, and `hasattr` returns True;
  4. add a test for `super()` inside a classmethod.
- #918 is one commit, `b24ab7d`, on the fork's `fix-property-classmethod` branch. It now clashes with master `029e522` in `eval.py`. #915 removed `unwrap_defined`, the `ModuleType` import and the module branch in `ast_attribute`, and #916 changed nearby code. The tests at the end of `tests/test_unit_eval.py` also clash.
- Today, `del a.x` goes through `EvalAttrSet.delattr()` (`eval.py`). That is plain Python `delattr`, which calls a pyscript deleter without awaiting it, so the deleter never runs. The setter avoids this with `setattr_async`, which finds the property with `pyscript_property()` and awaits a pyscript `fset`.
- The docs' Language Limitations still say `getattr()`/`hasattr()` on a pyscript property raise an error, and that a property deleter doesn't work.

## What we'll change
1. **Rebase.** Move #918's commit onto master `029e522` and resolve the clashes. It stays one commit, signed off.
   - *Check:* the full test suite, the code checks and the docs build pass, and every #918 test still passes.
2. **Deleter.** Add `delattr_async` next to `setattr_async`. It looks up the property the same way and, when the property's deleter is a pyscript function, awaits it. Otherwise it does what `del a.x` does today. `ast_delete` uses it for `del a.x`, including inside `del a.x, b[0]`.
   - *Check:* new scripts run in CPython and in pyscript, with every result compared:
     - the deleter runs, with its side effects;
     - a property with no deleter raises the same `AttributeError` as Python;
     - `property(fget, fset, fdel)`;
     - a subclass of `property`;
     - a class that overrides `__delattr__`;
     - a deleter that raises;
     - a native property's deleter;
     - deleting a plain attribute.
3. **`super()` in a classmethod.** Add CPython comparison scripts for both `super().make()` and `super(C, cls).make()` inside a classmethod, including a chain of three classes and a classmethod called on an instance. If any of them don't match Python, fix the `super()` lookup so they do.
   - *Check:* the scripts match CPython, and they fail if the fix is removed.
4. **Docs.** In Language Limitations (`docs/reference.rst`):
   - add the deleter (`@x.deleter`, and `del obj.prop`) to what works;
   - remove it from what doesn't;
   - replace the `getattr()`/`hasattr()` sentence with what really happens: `getattr(a, "x")` on a pyscript property gives a coroutine, not the value, and `hasattr(a, "x")` is True, so use `a.x` in pyscript code. The same applies to the built-in `setattr()` and `delattr()` if that's what they do; we check on the branch and describe what we find.
   - *Check:* `sphinx-build -W` passes, and each sentence matches a test or a check run on the branch.
5. **Description and reply.** Update #918's description and write a reply to the maintainer. It starts with "Thanks @craigbarratt" and answers his four points in order, saying exactly what changed and where. After Gate B, the team updates `fix-property-classmethod` on the fork with a lease-guarded force push (needed because of the rebase). Sean then updates the description and posts the reply.

## Who's on it
CEO, Engineer, QA, Security Officer, Auditor, plan review, plain-English check. The Researcher was skipped: the maintainer's comment and the code give the facts.

## Risks
- Zero-argument `super()` in a classmethod may not work yet with #916's lookup, which expects an instance as the first argument. Step 3 finds out, and fixes it if needed.
- My open batch-4 PRs (lambdas, `StopIteration`, trigger blanks) also change `eval.py` and the end of the test file. Whichever of them merges after #918 needs a small rebase. Those PRs are being updated for #916 right now, separately.
- The force push replaces #918's commit. It's lease-guarded and only after Gate B.

## Out of scope
- `functools.cached_property`, `super().prop`, and pyscript properties in classes that override `__getattribute__`/`__setattr__`. They stay listed as limitations, unless step 2 or 3 changes one of them.
- Making `getattr()`, `setattr()` or `delattr()` from native code call a pyscript property. That would need a different design.
