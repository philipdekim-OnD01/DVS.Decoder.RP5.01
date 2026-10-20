"""Bounded Fig46 layout checks, no inferred bit repair or frame labels."""
import pathlib,struct,json,collections
root=pathlib.Path(__file__).resolve().parents[2]
rev=lambda b:int(f'{b:08b}'[::-1],2)
transforms={'identity':lambda b:b,'reverse_bits_in_bytes':lambda b:bytes(map(rev,b)),'reverse_2bit_groups':lambda b:bytes(((x&3)<<6)|((x&12)<<2)|((x&48)>>2)|((x&192)>>6) for x in b)}
counts=collections.Counter(); examples=[]; sigcount=0
with (root/'recordings/2026-10-13/mipi-raw2-10s.dvsraw').open('rb') as f:
 f.seek(32)
 for r in range(16):
  h=struct.unpack('<QQ4I',f.read(32));raw=f.read(h[-1])
  sigs=[i*180+176 for i in range(976) if raw[i*180+176:i*180+180]==b'\xcc'*4]
  sigcount+=len(sigs)
  for p in sigs:
   for name,transform in transforms.items():
    for endian in ['>','<']:
     for direction in [1,-1]:
      # Adjacent physical words on either side of signature.
      w=[struct.unpack(endian+'I',transform(raw[p+direction*4*k:p+direction*4*k+4]))[0] for k in range(1,4)]
      key=f'{name}/{endian}/{direction}'
      size=(w[0]>>24)==16;dtype=(w[1]>>16)==1
      counts[key+'/size']+=size;counts[key+'/type']+=dtype;counts[key+'/both']+=size and dtype
      if size and dtype:examples.append([r,p,key,w])
result={'records':16,'signature_count':sigcount,'candidate_models':12,'checks':dict(counts),'matching_examples':examples,'limit':'Only adjacent words in 2 directions, 2 endians, 3 byte transforms; arbitrary packing and sensor configuration not excluded.'}
pathlib.Path(__file__).with_name('header_checks.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
