"""Standalone round2 cost_effective runner for twenty frozen inputs /34pages.

Defaults to offline dry-run. --execute requires a key in LLAMA_CLOUD_API_KEY.
No submission retries. Ambiguous POSTs are reconciled by durable intent tags.
"""
import argparse
import datetime as dt
import fcntl
import hashlib
import json
import os
import re
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from pathlib import Path

BASE = "https://api.cloud.llamaindex.ai"
RUN_TAG = "round2-llama-cost-effective"
LANE_DIR = Path(__file__).resolve().parent
TERMINAL = {"COMPLETED", "FAILED", "CANCELLED"}
ACTIVE = {"accepted", "submit_inflight", "submit_uncertain"}
EXPAND = ["markdown_full", "markdown", "items", "job_metadata", "usage"]
SIGNED = re.compile(r'https://[^\s"<>]+(?:X-Amz-|X-Goog-|[?&](?:signature|sig|token)=)[^\s"<>]*', re.I)
DIFFERENCES = ["REST v2 nested configuration replaces dashboard legacy fields.", "No documented v2 equivalent verified for high_res_ocr or hide_headers/hide_footers; those legacy fields are omitted.", "Full Markdown uses expand=markdown_full; no page joining or JSON-based score rescue.", "Cache stays enabled; cost optimizer disabled; screenshots saved, HTML tables requested; no prompts.", "API times and usage are captured separately from dashboard/connector wrapper times."]


def now():
    return dt.datetime.now(dt.timezone.utc).isoformat()


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def require(ok, message):
    if not ok:
        raise ValueError(message)


def atomic_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = (json.dumps(value, indent=2) + "\n").encode()
    fd, name = tempfile.mkstemp(prefix=".state-", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(raw); stream.flush(); os.fsync(stream.fileno())
        os.replace(name, path)
        directory = os.open(path.parent, os.O_RDONLY)
        try: os.fsync(directory)
        finally: os.close(directory)
    finally:
        if os.path.exists(name): os.unlink(name)


def safe_value(value, secret=""):
    if isinstance(value, dict):
        return {k: "[REDACTED_TRANSIENT_URL]" if k.lower() in {"url", "download_url", "presigned_url", "form_fields"} else safe_value(v, secret) for k, v in value.items()}
    if isinstance(value, list): return [safe_value(v, secret) for v in value]
    if isinstance(value, str):
        value = value.replace(secret, "[REDACTED_KEY]") if secret else value
        return SIGNED.sub("[REDACTED_SIGNED_URL]", value)
    return value


def config(file_id, tier, token, input_hash):
    require(tier == "cost_effective", "Only cost_effective allowed in round2 lane")
    return {"file_id": file_id, "tier": tier, "version": "latest", "disable_cache": False,
            "processing_options": {"cost_optimizer": {"enable": False}, "ignore": {"ignore_text_in_image": False}},
            "output_options": {"images_to_save": ["screenshot"], "markdown": {"inline_images": False, "tables": {"output_tables_as_markdown": False, "merge_continued_tables": False}}, "spatial_text": {"preserve_very_small_text": False}},
            "user_metadata": {"benchmark_run": RUN_TAG, "intent_token": token, "input_sha256": input_hash, "tier": tier}}


def local_plan(root):
    expected = "900f21e8a75d50444f12a0e3814d665a4f401a0d689194465d0b00467a762946"
    raw_manifest = (root / "corpus-freeze.json").read_bytes()
    require(sha(raw_manifest) == expected, "Frozen manifest checksum changed")
    freeze = json.loads(raw_manifest)
    for rel, record in freeze["files"].items():
        path = (root / rel).resolve()
        require(root.resolve() in path.parents, "Frozen path escapes artifact root")
        raw = path.read_bytes()
        require(sha(raw) == record["sha256"] and len(raw) == record["bytes"], f"Frozen file changed: {rel}")
    order = [f"{letter}{i:02}" for letter in "AB" for i in range(1,11)]
    require(freeze["ordered_fixture_ids"] == order and len(freeze["units"]) == 20, "Expected exact twenty-unit order")
    # IDs are historical candidates only; every one must be downloaded/hashed live before reuse.
    candidates, candidate_sources = {}, {}
    previous = json.loads((root / "execution-api-1/state.json").read_text())
    require(all(j["phase"] == "completed" for j in previous["jobs"]), "Prior REST phase not terminal")
    for fid, record in previous["files"].items():
        require(record["phase"] == "verified", "Prior file proof not verified")
        candidates[fid] = record["file_id"]
        candidate_sources[fid] = "execution-api-1/state.json/files/" + fid
    for path in sorted((root / "execution-dashboard-1/runs").glob("*/*/capture.json")):
        c = json.loads(path.read_text())
        if c["fixture_id"] not in candidates:
            candidates[c["fixture_id"]] = c["file_id"]
            candidate_sources[c["fixture_id"]] = str(path.relative_to(root))
    old = json.loads((root / "llama-recovery-2026-10-05/recovery-manifest.json").read_text())
    for c in old["jobs"]:
        fid = c["fixture_id"]
        if fid not in candidates:
            candidates[fid] = c["dashboard_configuration_observation"]["file_id"]
            candidate_sources[fid] = "llama-recovery-2026-10-05/recovery-manifest.json"
    units = {u["fixture_id"]: u for u in freeze["units"]}
    require(set(units) == set(order), "Frozen fixture identities differ")
    jobs = []
    for fid in order:
        u = units[fid]; path = root / u["directory"] / "input.pdf"; raw = path.read_bytes()
        require(sha(raw) == u["input_sha256"] and len(raw) == u["input_bytes"], f"Input mismatch: {fid}")
        require(1 <= u["input_page_count"] <= 4, "Page bound exceeded")
        if fid in previous["files"]:
            require(previous["files"][fid]["download_sha256"] == u["input_sha256"], "Old candidate hash differs")
        jobs.append({"fixture_id":fid, "tier":"cost_effective", "input_path":str(path.relative_to(root)), "input_sha256":u["input_sha256"], "input_bytes":u["input_bytes"], "pages":u["input_page_count"], "candidate_file_id":candidates.get(fid), "candidate_source":candidate_sources.get(fid)})
    require(len(jobs) == 20 and sum(j["pages"] for j in jobs) == 34, "Twenty-input/34-page bound differs")
    return {"schema":2, "benchmark_run":RUN_TAG, "freeze_sha256":expected, "jobs":jobs, "max_active":2, "stop_consecutive_failures":3, "version":"latest", "input_pages":34, "nominal_credits":102, "nominal_credits_per_page":3, "usage_note":"Nominal only; provider-returned credits may differ or be absent", "interface_differences":DIFFERENCES, "config_template":config("<verified-file-id>","cost_effective","<durable-intent-token>","<input-sha256>"), "output_lane":"round2/llama-cost-effective/execution"}


class TransportFailure(Exception):
    def __init__(self, status=None):
        self.status = status
        super().__init__("API request did not return usable success; details retained safely")


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class API:
    def __init__(self, key, project, out):
        self.key, self.project, self.out = key, project, out
        self.opener = urllib.request.build_opener(NoRedirect())
        self.download_opener = urllib.request.build_opener(NoRedirect())
        prefixes = [int(p.name.split(".", 1)[0]) for p in (out / "http").glob("*.json") if p.name.split(".", 1)[0].isdigit()]
        self.sequence = max(prefixes, default=0)

    def request(self, method, path, data=None, query=None, content_type="application/json"):
        q = {"project_id": self.project, **(query or {})}
        url = BASE + path + "?" + urllib.parse.urlencode(q, doseq=True)
        headers = {"Authorization": "Bearer " + self.key}
        if data is not None: headers["Content-Type"] = content_type
        start, tick = now(), time.monotonic(); status = None; raw = b""
        try:
            with self.opener.open(urllib.request.Request(url, data, headers, method=method), timeout=45) as response:
                status, raw = response.status, response.read()
        except urllib.error.HTTPError as error:
            status, raw = error.code, error.read()
        except Exception:
            self.record(method, path, start, tick, None, {"error_class": "TransportFailure"}, False)
            raise TransportFailure() from None
        try: value = json.loads(raw)
        except (ValueError, UnicodeError): value = {"non_json_body": raw.decode("utf-8", errors="replace")}
        safe = safe_value(value, self.key)
        self.record(method, path, start, tick, status, safe, safe == value, raw)
        if status is None or not 200 <= status < 300: raise TransportFailure(status)
        return value

    def record(self, method, path, start, tick, status, value, unmodified, raw=None):
        self.sequence += 1
        receipt = self.out / "http" / f"{self.sequence:05}.json"
        response = self.out / "http" / f"{self.sequence:05}.response.json"
        receipt.parent.mkdir(parents=True, exist_ok=True)
        if raw is not None:
            response.write_bytes(raw if unmodified else (json.dumps(value, indent=2) + "\n").encode())
        self.last_capture = str(receipt.relative_to(self.out))
        atomic_json(receipt, {"method": method, "path": path, "actual_dispatch_at_utc": start, "received_at_utc": now(), "http_wall_ms": round((time.monotonic() - tick) * 1000), "http_status": status, "response": value, "raw_response_path": str(response.relative_to(self.out)) if raw is not None else None, "raw_response_bytes_unmodified": unmodified and raw is not None, "response_object_unmodified": unmodified, "redaction_exception": None if unmodified else "Key/transient URLs excluded; no Authorization header persisted"})

    def verify_file(self, file_id, expected_hash):
        metadata = self.request("GET", f"/api/v1/beta/files/{file_id}")
        require(metadata.get("project_id") == self.project, "File belongs to another project")
        signed = self.request("GET", f"/api/v1/beta/files/{file_id}/content")["url"]
        require(signed.startswith("https://") and not urllib.parse.urlparse(signed).username, "Unsafe content URL")
        # Deliberately no Authorization header on transient signed download.
        try:
            with self.download_opener.open(urllib.request.Request(signed), timeout=45) as response: remote_hash = sha(response.read())
        except Exception: raise TransportFailure() from None
        require(remote_hash == expected_hash, "Remote reusable file bytes differ from freeze")
        return {"file_id": file_id, "download_sha256": remote_hash, "checked_at_utc": now(), "project_id": self.project}


def multipart(raw, name):
    boundary = "----dc" + uuid.uuid4().hex
    body = (f'--{boundary}\r\nContent-Disposition: form-data; name="purpose"\r\n\r\nparse\r\n--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="{name}"\r\nContent-Type: application/pdf\r\n\r\n').encode() + raw + f"\r\n--{boundary}--\r\n".encode()
    return body, "multipart/form-data; boundary=" + boundary


def matching_jobs(items, job):
    return [item for item in items if item.get("tier") == job["tier"] and (item.get("user_metadata") or {}).get("intent_token") == job["intent_token"] and (item.get("user_metadata") or {}).get("input_sha256") == job["input_sha256"] and (item.get("user_metadata") or {}).get("benchmark_run") == RUN_TAG]


class Runner:
    def __init__(self, root, out, plan, api, project):
        self.root, self.out, self.api = root, out, api
        self.state_path = out / "state.json"
        if self.state_path.exists():
            self.state = json.loads(self.state_path.read_text())
            require(self.state["plan"] == plan and self.state["project_id"] == project, "Plan/project changed; refusing resume")
        else:
            self.state = {"plan": plan, "project_id": project, "jobs": [{**j, "phase": "pending", "intent_token": uuid.uuid4().hex} for j in plan["jobs"]], "files": {}, "consecutive_failures": 0, "stopped": False, "completion_order": []}
            self.save()

    def save(self): atomic_json(self.state_path, self.state)

    def reconcile(self, job):
        items, token = [], None
        for _ in range(100):
            require(time.monotonic() < self.deadline, "Invocation deadline reached during reconciliation; preserve uncertain intent")
            q = {"created_at_on_or_after": job["submit_started_at_utc"], "page_size": 100}
            if token: q["page_token"] = token
            response = self.api.request("GET", "/api/v2/parse", query=q)
            items.extend(response["items"]); token = response.get("next_page_token")
            if not token: break
        else: raise ValueError("Reconciliation pagination incomplete; no submit allowed")
        matches = matching_jobs(items, job)
        job["reconciliation"] = {"at_utc": now(), "matches": [m["id"] for m in matches], "no_blind_retry": True}
        if len(matches) != 1:
            job["phase"] = "submit_uncertain"; self.save()
            raise ValueError("Uncertain submission not uniquely reconciled; stop without another POST")
        job["job_id"] = matches[0]["id"]; job["phase"] = "accepted"; self.save()

    def file_for(self, job):
        fid = job["fixture_id"]
        record = self.state["files"].get(fid)
        if record:
            if record.get("phase") == "uploaded":
                proof = self.api.verify_file(record["file_id"], job["input_sha256"])
                record.update(proof, phase="verified"); self.save()
            require(record.get("phase") == "verified", "Uncertain upload; reconcile file before any new upload")
            return record["file_id"]
        candidate = job.get("candidate_file_id")
        if candidate:
            proof = self.api.verify_file(candidate, job["input_sha256"])
            self.state["files"][fid] = {"phase": "verified", **proof, "reused_dashboard_file": True}; self.save(); return candidate
        raw = (self.root / job["input_path"]).read_bytes()
        require(sha(raw) == job["input_sha256"] and len(raw) == job["input_bytes"], "Staged bytes changed before upload")
        self.state["files"][fid] = {"phase": "upload_inflight", "started_at_utc": now(), "input_sha256": job["input_sha256"]}; self.save()
        body, mime = multipart(raw, f"dc-expanded-{fid}.pdf")
        # No automatic repeat even if only this upload response is lost.
        uploaded = self.api.request("POST", "/api/v1/beta/files", body, content_type=mime)
        file_id = uploaded["id"]
        self.state["files"][fid].update(phase="uploaded", file_id=file_id); self.save()
        proof = self.api.verify_file(file_id, job["input_sha256"])
        self.state["files"][fid] = {"phase": "verified", **proof, "reused_dashboard_file": False}; self.save(); return file_id

    def submit(self, job):
        file_id = self.file_for(job)
        require(time.monotonic() < self.deadline, "Invocation budget ended before parse submission; verified file retained")
        job.update(file_id=file_id, phase="submit_inflight", submit_started_at_utc=now())
        job["request"] = config(file_id, job["tier"], job["intent_token"], job["input_sha256"]); self.save()
        try:
            result = self.api.request("POST", "/api/v2/parse", json.dumps(job["request"]).encode())
            require(isinstance(result.get("id"), str), "Submission response lacks durable job ID")
            job.update(job_id=result["id"], phase="accepted", accepted_at_utc=now()); self.save()
        except Exception:
            job["phase"] = "submit_uncertain"; self.save()
            # Even HTTP rejection is never blindly retried by this runner.
            raise ValueError("Submit acceptance uncertain/rejected; resume reconciliation required") from None

    def finish(self, job, result):
        status = result["job"]["status"]
        markdown = result.get("markdown_full")
        pages = (result.get("markdown") or {}).get("pages", [])
        anomalies = []
        if len(pages) != job["pages"]: anomalies.append("Expanded Markdown page count differs from frozen input")
        if any(p.get("success") is not True for p in pages): anomalies.append("Markdown page missing success evidence or explicitly failed")
        numbers = [p.get("page_number") for p in pages]
        if len(set(numbers)) != len(pages) or any(type(n) is not int for n in numbers): anomalies.append("Page identity evidence missing or duplicated")
        if set(numbers) not in [set(range(job["pages"])), set(range(1, job["pages"] + 1))]: anomalies.append("Page ordinals do not cover the frozen input scope")
        consistency = {}
        for field in ["file_id", "tier"]:
            actual = result["job"].get(field)
            consistency[field] = {"expected": job[field], "reported": actual, "available": actual is not None, "matches": actual == job[field] if actual is not None else None}
            if actual is not None and actual != job[field]: anomalies.append(f"Returned job {field} mismatch")
        version = result["job"].get("version")
        consistency["version"] = {"requested": "latest", "reported": version, "latest_alias_resolution_verified": version == "latest" if version is not None else None, "note": "A reported dated version is retained, not asserted to be the current latest mapping"}
        if version is not None and version != "latest" and not re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(version)): anomalies.append("Unrecognized reported version")
        success = status == "COMPLETED" and isinstance(markdown, str) and bool(markdown) and not anomalies
        # Preserve whole-document provider string; never reconstruct from items.
        clean = safe_value(result, self.api.key)
        if isinstance(markdown, str):
            require(safe_value(markdown, self.api.key) == markdown, "Markdown contains transient secret; no unsafe exact capture")
        directory = self.out / "runs" / job["fixture_id"] / job["tier"]
        directory.mkdir(parents=True, exist_ok=True)
        atomic_json(directory / "output.json", clean)
        outputs = []
        if isinstance(markdown, str):
            raw = markdown.encode(); path = directory / "output.md"
            if path.exists(): require(path.read_bytes() == raw, "Existing Markdown differs; refusing overwrite")
            else: path.write_bytes(raw)
            outputs.append({"path": str(path.relative_to(self.out)), "sha256": sha(raw), "bytes": len(raw), "exact_provider_markdown_full": True})
        json_path = directory / "output.json"
        outputs.append({"path": str(json_path.relative_to(self.out)), "sha256": sha(json_path.read_bytes()), "bytes": len(json_path.read_bytes()), "representation": "REST v2 expanded result, supplementary only"})
        capture = {"fixture_id": job["fixture_id"], "tier": job["tier"], "job_id": job["job_id"], "file_id": job["file_id"], "status": status, "operational_success": success, "started_at_utc": job["submit_started_at_utc"], "observed_at_utc": now(), "input_sha256": job["input_sha256"], "input_bytes": job["input_bytes"], "pages": job["pages"], "config": job["request"], "outputs": outputs, "returned_usage": result["job"].get("usage"), "job_metadata": clean.get("job_metadata"), "terminal_api_capture": getattr(self.api, "last_capture", None), "raw_api_response_object_unmodified": clean == result, "provenance_note": "Authenticated REST v2; JSON response sanitized only if transient URLs/key appeared. Markdown scored alone; interface differences in plan."}
        capture.update(operation_anomalies=anomalies, returned_job_consistency=consistency)
        atomic_json(directory / "capture.json", capture)
        job.update(phase="completed" if success else "failed", observed_at_utc=now(), capture=str((directory / 'capture.json').relative_to(self.out)))
        self.state["completion_order"].append([job["fixture_id"], job["tier"]])
        self.state["consecutive_failures"] = 0 if success else self.state["consecutive_failures"] + 1
        if self.state["consecutive_failures"] >= 3: self.state["stopped"] = True
        self.save()
        print(f"{job['fixture_id']} {job['tier']}: {job['phase']}", flush=True)

    def run(self, reconcile_only=False, max_jobs=20, max_run_seconds=1800):
        self.deadline = time.monotonic() + max_run_seconds
        submitted = 0
        for job in self.state["jobs"]:
            if job["phase"] in {"submit_inflight", "submit_uncertain"}: self.reconcile(job)
        while True:
            if time.monotonic() >= self.deadline:
                self.save()
                print(json.dumps({"invocation_budget_reached": True, "accepted_job_ids_preserved": [j.get("job_id") for j in self.state["jobs"] if j["phase"] == "accepted"]})); return
            active = [j for j in self.state["jobs"] if j["phase"] == "accepted"]
            require(len(active) <= 2, "More than two accepted jobs; reconcile externally")
            # Pair barrier: consume every existing job's terminal observation
            # before filling any slot. No stop-boundary race with a partial pair.
            if not active and not reconcile_only and not self.state["stopped"]:
                for job in self.state["jobs"]:
                    if len(active) >= 2 or submitted >= max_jobs or time.monotonic() >= self.deadline: break
                    if job["phase"] == "pending": self.submit(job); active.append(job); submitted += 1
            if not active: break
            # Poll all existing jobs even after stop; retain already-in-flight work.
            for job in active:
                if time.monotonic() >= self.deadline: break
                result = self.api.request("GET", "/api/v2/parse/" + job["job_id"], query={"expand": EXPAND})
                require(result["job"]["id"] == job["job_id"], "Returned job identity mismatch")
                if result["job"]["status"] in TERMINAL: self.finish(job, result)
            if reconcile_only: break
            time.sleep(3)
        print(json.dumps({"stopped": self.state["stopped"], "completed": sum(j["phase"] == "completed" for j in self.state["jobs"]), "failed": sum(j["phase"] == "failed" for j in self.state["jobs"]), "pending": sum(j["phase"] == "pending" for j in self.state["jobs"])}))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path, help="Benchmark artifact root")
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--reconcile-only", action="store_true")
    parser.add_argument("--attach-file", action="append", default=[], metavar="FIXTURE_ID=FILE_ID", help="Reconcile a known uploaded file by authenticated byte-hash verification; no upload retry")
    parser.add_argument("--max-jobs", "--max-new-jobs", dest="max_jobs", type=int, default=1, help="Max new submissions this invocation (default one-job pilot); does not change frozen plan")
    parser.add_argument("--max-run-seconds", type=int, default=1800, help="Finite local invocation budget; preserve active IDs at exit")
    parser.add_argument("--project-id")
    parser.add_argument("--ack-api-v2-differences", action="store_true")
    args = parser.parse_args(); root = args.root.resolve(); plan = local_plan(root)
    if not args.execute:
        # No secret/environment access, HTTP or execution-lane writes in dry-run.
        print(json.dumps(plan, indent=2)); return
    require(args.project_id and args.ack_api_v2_differences, "Execution requires explicit project and acknowledgement of recorded v2 differences")
    key = os.environ.get("LLAMA_CLOUD_API_KEY", "")
    require(key and not key.startswith("op://"), "Resolved key must be supplied by LLAMA_CLOUD_API_KEY; never pass it as an argument")
    out = LANE_DIR / "execution"; out.mkdir(exist_ok=True)
    require(not args.reconcile_only or (out / "state.json").exists(), "Read-only reconciliation requires an existing execution state")
    require(0 <= args.max_jobs <= 20 and args.max_run_seconds > 0, "Invalid invocation limits")
    with (out / "runner.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        api = API(key, args.project_id, out)
        runner = Runner(root, out, plan, api, args.project_id)
        for binding in args.attach_file:
            fid, file_id = binding.split("=", 1)
            candidates = [j for j in runner.state["jobs"] if j["fixture_id"] == fid]
            require(candidates and all(j["phase"] == "pending" for j in candidates), "File reconciliation only allowed before that fixture's parse submissions")
            proof = api.verify_file(file_id, candidates[0]["input_sha256"])
            runner.state["files"][fid] = {"phase": "verified", **proof, "explicit_file_reconciliation": True}; runner.save()
        runner.run(args.reconcile_only, args.max_jobs, args.max_run_seconds)


if __name__ == "__main__":
    try: main()
    except Exception as error:
        # Never print arbitrary network exception strings or tracebacks.
        print(json.dumps({"stopped_for_attention": True, "error_class": type(error).__name__, "reason": str(error) if isinstance(error, ValueError) else "Transport/local error; resume existing state, do not resubmit blindly"}))
        raise SystemExit(1)
