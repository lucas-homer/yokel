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

# Datasource uids that provisioned dashboards / alert queries are allowed to reference. `__expr__` is
# Grafana's built-in server-side expression datasource (threshold/math nodes in alert rules).
PROVISIONED_DS_UIDS = {"prometheus", "loki", "__expr__"}

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
    source = (app.get("spec") or {}).get("source") or {}
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


def collect_prometheus_exprs(values: dict) -> list[str]:
    """Every Prometheus-datasource expr in the Grafana values (dashboard targets + alert queries)."""
    exprs: list[str] = []
    # Dashboard panel targets — all use the prometheus datasource.
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
                    if tgt.get("expr"):
                        exprs.append(tgt["expr"])
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
            for panel in d.get("panels", []):
                ds = panel.get("datasource")
                if isinstance(ds, dict) and ds.get("uid") and ds["uid"] not in provisioned:
                    err(f"grafana dashboard {provider}/{dname}: panel {panel.get('title')!r} "
                        f"references unprovisioned datasource uid {ds['uid']!r}")

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
                    refids = {d.get("refId") for d in rule.get("data", [])}
                    if rule.get("condition") not in refids:
                        err(f"grafana alert {rid!r}: condition {rule.get('condition')!r} "
                            f"is not a refId in data {sorted(refids)}")
                    for datum in rule.get("data", []):
                        uid = datum.get("datasourceUid")
                        if uid and uid not in provisioned:
                            err(f"grafana alert {rid!r}: query {datum.get('refId')!r} "
                                f"references unprovisioned datasource uid {uid!r}")
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


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--emit-promql", type=pathlib.Path, default=None,
                    help="write a synthetic promtool rules file of all Prometheus exprs to this path")
    ap.add_argument("--emit-values", type=pathlib.Path, default=None,
                    help="dump each app's inlined helm values into this dir (for `helm template`)")
    args = ap.parse_args()

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
