#!/usr/bin/env python3
import json, html

R = json.load(open('docs/research/foundry-result.json'))
winners = R['winners']
board = R['scoreboard']
JUDGE_NAMES = ['Pragmatic engineer', 'Skeptical VC', 'Civic-impact expert']
AXES = [('gap_fit','Gap fit'), ('feasibility','Feasibility'), ('demand','Demand'),
        ('defensibility','Defensibility'), ('mission_fit','Mission fit')]

def e(s): return html.escape(str(s if s is not None else ''))

def short(title): return title.split('—')[0].split(' - ')[0].strip()

CSS = """
:root{--ink:#1a1a2e;--muted:#5a6270;--line:#e3e6ec;--bg:#fbfcfe;--card:#fff;
--accent:#2c5f8a;--accent-soft:#eaf2f9;--green:#1f7a4d;--green-soft:#e7f4ec;
--amber:#9a6700;--amber-soft:#fdf3e0;--red:#a4343a;--red-soft:#fbeceb;--purple:#5b3fa0;--purple-soft:#efeafa;}
*{box-sizing:border-box;}
body{margin:0;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;
color:var(--ink);background:var(--bg);line-height:1.6;font-size:16px;}
.wrap{max-width:1000px;margin:0 auto;padding:0 24px 90px;}
header.hero{background:linear-gradient(135deg,#1a3a5c 0%,#2c5f8a 100%);color:#fff;padding:56px 24px 44px;margin-bottom:0;}
header.hero .wrap{padding-bottom:0;}
.eyebrow{text-transform:uppercase;letter-spacing:.12em;font-size:12px;font-weight:600;opacity:.8;margin:0 0 10px;}
header.hero h1{font-size:34px;line-height:1.2;margin:0 0 14px;font-weight:700;}
header.hero p{font-size:17px;opacity:.92;max-width:760px;margin:0;}
/* funnel */
.funnel{display:flex;gap:0;flex-wrap:wrap;background:#163250;color:#fff;}
.funnel .step{flex:1;min-width:140px;padding:18px 22px;border-right:1px solid rgba(255,255,255,.12);}
.funnel .step:last-child{border-right:none;}
.funnel .n{font-size:30px;font-weight:800;line-height:1;}
.funnel .lbl{font-size:12px;text-transform:uppercase;letter-spacing:.06em;opacity:.8;margin-top:6px;}
.funnel .step.final .n{color:#7fd1a3;}
.method{background:var(--accent-soft);border:1px solid #cfe0ef;border-left:4px solid var(--accent);
border-radius:10px;padding:18px 22px;margin:32px 0 36px;font-size:14.5px;}
.method b{color:var(--accent);}
h2.section{font-size:24px;margin:46px 0 6px;padding-bottom:10px;border-bottom:2px solid var(--line);}
.section-sub{color:var(--muted);margin:0 0 20px;font-size:15px;}
table{width:100%;border-collapse:collapse;margin:14px 0 26px;font-size:14.5px;background:var(--card);
border-radius:10px;overflow:hidden;box-shadow:0 1px 3px rgba(20,30,50,.05);}
th{background:#f3f6fa;text-align:left;padding:11px 14px;font-size:12px;text-transform:uppercase;
letter-spacing:.05em;color:var(--muted);border-bottom:1px solid var(--line);}
td{padding:11px 14px;border-bottom:1px solid var(--line);vertical-align:middle;}
tr:last-child td{border-bottom:none;}
.board tr.win td{background:#f4faf6;}
.board .rank{font-weight:800;color:var(--accent);width:34px;}
.board .score{font-weight:800;font-size:16px;}
.board a{color:var(--accent);text-decoration:none;border-bottom:1px solid #c5d8e8;}
.votes{font-family:ui-monospace,Menlo,monospace;font-size:12px;color:var(--muted);}
.tag-pill{display:inline-block;font-size:11px;font-weight:700;padding:2px 9px;border-radius:20px;
background:var(--accent-soft);color:var(--accent);letter-spacing:.02em;}
.seasoned{font-size:11px;font-weight:700;color:var(--green);}
/* dossier */
.idea{background:var(--card);border:1px solid var(--line);border-radius:14px;margin:26px 0;overflow:hidden;
box-shadow:0 2px 8px rgba(20,30,50,.06);scroll-margin-top:20px;}
.idea-head{padding:22px 28px 20px;background:linear-gradient(135deg,#f7f9fc,#eef4fa);border-bottom:1px solid var(--line);}
.idea-head .top{display:flex;justify-content:space-between;align-items:flex-start;gap:16px;flex-wrap:wrap;}
.idea-head h3{margin:0;font-size:23px;line-height:1.25;}
.idea-head .rankbadge{font-size:12px;font-weight:700;color:var(--muted);text-transform:uppercase;letter-spacing:.06em;margin-bottom:4px;}
.idea-head .tagline{margin:12px 0 0;font-size:16px;color:var(--ink);font-style:italic;opacity:.9;}
.scorebox{text-align:center;background:#fff;border:1px solid var(--line);border-radius:10px;padding:10px 16px;min-width:96px;}
.scorebox .big{font-size:30px;font-weight:800;color:var(--green);line-height:1;}
.scorebox .of{font-size:12px;color:var(--muted);}
.idea-body{padding:8px 28px 26px;}
.idea-body h4{font-size:12px;text-transform:uppercase;letter-spacing:.07em;color:var(--accent);
margin:22px 0 7px;border-bottom:1px solid var(--line);padding-bottom:5px;}
.idea-body p{margin:0 0 10px;font-size:15px;}
ul.steps{margin:6px 0 4px;padding-left:0;list-style:none;counter-reset:s;}
ul.steps li{position:relative;padding-left:34px;margin-bottom:10px;font-size:14.5px;counter-increment:s;}
ul.steps li::before{content:counter(s);position:absolute;left:0;top:0;width:23px;height:23px;border-radius:50%;
background:var(--accent);color:#fff;font-size:12px;font-weight:700;display:flex;align-items:center;justify-content:center;}
.builds td{font-size:13.5px;}
.builds td:first-child{font-weight:600;white-space:nowrap;}
.risk{display:grid;grid-template-columns:1fr;gap:0;border:1px solid var(--line);border-radius:8px;overflow:hidden;margin-bottom:10px;}
.risk .r{background:var(--red-soft);padding:10px 14px;font-size:14px;}
.risk .r b{color:var(--red);}
.risk .m{background:var(--green-soft);padding:10px 14px;font-size:14px;}
.risk .m b{color:var(--green);}
.judges{display:grid;gap:12px;margin:6px 0;}
@media(min-width:640px){.judges{grid-template-columns:repeat(3,1fr);}}
.judge{border:1px solid var(--line);border-radius:9px;padding:12px 14px;background:#fbfcfe;}
.judge .jh{display:flex;justify-content:space-between;align-items:baseline;margin-bottom:6px;}
.judge .jn{font-size:12px;font-weight:700;color:var(--accent);}
.judge .jt{font-size:18px;font-weight:800;color:var(--ink);}
.axisrow{display:flex;justify-content:space-between;font-size:11.5px;color:var(--muted);padding:1px 0;}
.axisrow .v{font-weight:700;color:var(--ink);}
.judge .jr{font-size:12px;color:var(--muted);margin-top:8px;line-height:1.45;}
.gapfill{background:var(--amber-soft);border-left:3px solid var(--amber);padding:12px 16px;border-radius:0 8px 8px 0;font-size:14px;margin:6px 0 4px;}
.verdict{background:var(--accent-soft);border:1px solid #cfe0ef;border-radius:9px;padding:14px 18px;margin-top:20px;font-size:14.5px;}
.verdict b{color:var(--accent);}
.twogrid{display:grid;gap:18px;}
@media(min-width:640px){.twogrid{grid-template-columns:1fr 1fr;}}
.minihdr{font-size:12px;text-transform:uppercase;letter-spacing:.07em;color:var(--accent);margin:0 0 6px;font-weight:700;}
footer{margin-top:46px;padding-top:20px;border-top:1px solid var(--line);font-size:13px;color:var(--muted);}
"""

def judge_block(votes):
    if not votes: return ''
    cells = []
    for i, v in enumerate(votes):
        name = JUDGE_NAMES[i] if i < len(JUDGE_NAMES) else f'Judge {i+1}'
        axes = ''.join(f'<div class="axisrow"><span>{lbl}</span><span class="v">{e(v.get(k))}</span></div>' for k,lbl in AXES)
        cells.append(f'''<div class="judge"><div class="jh"><span class="jn">{e(name)}</span>
<span class="jt">{e(v.get("total"))}<span style="font-size:11px;color:#999">/25</span></span></div>
{axes}<div class="jr">{e(v.get("rationale"))}</div></div>''')
    return '<div class="judges">' + ''.join(cells) + '</div>'

def builds_rows(bl):
    return ''.join(f'<tr><td>{e(b.get("name"))}</td><td>{e(b.get("what"))}</td></tr>' for b in bl)

def steps(lst):
    return '<ul class="steps">' + ''.join(f'<li>{e(s)}</li>' for s in lst) + '</ul>'

def risks(lst):
    out=''
    for r in lst:
        out += f'<div class="risk"><div class="r"><b>Risk:</b> {e(r.get("risk"))}</div><div class="m"><b>Mitigation:</b> {e(r.get("mitigation"))}</div></div>'
    return out

def resid(lst):
    if not lst: return ''
    return '<ul style="font-size:13.5px;color:#5a6270;padding-left:20px;margin:6px 0">' + ''.join(f'<li style="margin-bottom:5px">{e(x)}</li>' for x in lst) + '</ul>'

# ---- scoreboard (driven by seasoned winners; votes from the board, same order) ----
board_rows=''
for i,w in enumerate(winners):
    anchor = f'idea-{i+1}'
    title = w['title']
    name = short(title)
    rest = title[len(name):].lstrip(' —-').strip()
    titlecell = f'<a href="#{anchor}"><b>{e(name)}</b></a> <span style="color:#5a6270">{e(rest)}</span>'
    cat = f'<span class="tag-pill">{e(w.get("category"))}</span>'
    votes = '·'.join(str(x) for x in board[i].get('votes',[])) if i < len(board) else ''
    board_rows += f'''<tr class="win"><td class="rank">{i+1}</td>
<td>{titlecell}</td><td class="score">{e(w['score'])}</td>
<td class="votes">{e(votes)}</td><td>{cat}</td></tr>'''

# ---- dossiers ----
ideas_html=''
for i,w in enumerate(winners):
    anchor=f'idea-{i+1}'
    ideas_html += f'''
<div class="idea" id="{anchor}">
  <div class="idea-head">
    <div class="top">
      <div style="flex:1;min-width:260px">
        <div class="rankbadge">Rank #{i+1} · <span class="tag-pill">{e(w.get("category"))}</span></div>
        <h3>{e(w.get("title"))}</h3>
        <p class="tagline">{e(w.get("tagline"))}</p>
      </div>
      <div class="scorebox"><div class="big">{e(w.get("score"))}</div><div class="of">avg / 25</div></div>
    </div>
  </div>
  <div class="idea-body">
    <h4>The problem</h4><p>{e(w.get("the_problem"))}</p>
    <h4>Who it's for</h4><p>{e(w.get("target_user"))}</p>
    <h4>The solution</h4><p>{e(w.get("the_solution"))}</p>
    <h4>How it works</h4>{steps(w.get("how_it_works",[]))}
    <h4>What it builds on</h4>
    <table class="builds"><thead><tr><th>Asset</th><th>How it's used</th></tr></thead><tbody>{builds_rows(w.get("builds_on",[]))}</tbody></table>
    <h4>Gap it fills</h4><div class="gapfill">{e(w.get("gap_filled"))}</div>
    <div class="twogrid" style="margin-top:18px">
      <div><p class="minihdr">MVP scope</p><p style="font-size:14px">{e(w.get("mvp_scope"))}</p></div>
      <div><p class="minihdr">Why now</p><p style="font-size:14px">{e(w.get("why_now"))}</p></div>
    </div>
    <div class="twogrid" style="margin-top:6px">
      <div><p class="minihdr">Business model</p><p style="font-size:14px">{e(w.get("business_model"))}</p></div>
      <div><p class="minihdr">Defensibility</p><p style="font-size:14px">{e(w.get("defensibility"))}</p></div>
    </div>
    <h4>Key risks &amp; mitigations</h4>{risks(w.get("key_risks",[]))}
    <h4>How the judges scored it</h4>{judge_block(w.get("votes",[]))}
    <h4 style="margin-top:18px">Residual risks flagged in debate</h4>{resid(w.get("residual_risks",[]))}
    <div class="verdict"><b>Why it made the cut:</b> {e(w.get("verdict"))}</div>
  </div>
</div>'''

HTML = f'''<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Civic Tech — Idea Foundry Portfolio</title><style>{CSS}</style></head><body>
<header class="hero"><div class="wrap">
<p class="eyebrow">Idea Foundry · adversarially-vetted concepts</p>
<h1>Eleven seasoned civic-tech ideas</h1>
<p>Generated, debated, and scored by a multi-team pipeline grounded in the prior-art &amp; architecture research — each idea fills a named whitespace gap and builds on the open data, protocols, and codebases we surveyed. Every survivor was developed into a full dossier; ranked by ensemble score.</p>
</div></header>
<div class="funnel">
<div class="step"><div class="n">{R['generated']}</div><div class="lbl">Generated<br>(6 lenses)</div></div>
<div class="step"><div class="n">{R['curated']}</div><div class="lbl">Curated<br>distinct</div></div>
<div class="step"><div class="n">{R['survived']}</div><div class="lbl">Survived<br>the gauntlet</div></div>
<div class="step final"><div class="n">{len(winners)}</div><div class="lbl">Seasoned<br>into dossiers</div></div>
</div>
<div class="wrap">
<div class="method"><b>How these were made.</b> Six generator teams each worked a distinct lens (hyperlocal land-use · rulemaking legibility · deliberation/consensus · vertical "lite counsel" · infrastructure/protocol · engagement &amp; funding). Candidates were de-duplicated, then every idea ran an <b>adversarial gauntlet</b> — a red-team critic tried to kill it, a steelman defender conceded the fatal shots and refined it, and a neutral adjudicator decided survive/die. Survivors were scored by a <b>3-judge ensemble</b> (pragmatic engineer · skeptical VC · civic-impact expert) across five axes. The top 6 were developed into full dossiers. Scores are out of 25.</div>

<h2 class="section">Scoreboard — all {R['survived']} survivors</h2>
<p class="section-sub">Ranked by average ensemble score (out of 25). Vote columns are the three judges' totals (pragmatist · VC · civic). All {len(winners)} were seasoned into the dossiers below — click any idea to jump to it.</p>
<table class="board"><thead><tr><th>#</th><th>Idea</th><th>Avg</th><th>Judge votes</th><th>Category</th></tr></thead><tbody>{board_rows}</tbody></table>

<h2 class="section">The seasoned dossiers</h2>
<p class="section-sub">Each dossier is the post-debate, refined version — including the candid risks the red team raised and how the three judges scored it.</p>
{ideas_html}

<footer>Produced by the civic-idea-foundry workflow · {R['generated']} generated → {R['curated']} curated → {R['survived']} survived → {len(winners)} seasoned · 3-judge ensemble scoring. Dossiers reflect ideas as refined through adversarial debate; scores and rationales are the judges' assessments, not external validation.</footer>
</div></body></html>'''

open('docs/research/civic-idea-portfolio.html','w').write(HTML)
print('wrote civic-idea-portfolio.html', len(HTML), 'bytes')
