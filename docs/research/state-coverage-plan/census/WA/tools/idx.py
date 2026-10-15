import re
def rows(t):
    return re.findall(r'<a href = \S+?/(\d\d-\d\d-\d{3}[A-Z]?)\.htm>([^<]*)</a>', t)
