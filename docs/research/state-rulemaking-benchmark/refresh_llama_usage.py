"""Read-only usage refresh for the twelve already completed benchmark jobs."""
import json
import os
from pathlib import Path

from run_llama_api import API, atomic_json, now, require


def main():
    root = Path(__file__).resolve().parent / "artifacts"
    recovered = json.loads((root / "llama-recovery-2026-10-05/recovery-manifest.json").read_text())
    jobs = recovered["jobs"] + [json.loads(line) for line in
        (root / "execution-dashboard-1/dashboard-jobs.jsonl").read_text().splitlines() if line.strip()]
    require(len(jobs) == len({j["job_id"] for j in jobs}) == 12, "Expected twelve unique historical jobs")
    key = os.environ.get("LLAMA_CLOUD_API_KEY", "")
    require(key and not key.startswith("op://"), "Resolved credential required")
    out = root / "execution-api-1/historical-usage-refresh"
    out.mkdir(exist_ok=True)
    api = API(key, recovered["project_id"], out)
    rows = []
    for expected in jobs:
        result = api.request("GET", "/api/v2/parse/" + expected["job_id"],
                             query={"expand": ["usage", "job_metadata"]})
        job = result["job"]
        require(job["id"] == expected["job_id"] and job["tier"] == expected["tier"], "Job identity mismatch")
        require(job["status"] == "COMPLETED", "Historical job is not completed")
        rows.append({"fixture_id": expected["fixture_id"], "tier": expected["tier"],
                     "job_id": job["id"], "usage": job.get("usage"),
                     "job_metadata": result.get("job_metadata"), "http_receipt": api.last_capture})
        atomic_json(out / "usage.json", {"observed_at_utc": now(), "jobs": rows,
                                         "complete": len(rows) == 12, "read_only": True})
    values = [(j.get("usage") or {}).get("credits") for j in rows]
    print(json.dumps({"historical_jobs_checked": len(rows),
                      "reported_credits": sum(v for v in values if isinstance(v, (int, float))),
                      "missing_usage": sum(v is None for v in values)}))


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(json.dumps({"usage_refresh_failed": True, "error_class": type(error).__name__}))
        raise SystemExit(1)
