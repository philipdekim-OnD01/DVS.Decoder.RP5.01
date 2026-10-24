#!/usr/bin/env python3
"""Compare actual legacy decoded ref/sub pairs with completed SDK frame headers."""
import argparse,pathlib,json,struct,hashlib,platform
p=argparse.ArgumentParser();p.add_argument('--work',type=pathlib.Path,required=True);p.add_argument('--results',type=pathlib.Path,required=True);a=p.parse_args();r=a.work
legacy=[int(s.split(',')[1]) for s in (r/'dual-time.control.csv').read_text().splitlines()]
b=(r/'frames.bin').read_bytes();pos=0;sdk=[]
while pos<len(b):
 ts,period,n=struct.unpack_from('<QII',b,pos);sdk.append(ts);pos+=16+n*6
assert pos==len(b) and len(sdk)==1557 and len(legacy)==1558 and legacy[:1557]==sdk
assert hashlib.sha256((r/'dual-time.events').read_bytes()).digest()==hashlib.sha256((r/'dual.events').read_bytes()).digest()
report={'pass':True,'host':platform.platform(),'legacy_sub_timestamp_pairs':len(legacy),'sdk_complete_frame_timestamps':len(sdk),'compared_prefix_pairs':len(sdk),'equal':True,'final_legacy_pair_has_no_complete_sdk_frame':'EOF incomplete frame, excluded','event_trace_unchanged':True,'physical_time_accuracy':'UNKNOWN','method':'actual legacy ref/sub stats joined as ref*1000+sub compared to actual SDK SensorFrame.timestamp_us','sensor_time_sequence_sha256':hashlib.sha256(struct.pack('<'+str(len(sdk))+'Q',*sdk)).hexdigest()}
a.results.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({'pass':True,'timestamp_pairs':len(sdk)}))
