#!/usr/bin/env python3
"""New negative/race tests; preserve earlier 17/22/24-case evidence."""
import argparse,ast,hashlib,json,os,pathlib,subprocess,sys,tempfile,time,threading
from bundle_startup import make_fixture,validate_bundle,startup,temp_workspace,canonical,digest
from watchdog_worker import init,atomic
HERE=pathlib.Path(__file__).resolve().parent

def run_tests():
 cases=[]
 def note(name,**actual):cases.append({'name':name,'pass':True,**actual})
 with tempfile.TemporaryDirectory(prefix='rp5-readiness-') as d:
  base=pathlib.Path(d);bundle=base/'bundle';pin=make_fixture(bundle)
  assert validate_bundle(bundle,pin)['production_ready'] is False;note('externally-pinned-synthetic-bundle')
  def mutate(name,edit):
   b=base/name;p=make_fixture(b);m=json.loads((b/'manifest.json').read_text());edit(b,m)
   return b,p,m
  def refused(b,p):
   try:validate_bundle(b,p)
   except (ValueError,OSError):return
   raise AssertionError('invalid bundle accepted')
  for role in ('rp1_override','sensor_module','dt_overlay','setfile'):
   b,p,_=mutate('tamper-'+role,lambda b,m:None);f=b/(role+'.fixture');f.chmod(0o644);f.write_bytes(b'tampered');refused(b,p);note('refuse-'+role+'-hash-drift')
  b,p,_=mutate('missing-setfile',lambda b,m:(b/'setfile.fixture').unlink());refused(b,p);note('refuse-missing-setfile')
  for name,payload in (('duplicate-register',b'3000 0x00\n'*12),('bad-register',b'not-a-register\n'),('oversized-value',b'3000 0x100\n')):
   b,p,m=mutate(name,lambda b,m:None);f=b/'saved_registers.fixture';f.chmod(0o644);f.write_bytes(payload);m['files']['saved_registers']['sha256']=digest(payload)
   raw=canonical(m);(b/'manifest.json').chmod(0o644);(b/'manifest.json').write_bytes(raw);refused(b,digest(raw));note('refuse-'+name)
  for name,edit in (('wrong-dt',lambda m:m['target'].update(receiver_dt=49)),('wrong-geometry',lambda m:m['target'].update(width=960)),('path-traversal',lambda m:m['files']['setfile'].update(path='../outside')),('legacy-command',lambda m:m.update(command='legacy-rollback')),('fake-live-proof',lambda m:m.update(register_evidence='LIVE_VERIFIED'))):
   b,p,m=mutate(name,lambda b,m:None);edit(m);raw=canonical(m);(b/'manifest.json').chmod(0o644);(b/'manifest.json').write_bytes(raw);refused(b,digest(raw));note('refuse-'+name)
  b,p,m=mutate('rewrite-manifest',lambda b,m:None);m['target']['receiver_dt']=49;(b/'manifest.json').chmod(0o644);(b/'manifest.json').write_bytes(canonical(m));refused(b,p);note('external-pin-defeats-self-signed-tamper')
  b,p,m=mutate('symlink',lambda b,m:None);f=b/'setfile.fixture';data=f.read_bytes();f.unlink();outside=base/'outside';outside.write_bytes(data);f.symlink_to(outside);refused(b,p);note('refuse-bundle-symlink')
  root=temp_workspace(base/'normal');r=startup(root,bundle,pin);assert r['status']=='VERIFIED_SANDBOX' and not r['production_ready'];note('isolated-startup-no-production-actions',actual=r)
  for stage in ('after-initial-check','before-receiver','after-sensor-profile','before-processes'):
   root=temp_workspace(base/('marker-'+stage))
   def hook(point):
    if point==stage:(root/'pending_first_boot_validation').write_text('fake-installer')
   r=startup(root,bundle,pin,hook);assert r['status']=='REFUSED' and r['legacy_invocations']==0;note('marker-flip-'+stage,actual=r)
  root=temp_workspace(base/'fake-success');(root/'journal.json').write_text(json.dumps({'status':'VERIFIED_SANDBOX','production_ready':True}));(root/'pending_first_boot_validation').write_text('conflict')
  r=startup(root,bundle,pin);assert r['status']=='REFUSED' and not r['production_ready'] and not r['effects'];note('fake-prior-success-cannot-skip-guards')
  root=temp_workspace(base/'concurrent-installer');event=threading.Event();done=threading.Event()
  def installer():event.wait(2);(root/'pending_first_boot_validation').write_text('mock-only');done.set()
  t=threading.Thread(target=installer);t.start()
  def race(stage):
   if stage=='before-sensor-profile':event.set();assert done.wait(2)
  r=startup(root,bundle,pin,race);t.join();assert r['status']=='REFUSED' and not r['legacy_invocations'];note('concurrent-installer-marker-refused')
  for _ in range(2):assert startup(root,bundle,pin)['status']=='REFUSED'
  note('service-restart-simulation-remains-refused')
  root=temp_workspace(base/'concurrent-start');held=threading.Event();release=threading.Event();first=[]
  def hold(stage):
   if stage=='after-initial-check':held.set();assert release.wait(2)
  t=threading.Thread(target=lambda:first.append(startup(root,bundle,pin,hold)));t.start();assert held.wait(2);assert startup(root,bundle,pin)['status']=='REFUSED';release.set();t.join();assert first[0]['status']=='VERIFIED_SANDBOX';note('concurrent-start-controller-lock')
  root=temp_workspace(base/'drift');b=base/'startup-drift';p=make_fixture(b)
  def drift(stage):
   if stage=='before-processes':f=b/'producer.fixture';f.chmod(0o644);f.write_bytes(b'drift')
  assert startup(root,b,p,drift)['status']=='REFUSED';note('startup-revalidates-files-before-effects')
  # Genuine independent OS processes, but not systemd or real SSH yet.
  for name,cancel,proof in (('expiry',False,False),('valid-cancel',True,True),('wrong-token',True,False),('malformed-token',True,False)):
   root=base/('watch-'+name);secret=init(root,.35);p=subprocess.Popen([sys.executable,str(HERE/'watchdog_worker.py'),'--worker',str(root)],start_new_session=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
   if cancel:atomic(root,'cancel.json',{'run':secret['run'],'token':([] if name=='malformed-token' else secret['token'] if proof else 'wrong'),'proof':'VERIFIED_SANDBOX_ONLY'})
   stdout,stderr=p.communicate(timeout=4);assert p.returncode==0,(stdout,stderr)
   result=json.loads((root/'result.json').read_text());expected='CANCELLED_SANDBOX' if proof else 'FIRED_NOOP_ALERT';assert result['status']==expected and result['hardware_actions']==0;note('process-watchdog-'+name,actual=result)
  root=base/'watch-term';secret=init(root,2);p=subprocess.Popen([sys.executable,str(HERE/'watchdog_worker.py'),'--worker',str(root)])
  end=time.monotonic()+2
  while not (root/'ready.json').exists() and time.monotonic()<end:time.sleep(.01)
  p.terminate();assert p.wait(timeout=3)==0;assert json.loads((root/'result.json').read_text())['status']=='TERMINATED_NOOP_ALERT';note('watchdog-signal-alert-without-fallback')
  root=base/'watch-lock';init(root,.5);p=subprocess.Popen([sys.executable,str(HERE/'watchdog_worker.py'),'--worker',str(root)])
  end=time.monotonic()+2
  while not (root/'ready.json').exists() and time.monotonic()<end:time.sleep(.01)
  other=subprocess.run([sys.executable,str(HERE/'watchdog_worker.py'),'--worker',str(root)],capture_output=True,timeout=2);assert other.returncode==3;p.wait(timeout=3);note('watchdog-lock-contention')
  for source in ('bundle_startup.py','watchdog_worker.py','../event-restore/restore_current_raw2.py'):
   tree=ast.parse((HERE/source).read_text());imports=[]
   for node in ast.walk(tree):
    if isinstance(node,ast.Import):imports.extend(n.name.split('.')[0] for n in node.names)
    if isinstance(node,ast.ImportFrom):imports.append((node.module or '').split('.')[0])
    if isinstance(node,ast.Call) and isinstance(node.func,ast.Name):assert node.func.id not in ('eval','exec','compile','__import__')
    if isinstance(node,ast.Call) and isinstance(node.func,ast.Attribute):assert node.func.attr not in ('system','popen','execv','execve','spawnv')
   assert not set(imports)&{'subprocess','socket','ctypes'}
  note('startup-and-watchdog-no-command-network-or-live-backend')
 return {'pass':True,'scope':'new non-production readiness tests','case_count':len(cases),'cases':cases,'hardware_restore_tested':False,'production_ready':False,'source_sha256':{name:digest((HERE/name).read_bytes()) for name in ('bundle_startup.py','watchdog_worker.py','test_readiness.py')}}
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--results',type=pathlib.Path,required=True);a=p.parse_args();r=run_tests();a.results.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({'pass':True,'case_count':r['case_count']}))
