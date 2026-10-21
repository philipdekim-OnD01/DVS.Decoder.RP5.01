#!/usr/bin/env python3
"""Build/run the Linux file-mode pipeline; no V4L2 device opened."""
import argparse,hashlib,json,os,pathlib,platform,shutil,subprocess,sys,tempfile,time,signal
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/'event-offline'))
from prepare_core import prepare,FILES
p=argparse.ArgumentParser();p.add_argument('sdk',type=pathlib.Path);p.add_argument('sample',type=pathlib.Path);p.add_argument('work',type=pathlib.Path);p.add_argument('--sanitize',action='store_true');a=p.parse_args();a.work.mkdir(exist_ok=False)
sdk=a.work/'sdk';prepare(a.sdk,sdk);exe=a.work/'engine';here=pathlib.Path(__file__).resolve().parent
cmd=[os.getenv('CXX','g++'),'-std=c++20','-O2','-Wall','-Wextra','-Werror','-pthread','-I'+str(sdk/'include'),str(here/'engine.cpp'),*[str(sdk/'src'/f) for f in FILES],'-o',str(exe)]
if a.sanitize:cmd[1:1]=['-fsanitize=address,undefined','-fno-omit-frame-pointer','-g']
result={'sanitizers':a.sanitize,'platform':platform.platform(),'build_command':cmd,'sample_sha256':hashlib.sha256(a.sample.read_bytes()).hexdigest(),'runs':[]}
# Compile SDK objects once, then link each public test program.
options=cmd[:cmd.index(str(here/'engine.cpp'))]
objects=[]
for i,f in enumerate(FILES):
 obj=a.work/('sdk-'+str(i)+'.o');subprocess.run(options+['-c',str(sdk/'src'/f),'-o',str(obj)],check=True);objects.append(str(obj))
subprocess.run(options+[str(here/'engine.cpp'),*objects,'-o',str(exe)],check=True)
subprocess.run(options+[str(here/'queue_test.cpp'),*objects,'-o',str(a.work/'queue-test')],check=True)
subprocess.run([str(a.work/'queue-test')],check=True,timeout=5)
result['queue_drop_and_blocked_shutdown_tests']=True
expected='e15a8a75899f6352725e0a4fbcd73f537acd1496fda6ae8ac25cd17903be1798'
for name,capacity,delay in (('file',8,0),('slow-consumer',1,2000)):
 out=a.work/name;subprocess.run([str(exe),'--file',str(a.sample),str(out),str(capacity),str(delay)],check=True,timeout=90)
 m=json.loads((out/'metrics.json').read_text());m['name']=name;m['output_sha256']=hashlib.sha256((out/'frames.bin').read_bytes()).hexdigest()
 assert m['frames']==1557 and m['events']==1469217 and m['queue_drops']==0 and m['queue_final']==0 and m['queue_high_water']<=capacity and m['output_sha256']==expected,m
 assert m['invalid']==m['unknown']==m['sensor_frame_gaps']==0 and m['mode']=='file'
 assert m['sensor_frame_end_words_cid0']==1558 and m['on_events']+m['off_events']==1469217
 image=(out/'latest.ppm').read_bytes();assert image.startswith(b'P6\n960 720\n255\n') and len(image)==len(b'P6\n960 720\n255\n')+960*720*3
 shutil.copy2(here/'viewer.html',out/'index.html');result['runs'].append(m)
out=a.work/'interrupted';proc=subprocess.Popen([str(exe),'--file',str(a.sample),str(out),'1','10000']);time.sleep(0.5);proc.send_signal(signal.SIGTERM);code=proc.wait(timeout=5);assert code==130,code
m=json.loads((out/'metrics.json').read_text());assert m['interrupted'] and not m['error'];result['runs'].append(m)
out=a.work/'missing-input';r=subprocess.run([str(exe),'--file',str(a.work/'does-not-exist'),str(out)],capture_output=True,text=True,timeout=5);assert r.returncode==1 and 'file open failed' in r.stderr
result['missing_input_fails_cleanly']=True
r=subprocess.run([str(exe),'--device','/dev/dvs-deliberately-nonexistent','invalid-bus','8192','128',str(a.work/'refused-live'),'10','--armed'],capture_output=True,text=True,timeout=5)
assert r.returncode==1 and 'production inactive' in r.stderr and not (a.work/'refused-live').exists()
result['active_production_refuses_live_before_device_open']=True;result['pass']=True
(a.work/'gate-b-results.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
