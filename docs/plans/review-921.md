# Plan: review-921

**What Sean asked for:** "yes on 921" (make the change the maintainer asked for on upstream #921)

The maintainer's review of #921: "The stripping works, but the example in #617 still fails: its lines end in `and` with no brackets around the whole expression, which is a `SyntaxError` after stripping. It's also inconsistent: with two or more `@state_trigger` entries, each one is already inside the `any([...])` brackets, so a multi-line entry works there but not on its own. Could you parse each trigger expression as `"(" + expr + "\n)"` instead? That handles the leading and trailing blanks too, lets any multi-line expression work as it would inside brackets in Python, and keeps a trailing `# comment` working. The error report would need to adjust the first line's offset by one. The docs could then drop the note that a multi-line expression needs brackets."

## What we found
- #921 is one commit, `1e39bf5`, on the fork's `fix-trigger-expr-whitespace-617` branch, on `029e522`. It still merges cleanly into today's master `a7a9541`.
- #921 strips the blanks around each trigger expression (`strip_trigger_expr` in `trigger.py`) before it's parsed. That fixes blanks, but a line break in the middle still needs brackets, as in Python. #617's own example has lines that end in `and` with no outer brackets, so it still fails.
- With two or more `@state_trigger` entries, pyscript joins them into one `any([...])` expression, so each entry is already inside brackets and a multi-line entry works there. With one entry it doesn't. The maintainer's suggestion makes both cases behave the same.
- Trigger expressions are parsed in these places: `@state_trigger` (one entry or several), `@state_active`, and the expressions of `@event_trigger`, `@mqtt_trigger`, `@webhook_trigger` and `@webhook_handler`. The current code parses them all in one place (`decorators/base.py`), which `task.wait_until` also uses. The older code path that the tests still run (`TrigTime.wait_until` and `TrigInfo` in `trigger.py`) parses them separately. Error messages show the line of code and point at the error's position on that line (`EvalExceptionFormatter` in `eval.py`). Adding `"("` in front moves every position on the first line one place to the right.

## What we'll change
"CPython comparison" means the same expression is parsed by ordinary Python inside brackets, and the result is compared with pyscript's.

1. **Parse each trigger expression inside brackets.** One shared helper parses an expression as `"(" + expr + "\n)"`, as the maintainer suggested, and every place listed above uses it, in the current code and the older code path. The new line before `)` keeps a trailing `# comment` from hiding the closing bracket. With several `@state_trigger` entries, each entry gets its own brackets inside the `any([...])`. So:
   - an expression can start and end with blanks, and run over several lines with no brackets of its own;
   - one `@state_trigger` entry behaves the same as one of several. One rare change: an entry written as a bare tuple, like `a, b`, used to become two separate items in the `any([...])`. Now it's one tuple, which is always true, as it already was for a single trigger;
   - a plain state-variable name with blanks around it, like `" binary_sensor.door "`, is still treated as a name that triggers on any change;
   - an empty expression, or one with only blanks or a `# comment`, stays an error, rather than quietly becoming an empty tuple `()` that is never true. A written `()` still works as before;
   - text that closes the added opening bracket before its end, like `a) or (b`, is rejected with a syntax error, because it isn't one expression. A short check of the expression's tokens does this, skipping brackets inside strings and comments;
   - a few things that were errors before now work, as they would inside brackets in Python: a bare `x := value`, and a line that ends in `\`.

   #921's `strip_trigger_expr` is removed wherever the new helper replaces it.
   - *Check:* tests for #617's exact example as a single `@state_trigger`, and as one of several; leading and trailing blanks and tabs; a trailing `# comment` on the last line and on a middle line; `@state_active`, `task.wait_until` and the event, MQTT, webhook trigger and webhook handler expressions, in the current code and the older code path; a state name with blanks around it; the bare tuple, walrus and `\` cases; the empty, comment-only and `a) or (b` errors, and `a) or (b` next to a string or comment that holds a `)`, which must still work. For each expression that should work, the parsed result is compared with ordinary Python parsing the same text inside brackets.
2. **Error messages point at the user's own text.** "The user's own text" means the expression exactly as written, including any blank lines at its start. Syntax errors (when the expression is read) and errors while it runs (for example a name that doesn't exist) show the user's line, not the line with the added `(`, and point at the right place. On the first line, the position moves back by one, as the maintainer said. Errors on later lines keep their position. An error found at the added closing `)`, for example in `x == 1 and`, which is cut short, is reported at the end of the user's last line. The same corrected line, text and position are in the error a script can catch and read, not just the logged message. With several `@state_trigger` entries, errors show the combined `any([...])` text, as they do today. Ordinary script code and `eval()` are parsed as before.
   - *Check:* tests for a syntax error on the first line and on a later line, a cut-short expression, an unclosed bracket, and an error while it runs on the first line and on a later line, each checking the reported line, the text shown and where it points, in the logged message and in the caught error; and an error in the second of several `@state_trigger` entries, including a multi-line one. #921's existing error tests are updated where the text changes.
3. **Docs.** In `docs/reference.rst`, replace #921's note with one saying that a trigger expression can start and end with blanks and run over several lines without brackets, and that the same goes for `@state_active`, `task.wait_until` and the expressions of `@event_trigger`, `@mqtt_trigger`, `@webhook_trigger` and `@webhook_handler`. The sentence saying a multi-line expression needs brackets goes.
   - *Check:* the docs build with warnings treated as errors (`sphinx-build -W -b html docs <folder>`) passes, and each sentence matches a test.
4. **Upstream PR update.** One new commit, signed off as the project requires, on top of #921's commit, so the maintainer can see exactly what changed. The team writes a new #921 description, in the layout of the earlier upstream PRs, and a reply that starts with "Thanks @craigbarratt" and answers each of his points in order, saying exactly what changed and where. After Sean approves the finished work on GitHub (Gate B), the team adds the commit to `fix-trigger-expr-whitespace-617`. That's an ordinary push that adds to the branch, with no force push. Sean then pastes the new description and posts the reply.
   - *Check:* on Python 3.14, the full test suite (`pytest`), the formatting, style, lint and type checks (`pre-commit run --all-files`) and the docs build (`sphinx-build -W`) all pass, and the branch still merges into master with no clashes.

## Who's on it
CEO, Engineer, QA, Security Officer, Auditor, plan review, plain-English check. The Researcher was skipped: the maintainer's comment and the code give the facts.

## Risks
- The line and position in error messages are easy to get wrong by one. Step 2's tests check them exactly.
- Rejecting `a) or (b` goes a little beyond what the maintainer asked. It's a short check, and the reply will say why it's there, so he can ask for it to be dropped.
- #919 (lambdas) and #920 (`StopIteration`) don't touch the trigger code, so they don't clash with this change.

## Out of scope
- Other strings that aren't trigger expressions, such as script code, `@time_trigger` and `@state_trigger` keyword options.
- Updating #919 and #920 for the new master. That's a separate job.

## Record
**2026-11-22. Built and checked.** The finished change is `team/review-921-pr`: one new commit, `9fe371a` "parse trigger expressions inside brackets so they can span lines (#617)", on top of #921's commit `1e39bf5`. It's signed off. After Gate B, it's added to the fork's `fix-trigger-expr-whitespace-617` with an ordinary push.

**What shipped**
- The new `AstEval.parse_trigger_expr()` in `eval.py` parses each trigger expression as `"(" + expr + "\n)"`. It's used by `create_expression` in `decorators/base.py`, which covers `@state_trigger`, `@state_active`, `@event_trigger`, `@mqtt_trigger`, `@webhook_trigger`, `@webhook_handler` and `task.wait_until`, and by the older paths in `trigger.py`, `TrigInfo` and `TrigTime.wait_until`.
- With several `@state_trigger` entries, each one gets its own brackets inside the `any([...])`. The `any([...])` stays, so all entries are still evaluated.
- Positions on line 1 move back by one after parsing. A syntax error is corrected in all its fields before it's raised again. An error at the added `)` is reported at the end of the user's last line that isn't blank.
- A short token check, `check_added_brackets`, rejects:
  - empty, blank-only and comment-only expressions;
  - an early close like `a) or (b`;
  - and it reports the user's own unclosed bracket at that bracket.
- #921's `strip_trigger_expr()` and `any_trigger_exprs()` are removed.
- Docs: the note in the `@state_trigger` section of `docs/reference.rst` is rewritten, and the "needs brackets" sentence is gone.

**Checks:** 298 tests, pre-commit (ruff, pylint, mypy, codespell and the others) and the docs build with warnings treated as errors all pass on Python 3.14. The branch merges into master `a7a9541` with no clashes. The new decorator and webhook tests fail on `1e39bf5`.
- **Plan review:** it found three gaps: entries in the several-entry case need their own brackets, errors at the added `)` need handling, and `@webhook_handler` was missing. All three were added to the plan before Gate A.
- **QA:** pass. Two wording notes on the description were fixed.
- **Security:** clear, with one should-fix. Some invalid inputs with a lone carriage return and a non-ASCII character made the token check fail with a text-decoding error, instead of the parser's ordinary syntax error. Fixed, and a test was added (`test_parse_trigger_expr_tokenize_decode_error`).
- **Audit:** approve, with no findings. It checked 376 valid inputs against Python and found no difference.

**Known limits, not changed (they also happen before this change)**
- Error markers on a line with non-ASCII text before the error can sit a few characters early in the logged message. The caught error has the right position.
- A run-time error that spans two lines is marked only on its first line.
- With a lone carriage return as a line break, error positions can be slightly off.
