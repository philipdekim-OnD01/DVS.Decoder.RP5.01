#!/usr/bin/env python3
"""New standalone-package E2E only; no legacy analysis or hardware tests."""
import argparse,pathlib,subprocess,json,hashlib,struct,resource,platform
p=argparse.ArgumentParser();p.add_argument('--package',type=pathlib.Path,required=True);p.add_argument('--sample',type=pathlib.Path,required=True);p.add_argument('--results',type=pathlib.Path,required=True);a=p.parse_args();exe=a.package/'bin/event-b'
sha=hashlib.sha256(a.sample.read_bytes()).hexdigest();assert sha=='962925dfaf87fcd1a16d04cd6e122d32558527b543f39acc2803926f2fc897b3'
cmd=[str(exe),'replay','--file',str(a.sample),'--name','approved-sample'];r=subprocess.run(cmd,capture_output=True,text=True,timeout=60);assert r.returncode==0,(r.stdout,r.stderr)
run=a.package/'runs/approved-sample';m=json.loads((run/'metrics.json').read_text());status=json.loads((run/'status.json').read_text());data=(run/'frames.bin').read_bytes();outsha=hashlib.sha256(data).hexdigest()
assert outsha=='e15a8a75899f6352725e0a4fbcd73f537acd1496fda6ae8ac25cd17903be1798'
assert m['frames']==1557 and m['events']==1469217 and m['on_events']==706157 and m['off_events']==763060
assert m['queue_drops']==0 and m['queue_final']==0 and m['queue_high_water']<=m['queue_capacity'] and status['complete']
assert m['invalid']==m['unknown']==m['sensor_frame_gaps']==0 and m['eof_partial_bytes']==0 and m['eof_incomplete_frames']==1
pos=0;times=[];completed_events=0
while pos<len(data):
 ts,period,n=struct.unpack_from('<QII',data,pos);times.append(ts)
 for i in range(n):completed_events+=data[pos+16+i*6+4].bit_count()
 pos+=16+n*6
assert pos==len(data) and len(times)==1557
ppm=(run/'latest.ppm').read_bytes();assert ppm.startswith(b'P6\n960 720\n255\n') and len(ppm)==2073615
nm=subprocess.check_output(['nm','-C',str(a.package/'bin/event-b-engine')],text=True);assert 'V4L2Capture' not in nm
r=subprocess.run([str(exe),'--device','/tmp/dvs-never-open-device'],capture_output=True,text=True,timeout=3);assert r.returncode==2 and 'PHASE_C_BLOCKED' in r.stderr
report={'pass':True,'host':platform.platform(),'command':cmd,'sample_sha256':sha,'frame_output_sha256':outsha,'metrics':m,'status':status,'complete_frame_event_count':completed_events,'first_timestamp_us':times[0],'last_timestamp_us':times[-1],'timestamp_non_decreasing':all(b>=a for a,b in zip(times,times[1:])),'child_max_rss_KiB':resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss,'V4L2Capture_symbol_absent':True,'device_refusal_before_execution':True,'prior_suites_repeated':False,'phase_c':'HARD BLOCKED','production_changed':False}
a.results.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
