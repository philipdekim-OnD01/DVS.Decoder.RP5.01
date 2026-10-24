#!/usr/bin/env python3
"""New launcher/runtime checks using only private synthetic files and owned children."""
import argparse,pathlib,subprocess,json,os,signal,time,platform
p=argparse.ArgumentParser();p.add_argument('--package',type=pathlib.Path,required=True);p.add_argument('--results',type=pathlib.Path,required=True);a=p.parse_args();root=a.package;exe=root/'bin/event-b';cfg=root/'config';cases=[]
# All test names are new within this test-owned package.
valid=cfg/'tiny-event.bin';g=bytes([132,10,1,2]);frame=bytes([8,0,0,1,8,128,0,0,4,32,8,79])+g+bytes([12,0,8,0]);valid.write_bytes(frame)
def reject(name,args,needle=None):
 run=root/'runs'/name;existed=run.exists();before={str(f.relative_to(run)):f.read_bytes() for f in run.iterdir() if f.is_file()} if existed else {};r=subprocess.run([str(exe),*args],capture_output=True,text=True,timeout=3)
 assert r.returncode==2 and run.exists()==existed,(name,r.returncode,r.stderr)
 if existed:assert before=={str(f.relative_to(run)):f.read_bytes() for f in run.iterdir() if f.is_file()}
 if needle:assert needle in r.stderr,(name,r.stderr)
 cases.append({'name':name,'pass':True,'exit':r.returncode})
base=['replay','--file',str(valid)]
for name,content in [('bad-json','{'),('bad-shape','[]'),('bad-bool','{"queue_capacity":true,"decode_delay_us":0}'),('bad-duplicate','{"queue_capacity":1,"queue_capacity":2,"decode_delay_us":0}'),('bad-range','{"queue_capacity":0,"decode_delay_us":0}'),('bad-extra','{"queue_capacity":8,"decode_delay_us":0,"device":"x"}')]:
 f=cfg/(name+'.json');f.write_text(content);reject(name,base+['--name',name,'--config',str(f)])
fifo=cfg/'fifo-runtime.json';os.mkfifo(fifo);reject('fifo-config',base+['--name','fifo-config','--config',str(fifo)],'regular');fifo.unlink()
link=cfg/'symlink-config.json';link.symlink_to(cfg/'default.json');reject('symlink-config',base+['--name','symlink-config','--config',str(link)],'regular')
reject('outside-config',base+['--name','outside-config','--config',str(valid.parent.parent/'manifest.json')],'package/config')
reject('device-refusal',['replay','--device=/tmp/never-open'],'PHASE_C_BLOCKED')
reject('bad-name',base+['--name','../escaped'],'run name')
reject('missing-file',['replay','--file',str(cfg/'missing'),'--name','missing-file'])
empty=cfg/'empty.bin';empty.write_bytes(b'');reject('empty-file',['replay','--file',str(empty),'--name','empty-file'],'regular')
# Real new package invocation on a tiny synthetic input, outside repository cwd.
r=subprocess.run([str(exe),*base,'--name','synthetic-runtime'],capture_output=True,text=True,cwd='/tmp',timeout=5);assert r.returncode==0,r.stderr
out=root/'runs/synthetic-runtime';s=json.loads((out/'status.json').read_text());m=json.loads((out/'metrics.json').read_text());assert s['complete'] and s['exit_code']==0 and m['frames']==1 and m['events']==2 and m['queue_final']==0
cases.append({'name':'independent-cwd-and-complete-status','pass':True})
reject('synthetic-runtime',base+['--name','synthetic-runtime'],'already exists')
# New package signal forwarding, with bounded private synthetic file + delay.
slow=cfg/'slow.json';slow.write_text('{"queue_capacity":1,"decode_delay_us":10000}');many=cfg/'many.bin';many.write_bytes(frame*2000)
proc=subprocess.Popen([str(exe),'replay','--file',str(many),'--name','signal-runtime','--config',str(slow)],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,cwd='/tmp');time.sleep(.2);proc.send_signal(signal.SIGTERM);proc.communicate(timeout=4)
status=json.loads((root/'runs/signal-runtime/status.json').read_text());assert proc.returncode==130 and status['exit_code']==130 and not status['complete'];cases.append({'name':'signal-forwarding-non-success-status','pass':True})
r=subprocess.run([str(exe),'info'],capture_output=True,text=True,timeout=3);assert r.returncode==0 and json.loads(r.stdout)['phase_c']=='HARD BLOCKED';cases.append({'name':'standalone-info-manifest','pass':True})
a.results.write_text(json.dumps({'pass':True,'host':platform.platform(),'cases':cases,'passed':len(cases),'scope':'new package runtime only; synthetic files/processes, no device/production calls','phase_c':'HARD BLOCKED','production_changed':False},indent=2)+'\n');print(json.dumps({'passed':len(cases)}))
