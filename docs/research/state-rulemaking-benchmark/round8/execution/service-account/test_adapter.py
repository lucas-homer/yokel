import contextlib,importlib.util,io,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('r8_adapter',HERE/'adapter.py');a=importlib.util.module_from_spec(spec);spec.loader.exec_module(a)
class NoEnvironment:
    def __contains__(self,key):raise AssertionError('environment read')
    def get(self,key):raise AssertionError('environment read')
class Runtime:
    def run(self,*args,**kwargs):return dict(documents=8,PDF_pages=40,source_validation=[],state='completed')
class Controls(unittest.TestCase):
    def test_check_never_reads_credentials(self):
        with patch.object(a,'verify_inputs',return_value={}),patch.object(a,'runtime_module',return_value=Runtime()),patch.object(a.os,'environ',NoEnvironment()):
            self.assertFalse(a.check()['credentials_read'])
    def test_existing_run_denied_before_credentials(self):
        with tempfile.TemporaryDirectory() as temp:
            with patch.object(a,'verify_inputs',return_value={}),patch.object(a,'RUN',Path(temp)),patch.object(a.os,'environ',NoEnvironment()):
                with self.assertRaises(a.Denied):a.live_initial()
    def test_cli_error_does_not_echo_input(self):
        stream=io.StringIO()
        with patch.object(a.sys,'argv',['adapter','caller-secret']),contextlib.redirect_stderr(stream):self.assertEqual(a.main(),1)
        self.assertNotIn('caller-secret',stream.getvalue())
if __name__=='__main__':unittest.main(verbosity=2)
