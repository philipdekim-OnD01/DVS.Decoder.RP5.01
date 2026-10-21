"""Apply narrow, checked experiment-only changes to a private SDK copy."""
import pathlib, shutil
FILES=('decoder.cpp','source.cpp','pipe.cpp','nrv_dvs/decoder.cpp','nrv_dvs/source.cpp','nrv_dvs/pipe.cpp')
def replace_once(text,old,new):
    if text.count(old)!=1: raise RuntimeError('SDK patch anchor mismatch: '+old[:65])
    return text.replace(old,new)
def prepare(original,dest):
    shutil.copytree(original/'include',dest/'include')
    for name in FILES:
        target=dest/'src'/name; target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(original/'src'/name,target)
    (dest/'include/nrv_dvs/export.h').write_text('#pragma once\n#define NRV_DVS_API\n#define NRV_DVS_NO_EXPORT\n')
    p=dest/'include/decoder.h'; s=p.read_text(); s=replace_once(s,'  Context cid_[2];','  std::uint8_t carry_[4]{};\n  std::size_t carry_size_ = 0;\n  Context cid_[2];'); p.write_text(s)
    p=dest/'include/nrv_dvs/decoder.h'; s=p.read_text(); s=replace_once(s,'  std::uint64_t buffers = 0;', '  std::uint64_t eof_partial_bytes = 0, eof_incomplete_frames = 0;\n  std::uint64_t buffers = 0;'); p.write_text(s)
    p=dest/'src/decoder.cpp'; s=p.read_text()
    s=replace_once(s,'      return ec;','''    {
      if (ec == std::errc::broken_pipe) {
        work_.eof_partial_bytes += carry_size_;
        work_.eof_incomplete_frames += building_ ? 1 : 0;
        carry_size_ = 0; building_ = false;
        std::lock_guard lock(stats_mutex_); stats_ = work_;
      }
      return ec;
    }''')
    s=replace_once(s,'      ++work_.discontinuities;','      carry_size_ = 0;\n      ++work_.discontinuities;')
    s=replace_once(s,'''    const auto *words = reinterpret_cast<const std::uint8_t *>(raw_.data());
    for (std::size_t i = 0; i + 4 <= raw_.size(); i += 4)
      Word(words + i);''','''    for (auto byte : raw_) {
      carry_[carry_size_++] = static_cast<std::uint8_t>(byte);
      if (carry_size_ == 4) { Word(carry_); carry_size_ = 0; }
    }''')
    p.write_text(s)
