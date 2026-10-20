"""Reject/characterize the existing adjacent-word candidate; never decode a clock."""
from pathlib import Path
import struct,collections,json
root=Path(__file__).resolve().parents[2]
rows=[]
with (root/'recordings/2026-10-13/mipi-raw2-10s.dvsraw').open('rb') as f:
 f.seek(32)
 for r in range(16):
  h=struct.unpack('<QQ4I',f.read(32));b=f.read(h[-1]);values=[];sites=[]
  for i in range(976):
   p=i*180+176
   if b[p:p+4]==b'\xcc'*4:
    values.append(struct.unpack('>I',b[p+12:p+16])[0]);sites.append(p+12)
  rows.append({'record':r,'candidate_values':values,'distinct_values':len(set(values)), 'first_candidate_file_offset':64+r*175712+sites[0]})
transitions=[sum(((b-a)&0xffffffff)==1 for a,b in zip(rows[i]['candidate_values'],rows[i+1]['candidate_values'])) for i in range(15)]
result={'layout':'signature+12 BE32, unvalidated candidate only','records':rows,'constant_candidate_per_run_count':sum(r['distinct_values']==1 for r in rows),'plus_one_at_same_slot_across_records':transitions,'limit':'16-marker runs are not proven sensor frames; neither equality nor +1 establishes identity. Failure only rejects this direct candidate as evidence.'}
Path(__file__).with_name('counter_consistency.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({k:v for k,v in result.items() if k!='records'},indent=2))
print('distinct per run:',[r['distinct_values'] for r in rows])
