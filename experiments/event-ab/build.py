#!/usr/bin/env python3
"""Compile private sources outside Git, with narrow observation-only SDK hooks."""
import argparse,pathlib,sys,subprocess,shutil,json,hashlib
HERE=pathlib.Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'event-offline'))
from prepare_core import prepare,replace_once
p=argparse.ArgumentParser();p.add_argument('--sdk',type=pathlib.Path,required=True);p.add_argument('--legacy',type=pathlib.Path,required=True);p.add_argument('--work',type=pathlib.Path,required=True);a=p.parse_args()
a.work.mkdir(parents=True,exist_ok=True);copy=a.work/'sdk';prepare(a.sdk,copy)
src=copy/'src/decoder.cpp';s=src.read_text();s='#include "trace.hpp"\n'+s
s=replace_once(s,'void Decoder::Impl::Word(const std::uint8_t *b) noexcept {','void Decoder::Impl::Word(const std::uint8_t *b) noexcept {\n  ab::begin(b); ab::Guard observation(work_.unsynced_groups);')
s=replace_once(s,'  Context &s = cid_[cid];','  Context &s = cid_[cid];\n  ab::context(s.x,s.mo,s.ref_ok,s.sub_ok,s.epoch_ready,s.ref);')
s=replace_once(s,'      work_.events += n;','      work_.events += n;\n      ab::event(cid,s.x,groups[k]*8,masks[k],polarity[k]);')
src.write_text(s)
# Initialize recorder before constructing threaded SDK components.
replay=(HERE.parent/'event-offline/replay.cpp').read_text().replace('#include "source.h"','#include "trace.hpp"\n#include "source.h"').replace(' try {',' try {\n  ab::start();')
(a.work/'replay.cpp').write_text(replay)
common=['clang++','-std=c++20','-O2','-pthread','-I'+str(HERE)]
commands=[common+['-I'+str(a.legacy),str(HERE/'legacy_replay.cpp'),str(a.legacy/'s5krc1s_decoder.cpp'),'-o',str(a.work/'legacy')],common+['-DEVENT_EXTENDED','-I'+str(copy/'include'),str(a.work/'replay.cpp')]+[str(copy/'src'/x) for x in ('decoder.cpp','source.cpp','pipe.cpp','nrv_dvs/decoder.cpp','nrv_dvs/source.cpp','nrv_dvs/pipe.cpp')]+['-o',str(a.work/'sdk-replay')]]
for c in commands:subprocess.run(c,check=True)
print(json.dumps({'built':True,'compiler':subprocess.check_output(['clang++','--version'],text=True).splitlines()[0],'commands':commands,'private_copy_decoder_sha256':hashlib.sha256(src.read_bytes()).hexdigest()}))
