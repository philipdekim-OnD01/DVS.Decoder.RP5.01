#!/usr/bin/env python3
"""Run only file acquisition/CLI guard checks against a provided built engine."""
import argparse,hashlib,json,os,pathlib,subprocess,tempfile
p=argparse.ArgumentParser();p.add_argument('engine',type=pathlib.Path);p.add_argument('sample',type=pathlib.Path);p.add_argument('--results',type=pathlib.Path,required=True);a=p.parse_args();engine=str(a.engine.resolve());cases=[]
with tempfile.TemporaryDirectory(prefix='rp5-engine-guards-') as d:
 root=pathlib.Path(d);fifo=root/'fifo';os.mkfifo(fifo);link=root/'link';link.symlink_to(a.sample.resolve())
 for name,source in (('fifo',fifo),('symlink',link),('directory',root),('kernel-virtual-file',pathlib.Path('/proc/version'))):
  r=subprocess.run([engine,'--file',str(source),str(root/('reject-'+name))],capture_output=True,text=True,timeout=5);assert r.returncode==1 and ('regular non-symlink' in r.stderr or 'kernel virtual files refused' in r.stderr),(name,r.stderr)
  cases.append({'name':name,'exit_code':r.returncode,'refused':True})
 out=root/'sample';subprocess.run([engine,'--file',str(a.sample.resolve()),str(out)],check=True,timeout=60)
 m=json.loads((out/'metrics.json').read_text());sha=hashlib.sha256((out/'frames.bin').read_bytes()).hexdigest();assert m['frames']==1557 and m['events']==1469217 and sha=='e15a8a75899f6352725e0a4fbcd73f537acd1496fda6ae8ac25cd17903be1798'
 for name,args in (('live',["--device","/dev/dvs-not-real","bus","8192","128",str(root/'live'),"10","--armed"]),('force',["--device","/dev/dvs-not-real","bus","8192","128",str(root/'live'),"10","--armed","--force"])):
  r=subprocess.run([engine,*args],capture_output=True,text=True,timeout=5);assert r.returncode==1 and not (root/'live').exists();cases.append({'name':name,'exit_code':r.returncode,'refused':True})
result={'pass':True,'sanitizers':'ASan/UBSan build','cases':cases,'sample_frames':m['frames'],'sample_events':m['events'],'sample_output_sha256':sha,'production_ready':False,'hardware_restore_tested':False,'private_outputs_retained_in_public_repo':False}
a.results.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'pass':True,'guards':len(cases),'frames':m['frames']}))
