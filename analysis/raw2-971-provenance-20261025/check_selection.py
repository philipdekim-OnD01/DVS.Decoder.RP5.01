#!/usr/bin/env python3
"""Bounded first16 RAW check plus audit-derived Wrap21 arithmetic, no decoder patch."""
import argparse,hashlib,json,pathlib,struct
p=argparse.ArgumentParser();p.add_argument('raw',type=pathlib.Path);p.add_argument('--results',type=pathlib.Path,required=True);a=p.parse_args()
sha=hashlib.sha256();rows=[]
with a.raw.open('rb') as f:
 assert struct.unpack('<8s6I',f.read(32))==(b'DVSRAW01',960,720,175680,32,16140,10000)
 for r in range(16):
  h=f.read(32);meta=struct.unpack('<QQ4I',h);assert meta[-1]==175680;b=f.read(175680);assert len(b)==175680;sha.update(h+b)
  flags=[b[i*180+176:i*180+180]==b'\xcc'*4 and len(set(struct.unpack('<45I',b[i*180:(i+1)*180])))<=20 for i in range(976)]
  starts=[i for i in range(976) if flags[i] and not flags[(i-1)%976]];assert len(starts)==1
  m=starts[0];assert sum(flags)==16
  first=(m+16)%976;selected=[(first+i)%976 for i in range(960)]
  rows.append({'host_record':r,'host_sequence':meta[2],'candidate_marker_id':r,'candidate_marker_chunk':m,'marker_file_offset':64+r*175712+m*180,'candidate_span_chunks':971 if r<15 else None,'first_pixel':first,'selected_count':960,'flagged_source_chunks':sum(flags[i] for i in selected),'first_backward_serial':next((i for i in range(1,960) if selected[i]<selected[i-1]),None),'sensor_frame':'UNKNOWN'})
assert sha.hexdigest()=='d39ee91aea93fe1605a189aff91326ae43803558642b3f4baeacf81daf46508b'
assert [976+b['candidate_marker_chunk']-a['candidate_marker_chunk'] for a,b in zip(rows,rows[1:])]==[971]*15
arithmetic=[]
for record,head,tail in ((173,15,6),(174,10,11),(175,5,16)):
 selected=list(range(head,head+960));flagged=set(range(head))|set(range(976-tail,976));overlap=sorted(set(selected)&flagged);assert len(overlap)==5
 arithmetic.append({'source':'audit #6300566219 arithmetic, NOT reread RAW','host_record':record,'head':head,'tail':tail,'previous_tail':16-head,'candidate_interval':976-(head+tail-16),'candidate_marker_start_chunk':976-tail,'candidate_marker_file_offset':64+record*175712+(976-tail)*180,'first_pixel':head,'selected_source_range':[head,head+959],'flagged_overlap':overlap,'sensor_frame':'UNKNOWN'})
result={'pass':True,'raw_records_read':16,'raw_bytes_read':32+16*175712,'sample_records_sha256':sha.hexdigest(),'first_bad_layer':'UNKNOWN','rows':rows,'audit_derived_arithmetic':arithmetic,'test_scope':'first16 identity/selection and three schematic audit examples; not full200 rerun or authenticated sensor recovery','production_changes':0}
a.results.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'pass':True,'records_read':16,'schematic_cases':3,'first_bad_layer':'UNKNOWN'}))
