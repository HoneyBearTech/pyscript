# Plan: fixes-batch-1

## What Sean asked for
"Start with pyscript": fix open problems in pyscript and send each fix back to the original project (custom-components/pyscript) as its own pull request.

## What we found
- **Baseline:** the test suite and every style check pass on today's code. That is 202 tests, on Python 3.14 and Home Assistant 2026.11.
- **Few real bugs:** of the 139 open issues, only a handful are real problems an outsider can fix today. Most of the rest are:
  - feature requests;
  - how-to questions;
  - problems the maintainer has said are the user's responsibility;
  - issues already fixed in the code but never closed (about 17, for example #686, #676, #819, #761, #512).
- **Five worth fixing now:** these need no design decision from the maintainer.
  - **#875:** a type hint inside a class that names another class from the same script (`bar: Foo | None`) crashes with a TypeError.
  - **#891:** a class that inherits from another class defined in the script doesn't get its parent's setup method (`__init__`). Creating it fails or leaves it half set up.
  - **#877:** at startup, pyscript reads Home Assistant's private saved-state data directly. Home Assistant now offers a supported way to read it.
  - **#729:** the docs suggest `modules.MODULE` is something you can import. It isn't, and the right form is `import MODULE`.
  - **#814:** the generated helper "stubs" (used by code editors) list some argument types too narrowly. Some items on that list are already fixed.

## What we'll change
1. **Fix #875** in the script runner (`custom_components/pyscript/eval.py`), so a type hint inside a class can name a class defined in the same script.
   - **Check:** a new test in `tests/test_unit_eval.py` reproduces the crash. It must fail before the fix and pass after.
   - **Fallback:** if there is no safe code fix, add a short note to the docs' "Language Limitations" section showing the `Optional[Foo]` workaround.
2. **Fix #891** in `custom_components/pyscript/eval.py`: a child class with no `__init__` of its own uses its parent's.
   - **Check:** new tests in `tests/test_unit_eval.py` cover a child class with no `__init__`, with and without arguments.
   - **Not included:** calling the parent's `__init__` from inside the child (`super().__init__(...)`) is a harder change. It may need the maintainer's view, so it is out of scope here.
3. **Fix #877** in `custom_components/pyscript/__init__.py`: read saved pyscript states through Home Assistant's supported `async_get_stored_states()`.
   - The current method stays as a fallback for older Home Assistant versions.
   - **Check:** the existing restore tests in `tests/test_init.py` still pass, and a new test covers the supported path.
4. **Fix #729** in `docs/reference.rst`: one or two sentences explaining that `modules.MODULE` is only an internal name used in logs and reloads, and that modules are loaded with `import MODULE`.
   - **Check:** read the docs change; a docs build if one runs locally.
5. **Fix #814** in `custom_components/pyscript/stubs/`: check each item still listed in the issue against the generated stubs, and correct only those that are still wrong.
   - **Check:** `tests/test_stubs.py`, extended where it helps.
   - **If unsure:** if this turns out to be unclear or big, it is dropped from this batch and reported.
6. **Run every CI check:** pylint, mypy, ruff and pytest, the same way the project's CI runs them, on Python 3.14.
7. **Send upstream, only after the final approval on this PR:**
   - Each fix gets its own clean branch, started from the original project's latest code. It holds only that fix and its test. None of these plan or notes files go upstream.
   - That branch is pushed to this fork, then opened as one pull request per fix against custom-components/pyscript.
   - Each description is written as Sean working alone, in plain English: what was broken, why, what changed, how it was tested, and `Closes #<n>`.
   - Draft titles:
     - "Fix TypeError when a class type hint names another class from the same script (#875)"
     - "Let subclasses use their parent class's __init__ when they don't define one (#891)"
     - "Restore saved pyscript states through Home Assistant's supported API (#877)"
     - "Docs: clarify that modules.MODULE is a context name, not an import path (#729)"
     - "Widen argument types in the generated stubs (#814)"
   - The full text of each title and description is in the final report here, before anything is sent.

## Who's on it
Researcher (done), Engineer, QA, Security Officer, Auditor, plus a plan check and a plain-English check.

## Risks
- **#877 and saved values:** this changes how saved values come back after a restart. A mistake could lose users' saved pyscript values. The old method stays as a fallback, and tests cover both paths.
- **#875 and #891 and the script runner:** these touch the core of how scripts are run. Each is kept as small as possible, and the full test suite must pass.
- **The maintainer may want something different:** he may prefer another fix, or the bigger rework in #885. Each pull request is small so it's easy to change.

## Out of scope
- **Need a design decision from the maintainer:** #831, #885, and the `super().__init__` part of #891.
- **#829:** the warning could not be reproduced.
- **#850 and #879:** the maintainer says these are not pyscript's job.
- **Already-fixed issues:** commenting on the ~17 issues that are already fixed, so they can be closed. That's a separate step if Sean wants it.
- **Fork-only files:** no guidelines files, badges or notes go into the upstream pull requests.
