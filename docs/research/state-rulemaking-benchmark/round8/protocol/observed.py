"""Runtime-facing R8 observed contract; no network, credentials or fresh source reads."""
import importlib.util
from pathlib import Path
_path=Path(__file__).with_name('evaluate.py')
_spec=importlib.util.spec_from_file_location('round8_protocol_observed_contract',_path)
_module=importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_module)
validate_observed=_module.validate_observed
observed_schema=_module.observed_schema
