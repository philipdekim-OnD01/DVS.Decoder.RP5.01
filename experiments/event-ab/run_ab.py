#!/usr/bin/env python3
"""Run three actual parsers. Per-event traces are private; publish aggregates only."""
import argparse,pathlib,subprocess,os,json,hashlib,struct,itertools,platform
HERE=pathlib.Path(__file__).resolve().parent
p=argparse.ArgumentParser();p.add_argument('--work',type=pathlib.Path,required=True);p.add_argument('--sample',type=pathlib.Path,required=True);p.add_argument('--results',type=pathlib.Path,required=True);a=p.parse_args()
assert a.sample.is_file() and a.sample.stat().st_size==8388608
assert hashlib.sha256(a.sample.read_bytes()).hexdigest()=='962925dfaf87fcd1a16d04cd6e122d32558527b543f39acc2803926f2fc897b3'
results={}
for mode in ('reference','dual','sdk'):
 env=dict(os.environ,AB_TRACE_PREFIX=str(a.work/mode))
 cmd=[str(a.work/'legacy'),str(a.sample),mode] if mode!='sdk' else [str(a.work/'sdk-replay'),str(a.sample),'1048576',str(a.work/'frames.bin')]
 r=subprocess.run(cmd,env=env,capture_output=True,text=True,check=True);results[mode]=json.loads(r.stdout);results[mode]['event_trace_sha256']=hashlib.sha256((a.work/(mode+'.events')).read_bytes()).hexdigest()

def words(path):
 with path.open('rb') as f:
  for offset,group in itertools.groupby(iter(lambda:f.read(16),b''),key=lambda x:struct.unpack_from('<Q',x)[0]):
   yield offset,[(struct.unpack_from('<HHBB',x,8)) for x in group]

def compare(mode):
 old=iter(words(a.work/(mode+'.events')));new=iter(words(a.work/'sdk.events'));o=next(old,None);n=next(new,None);same=diff=0;first=None
 while o is not None or n is not None:
  offset=min(x[0] for x in (o,n) if x is not None);oe=o[1] if o and o[0]==offset else [];ne=n[1] if n and n[0]==offset else []
  if oe==ne:same+=1
  else:
   diff+=1
   if first is None:first={'byte_offset':offset,'word_index':offset//4,'legacy_events':oe[:16],'sdk_events':ne[:16],'legacy_count':len(oe),'sdk_count':len(ne)}
  if o and o[0]==offset:o=next(old,None)
  if n and n[0]==offset:n=next(new,None)
 return {'equal_event_words':same,'different_event_words':diff,'first_divergence':first,'tuple_order':'x,y,polarity(0ON/1OFF),CID; timestamp not comparable'}
report={'host':platform.platform(),'sample_sha256':hashlib.sha256(a.sample.read_bytes()).hexdigest(),'actual_parsers':results,'comparisons':{m:compare(m) for m in ('reference','dual')},'complete_output_sha256':hashlib.sha256((a.work/'frames.bin').read_bytes()).hexdigest(),'hardware_actions':0,'physical_correctness':'UNKNOWN'}
a.results.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
