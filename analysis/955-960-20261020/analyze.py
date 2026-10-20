"""Read only: first 16 stored DMA records; no pixel or sensor-frame claims."""
import collections, hashlib, json, pathlib, struct
root=pathlib.Path(__file__).resolve().parents[2]
p=root/'recordings/2026-10-13/mipi-raw2-10s.dvsraw'
rows=[]; stream=[]; sample_hash=hashlib.sha256()
with p.open('rb') as f:
    fh=f.read(32)
    assert struct.unpack('<8s6I',fh)==(b'DVSRAW01',960,720,175680,32,16140,10000)
    for r in range(16):
        rh=f.read(32); h=struct.unpack('<QQ4I',rh); b=f.read(h[-1])
        assert len(b)==175680
        sample_hash.update(rh+b)
        flags=[]
        for i in range(976):
            c=b[i*180:(i+1)*180]
            flags.append(c[176:]==b'\xcc'*4 and len(set(struct.unpack('<45I',c)))<=20)
        starts=[i for i in range(976) if flags[i] and (i==0 or not flags[i-1])]
        assert len(starts)==1
        s=starts[0]; n=0
        while s+n<976 and flags[s+n]: n+=1
        assert n==16
        # Header beginning at signature, allowing its following words across a chunk.
        off=s*180+176
        header=struct.unpack('>4I',b[off:off+16])
        rows.append(dict(record=r,sequence=h[2],flags=h[3],marker_chunk=s,
                         marker_file_offset=64+r*175712+s*180,
                         signature_file_offset=64+r*175712+off,
                         header_be=[f'{v:08x}' for v in header]))
        stream.append(r*976+s)
spacings=[b-a for a,b in zip(stream,stream[1:])]
assert spacings==[971]*15
assert all(b['sequence']==a['sequence']+1 for a,b in zip(rows,rows[1:]))
assert all(r['flags']&0x40==0 for r in rows)
result=dict(scope='first 16 records only; chunk != proven physical column',
            sample_records_sha256=sample_hash.hexdigest(),rows=rows,
            marker_spacing_histogram=dict(collections.Counter(spacings)),
            marker_run_lengths={'16':16},
            record0_decoder=dict(first_pixel=880,source_chunk_order='880..975,0..863',
                                 backwards_jump_byte=175676,next_byte_after_jump=0,
                                 chronological_next_marker_record=1,chronological_next_marker_chunk=859),
            header_status='signature verified; Fig46 fixed header/type and frame counter NOT validated')
out=pathlib.Path(__file__).with_name('evidence.json');out.write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
