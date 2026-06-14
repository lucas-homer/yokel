#!/usr/bin/env python3
"""Render the DocketClock + Watershed Watch architecture foundry result as HTML."""
import json, html

R = json.load(open('docs/research/arch-foundry-result.json'))
DC = R['docketclock']['architecture']
DCP = R['docketclock']['proposals']
FIT = R['watershed']['fit']
WW = R['watershed']['architecture']
WWP = R['watershed']['proposals']


def e(x):
    return html.escape(str(x if x is not None else ''))


def li(items):
    return ''.join(f'<li>{e(x)}</li>' for x in (items or []))


def kv_rows(rows, cols):
    out = []
    for r in rows:
        tds = ''.join(f'<td>{e(r.get(c,""))}</td>' for c in cols)
        out.append(f'<tr>{tds}</tr>')
    return ''.join(out)


def cards(items, name_k, body_k, sub_k=None, accent='blue'):
    out = []
    for it in items:
        sub = f'<p class="cardsub">{e(it.get(sub_k))}</p>' if sub_k and it.get(sub_k) else ''
        out.append(
            f'<div class="card c-{accent}"><h4>{e(it.get(name_k))}</h4>'
            f'<p>{e(it.get(body_k))}</p>{sub}</div>'
        )
    return ''.join(out)


def steps(items, k1, k2):
    out = []
    for i, it in enumerate(items, 1):
        out.append(
            f'<div class="step"><span class="num">{i}</span>'
            f'<div><strong>{e(it.get(k1))}</strong><p>{e(it.get(k2))}</p></div></div>'
        )
    return ''.join(out)


def risk_rows(items):
    return ''.join(
        f'<tr><td class="risk">{e(r.get("risk"))}</td><td>{e(r.get("mitigation"))}</td></tr>'
        for r in items
    )

# ---- Codex ledger ----
ledger = DC['codex_ledger']
kept_html = ''.join(f'<li><b>{e(x["item"])}</b> — {e(x["why"])}</li>' for x in ledger['kept'])
changed_html = ''.join(
    f'<li><b>{e(x["item"])}</b><div class="fromto"><span class="from">{e(x.get("from","—"))}</span>'
    f'<span class="arrow">→</span><span class="to">{e(x["to"])}</span></div><em>{e(x["why"])}</em></li>'
    for x in ledger['changed']
)
rej_html = ''.join(f'<li><b>{e(x["item"])}</b> — {e(x["why"])}</li>' for x in ledger['rejected'])

# ---- proposal score chips ----
def score_chips(props):
    out = []
    for p in props:
        s = p['critique']['score']
        cls = 'hi' if s >= 7 else ('mid' if s >= 6 else 'lo')
        out.append(f'<span class="chip {cls}"><b>{e(p["stance"])}</b> {s}/10</span>')
    return ''.join(out)

# ---- DocketClock sections ----
dc_canon = DC['canonical_object']
canon_rows = ''.join(
    f'<tr><td class="mono">{e(f["field"])}</td><td>{e(f["desc"])}</td></tr>'
    for f in dc_canon['key_fields']
)
conf = DC['confidence_model']
conf_rows = ''.join(
    f'<tr><td><span class="state s-{e(s["state"]).lower()}">{e(s["state"])}</span></td>'
    f'<td>{e(s["meaning"])}</td><td>{e(s["alert_behavior"])}</td></tr>'
    for s in conf['states']
)
dc_pipeline = steps(DC['pipeline'], 'stage', 'what')
dc_components = cards(DC['components'], 'name', 'responsibility', 'tech', 'blue')
dc_sources = kv_rows(DC['data_sources'], ['source', 'role', 'gotchas'])
dc_delivery = ''.join(f'<div class="pill-card"><b>{e(d["surface"])}</b><p>{e(d["detail"])}</p></div>' for d in DC['delivery_surfaces'])
dc_stack = kv_rows(DC['tech_stack'], ['layer', 'choice', 'why'])
dc_build = steps(DC['build_sequence'], 'milestone', 'deliverable')
dc_risks = risk_rows(DC['top_risks'])
dc_mvp = DC['mvp_boundary']
dc_diverge = li(DC.get('divergences_from_prior_dossier'))
dc_oq = li(DC.get('open_questions'))

# ---- Watershed sections ----
boundary = FIT['layer_boundary']
ww_components = cards(WW['components'], 'name', 'responsibility', 'tech', 'green')
ww_geo = WW['geo_scoping']
ww_sources = kv_rows(WW['data_sources'], ['source', 'role', 'gotchas'])
ww_action = steps(WW['action_loop'], 'step', 'what')
ww_tiers = ''.join(
    f'<div class="tier t{i}"><b>{e(t["tier"])}</b><p>{e(t["what"])}</p>'
    f'<span class="label">{e(t.get("labeling",""))}</span></div>'
    for i, t in enumerate(WW['coverage_tiers'], 1)
)
ww_stack = kv_rows(WW['tech_stack'], ['layer', 'choice', 'why'])
ww_build = steps(WW['build_sequence'], 'milestone', 'deliverable')
ww_risks = risk_rows(WW['top_risks'])
ww_mvp = WW['mvp_boundary']
ww_oq = li(WW.get('open_questions'))

fit_verdict_cls = {'yes-fully': 'hi', 'yes-partially': 'mid', 'no': 'lo'}[FIT['builds_on_docketclock']]

HTML = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>DocketClock + Watershed Watch — Architecture</title>
<style>
:root{{--bg:#f3f1ea;--ink:#15201c;--muted:#5d6b63;--panel:#fffdf8;--line:#ddd5c5;
--blue:#255f7d;--green:#145b43;--amber:#a3641a;--red:#9a3f33;--mint:#e2efe7;--sky:#dfecf3;
--shadow:0 18px 50px rgba(30,40,25,.10);}}
*{{box-sizing:border-box}}
body{{margin:0;background:radial-gradient(circle at 10% 0,rgba(37,95,125,.12),transparent 32rem),
radial-gradient(circle at 92% 3%,rgba(20,91,67,.12),transparent 30rem),var(--bg);
color:var(--ink);font-family:Georgia,Cambria,"Times New Roman",serif;line-height:1.55}}
.wrap{{max-width:1180px;margin:0 auto;padding:0 24px}}
header{{padding:60px 0 30px;border-bottom:1px solid var(--line)}}
.eyebrow{{font:800 12px/1.2 ui-monospace,Menlo,monospace;letter-spacing:.14em;text-transform:uppercase;color:var(--blue);margin-bottom:16px}}
h1{{font-size:clamp(40px,6vw,72px);line-height:.96;letter-spacing:-.04em;margin:0 0 16px;max-width:960px}}
.sub{{font-size:clamp(18px,2vw,23px);max-width:880px;color:#33433d;margin:0}}
.section-label{{font:800 12px/1 ui-monospace,Menlo,monospace;letter-spacing:.12em;text-transform:uppercase;
color:var(--green);margin:54px 0 6px}}
h2{{font-size:clamp(28px,3.4vw,46px);line-height:1;letter-spacing:-.03em;margin:4px 0 10px}}
h3{{font-size:24px;letter-spacing:-.02em;margin:34px 0 12px}}
h4{{font-size:17px;margin:0 0 6px;letter-spacing:-.01em}}
.lede{{font-size:18px;color:#33433d;max-width:900px}}
.mono{{font-family:ui-monospace,Menlo,Consolas,monospace;font-size:13px}}
.panel{{background:var(--panel);border:1px solid var(--line);border-radius:20px;padding:22px 24px;box-shadow:var(--shadow);margin:16px 0}}
.thesis{{border-left:5px solid var(--blue)}}
.thesis.g{{border-left-color:var(--green)}}
table{{width:100%;border-collapse:collapse;margin:10px 0 4px;font-size:14.5px}}
th,td{{border-bottom:1px solid var(--line);padding:9px 10px;text-align:left;vertical-align:top}}
th{{font:800 10.5px/1.2 ui-monospace,Menlo,monospace;text-transform:uppercase;letter-spacing:.07em;color:var(--muted)}}
td.mono{{font-family:ui-monospace,Menlo,monospace;font-size:12.5px;color:var(--blue);white-space:nowrap}}
td.risk{{font-weight:700;color:var(--ink);width:42%}}
.grid{{display:grid;grid-template-columns:repeat(2,1fr);gap:14px;margin:14px 0}}
.grid3{{display:grid;grid-template-columns:repeat(3,1fr);gap:14px;margin:14px 0}}
.card{{background:var(--panel);border:1px solid var(--line);border-radius:16px;padding:16px 17px;box-shadow:0 10px 28px rgba(30,40,25,.06)}}
.card p{{margin:0;color:#33433d;font-size:14.5px}}
.card .cardsub{{margin-top:8px;font-family:ui-monospace,Menlo,monospace;font-size:11.5px;color:var(--muted)}}
.c-blue{{border-top:3px solid var(--blue)}} .c-green{{border-top:3px solid var(--green)}}
.step{{display:flex;gap:14px;align-items:flex-start;padding:13px 0;border-bottom:1px solid var(--line)}}
.step .num{{flex:none;width:30px;height:30px;border-radius:50%;background:var(--mint);color:var(--green);
font:800 14px/30px ui-monospace,Menlo,monospace;text-align:center}}
.step strong{{display:block;font-size:15.5px}} .step p{{margin:3px 0 0;color:#46544d;font-size:14px}}
.pill-card{{background:var(--sky);border:1px solid #cfe0ea;border-radius:14px;padding:13px 15px;margin-bottom:10px}}
.pill-card b{{color:var(--blue)}} .pill-card p{{margin:5px 0 0;font-size:14px;color:#33433d}}
.state{{font:800 11px/1 ui-monospace,Menlo,monospace;padding:5px 8px;border-radius:6px;display:inline-block}}
.s-high{{background:#dff0e5;color:var(--green)}} .s-medium{{background:#fdf0d6;color:var(--amber)}}
.s-low{{background:#fbe7d8;color:var(--amber)}} .s-conflicting{{background:#f7dcd6;color:var(--red)}}
.s-stale{{background:#e8e4da;color:var(--muted)}} .s-unknown{{background:#e8e4da;color:var(--muted)}}
.ledger{{display:grid;grid-template-columns:repeat(3,1fr);gap:14px;margin:16px 0}}
.ledger>div{{border-radius:16px;padding:16px 18px;border:1px solid var(--line)}}
.ledger .kept{{background:#dff0e5}} .ledger .changed{{background:#fdf0d6}} .ledger .rejected{{background:#f7dcd6}}
.ledger h4{{font:800 12px/1 ui-monospace,Menlo,monospace;letter-spacing:.08em;text-transform:uppercase;margin-bottom:10px}}
.ledger .kept h4{{color:var(--green)}} .ledger .changed h4{{color:var(--amber)}} .ledger .rejected h4{{color:var(--red)}}
.ledger ul{{margin:0;padding-left:18px}} .ledger li{{margin-bottom:11px;font-size:13.5px;color:#2c3a33}}
.fromto{{display:flex;gap:7px;align-items:center;margin:4px 0;flex-wrap:wrap;font-family:ui-monospace,Menlo,monospace;font-size:11.5px}}
.fromto .from{{color:var(--muted);text-decoration:line-through}} .fromto .to{{color:var(--green);font-weight:700}}
.fromto .arrow{{color:var(--ink)}}
.ledger li em{{display:block;margin-top:3px;color:var(--muted);font-style:italic;font-size:12.5px}}
.chips{{display:flex;gap:8px;flex-wrap:wrap;margin:12px 0}}
.chip{{font:700 12px/1 ui-monospace,Menlo,monospace;padding:7px 11px;border-radius:999px;border:1px solid var(--line)}}
.chip.hi{{background:#dff0e5;color:var(--green)}} .chip.mid{{background:#fdf0d6;color:var(--amber)}} .chip.lo{{background:#f7dcd6;color:var(--red)}}
.chip b{{font-weight:800}}
.verdict{{display:inline-block;font:800 13px/1 ui-monospace,Menlo,monospace;padding:8px 13px;border-radius:999px;letter-spacing:.04em}}
.verdict.hi{{background:#dff0e5;color:var(--green)}} .verdict.mid{{background:#fdf0d6;color:var(--amber)}} .verdict.lo{{background:#f7dcd6;color:var(--red)}}
.two{{display:grid;grid-template-columns:1fr 1fr;gap:16px;margin:16px 0}}
.two .box{{background:var(--panel);border:1px solid var(--line);border-radius:16px;padding:18px 20px;box-shadow:var(--shadow)}}
.two .box.dc{{border-top:4px solid var(--blue)}} .two .box.ww{{border-top:4px solid var(--green)}}
.two .box h4{{font:800 12px/1 ui-monospace,Menlo,monospace;letter-spacing:.07em;text-transform:uppercase;margin-bottom:10px}}
.two .box.dc h4{{color:var(--blue)}} .two .box.ww h4{{color:var(--green)}}
.two ul{{margin:0;padding-left:18px}} .two li{{margin-bottom:8px;font-size:13.5px;color:#2c3a33}}
.tier{{border-radius:14px;padding:15px 17px;margin-bottom:11px;border:1px solid var(--line)}}
.tier.t1{{background:#dff0e5}} .tier.t2{{background:#fdf0d6}} .tier.t3{{background:#e8e4da}}
.tier b{{font-size:15px}} .tier p{{margin:5px 0 6px;font-size:14px;color:#33433d}}
.tier .label{{font-family:ui-monospace,Menlo,monospace;font-size:11.5px;color:var(--muted)}}
.mvpbox{{display:grid;grid-template-columns:1fr 1fr;gap:16px;margin:14px 0}}
.mvpbox .in{{background:#dff0e5;border-radius:16px;padding:16px 20px}}
.mvpbox .out{{background:#f1ede3;border-radius:16px;padding:16px 20px}}
.mvpbox h4{{font:800 12px/1 ui-monospace,Menlo,monospace;letter-spacing:.07em;text-transform:uppercase;margin-bottom:8px}}
.mvpbox .in h4{{color:var(--green)}} .mvpbox .out h4{{color:var(--muted)}}
.mvpbox ul{{margin:0;padding-left:18px}} .mvpbox li{{font-size:13px;margin-bottom:7px;color:#2c3a33}}
.first{{margin-top:12px;font-size:14px;background:var(--sky);border-radius:12px;padding:13px 16px}}
.first b{{color:var(--blue)}}
ul.tight li{{margin-bottom:7px;font-size:14.5px;color:#2c3a33}}
footer{{border-top:1px solid var(--line);margin-top:60px;padding:24px 0 50px;color:var(--muted);font-size:13px}}
@media(max-width:860px){{.grid,.grid3,.ledger,.two,.mvpbox{{grid-template-columns:1fr}}}}
</style></head>
<body>
<header><div class="wrap">
<div class="eyebrow">Yokel · architecture foundry · 13 agents · 3 competing architects → adversarial critique → Opus synthesis</div>
<h1>DocketClock, then Watershed Watch on top of it.</h1>
<p class="sub">Two architectures designed by a multi-agent team: the federal comment-deadline <b>substrate</b>, reconciled against Codex's plan with an explicit kept/changed/rejected ledger — and the basin-scoped environmental wedge that rents it.</p>
</div></header>
<main class="wrap">

<div class="section-label">Part A · the substrate</div>
<h2>{e(DC['title'])}</h2>
<p class="lede">{e(DC['one_liner'])}</p>
<div class="chips">{score_chips(DCP)} <span class="chip" style="background:#fff;color:#555">stances proposed → critiqued → synthesized</span></div>

<div class="panel thesis"><h4>Architecture thesis</h4><p>{e(DC['architecture_thesis'])}</p></div>

<h3>How much of Codex's plan we kept</h3>
<p class="lede">You asked us to use judgment on how much of Codex's architecture to incorporate. Here is the full ledger.</p>
<div class="ledger">
<div class="kept"><h4>✓ Kept ({len(ledger['kept'])})</h4><ul>{kept_html}</ul></div>
<div class="changed"><h4>~ Changed ({len(ledger['changed'])})</h4><ul>{changed_html}</ul></div>
<div class="rejected"><h4>✕ Rejected ({len(ledger['rejected'])})</h4><ul>{rej_html}</ul></div>
</div>

<h3>Canonical object — {e(dc_canon['name'])}</h3>
<p class="lede">{e(dc_canon['design_notes'])}</p>
<div class="panel"><table><thead><tr><th>Field</th><th>Meaning</th></tr></thead><tbody>{canon_rows}</tbody></table></div>

<h3>Pipeline</h3>
<div class="panel">{dc_pipeline}</div>

<h3>Components</h3>
<div class="grid">{dc_components}</div>

<h3>Confidence model</h3>
<p class="lede">{e(conf['how_computed'])}</p>
<div class="panel"><table><thead><tr><th>State</th><th>Meaning</th><th>Alert behavior</th></tr></thead><tbody>{conf_rows}</tbody></table></div>

<h3>Data sources</h3>
<div class="panel"><table><thead><tr><th>Source</th><th>Role</th><th>Gotchas</th></tr></thead><tbody>{dc_sources}</tbody></table></div>

<h3>Delivery surfaces</h3>
<div class="grid">{dc_delivery}</div>

<h3>MVP boundary</h3>
<div class="mvpbox">
<div class="in"><h4>In scope (v1)</h4><ul>{li(dc_mvp['in_scope'])}</ul></div>
<div class="out"><h4>Deferred</h4><ul>{li(dc_mvp['deferred'])}</ul></div>
</div>
<div class="first"><b>First customer:</b> {e(dc_mvp['first_customer'])}</div>

<h3>Tech stack</h3>
<div class="panel"><table><thead><tr><th>Layer</th><th>Choice</th><th>Why</th></tr></thead><tbody>{dc_stack}</tbody></table></div>

<h3>Build sequence (12 weeks)</h3>
<div class="panel">{dc_build}</div>

<h3>Top risks</h3>
<div class="panel"><table><thead><tr><th>Risk</th><th>Mitigation</th></tr></thead><tbody>{dc_risks}</tbody></table></div>

<h3>Divergences from our earlier dossier</h3>
<div class="panel"><ul class="tight">{dc_diverge}</ul></div>

<h3>Open questions (must answer Week 1)</h3>
<div class="panel"><ul class="tight">{dc_oq}</ul></div>

<div class="section-label">Part B · the wedge</div>
<h2>Watershed Watch — is it the land-use wedge on top of DocketClock?</h2>

<div class="grid">
<div class="card c-green"><h4>Builds on DocketClock?</h4>
<p><span class="verdict {fit_verdict_cls}">{e(FIT['builds_on_docketclock']).upper()}</span></p>
<p style="margin-top:10px">{e(FIT['rationale'])}</p></div>
<div class="card c-green"><h4>A genuine vertical wedge — or just a Waterkeeper skin?</h4>
<p><span class="verdict {'hi' if FIT['is_land_use_wedge'] else 'lo'}">{'YES — A REAL WEDGE' if FIT['is_land_use_wedge'] else 'NO'}</span></p>
<p style="margin-top:10px">{e(FIT['wedge_reasoning'])}</p></div>
</div>

<h3>The layer boundary</h3>
<div class="two">
<div class="box dc"><h4>DocketClock provides (rented)</h4><ul>{li(boundary['docketclock_provides'])}</ul></div>
<div class="box ww"><h4>Watershed Watch owns (the anti-skin IP)</h4><ul>{li(boundary['watershed_adds'])}</ul></div>
</div>

<h3>What the wedge forces the substrate to expose</h3>
<div class="panel"><ul class="tight">{li(FIT['requirements_on_docketclock'])}</ul></div>

<div class="panel" style="border-left:5px solid var(--amber)"><h4>When to build it standalone instead</h4><p>{e(FIT['counterfactual_if_standalone'])}</p></div>

<h2 style="margin-top:48px">{e(WW['title'])}</h2>
<p class="lede">{e(WW['one_liner'])}</p>
<div class="chips">{score_chips(WWP)}</div>

<div class="panel thesis g"><h4>Architecture thesis</h4><p>{e(WW['architecture_thesis'])}</p></div>

<div class="panel"><h4>Relationship to DocketClock</h4><p>{e(WW['relationship_to_docketclock'])}</p></div>

<h3>Components</h3>
<div class="grid">{ww_components}</div>

<h3>Geo-scoping — {e(ww_geo['primitive'])}</h3>
<div class="panel"><p>{e(ww_geo['how'])}</p><p style="margin-top:10px;color:var(--muted)"><b>Gotchas:</b> {e(ww_geo.get('gotchas',''))}</p></div>

<h3>Data sources</h3>
<div class="panel"><table><thead><tr><th>Source</th><th>Role</th><th>Gotchas</th></tr></thead><tbody>{ww_sources}</tbody></table></div>

<h3>The monitor → act → see-impact loop</h3>
<div class="panel">{ww_action}</div>

<h3>Coverage tiers (the load-bearing honesty device)</h3>
{ww_tiers}

<h3>MVP boundary</h3>
<div class="mvpbox">
<div class="in"><h4>In scope (v1)</h4><ul>{li(ww_mvp['in_scope'])}</ul></div>
<div class="out"><h4>Deferred</h4><ul>{li(ww_mvp['deferred'])}</ul></div>
</div>
<div class="first"><b>First design partner:</b> {e(ww_mvp['first_partner'])}</div>

<h3>Tech stack</h3>
<div class="panel"><table><thead><tr><th>Layer</th><th>Choice</th><th>Why</th></tr></thead><tbody>{ww_stack}</tbody></table></div>

<h3>Build sequence (12 weeks)</h3>
<div class="panel">{ww_build}</div>

<h3>Top risks</h3>
<div class="panel"><table><thead><tr><th>Risk</th><th>Mitigation</th></tr></thead><tbody>{ww_risks}</tbody></table></div>

<h3>Open questions (must answer Week 1)</h3>
<div class="panel"><ul class="tight">{ww_oq}</ul></div>

</main>
<footer><div class="wrap">Generated from arch-foundry-result.json — 13 agents, 3 DocketClock architects + 2 Watershed architects, each adversarially critiqued, synthesized by an Opus lead-architect. Scores are single-critic soundness ratings, not an ensemble.</div></footer>
</body></html>"""

open('docs/research/docketclock-watershed-architecture.html', 'w').write(HTML)
print('wrote docketclock-watershed-architecture.html', len(HTML), 'bytes')
