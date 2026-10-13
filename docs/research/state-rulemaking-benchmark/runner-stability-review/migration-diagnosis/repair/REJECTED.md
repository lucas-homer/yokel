# Superseding review verdict: do not build or run repair.m

2026-10-11. The prompt-only native candidate is **rejected for live use**. Its 19 pure
fixture checks prove transformation/preservation logic only, not permission to change
the backend partition. Independent reviewer identified that partition mutation requires
explicit validated database credentials; the prompt-credential SetAccess path does not
provide them. The stopped source/HANDOFF are historical candidate evidence, not approval.

No production helper was built or executed, no live mutation occurred, and stable-v1
remains unchanged. Do not extend this helper into a custom password collector when
the installed built-in CLI supports a local prompt and narrower reviewed operation.

Primary and reviewer are assessing `security set-generic-password-partition-list`
without `-k`. Installed help explicitly directs omission for a prompt. That command's
matching selectors can update all matching items, so exact account/service matching
in the one explicit login keychain must first be proven to select **exactly one**
reference with no password data. CLI mutation remains user-only after independent
review. No command has been run by this task.
