# Plan: super-prop

**What Sean asked for:** "work the suggested follow-up on 918"

The maintainer's follow-up, from his approval of #918: "`super().prop` could be supported by looking up the property in the MRO after `__thisclass__` when the object is a `super`."

## What we found
- Since #918 (master `5820c4f`), pyscript runs a pyscript property's getter itself, because Python can't call pyscript's async functions. It finds the property with `pyscript_property(obj, attr, hook)` (`eval.py`), which looks along `type(obj).__mro__`.
- For `super().prop`, the object is a `super` object. `type(obj)` is `super`, which has no `prop`, so pyscript leaves the lookup to Python. Python then calls the pyscript getter like a normal function and gets back a coroutine instead of the value. So the most common use, a subclass property that extends its parent's, doesn't work:

  ```python
  class Base:
      @property
      def label(self):
          return "base"

  class Child(Base):
      @property
      def label(self):
          return super().label + "+child"   # TypeError: a coroutine, not "base"
  ```
- The docs' Language Limitations list `super().prop` as not working.
- A `super` object knows where to look: `__thisclass__` (the class it was made in), `__self__` (the object), and `__self_class__` (the object's class, or the object itself when it's a class). Python searches `__self_class__.__mro__` (the ordered list of classes it checks) after `__thisclass__`. It gives the property no instance only when `__self__` is `__self_class__`, and it never searches for `__class__`.

## What we'll change
1. **Find the property behind `super()`.** In `ast_attribute`, for reading an attribute only, the new check goes after the existing state-variable, assignment and `__init__` handling, and before the ordinary property check. When the object is exactly a `super` object (not a subclass of `super`), and the attribute isn't `__class__`, search `__self_class__.__mro__` after `__thisclass__`, as Python does. If the first class that has the attribute holds a plain `property` whose getter (the function that computes the value) is a pyscript function, and `__self__` is not `__self_class__`, await the getter with `__self__`. That includes a class whose metaclass defines the property. Otherwise, leave everything to Python, as now. An `AttributeError` from the getter goes straight to the caller, with no `__getattr__` fallback, because `super` doesn't use one. That covers:
   - an unbound `super(C)`;
   - `super(C, cls)` on a class, where Python returns the property object itself;
   - a nearer plain attribute or method that hides a farther property;
   - a property with no getter;
   - a `super` object whose `__thisclass__` is no longer in the list, for example after `__bases__` changes, where Python's own error stays;
   - a `property` subclass;
   - a compiled or native getter;
   - a plain attribute or method. Pyscript methods and `super().__init__()` keep their existing paths.

   A class's own `__getattribute__` doesn't matter here, because Python's `super` doesn't use it. The code follows the same rule.
   - *Check:* new scripts run in CPython and in pyscript, and every result is compared:
     - `super().prop` and `super(C, self).prop` in a method and in an overriding property getter;
     - a chain of three classes;
     - a property defined in a mixin, in a diamond-shaped hierarchy;
     - a getter that raises `AttributeError`, which needs no `__getattr__` fallback, because `super` doesn't use one;
     - a compiled getter;
     - a native property;
     - `super(C, cls).prop` on a class;
     - a class with its own `__getattribute__`;
     - `super(C, self).prop` inside a generator expression and a comprehension, where zero-argument `super()` in a generator expression gives Python's own `TypeError`;
     - a metaclass property read through `super(Meta, cls)`;
     - a property named `__class__` on a parent, where `super().__class__` is still `super`;
     - a `super` subclass with its own `__getattribute__`;
     - a nearer plain attribute hiding a farther property, and a property with no getter;
     - `super()` after the class's bases change;
     - setting or deleting through `super()`, which raises the same `AttributeError` as Python;
     - calling a parent's setter directly with `super(C, type(self)).prop.fset(self, value)`.
   - The scripts for the new behaviour (a pyscript getter reached through `super()`) must fail without the change. The others check behaviour that already works and must keep working.
2. **Docs.** In Language Limitations, take `super().prop` off the "doesn't work" list and add it to what works. A pyscript getter on a `property` subclass stays listed as not working, through `super()` too. The limit for classes with their own `__getattribute__` stays, but it says that reading through `super()` isn't affected, because `super` skips that method, as in Python.
   - *Check:* `sphinx-build -W` passes, and each sentence matches a test.
3. **Upstream PR.** One commit, signed off, on a new fork branch `support-super-property` from master `5820c4f`. The team writes a full description in the layout of the earlier upstream PRs, #916 and #918 (What was broken, Why, What I changed, Testing, Docs, Note), which credits the maintainer's suggestion. After Gate B, the team pushes the branch to the fork. Sean opens the PR from a link with the title filled in.
   - *Check:* on Python 3.14, the full test suite (`pytest`), the formatting, style, lint and type checks (`pre-commit run --all-files`), and the docs build (`sphinx-build -W`) all pass.

## Who's on it
CEO, Engineer, QA, Security Officer, Auditor, plan review, plain-English check. The Researcher was skipped: the maintainer's comment and the code give the facts.

## Risks
- The extra check runs on every attribute load. It only applies when the object is a `super` object, so the cost elsewhere should be one type check. The Engineer measures it.
- #919 (lambdas) and #920 (`StopIteration`) also change `eval.py` and the end of the test file, and they're being updated for #918 next. Whichever merges later needs a small rebase.

## Out of scope
- `functools.cached_property`, and pyscript getters on `property` subclasses. They stay listed as limits.
- Updating #919 and #920 for #918. That's the next job.
