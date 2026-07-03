#!/usr/bin/env python3
"""
validate-argocd-apps.py — a no-cluster static guard over the ArgoCD Application manifests in
infra/argocd/apps/, run in CI (.github/workflows/infra-config.yml) BEFORE anything reaches the cluster.

Argo syncs these straight from git, so a malformed inlined Helm `values` block (a bad indent, a broken
dashboard JSON string, an alert rule whose `condition` points at a non-existent refId) is only caught
when Argo tries to sync it — i.e. live, after merge. This script moves that failure left:

  1. Every apps/*.yaml parses as a Kubernetes Application with a source.
  2. Every inlined `spec.source.helm.values` parses as YAML.
  3. Grafana (the big one, ~1700 lines of inlined dashboards + alerting):
       - each provisioned dashboard is valid JSON with a uid + at least one panel;
       - every panel target and alert-rule query references a datasource uid that is actually
         provisioned (prometheus / loki / __expr__);
       - each alert rule's `condition` is a refId present in its `data`, and every non-__expr__ query
         carries a real datasourceUid.
  4. With --emit-promql <path>, write a synthetic PROMETHEUS rules file of every Prometheus-datasource
     expr (dashboards + alerts) so the workflow can `promtool check rules` it — an offline PromQL
     SYNTAX check (Grafana's own alerting format is NOT promtool-checkable, hence the wrapping).

Pure stdlib + PyYAML. Exits non-zero (with a listed reason) on the first class of failure found.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys

import yaml

REPO = pathlib.Path(__file__).resolve().parents[2]
APPS_DIR = REPO / "infra" / "argocd" / "apps"

errors: list[str] = []


def err(msg: str) -> None:
    errors.append(msg)


def load_apps() -> list[tuple[pathlib.Path, dict]]:
    out: list[tuple[pathlib.Path, dict]] = []
    for path in sorted(APPS_DIR.glob("*.yaml")):
        try:
            docs = [d for d in yaml.safe_load_all(path.read_text()) if d]
        except yaml.YAMLError as e:
            err(f"{path.name}: not valid YAML — {e}")
            continue
        for doc in docs:
            out.append((path, doc))
    return out


def inlined_values(app: dict) -> dict | None:
    """Parse spec.source.helm.values (a YAML string) into a dict, or None if the app has none."""
    spec = app.get("spec") or {}
    name = (app.get("metadata") or {}).get("name", "?")
    # Multi-source apps (spec.sources, a list) would have their inlined values silently skipped by the
    # singular read below. None exist today — fail LOUDLY if one is added so it isn't unvalidated by accident.
    if spec.get("sources"):
        err(f"{name}: uses spec.sources (multi-source) — inlined-values validation is not supported yet; "
            f"extend this script before adding a sources: app")
        return None
    source = spec.get("source") or {}
    raw = (source.get("helm") or {}).get("values")
    if raw is None:
        return None
    try:
        parsed = yaml.safe_load(raw)
    except yaml.YAMLError as e:
        err(f"{app.get('metadata', {}).get('name', '?')}: inlined helm values are not valid YAML — {e}")
        return None
    if not isinstance(parsed, dict):
        err(f"{app.get('metadata', {}).get('name', '?')}: inlined helm values did not parse to a mapping")
        return None
    return parsed


def check_app_shape(path: pathlib.Path, app: dict) -> None:
    name = (app.get("metadata") or {}).get("name")
    if app.get("kind") != "Application":
        err(f"{path.name}: kind is {app.get('kind')!r}, expected Application")
        return
    if not name:
        err(f"{path.name}: missing metadata.name")
    spec = app.get("spec") or {}
    if not (spec.get("source") or spec.get("sources")):
        err(f"{path.name}: spec has neither source nor sources")


def _ds_uid(obj: dict) -> str | None:
    """The datasource uid on a panel/target, or None (a bare string datasource has no uid to check)."""
    ds = obj.get("datasource") if isinstance(obj, dict) else None
    return ds.get("uid") if isinstance(ds, dict) else None


def _effective_ds_uid(target: dict, panel: dict) -> str | None:
    """A target's datasource wins; else it inherits the panel's."""
    return _ds_uid(target) or _ds_uid(panel)


def collect_prometheus_exprs(values: dict) -> list[str]:
    """Every PROMETHEUS-datasource expr in the Grafana values (dashboard targets + alert queries).

    Filters by the target's EFFECTIVE datasource so a future Loki/LogQL (or __expr__) target is never
    fed to the promtool PromQL check — which would fail on non-PromQL.
    """
    exprs: list[str] = []
    for provider in (values.get("dashboards") or {}).values():
        for dash in provider.values():
            raw = dash.get("json")
            if not raw:
                continue
            try:
                d = json.loads(raw)
            except json.JSONDecodeError:
                continue  # reported separately in check_grafana
            for panel in d.get("panels", []):
                for tgt in panel.get("targets", []):
                    expr = tgt.get("expr")
                    if expr and _effective_ds_uid(tgt, panel) == "prometheus":
                        exprs.append(expr)
    # Alert rule queries whose datasource is prometheus (skip __expr__ threshold/math models).
    for fname, block in (values.get("alerting") or {}).items():
        if not fname.startswith("rules"):
            continue
        for group in (block or {}).get("groups", []):
            for rule in group.get("rules", []):
                for datum in rule.get("data", []):
                    if datum.get("datasourceUid") == "prometheus":
                        expr = (datum.get("model") or {}).get("expr")
                        if expr:
                            exprs.append(expr)
    return exprs


def check_grafana(values: dict) -> None:
    # Datasource uids actually provisioned (so dashboards/alerts can only point at real ones).
    ds_block = (values.get("datasources") or {}).get("datasources.yaml") or {}
    provisioned = {ds.get("uid") for ds in ds_block.get("datasources", [])}
    provisioned |= {"__expr__"}  # always available

    # Dashboards.
    dashboards = values.get("dashboards") or {}
    if not dashboards:
        err("grafana: no dashboards provisioned (expected under `dashboards`)")
    for provider, dash_map in dashboards.items():
        for dname, dash in dash_map.items():
            raw = dash.get("json")
            if not raw:
                err(f"grafana dashboard {provider}/{dname}: no `json` key")
                continue
            try:
                d = json.loads(raw)
            except json.JSONDecodeError as e:
                err(f"grafana dashboard {provider}/{dname}: embedded JSON invalid — {e}")
                continue
            if not d.get("uid"):
                err(f"grafana dashboard {provider}/{dname}: JSON missing `uid`")
            panels = [p for p in d.get("panels", []) if p.get("type") != "row"]
            if not panels:
                err(f"grafana dashboard {provider}/{dname}: no (non-row) panels")
            # Validate datasource uids at BOTH the panel and per-target level (a target can override).
            for panel in d.get("panels", []):
                checkables = [(panel, "panel")] + [(t, "target") for t in panel.get("targets", [])]
                for obj, where in checkables:
                    uid = _ds_uid(obj)
                    if uid and uid not in provisioned:
                        err(f"grafana dashboard {provider}/{dname}: {where} in panel "
                            f"{panel.get('title')!r} references unprovisioned datasource uid {uid!r}")

    # Alerting: rules ↔ data refIds, datasource uids, contactpoint/policy receiver consistency.
    alerting = values.get("alerting") or {}
    receivers: set[str] = set()
    for fname, block in alerting.items():
        block = block or {}
        if fname.startswith("contactpoints"):
            for cp in block.get("contactPoints", []):
                receivers.add(cp.get("name"))
        if fname.startswith("rules"):
            for group in block.get("groups", []):
                for rule in group.get("rules", []):
                    rid = rule.get("uid") or rule.get("title")
                    # Collect refIds, flagging any query that lacks one (a None refId must NOT silently
                    # satisfy a missing condition below).
                    refids: set[str] = set()
                    for datum in rule.get("data", []):
                        rf = datum.get("refId")
                        if rf is None:
                            err(f"grafana alert {rid!r}: a query in `data` is missing refId")
                        else:
                            refids.add(rf)
                        uid = datum.get("datasourceUid")
                        if uid is None:
                            err(f"grafana alert {rid!r}: query {rf!r} is missing datasourceUid")
                        elif uid not in provisioned:
                            err(f"grafana alert {rid!r}: query {rf!r} "
                                f"references unprovisioned datasource uid {uid!r}")
                    cond = rule.get("condition")
                    if not cond:
                        err(f"grafana alert {rid!r}: missing `condition`")
                    elif cond not in refids:
                        err(f"grafana alert {rid!r}: condition {cond!r} "
                            f"is not a refId in data {sorted(refids)}")
    # Every policy receiver must be a provisioned contact point.
    for fname, block in alerting.items():
        if fname.startswith("policies"):
            for pol in (block or {}).get("policies", []):
                if pol.get("receiver") and pol["receiver"] not in receivers:
                    err(f"grafana policy: receiver {pol['receiver']!r} has no matching contact point "
                        f"{sorted(r for r in receivers if r)}")


def emit_promql_rules(exprs: list[str], path: pathlib.Path) -> None:
    """Wrap exprs as recording rules so `promtool check rules` parses each expr (offline syntax check)."""
    rules = [{"record": f"ci_syntax_check:r{i}", "expr": expr} for i, expr in enumerate(exprs)]
    doc = {"groups": [{"name": "ci-promql-syntax-check", "rules": rules}]}
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(doc, width=100000, sort_keys=False))
    print(f"  wrote {len(rules)} exprs to {path} for promtool")


def emit_values(name: str, values: dict, outdir: pathlib.Path) -> None:
    """Dump an app's inlined helm values so the workflow can `helm template` the chart against them."""
    outdir.mkdir(parents=True, exist_ok=True)
    (outdir / f"{name}.values.yaml").write_text(yaml.safe_dump(values, width=100000, sort_keys=False))


def _minimal_grafana_values() -> dict:
    """A minimal VALID Grafana values dict — the fixture the self-test mutates to prove each check bites."""
    dash = {"uid": "d", "panels": [{
        "type": "timeseries", "title": "p", "datasource": {"uid": "prometheus"},
        "targets": [{"refId": "A", "expr": "up", "datasource": {"uid": "prometheus"}}],
    }]}
    return {
        "datasources": {"datasources.yaml": {"datasources": [{"uid": "prometheus"}, {"uid": "loki"}]}},
        "dashboards": {"prov": {"d": {"json": json.dumps(dash)}}},
        "alerting": {
            "rules.yaml": {"groups": [{"rules": [{"uid": "r", "title": "R", "condition": "C", "data": [
                {"refId": "A", "datasourceUid": "prometheus", "model": {"expr": "up"}},
                {"refId": "C", "datasourceUid": "__expr__", "model": {}}]}]}]},
            "contactpoints.yaml": {"contactPoints": [{"name": "cp"}]},
            "policies.yaml": {"policies": [{"receiver": "cp"}]},
        },
    }


def _isolated(fn) -> list[str]:
    """Run a check with a clean global error list; return the errors it produced."""
    errors.clear()
    fn()
    produced = list(errors)
    errors.clear()
    return produced


def self_test() -> int:
    """Exercise the checks against known-bad fixtures so the guard's own logic can't silently rot.

    No pytest — this repo has no Python test convention; the workflow runs `--self-test` as a fast first
    step so the C1–C4 datasource/refId fixes stay enforced as the real Grafana values grow.
    """
    import copy
    fails: list[str] = []

    def case(label: str, produced: list[str], needle: str | None, want_error: bool = True) -> None:
        ok = (bool(produced) == want_error) and (needle is None or any(needle in e for e in produced))
        if not ok:
            fails.append(f"{label} — got {produced}")
        print(f"  [{'ok ' if ok else 'FAIL'}] {label}")

    def mutated(fn) -> dict:
        v = copy.deepcopy(_minimal_grafana_values())
        fn(v)
        return v

    def set_dash(v: dict, dash: dict) -> None:
        v["dashboards"]["prov"]["d"]["json"] = json.dumps(dash)

    base = _minimal_grafana_values()
    case("valid config → no errors", _isolated(lambda: check_grafana(copy.deepcopy(base))), None, want_error=False)
    case("broken dashboard JSON",
         _isolated(lambda: check_grafana(mutated(lambda v: v["dashboards"]["prov"]["d"].__setitem__("json", "{not json")))),
         "JSON invalid")
    case("dashboard with no panels",
         _isolated(lambda: check_grafana(mutated(lambda v: set_dash(v, {"uid": "d", "panels": []})))),
         "no (non-row) panels")
    case("panel-level unprovisioned datasource",
         _isolated(lambda: check_grafana(mutated(lambda v: set_dash(v, {"uid": "d", "panels": [
             {"type": "timeseries", "title": "p", "datasource": {"uid": "bogus"}, "targets": []}]})))),
         "unprovisioned datasource uid 'bogus'")
    case("target-level unprovisioned datasource",
         _isolated(lambda: check_grafana(mutated(lambda v: set_dash(v, {"uid": "d", "panels": [
             {"type": "timeseries", "title": "p", "targets": [
                 {"refId": "A", "expr": "up", "datasource": {"uid": "bogus"}}]}]})))),
         "unprovisioned datasource uid 'bogus'")
    case("alert condition not a refId",
         _isolated(lambda: check_grafana(mutated(lambda v: v["alerting"]["rules.yaml"]["groups"][0]["rules"][0].__setitem__("condition", "Z")))),
         "is not a refId")
    case("alert missing condition",
         _isolated(lambda: check_grafana(mutated(lambda v: v["alerting"]["rules.yaml"]["groups"][0]["rules"][0].__setitem__("condition", None)))),
         "missing `condition`")
    case("alert query missing refId",
         _isolated(lambda: check_grafana(mutated(lambda v: v["alerting"]["rules.yaml"]["groups"][0]["rules"][0]["data"][0].pop("refId")))),
         "missing refId")
    case("alert query missing datasourceUid",
         _isolated(lambda: check_grafana(mutated(lambda v: v["alerting"]["rules.yaml"]["groups"][0]["rules"][0]["data"][0].pop("datasourceUid")))),
         "missing datasourceUid")
    case("policy receiver with no contact point",
         _isolated(lambda: check_grafana(mutated(lambda v: v["alerting"]["policies.yaml"]["policies"][0].__setitem__("receiver", "ghost")))),
         "no matching contact point")
    case("multi-source app fails loudly",
         _isolated(lambda: inlined_values({"metadata": {"name": "x"}, "spec": {"sources": [{"chart": "c"}]}})),
         "multi-source")

    # collect_prometheus_exprs must EXCLUDE non-prometheus targets (so promtool never sees LogQL).
    mixed = {"uid": "d", "panels": [{"type": "timeseries", "title": "p", "targets": [
        {"refId": "A", "expr": "up", "datasource": {"uid": "prometheus"}},
        {"refId": "B", "expr": '{job="x"}', "datasource": {"uid": "loki"}}]}]}
    exprs = collect_prometheus_exprs({"dashboards": {"prov": {"d": {"json": json.dumps(mixed)}}}})
    case("collect_prometheus_exprs excludes loki targets", ["ok"] if exprs == ["up"] else [], "ok")

    print(f"\n{'✓ self-test passed' if not fails else f'✗ {len(fails)} self-test case(s) FAILED'}")
    return 1 if fails else 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--self-test", action="store_true",
                    help="run the validator's own negative-case checks and exit (no cluster, no repo scan)")
    ap.add_argument("--emit-promql", type=pathlib.Path, default=None,
                    help="write a synthetic promtool rules file of all Prometheus exprs to this path")
    ap.add_argument("--emit-values", type=pathlib.Path, default=None,
                    help="dump each app's inlined helm values into this dir (for `helm template`)")
    args = ap.parse_args()

    if args.self_test:
        return self_test()

    apps = load_apps()
    if not apps:
        err(f"no Application manifests found under {APPS_DIR}")

    all_exprs: list[str] = []
    values_index: dict[str, dict] = {}
    for path, app in apps:
        check_app_shape(path, app)
        values = inlined_values(app)
        if values is None:
            continue
        name = (app.get("metadata") or {}).get("name")
        if name == "grafana":
            check_grafana(values)
            all_exprs.extend(collect_prometheus_exprs(values))
        if args.emit_values is not None and not errors and name:
            emit_values(name, values, args.emit_values)
            src = (app.get("spec") or {}).get("source") or {}
            # Only Helm-chart sources (repoURL + chart) can be `helm template`-d; skip git-manifest apps.
            if src.get("chart") and src.get("repoURL"):
                values_index[name] = {
                    "repoURL": src["repoURL"], "chart": src["chart"],
                    "targetRevision": src.get("targetRevision", ""),
                    "valuesFile": f"{name}.values.yaml",
                }

    if args.emit_values is not None and not errors:
        (args.emit_values / "_index.json").write_text(json.dumps(values_index, indent=2))

    print(f"validated {len({p.name for p, _ in apps})} app manifest(s); "
          f"collected {len(all_exprs)} Prometheus expression(s)")

    if args.emit_promql is not None and not errors:
        emit_promql_rules(all_exprs, args.emit_promql)

    if errors:
        print(f"\n✗ {len(errors)} problem(s):", file=sys.stderr)
        for e in errors:
            print(f"  - {e}", file=sys.stderr)
        return 1
    print("✓ all checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
