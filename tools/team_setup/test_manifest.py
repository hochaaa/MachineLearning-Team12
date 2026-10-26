"""Synthetic checker tests; all writes stay in newly created TemporaryDirectory."""
import hashlib,tempfile,unittest
from pathlib import Path
from check_runtime import verify
class RuntimeManifestTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='scent-manifest-');self.root=Path(self.temp.name);(self.root/'asset').write_bytes(b'synthetic')
        self.manifest={'files':[{'path':'asset','bytes':9,'sha256':hashlib.sha256(b'synthetic').hexdigest(),'required':True}]}
    def tearDown(self):self.temp.cleanup()
    def test_valid_and_no_write(self):
        p=self.root/'asset';before=p.stat().st_mtime_ns;self.assertEqual(verify(self.root,self.manifest),[]);self.assertEqual(p.stat().st_mtime_ns,before)
    def test_missing(self):
        self.manifest['files'][0]['path']='missing';self.assertEqual(verify(self.root,self.manifest)[0]['reason'],'missing')
    def test_changed_bytes(self):
        (self.root/'asset').write_bytes(b'different');self.assertEqual(verify(self.root,self.manifest)[0]['reason'],'hash_or_size_mismatch')
    def test_traversal(self):
        self.manifest['files'][0]['path']='../outside';self.assertEqual(verify(self.root,self.manifest)[0]['reason'],'unsafe_path')
if __name__=='__main__':unittest.main(verbosity=2)
