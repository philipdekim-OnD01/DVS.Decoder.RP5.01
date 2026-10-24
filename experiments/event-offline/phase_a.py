#!/usr/bin/env python3
"""Native regression gate; SDK/sample stay private. No device access."""
import argparse,hashlib,json,os,pathlib,platform,struct,subprocess,tempfile,time
from prepare_core import prepare,FILES
p=argparse.ArgumentParser();p.add_argument('sdk',type=pathlib.Path);p.add_argument('sample',type=pathlib.Path);p.add_argument('results',type=pathlib.Path);a=p.parse_args()
report={'host':platform.platform(),'compiler':subprocess.check_output([os.getenv('CXX','g++'),'--version'],text=True).splitlines()[0], 'sample_sha256':hashlib.sha256(a.sample.read_bytes()).hexdigest(),'tests':[]}
assert report['sample_sha256']=='962925dfaf87fcd1a16d04cd6e122d32558527b543f39acc2803926f2fc897b3'
def word(*b):return bytes(b)
def frame(f=0,ref=10,sub=1,cid=0,x=3):
    c=cid*2
    return b''.join((word(8+c,(ref>>16)&63,(ref>>8)&255,ref&255),word(8+c,128,sub>>8,sub&255),word(4+c,32|((f>>5)&7),((f&31)<<3)|(x>>8),x&255),word(128+c,2,0,1),word(12+c,(f>>5)&7,(f&31)<<3,0)))
with tempfile.TemporaryDirectory(prefix='rp5-gate-a-') as d:
    root=pathlib.Path(d);sdk=root/'sdk';prepare(a.sdk,sdk);exe=root/'replay'
    cmd=[os.getenv('CXX','g++'),'-std=c++20','-O2','-pthread','-DEVENT_EXTENDED','-I'+str(sdk/'include'),str(pathlib.Path(__file__).with_name('replay.cpp')),*[str(sdk/'src'/f) for f in FILES],'-o',str(exe)]
    subprocess.run(cmd,check=True);report['build_command']=cmd
    report['sdk_inputs_sha256']={str(f.relative_to(a.sdk)):hashlib.sha256(f.read_bytes()).hexdigest() for f in sorted(a.sdk.rglob('*')) if f.is_file() and (f.parent==a.sdk/'src' or f.parent==a.sdk/'include') and f.suffix in ('.cpp','.h')}
    def run(name,data=None,chunk=4093,gap=None):
        src=a.sample
        if data is not None:src=root/'input.bin';src.write_bytes(data)
        out=root/'out.bin';args=[str(exe),str(src),str(chunk),str(out)]
        if gap is not None:args.append(str(gap))
        r=json.loads(subprocess.check_output(args,text=True));r['name']=name;r['sha256']=hashlib.sha256(out.read_bytes()).hexdigest();report['tests'].append(r)
        return r,out.read_bytes()
    baseline=None
    for n in (1048576,4,4093,1,0):
        r,_=run('sample-'+('random-seed-20261021' if n==0 else str(n)),chunk=n)
        keys=('sha256','frames','events','invalid','unknown','frame_gaps','eof_partial_bytes','eof_incomplete_frames')
        if baseline:assert all(r[k]==baseline[k] for k in keys),r
        else:baseline=r;assert r['frames']==1557 and r['events']==1469217
    assert baseline['sha256']=='e15a8a75899f6352725e0a4fbcd73f537acd1496fda6ae8ac25cd17903be1798'
    r,b=run('frame-and-timestamp-wrap',frame(255,(1<<22)-1,900)+frame(0,0,100));assert r['frames']==2 and r['frame_gaps']==0 and struct.unpack_from('<I',b,22+8)[0]==200
    r,_=run('cid-separation',frame(cid=1)+frame());assert r['frames']==1 and r['cid1_events']==1 and r['events']==2
    for n in (1,2,3):
        r,_=run('truncated-word-'+str(n),frame()+b'\x08\x80\x01'[:n]);assert r['eof_partial_bytes']==n and r['frames']==1
    r,_=run('missing-frame-end',frame()[:-4]);assert r['frames']==0 and r['eof_incomplete_frames']==1
    r,_=run('invalid-x',frame(x=960));assert r['invalid']>=1 and r['events']==0
    r,_=run('invalid-y',frame()[:12]+word(129,106,0,1)+frame()[16:]);assert r['invalid']>=1 and r['events']==0
    r,_=run('invalid-sub',frame(sub=1000));assert r['invalid']>=1 and r['events']==0
    r,_=run('unknown-word',word(16,0,0,1)+frame());assert r['unknown']==1 and r['frames']==1
    r,_=run('malformed-frame-end',frame()[:-4]+word(12,0,0,1));assert r['invalid']==1 and r['frames']==0
    r,b=run('discontinuity-resync',frame()[:13]+word(128,2,0,1)+frame(2),chunk=7,gap=13);assert r['discontinuities']==1 and r['frames']==1 and r['unsynced_groups']==1 and r['events']==1
    report['pass']=True
report['completed_unix']=time.time();a.results.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({'pass':True,'tests':len(report['tests']),'frames':baseline['frames'],'events':baseline['events']}))
