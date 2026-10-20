"""First 16 records: characterize candidate words; no correction applied."""
from pathlib import Path
import struct,json,collections,hashlib
root=Path(__file__).resolve().parents[2]
word_hist=[collections.Counter() for _ in range(4)]
rows=[]; byte_counts=collections.Counter(); digest=hashlib.sha256()
with (root/'recordings/2026-10-13/mipi-raw2-10s.dvsraw').open('rb') as f:
 f.seek(32)
 for r in range(16):
  rh=f.read(32);h=struct.unpack('<QQ4I',rh);b=f.read(h[-1]);digest.update(rh+b)
  byte_counts.update(b)
  for i in range(976):
   p=i*180+176
   if b[p:p+4]!=b'\xcc'*4:continue
   w=struct.unpack('>4I',b[p:p+16])
   for j,v in enumerate(w):word_hist[j][f'{v:08x}']+=1
   rows.append({'record':r,'chunk':i,'file_offset':64+r*175712+p,'words_be':[f'{v:08x}' for v in w]})
result={'scope':'first 16 records, 256 signature sites; adjacent words only',
 'sample_sha256':digest.hexdigest(),'word_histograms':list(map(dict,word_hist)),
 'expected_head0_popcount':(0x100000e0).bit_count(),
 'observed_head0_popcounts':sorted(set(int(v,16).bit_count() for v in word_hist[1])),
 'observed_head1_popcounts':sorted(set(int(v,16).bit_count() for v in word_hist[2])),
 'payload_byte_10_hex_count':byte_counts[0x10],
 'limits':'Permutation invariants apply only to the adjacent candidate words. They do not exclude interleaving, displacement, different chip revision or corruption; no physical loss conclusion.',
 'examples':rows[:2]}
assert sum(word_hist[0].values())==256
Path(__file__).with_name('header_invariants.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
