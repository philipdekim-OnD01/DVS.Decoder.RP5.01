#!/usr/bin/env python3
"""Harmless real watchdog process: cancellation or bounded NOOP alert file only.
No shell runner, systemd API, I2C, modules, service restart or hardware action.
"""
import argparse,fcntl,hashlib,json,math,os,pathlib,re,secrets,signal,tempfile,time
stopped=False
def stop(_signum,_frame):
 global stopped
 stopped=True
def atomic(root,name,value):
 temporary=root/(name+'.next');temporary.write_text(json.dumps(value,indent=2)+'\n');temporary.replace(root/name)
def checked(root):
 p=pathlib.Path(root)
 allowed_tmp=pathlib.Path('/tmp').resolve() if os.uname().sysname=='Linux' else pathlib.Path(tempfile.gettempdir()).resolve()
 if p.is_symlink() or not p.resolve().is_relative_to(allowed_tmp):raise ValueError('watchdog is sandbox temp-only')
 if (p/'WATCHDOG_SANDBOX').read_text()!='NOOP-ONLY-V1':raise ValueError('not a watchdog sandbox')
 for name in ('request.json','cancel.json','result.json','ready.json','lock'):
  if (p/name).is_symlink() or (p/(name+'.next')).is_symlink():raise ValueError('sandbox symlink')
 return p
def init(root,timeout):
 if not 0.2<=timeout<=10:raise ValueError('timeout out of bounds')
 p=pathlib.Path(root)
 if not p.resolve().is_relative_to(pathlib.Path(tempfile.gettempdir()).resolve()):raise ValueError('temp only')
 p.mkdir();(p/'WATCHDOG_SANDBOX').write_text('NOOP-ONLY-V1')
 token=secrets.token_hex(24);run=secrets.token_hex(12)
 atomic(p,'request.json',{'schema':1,'run':run,'token_sha256':hashlib.sha256(token.encode()).hexdigest(),'timeout':timeout,'action':'WRITE_NOOP_ALERT_ONLY'})
 return {'run':run,'token':token}
def validate_request(req):
 if not isinstance(req,dict) or set(req)!={'schema','run','token_sha256','timeout','action'}:raise ValueError('invalid watchdog request')
 if type(req['schema']) is not int or req['schema']!=1 or req['action']!='WRITE_NOOP_ALERT_ONLY':raise ValueError('invalid watchdog request')
 for key,length in (('run',24),('token_sha256',64)):
  if not isinstance(req[key],str) or re.fullmatch('[0-9a-f]{'+str(length)+'}',req[key]) is None:raise ValueError('invalid watchdog identity')
 duration=req['timeout']
 if type(duration) not in (int,float) or not math.isfinite(duration) or not .2<=duration<=10:raise ValueError('invalid watchdog timeout')
def worker(root):
 p=checked(root);req=json.loads((p/'request.json').read_text())
 validate_request(req)
 with (p/'lock').open('a') as lock:
  try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
  except BlockingIOError:return 3
  if any((p/name).exists() for name in ('ready.json','result.json')):raise ValueError('watchdog sandbox already used')
  start=time.monotonic();deadline=start+req['timeout']
  atomic(p,'ready.json',{'pid':os.getpid(),'ppid':os.getppid(),'sid':os.getsid(0),'cgroup':pathlib.Path('/proc/self/cgroup').read_text() if pathlib.Path('/proc/self/cgroup').exists() else None,'run':req['run'],'source_sha256':hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest()})
  status='FIRED_NOOP_ALERT';invalid=0
  while time.monotonic()<deadline:
   if stopped:status='TERMINATED_NOOP_ALERT';break
   cancel=p/'cancel.json'
   if cancel.exists():
    try:
     c=json.loads(cancel.read_text())
     if isinstance(c,dict) and set(c)=={'run','token','proof'} and isinstance(c['token'],str) and c['run']==req['run'] and hashlib.sha256(c['token'].encode()).hexdigest()==req['token_sha256'] and c['proof']=='VERIFIED_SANDBOX_ONLY':status='CANCELLED_SANDBOX';break
    except (ValueError,TypeError,OSError):pass
    invalid+=1
   time.sleep(.025)
  atomic(p,'result.json',{'status':status,'run':req['run'],'elapsed':time.monotonic()-start,'invalid_cancel_observations':invalid,'hardware_actions':0,'production_ready':False,'action':'marker-only','cgroup':pathlib.Path('/proc/self/cgroup').read_text() if pathlib.Path('/proc/self/cgroup').exists() else None})
 return 0
def main():
 p=argparse.ArgumentParser();p.add_argument('--worker',type=pathlib.Path,required=True);a=p.parse_args()
 signal.signal(signal.SIGTERM,stop);signal.signal(signal.SIGINT,stop)
 return worker(a.worker)
if __name__=='__main__':raise SystemExit(main())
