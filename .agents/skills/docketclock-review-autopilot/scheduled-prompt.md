# The scheduled task's prompt (verbatim)

The T3 Code scheduled task "Review autopilot" runs the text below the rule, daily at 07:00 local,
bound to the dedicated "Review autopilot" thread (provider `claudeAgent`, model `claude-opus-5-5`,
effort `high`), whose checkout is a worktree on branch `t3/review-autopilot`, created from `main`
and never committed to. To flip to write mode, change `AUTOPILOT_MODE` to `write` **and** add the
line `AUTOPILOT_GATE=met:<YYYY-MM-DD>` here and in the task's prompt (`update_scheduled_task`) in
the same change, only after the runbook's gate record shows all three parts met on that date.

---

AUTOPILOT_MODE=shadow

Review autopilot run. First, in this checkout, run `git fetch -q origin main && git merge -q --ff-only origin/main`. If that fails, write the git error to `/tmp/review-autopilot/checkout-failure.txt`, page it once — `curl -fsS -H 'Title: Review autopilot: checkout update failed' --data-binary @/tmp/review-autopilot/checkout-failure.txt "$(cat ~/.config/yokel/ntfy-url)" >/dev/null`, never printing the URL — then continue with the checkout as it is and record the failure under Tooling in the report (already paged; do not page it again). Then load `.agents/skills/docketclock-review-autopilot/SKILL.md` and follow it exactly in the mode above. On Mondays include the weekly audit. Finish with the one-message report in the skill's format and stop; do not start other work, do not commit, and do not change this task.
