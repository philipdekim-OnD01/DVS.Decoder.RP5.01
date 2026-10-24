#!/usr/bin/env python3
"""Small synthetic tests of new trace hooks/state evidence, not old full suites."""
import argparse,pathlib,struct,json,hashlib,subprocess,os,platform
p=argparse.ArgumentParser();p.add_argument('--work',type=pathlib.Path,required=True);p.add_argument('--results',type=pathlib.Path,required=True);a=p.parse_args()
def w(*v):return bytes(v)
g=w(132,10,1,2)
def frame(n,mo=False):return w(8,0,0,n)+w(8,128,0,0)+w(4,32+(128 if mo else 0),n*8,79)+g+w(12,0,n*8,0)
fixture=w(4,0,0,79)+g+bytes(8192)+w(12,0,0,0)+frame(1)+g+frame(2)+b'\x08\x00'
cases=[];hashes=[];tracehashes=[];unsynchashes=[]
def run(name,data,chunk):
 path=a.work/(name+'.bin');path.write_bytes(data);out=a.work/(name+'.frames');env=dict(os.environ,AB_TRACE_PREFIX=str(a.work/name))
 cmd=[str(a.work/'sdk-replay'),str(path),str(chunk),str(out)];r=json.loads(subprocess.check_output(cmd,env=env,text=True));events=(a.work/(name+'.events')).read_bytes();trace=list(struct.iter_unpack('<QHHBBxx',events));u=(a.work/(name+'.unsynced.csv')).read_text();return r,trace,u,hashlib.sha256(out.read_bytes()).hexdigest(),hashlib.sha256(events).hexdigest()
for chunk in (1,4,4093,1048576,0):
 name='synthetic-split-'+str(chunk);r,t,u,h,th=run(name,fixture,chunk)
 assert r['frames']==2 and r['events']==4 and r['on']==2 and r['off']==2 and r['unsynced_groups']==2 and r['eof_partial_bytes']==2 and r['invalid']==0 and r['unknown']==0
 assert {int(line.split(',')[0]) for line in u.splitlines()}=={4,8224}
 hashes.append(h);tracehashes.append(th);unsynchashes.append(hashlib.sha256(u.encode()).hexdigest());cases.append({'name':name,'pass':True,'input_sha256':hashlib.sha256(fixture).hexdigest(),'output_sha256':h,'trace_sha256':th,'stats':r})
assert len(set(hashes))==len(set(tracehashes))==len(set(unsynchashes))==1
r,t,u,h,th=run('synthetic-mo1',frame(1,True),3);assert {(v[2],v[3]) for v in t}=={(17,0),(8,1)} and r['events']==2
cases.append({'name':'synthetic-mo1-signed-group2','pass':True,'input_sha256':hashlib.sha256(frame(1,True)).hexdigest(),'trace_sha256':th,'expected_y_polarity':[[17,0],[8,1]]})
invalid=w(128,8,1,1)
r,t,u,h,th=run('synthetic-invalid-priority',invalid,1);assert r['invalid']==1 and r['unsynced_groups']==0 and not t
cases.append({'name':'synthetic-delta0-invalid-before-unsynced','pass':True,'input_sha256':hashlib.sha256(invalid).hexdigest(),'stats':r})
report={'host':platform.platform(),'cases':cases,'passed':len(cases),'full_sample_split_suite_rerun':False,'scope':'new observation hooks and small synthetic context/EOF cases; no new production parser change','hardware_actions':0,'phase_c':'HARD BLOCKED'}
a.results.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({'passed':len(cases)}))
