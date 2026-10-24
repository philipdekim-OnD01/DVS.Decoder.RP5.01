#!/usr/bin/env python3
"""Request/replay regression: temporary NOOP sandboxes only, no hardware API."""
import argparse,copy,hashlib,json,pathlib,platform,subprocess,sys,tempfile
import watchdog_worker as w

def main():
 parser=argparse.ArgumentParser();parser.add_argument('--results',type=pathlib.Path,required=True);args=parser.parse_args()
 cases=[]
 with tempfile.TemporaryDirectory(prefix='dvs-request-tests-') as tmp:
  root=pathlib.Path(tmp);w.init(root/'template',.2)
  valid=json.loads((root/'template'/'request.json').read_text())
  mutations=[('schema_bool','schema',True),('schema_float','schema',1.0),('run_null','run',None),('run_empty','run',''),('run_nonhex','run','z'*24),('hash_list','token_sha256',[]),('hash_short','token_sha256','a'*63),('timeout_bool','timeout',True),('timeout_string','timeout','1'),('timeout_null','timeout',None),('timeout_nan','timeout',float('nan')),('timeout_inf','timeout',float('inf')),('timeout_negative','timeout',-1),('timeout_long','timeout',11),('action_other','action','RESTORE')]
  for name,key,value in mutations:
   req=copy.deepcopy(valid);req[key]=value
   try:w.validate_request(req)
   except ValueError:cases.append({'case':name,'pass':True});continue
   raise AssertionError(name)
  for req in ([],None,{},dict(valid,extra=True)):
   try:w.validate_request(req)
   except ValueError:cases.append({'case':'shape_'+str(len(cases)),'pass':True});continue
   raise AssertionError('invalid shape accepted')
  worker=pathlib.Path(w.__file__).resolve()
  for name in ('ready.json','result.json'):
   sandbox=root/name.replace('.json','');w.init(sandbox,.2);(sandbox/name).write_text('{}')
   proc=subprocess.run([sys.executable,str(worker),'--worker',str(sandbox)],capture_output=True,text=True,timeout=3)
   assert proc.returncode!=0 and 'already used' in proc.stderr
   assert (sandbox/name).read_text()=='{}'
   if name!='result.json':assert not (sandbox/'result.json').exists()
   cases.append({'case':'reject_replay_'+name,'pass':True})
  sandbox=root/'fresh';w.init(sandbox,.2)
  subprocess.run([sys.executable,str(worker),'--worker',str(sandbox)],check=True,timeout=3)
  result=json.loads((sandbox/'result.json').read_text());assert result['status']=='FIRED_NOOP_ALERT' and result['hardware_actions']==0
  cases.append({'case':'fresh_expiry','pass':True,'elapsed':result['elapsed']})
 report={'host':platform.platform(),'source_sha256':hashlib.sha256(pathlib.Path(w.__file__).read_bytes()).hexdigest(),'cases':cases,'passed':len(cases),'production_ready':False,'hardware_actions':0,'scope':'local process and temp files only; not systemd or hardware recovery'}
 args.results.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({'passed':len(cases),'production_ready':False}))
if __name__=='__main__':main()
