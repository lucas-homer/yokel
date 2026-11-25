# Agent vs DocketClock benchmark

Does DocketClock make an agent more right about federal comment deadlines, and how often does a plain
agent give a confident wrong date? Design and rationale: the "Agent vs DocketClock: test design" doc
(linked from the PR that added this directory).

Everything here runs **on the operator's Mac**, on their own Claude plan, through headless Claude Code
(`claude -p`). The answer key and the run outputs live under `~/.config/yokel/bench/`, never in the repo:
a key on GitHub is a key a web-searching agent can find.

## Arms

| Arm         | Gets                                                                                       |
| ----------- | ------------------------------------------------------------------------------------------ |
| A           | Web search and fetch                                                                       |
| B           | A + `curl` to the Federal Register and Regulations.gov APIs (the arm that matters)         |
| C           | B + the DocketClock API                                                                    |
| D-machine   | No agent: DocketClock's own derivation with human verdicts hidden (`review show --blind`)  |
| D-published | No agent: what DocketClock published, pins included (wins the pin stratum by construction) |

Models: `opus` (claude-opus-5-5) and `fable` (claude-fable-5-2). The frozen prompts are in `prompts/`;
the run directory is named after their hash, so changing a prompt or `src/bench/questions.ts` starts a
new run instead of mixing results.

## One-time setup

```sh
# secrets, readable only by you; arm C also needs the API URL and a key
cat ~/.config/yokel/bench.env
#   REGS_API_KEY_BENCH=…        a separate api.data.gov key (the poller's is near its hourly limit)
#   DOCKETCLOCK_API_URL=https://…workers.dev
#   DOCKETCLOCK_API_KEY=…

# check what a benchmark session actually loads: tools should be the arm's, MCP servers none
pnpm --filter @yokel/docketclock bench:run --preflight --models opus
```

If preflight shows MCP servers, extra tools or memory files, stop: the isolation leaks.

## Workflow

```sh
# 1. export the key (read-only; needs DATABASE_URL for Neon)
DATABASE_URL=… pnpm --filter @yokel/docketclock bench:export

# 2. hand-check: items with "needs_check": true (misses, routine, "never moved") are graded by
#    DocketClock's own post-close check. Check them against the live sources, fix any key, and set
#    needs_check to false. The grader skips unchecked items unless --include-unchecked.

# 3. pilot: 20 items spread across strata, arms B and C, both models
pnpm --filter @yokel/docketclock bench:run --sample 20 --arms B,C --models opus,fable --dry-run
pnpm --filter @yokel/docketclock bench:run --sample 20 --arms B,C --models opus,fable

# 4. grade (prints and writes report.md in the run dir)
pnpm --filter @yokel/docketclock bench:grade --run ~/.config/yokel/bench/runs/prompts-<hash>
```

`bench:run` is resumable: re-running the same command skips jobs already in `results.jsonl`.

## Strata in the key

| Stratum       | Family | Key from                                                                                           |
| ------------- | ------ | -------------------------------------------------------------------------------------------------- |
| pin           | lookup | honored human `pin_close` verdicts                                                                 |
| withdrawn     | lookup | honored `confirm_withdrawn`                                                                        |
| escalate      | lookup | honored `escalate` (the right answer is "unresolved")                                              |
| miss          | lookup | accuracy records with `was_correct = false`; key = latest contradicting portal value (needs check) |
| routine       | lookup | random accuracy records with `was_correct = true` (needs check)                                    |
| point_in_time | memory | what Regulations.gov showed on a past day, from the observation log                                |
| moved         | memory | whether the portal close ever changed, and its earliest value                                      |

Not yet in the key: multi-deadline notices (the ADR 0017 hand labels were never committed) and discovery
questions.

## Grades

`correct`, `honest_miss` (abstained or low confidence where the key was resolvable), `correct_abstention`
(abstained on an escalate), `silent_wrong` (confident and wrong: the headline number), `unparseable`,
`void` (reached a blocked host, used a tool outside the arm, or ran Bash other than `curl`). The rules are
the pure functions in `src/bench/grade.ts`, pinned by `test/bench-grade.test.ts`.

## Known caveats

- In arm C the DocketClock API serves your pins as the published close, so C sees the answer on the pin
  stratum. That is part of what DocketClock is (human review is the product), but read C's pin numbers
  with that in mind; D-machine is the honest no-human baseline.
- Web search results cannot be filtered by domain from settings, so blocked hosts are enforced on fetch and
  curl, and the grader voids any job whose tool inputs name one.
- `--max-turns` is passed to `claude -p`; confirm on the pilot that turn counts in `results.jsonl` respect it.
