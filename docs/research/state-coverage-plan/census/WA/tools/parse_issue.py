import re, html
ROW=re.compile(r'<tr>(.*?)</tr>', re.S|re.I)
def parse(t):
    rows=[]; agency=None
    for m in re.finditer(r'<tr><td width="5%"></td>(.*?)</tr>', t, re.S):
        cells=re.findall(r'<td[^>]*>(.*?)</td>', m.group(1), re.S)
        if len(cells)<4: continue
        a=re.search(r'NAME=([^>]*)>(.*?)</a>', cells[0])
        if a: agency=html.unescape(a.group(2)).strip(); agency_url=re.search(r'href\s*=\s*(\S+)',cells[0]).group(1)
        h=re.search(r'href\s*=\s*(\S+)>(.*?)</a>(.*)', cells[1], re.S)
        p=re.search(r'href\s*=\s*(\S+)>(.*?)</a>', cells[2])
        ty=re.search(r'>([A-Z]+)</a>', cells[3])
        rows.append(dict(agency=agency, agency_url=agency_url, wsr=h.group(2).strip() if h else None,
            extra=re.sub('<[^>]+>','',h.group(3)).strip() if h else cells[1],
            htm=h.group(1) if h else None, pdf=p.group(1) if p else None,
            type=ty.group(1) if ty else re.sub('<[^>]+>','',cells[3]).strip()))
    links=re.findall(r'<a href = (http\S+\.pdf)>([^<]+)</a>', t.split('Agency</b>')[0])
    return rows, links
