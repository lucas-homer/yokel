import importlib.util,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('preflight',ROOT/'audit.py');a=importlib.util.module_from_spec(spec);spec.loader.exec_module(a)
class Preparation(unittest.TestCase):
    def test_native_metrics_without_semantic_output(self):
        result=a.native_metrics('é🙂\f'.encode());self.assertEqual(result,{'bytes':7,'codepoints':3,'formfeeds':1,'replacement_characters':0,'nonempty':True});self.assertNotIn('text',result)
    def test_invalid_utf8(self):
        with self.assertRaises(UnicodeDecodeError):a.native_metrics(b'\xff')
    def test_relative_path_confinement(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);(p/'ok').write_text('synthetic');self.assertEqual(a.confined(p,'ok'),(p/'ok').resolve())
            for bad in ('../elsewhere',str(p/'ok'),'missing'):
                with self.subTest(bad=bad),self.assertRaises(ValueError):a.confined(p,bad)
    def test_write_once_artifacts(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'artifact.json';a.write_new(p,{'x':1})
            with self.assertRaises(FileExistsError):a.write_new(p,{'x':2})
    def test_no_execution_at_import(self):
        self.assertFalse((ROOT/'audit.json').exists());self.assertFalse((ROOT/'labeler-inputs.json').exists())
if __name__=='__main__':unittest.main(verbosity=2)
