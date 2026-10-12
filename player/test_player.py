import gzip
import hashlib
import struct
import tempfile
import unittest
from pathlib import Path
from raw_player import Recording, prepare, FILE_HEADER, RECORD_HEADER, PAYLOAD

class PlayerTests(unittest.TestCase):
    def make(self, root, sequences=(4294967295, 0, 2)):
        data=FILE_HEADER.pack(b'DVSRAW01',960,720,PAYLOAD,32,len(sequences),10000)
        for i,seq in enumerate(sequences):
            data+=RECORD_HEADER.pack(i*1000,i*1000,seq,0,1048576,PAYLOAD)+bytes(PAYLOAD)
        path=root/'sample.dvsraw';path.write_bytes(data);return path,data
    def test_wrap_gap_and_exact_record_bytes(self):
        with tempfile.TemporaryDirectory() as tmp:
            path,data=self.make(Path(tmp))
            with Recording(path) as r:
                self.assertEqual(r.info['host_sequence_gaps'],1)
                self.assertEqual(r.record(0),data[32:32+r.stride])
                with self.assertRaises(IndexError):r.record(-1)
                with self.assertRaises(IndexError):r.record(3)
    def test_truncation_and_corrupt_record_length(self):
        with tempfile.TemporaryDirectory() as tmp:
            path,data=self.make(Path(tmp));path.write_bytes(data[:-1])
            with self.assertRaises(ValueError):Recording(path)
            bad=bytearray(data);struct.pack_into('<I',bad,32+28,123);path.write_bytes(bad)
            with self.assertRaises(ValueError):Recording(path)
    def test_gzip_verified_and_source_unchanged(self):
        with tempfile.TemporaryDirectory() as tmp:
            path,data=self.make(Path(tmp));path.unlink()
            gz=path.with_suffix('.dvsraw.gz');gz.write_bytes(gzip.compress(data))
            original=gz.read_bytes();meta={'raw_sha256':hashlib.sha256(data).hexdigest()}
            output,verified=prepare(gz,meta)
            self.assertTrue(verified);self.assertEqual(output.read_bytes(),data)
            self.assertEqual(gz.read_bytes(),original)
            self.assertEqual(prepare(gz,meta),(output,True))
    def test_bad_hash_does_not_publish_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            path,data=self.make(Path(tmp));path.unlink()
            gz=path.with_suffix('.dvsraw.gz');gz.write_bytes(gzip.compress(data))
            with self.assertRaises(ValueError):prepare(gz,{'raw_sha256':'0'*64})
            self.assertFalse(path.exists())

if __name__=='__main__':unittest.main()
