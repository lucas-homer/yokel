#!/bin/zsh
# Run batches sequentially; abort the chain if any batch reports a stopped host.
cd /Users/home/.t3/worktrees/yokel/research-state-rulemaking/docs/research/state-coverage-plan/census
for b in "$@"; do
  python3 capture.py --requests WA/requests/$b.jsonl --out WA/capture-results/$b.jsonl > /dev/null 2> /tmp/wa-acq/$b.err
  echo "$b $(date -u +%FT%TZ) $(cat /tmp/wa-acq/$b.err)"
  if ! grep -q '"stopped_hosts": {}' /tmp/wa-acq/$b.err; then echo "ABORT: stopped host in $b"; exit 3; fi
done
