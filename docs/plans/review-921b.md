# Plan: review-921b

**What Sean asked for:** "yes on 921", meaning rework #921 the simpler way the two reviewers asked.

## The two comments we haven't answered
- **The maintainer, 20:21 UTC:** "A simpler variant: only wrap when the expression contains a new line, and otherwise just strip it, as you do now. Single-line expressions then keep their exact error offsets. For a multi-line one, `"(" + expr + "\n)"` without stripping keeps the line numbers the same as the original, and only shifts the columns on the first line by one. That first line is usually empty in a triple-quoted string."
- **dmamelin, 21:43 UTC:** "+1 to @craigbarratt's simpler variant: wrap only multi-line expressions, strip single-line ones. The current version solves a small problem with a lot of machinery: a tokenize pass, position remapping for every expression, and tests that pin exact CPython error offsets. It also quietly makes new syntax valid, like a bare generator, walrus, or `a, b` as one tuple. Once that ships it becomes API we have to keep. A bare generator is a real footgun: forget `any()` and the trigger fires on every change."

The maintainer's 20:21 comment came in before our 20:37 reply, but the reply didn't answer it. The new reply apologises and answers both comments.

## What we found
- #921 is now two commits on the fork's `fix-trigger-expr-whitespace-617` branch:
  - `1e39bf5`, which strips blanks with `strip_trigger_expr()` and puts each of several `@state_trigger` entries on its own lines with `any_trigger_exprs()`;
  - `9fe371a`, the big second commit: `AstEval.parse_trigger_expr()`, a token check, and position fixes for every expression.
- Both still merge cleanly into master `a7a9541`.
- With several entries, `1e39bf5` already puts each one inside the `any([...])` brackets on its own lines. So a multi-line entry already works there. Only a single multi-line expression needs the new wrapping.
- In the wrapped text `"(" + expr + "\n)"`, Python reports a bare generator, a bare tuple, an empty expression and `a) or (b` as starting at our added `(`. An expression the user wrote correctly starts after it. This was checked on Python 3.14. A bare `:=` or `yield` can't be told apart from a bracketed one that way, so plan review proposed a second, cheap parse for those three kinds only.

## What we'll change
1. **Replace the second commit with a much smaller one.** `9fe371a` is replaced by one new signed-off commit on top of `1e39bf5`. `1e39bf5` stays as it is.
   - The token check goes.
   - The position fixes for every expression go.
   - So do the tests that pin Python's exact error positions.
2. **Wrap only multi-line expressions, as the maintainer suggested.** An expression counts as multi-line when it still has a line break (`\n` or `\r`) after the blanks around it are removed.
   - **A one-line expression** is stripped and parsed exactly as in `1e39bf5`, so it keeps its exact error positions. Nothing new is accepted or rejected, and `a, b` and `(x := 1)` work as before.
   - **A multi-line expression** is parsed as `"(" + expr + "\n)"`, without stripping, so its line numbers stay as written. Error messages show the user's own text and point at the right place:
     - for a syntax error, the error's start and end on line 1 move one character left. The same goes for the fields a script can read from a caught `SyntaxError`;
     - for an error while it runs, the position of the part of the expression that failed moves one character left when that part is on line 1;
     - an error found at the added `)`, for example when the expression is cut short after `and`, is reported at the end of the user's last line that isn't blank;
     - an unclosed bracket of the user's own makes Python blame the added `(`. That's reported at the start of the first line. It isn't traced back to the user's bracket, because that would need the token machinery again.

     All of this stays a few lines, for multi-line expressions only. The error report keeps recognising the new parse step, as it does `AstEval.parse`.
   - **State triggers.** The callers in `decorators/state.py` and `trigger.py` strip each entry before parsing. They now use a stripped copy only to recognise a bare state name, and pass the original text on, so line numbers survive.
   - **Several `@state_trigger` entries** keep `1e39bf5`'s `any([...])`: stripped entries, each on its own lines inside the brackets. Only the expression entries are counted, after the bare names are taken out.
   - **Where it's used:**
     - in the current code, `create_expression` in `decorators/base.py`. That covers `@state_trigger`, `@state_active`, `@event_trigger`, `@mqtt_trigger`, `@webhook_trigger`, `@webhook_handler`, and `task.wait_until` through `decorator.py`;
     - in the older code path, `TrigTime.wait_until` and `TrigInfo` in `trigger.py`. That path has no `@webhook_handler`.
   - *Check:* the tests cover behaviour, not Python's exact error wording:
     - #617's exact example as a single `@state_trigger`;
     - one-line expressions with blanks, including `a, b` and `(x := 1)`, behaving as in `1e39bf5`;
     - a trailing `# comment`;
     - several entries mixing bare names and multi-line expressions, with comments on either;
     - a syntax error and an error while running, on the first line and on a later line of a multi-line expression, checking the reported line, the text shown and the marker;
     - a cut-short expression and an unclosed bracket;
     - Windows line endings (`\r\n`) and a lone `\r`;
     - non-English letters on the first line;
     - every trigger kind, in both code paths where it exists.
3. **No new kinds of expression, as dmamelin asked.** The only new thing is that a line break no longer needs brackets. After parsing a multi-line expression, a small check gives a clear `SyntaxError` for anything that's valid only because of the added brackets:
   - **Starts at the added bracket.** Python reports where each part of an expression starts. When it says the whole expression starts at our `(`, the expression needed that bracket. That covers:
     - a bare generator (`x == 1 for x in y`), which would always count as true;
     - a bare tuple (`a,\n b`), including one with `*`;
     - an empty or comment-only expression;
     - `a) or (b`.
   - **A bare `:=`, `yield` or `yield from`.** Python's parsed result looks the same with and without the user's own brackets. So for these three, the text is parsed once more as a keyword value (`f(value=...)`), where a bare one is an error and a bracketed one isn't.
   - What a user writes inside their own brackets still works, for example `(x := 1)` and `any(x for x in y)`. There's no token pass.
   - *Check:* there's a test for each rejected form, and for the same forms inside the user's own brackets, which keep working. Each is tried with a comment line before it and with indentation.
4. **Docs.** Replace the note in the `@state_trigger` section of `docs/reference.rst`:
   - a trigger expression may start and end with blanks;
   - an expression written over several lines is read as if inside brackets, so it needs no brackets of its own;
   - an expression over several lines can't rely on the added brackets for anything else: a bare generator, a bare tuple, an empty expression, or a bare `:=` or `yield` gives an error;
   - the same goes for `@state_active`, `task.wait_until` and the event, MQTT, webhook trigger and webhook handler expressions.
   - *Check:* the docs build with warnings treated as errors passes, and every sentence matches a test.
5. **Reply and description.** The team writes:
   - a reply that starts with "Thanks @craigbarratt and @dmamelin". It apologises for missing the 20:21 comment, then answers each point in order and says what changed and where. For the maintainer's points: wrap only multi-line, strip single-line, line numbers unchanged, the first-line column. For dmamelin's: the machinery that's gone, no new syntax, the bare generator;
   - an updated #921 description.

   After Sean approves the finished work on GitHub (Gate B), the team replaces the second commit on the fork's `fix-trigger-expr-whitespace-617`. The push is guarded: it only goes through if nobody has changed the branch since `9fe371a`. Sean then pastes the description and posts the reply.
   - *Check:* on Python 3.14, the full test suite, pre-commit and the docs build all pass, and the branch merges into master with no clashes. Just before Gate B, the team fetches #921's comments again and answers any new ones.

## Who's on it
CEO, Engineer, QA, Security Officer, Auditor, plan review, plain-English check. The Researcher was skipped: the comments and the code give the facts.

## Risks
- The check in step 3 relies on where Python's parser says a node starts. Tests cover each form, so a change in Python would show up as a failing test.
- Replacing a commit that reviewers have already seen: the reply says so plainly. The first commit is unchanged.

## Out of scope
- #920's rework, which is a separate job and is running now.
