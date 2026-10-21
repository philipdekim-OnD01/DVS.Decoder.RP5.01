#!/usr/bin/env python3
"""Build private SDK core in a temporary directory; never open sensor devices."""
import argparse, hashlib, json, pathlib, shutil, subprocess, tempfile
p=argparse.ArgumentParser(); p.add_argument('sdk',type=pathlib.Path); p.add_argument('sample',type=pathlib.Path); p.add_argument('--results',type=pathlib.Path,required=True)
a=p.parse_args(); rows=[]
with tempfile.TemporaryDirectory(prefix='dvs-offline-') as tmp:
    root=pathlib.Path(tmp); sdk=root/'sdk'; shutil.copytree(a.sdk,sdk,ignore=shutil.ignore_patterns('build','.git'))
    (sdk/'include/nrv_dvs/export.h').write_text('#pragma once\n#define NRV_DVS_API\n#define NRV_DVS_NO_EXPORT\n')
    source=sdk/'src/decoder.cpp'; original=source.read_text()
    needle='''    const auto *words = reinterpret_cast<const std::uint8_t *>(raw_.data());
    for (std::size_t i = 0; i + 4 <= raw_.size(); i += 4)
      Word(words + i);'''
    replacement='''    for (auto byte : raw_) {
      carry_[carry_size_++] = static_cast<std::uint8_t>(byte);
      if (carry_size_ == 4) { Word(carry_); carry_size_ = 0; }
    }'''
    if original.count(needle)!=1: raise RuntimeError('unexpected SDK decoder revision')
    h=sdk/'include/decoder.h'; header=h.read_text()
    if header.count('  Context cid_[2];')!=1: raise RuntimeError('unexpected SDK header revision')
    for patched in (False,True):
        source.write_text(original if not patched else original.replace(needle,replacement).replace('      ++work_.discontinuities;','      carry_size_ = 0;\n      ++work_.discontinuities;'))
        h.write_text(header if not patched else header.replace('  Context cid_[2];','  std::uint8_t carry_[4]{};\n  std::size_t carry_size_ = 0;\n  Context cid_[2];'))
        exe=root/('patched' if patched else 'original')
        files=[sdk/'src'/f for f in ('decoder.cpp','source.cpp','pipe.cpp','nrv_dvs/decoder.cpp','nrv_dvs/source.cpp','nrv_dvs/pipe.cpp')]
        subprocess.run(['clang++','-std=c++20','-O2','-pthread','-I'+str(sdk/'include'),str(pathlib.Path(__file__).with_name('replay.cpp')),*map(str,files),'-o',str(exe)],check=True)
        for chunk in ((1048576,4093) if not patched else (1048576,4093,4,1)):
            out=root/'frames.bin'
            result=subprocess.run([str(exe),str(a.sample.resolve()),str(chunk),str(out)],check=True,capture_output=True,text=True)
            row=json.loads(result.stdout); row.update(patched=patched,sha256=hashlib.sha256(out.read_bytes()).hexdigest()); rows.append(row)
    baseline=rows[0]['sha256']
    keys=('sha256','frames','events','invalid','unknown','frame_gaps')
    passed=rows[0]['frames']>0 and all(all(r[k]==rows[0][k] for k in keys) for r in rows if r['patched'])
    a.results.write_text(json.dumps({'sample_sha256':hashlib.sha256(a.sample.read_bytes()).hexdigest(),'split_invariance_pass':passed,'runs':rows},indent=2)+'\n')
    if not passed: raise RuntimeError('split invariance failed')
