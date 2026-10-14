"""R19 offline payload/dependency verification (shared pin utility)."""
import importlib.util
from pathlib import Path
import sys
HERE=Path(__file__).resolve().parent
path=HERE.parent/'pin_ready.py'
s=importlib.util.spec_from_file_location('r19_shared_pins',path)
m=importlib.util.module_from_spec(s)
s.loader.exec_module(m)
if __name__=='__main__':
    m.main()
