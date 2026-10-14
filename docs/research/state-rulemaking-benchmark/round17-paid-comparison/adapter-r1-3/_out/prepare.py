from pathlib import Path
HERE = Path(__file__).resolve().parent.parent
for name in ('test_adapter.py', 'test_revision.py', 'test_host_driver.py'):
    p = HERE / name
    s = p.read_text().replace('HERE = Path(__file__).resolve().parent',
        "HERE = Path(__file__).resolve().parent\nOUT = HERE / '_out'\nOUT.mkdir(exist_ok=True)")
    p.write_text(s.replace('dir=HERE', 'dir=OUT'))
p = HERE / 'fake_http.py'
s = p.read_text().replace("ADAPTER = HERE.parent / 'adapter-r1-1'", 'ADAPTER = HERE')
s = s.replace('dir=HERE)', "dir=HERE / '_out')")
s = s.replace('Loads the r1.1 adapter', 'Loads the r1.2 adapter').replace('../adapter-r1-1 by absolute path', 'this adapter by absolute path')
p.write_text(s)
for rel, old, new in (
    ('_out/round2-repros/_load.py', "HERE.parent / 'adapter-r1-1'", 'HERE.parent.parent'),
    ('_out/round2-repros/orig-repros/_load.py', "HERE.parent.parent / 'adapter-r1-1'", 'HERE.parent.parent.parent')):
    p = HERE / rel
    p.write_text(p.read_text().replace(old, new))
