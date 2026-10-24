#!/usr/bin/env python3
"""Build a private, standalone Linux file-only Event B tree. No install/service API."""
import argparse,pathlib,sys,subprocess,os,shutil,json,hashlib,platform
HERE=pathlib.Path(__file__).resolve().parent;ROOT=HERE.parent
sys.path.insert(0,str(ROOT/'experiments/event-offline'))
from prepare_core import prepare,FILES
p=argparse.ArgumentParser();p.add_argument('--sdk',type=pathlib.Path,required=True);p.add_argument('--output',type=pathlib.Path,required=True);a=p.parse_args()
if platform.system()!='Linux':p.error('Linux native build required; RP5 ext/tmpfs file guard retained')
if a.output.exists():p.error('output must be fresh')
a.output=a.output.absolute();a.output.mkdir(mode=0o700,parents=False)
for d in ('bin','share','config','runs','build'): (a.output/d).mkdir()
sdk=a.output/'build/sdk';prepare(a.sdk,sdk)
engine=ROOT/'experiments/event-engine';exe=a.output/'bin/event-b-engine';cmd=[os.getenv('CXX','g++'),'-std=c++20','-O2','-Wall','-Wextra','-Werror','-pthread','-DEVENT_FILE_ONLY','-I'+str(sdk/'include'),str(engine/'engine.cpp')]+[str(sdk/'src'/f) for f in FILES]+['-o',str(exe)]
subprocess.run(cmd,check=True)
shutil.copy2(HERE/'app.py',a.output/'bin/event-b');(a.output/'bin/event-b').chmod(0o700)
for n in ('index.html','viewer.js'):shutil.copy2(HERE/n,a.output/'share'/n)
shutil.copy2(HERE/'default.json',a.output/'config/default.json')
paths=[engine/n for n in ('engine.cpp','packet.hpp','regular_input.hpp')]+[ROOT/'experiments/event-offline/prepare_core.py']+[HERE/n for n in ('build.py','app.py','index.html','viewer.js','default.json')]
manifest={'package':'Event B file-only','platform':platform.platform(),'compiler':subprocess.check_output([cmd[0],'--version'],text=True).splitlines()[0],'build_command':cmd,'source_sha256':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths},'private_sdk_sha256':{f:hashlib.sha256((a.sdk/'src'/f).read_bytes()).hexdigest() for f in FILES},'binary_sha256':hashlib.sha256(exe.read_bytes()).hexdigest(),'phase_c':'HARD BLOCKED','live_backend_compiled':False}
(a.output/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n');print(json.dumps(manifest,indent=2))
