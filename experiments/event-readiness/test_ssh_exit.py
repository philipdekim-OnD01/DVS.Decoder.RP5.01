#!/usr/bin/env python3
"""Close ONLY a newly created test SSH client; dedicated marker unit must survive."""
import argparse,json,pathlib,re,shlex,subprocess,time
HOST='philip@192.168.0.177'
SCRIPT='/tmp/dvs-readiness-20261022/readiness/systemd_sandbox_gate.py'
WORK='/tmp/dvs-watchdog-ssh-exit-20261022-v3'
def run(work):
 if not re.fullmatch(r'/tmp/dvs-watchdog-ssh-exit-[A-Za-z0-9-]+',work):raise ValueError('invalid fresh test path')
 remote=shlex.join(['python3',SCRIPT,'--ssh-arm',work])
 ssh=['ssh','-o','BatchMode=yes','-o','ConnectTimeout=5',HOST]
 p=subprocess.Popen(ssh+[remote],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
 try:
  line=p.stdout.readline().strip()
  if line!='ARMED '+work+'/ssh-exit':raise RuntimeError('isolated watchdog arm failed: '+line+' '+p.stderr.read())
  p.terminate();code=p.wait(timeout=3)
 except BaseException:
  if p.poll() is None:p.kill();p.wait(timeout=3)
  raise
 query='''import pathlib,json,time
root=pathlib.Path(__ROOT_LITERAL__)
absent=not (root/"result.json").exists()
end=time.monotonic()+5
while not (root/"result.json").exists() and time.monotonic()<end:time.sleep(.025)
print(json.dumps({"result_absent_after_client_exit":absent,"result":json.loads((root/"result.json").read_text()),"ready":json.loads((root/"ready.json").read_text()),"properties":(root/"properties.txt").read_text(),"query_session_cgroup":pathlib.Path("/proc/self/cgroup").read_text()}))
'''
 query=query.replace('__ROOT_LITERAL__',json.dumps(work+'/ssh-exit'))
 r=json.loads(subprocess.check_output(ssh+['python3 -c '+shlex.quote(query)],text=True,timeout=10))
 assert r['result_absent_after_client_exit'] and r['result']['status']=='FIRED_NOOP_ALERT' and r['result']['hardware_actions']==0
 assert 'rp5-dvs-rdy-' in r['ready']['cgroup'] and r['ready']['cgroup']!=r['query_session_cgroup']
 return dict(pass_=True,ssh_client_returncode=code,scope='one owned test SSH client terminated; separate manager unit writes NOOP marker',production_ready=False,hardware_restore_tested=False,network_outage_tested=False,**r)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--results',type=pathlib.Path,required=True);p.add_argument('--work',default=WORK);a=p.parse_args();r=run(a.work);a.results.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({'pass':r['pass_'],'ssh_client_returncode':r['ssh_client_returncode']}))
