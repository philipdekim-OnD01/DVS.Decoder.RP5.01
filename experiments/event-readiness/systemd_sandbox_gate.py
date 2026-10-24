#!/usr/bin/env python3
"""Exercise NEW marker-only transient watchdog units; never production units.
Requires explicit readiness task authorization. No restore/hardware commands.
"""
import argparse,hashlib,json,pathlib,secrets,subprocess,time
from watchdog_worker import init
HERE=pathlib.Path(__file__).resolve().parent
PROPERTIES=('User=philip','Group=philip','ProtectSystem=strict','ProtectHome=true','PrivateDevices=true','PrivateNetwork=true','NoNewPrivileges=true','ProtectKernelTunables=true','ProtectKernelModules=true','ProtectControlGroups=true','DevicePolicy=closed','RestrictAddressFamilies=AF_UNIX','CapabilityBoundingSet=','InaccessiblePaths=/run/dbus /run/user /run/systemd/private','UMask=0077','Nice=10','CPUQuota=25%','MemoryMax=128M','TasksMax=8','TimeoutStopSec=1s','KillMode=control-group')

def show(unit):
 return subprocess.check_output(['systemctl','show',unit,'-p','Id','-p','User','-p','ControlGroup','-p','ProtectSystem','-p','ProtectHome','-p','PrivateDevices','-p','PrivateNetwork','-p','NoNewPrivileges','-p','ReadWritePaths','-p','DevicePolicy','-p','RuntimeMaxUSec','-p','ExecStart'],text=True)
def arm(work,name,timeout=1.5,runtime='5s'):
 root=work/name;secret=init(root,timeout)
 unit='rp5-dvs-rdy-'+secrets.token_hex(5)+'-'+name+'.service'
 assert unit.startswith('rp5-dvs-rdy-') and '.service'==pathlib.Path(unit).suffix
 cmd=['sudo','-n','systemd-run','--quiet','--collect','--unit='+unit]
 for p in PROPERTIES+('ReadWritePaths='+str(root),'RuntimeMaxSec='+runtime):cmd+=['--property='+p]
 cmd+=['/usr/bin/python3',str(HERE/'watchdog_worker.py'),'--worker',str(root)]
 subprocess.run(cmd,check=True,capture_output=True,text=True,timeout=10)
 deadline=time.monotonic()+3
 while not (root/'ready.json').exists() and time.monotonic()<deadline:time.sleep(.02)
 if not (root/'ready.json').exists():raise RuntimeError('isolated unit did not signal readiness; no protection relaxation')
 properties=show(unit)
 for required in ('User=philip','ProtectSystem=strict','ProtectHome=yes','PrivateDevices=yes','PrivateNetwork=yes','NoNewPrivileges=yes','DevicePolicy=closed'):
  if required not in properties:raise RuntimeError('required sandbox property not effective: '+required)
 ready=json.loads((root/'ready.json').read_text())
 if ready.get('source_sha256')!=hashlib.sha256((HERE/'watchdog_worker.py').read_bytes()).hexdigest():raise RuntimeError('worker source drift')
 if unit not in ready.get('cgroup',''):raise RuntimeError('worker not in dedicated systemd cgroup')
 (root/'properties.txt').write_text(properties)
 (root/'unit.txt').write_text(unit)
 return root,secret,ready,properties

def result(root):
 end=time.monotonic()+5
 while not (root/'result.json').exists() and time.monotonic()<end:time.sleep(.025)
 return json.loads((root/'result.json').read_text())
def run(work):
 work.mkdir(exist_ok=False);cases=[]
 for name,timeout,runtime,cancel,expected in (
  ('expiry',1.2,'5s','none','FIRED_NOOP_ALERT'),
  ('cancel',1.5,'5s','valid','CANCELLED_SANDBOX'),
  ('badcancel',1.2,'5s','invalid','FIRED_NOOP_ALERT'),
  ('typedcancel',1.2,'5s','malformed','FIRED_NOOP_ALERT'),
  ('runtimecap',6,'3s','none','TERMINATED_NOOP_ALERT')):
  root,secret,ready,properties=arm(work,name,timeout,runtime)
  if cancel!='none':
   from watchdog_worker import atomic
   atomic(root,'cancel.json',{'run':secret['run'],'token':([] if cancel=='malformed' else secret['token'] if cancel=='valid' else 'wrong'),'proof':'VERIFIED_SANDBOX_ONLY'})
  r=result(root);assert r['status']==expected and r['hardware_actions']==0
  cases.append({'name':name,'expected':expected,'actual':r,'ready':ready,'effective_properties':properties,'pass':True})
 r={'pass':True,'scope':'new marker-only isolated systemd units','cases':cases,'production_service_changed':False,'hardware_restore_tested':False,'production_ready':False}
 (work/'systemd-results.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({'pass':True,'systemd_cases':len(cases)}))
def main():
 p=argparse.ArgumentParser();p.add_argument('--work',type=pathlib.Path);p.add_argument('--ssh-arm',type=pathlib.Path);a=p.parse_args()
 work=(a.ssh_arm or a.work).resolve()
 if not work.is_relative_to(pathlib.Path('/tmp')) or work.exists():raise ValueError('fresh /tmp workspace required')
 if a.ssh_arm:
  work.mkdir();root,_,_,_=arm(work,'ssh-exit',1.5)
  print('ARMED '+str(root),flush=True)
  # The client will terminate ONLY this SSH channel. Manager-owned unit survives.
  time.sleep(5)
 else:run(work)
if __name__=='__main__':main()
