#include "raw2_alignment_audit.hpp"
#include <vector>
#include <cstdint>
#include <cassert>
#include <cstdio>

void test_period(unsigned stride, unsigned n=25) {
    using raw2qa::EmbeddedAlignmentAudit;
    const unsigned columns=976;
    std::vector<std::uint8_t> bytes(n*columns*180, 0);
    for(unsigned pos=864;pos+16<n*columns;pos+=stride)
        for(unsigned j=0;j<16;++j)
            for(unsigned k=176;k<180;++k) bytes[(pos+j)*180+k]=0xCC;
    EmbeddedAlignmentAudit qa;
    for(unsigned i=0;i<n;++i) qa.observe_record(bytes.data()+i*columns*180,columns*180);
    qa.finalize();
    const auto &s=qa.stats();
    assert(s.starts>20);
    assert(s.invalid_run_length==0);
    assert(s.complete_runs==s.starts);
    assert(s.other_intervals==0);
    if(stride==971) {assert(s.intervals_971==s.starts-1);assert(s.intervals_976==0);}
    if(stride==976) {assert(s.intervals_976==s.starts-1);assert(s.intervals_971==0);}
}
int main() {
    test_period(971);test_period(976);
    raw2qa::EmbeddedAlignmentAudit q;
    std::vector<std::uint8_t> b(976*180,0);
    q.observe_record(b.data(),b.size());q.discontinuity();
    assert(q.stats().discontinuities==1);
    std::puts("PASS: RAW2 embedded signature run, period 971, period 976, record boundary, discontinuity");
}
