#include "boundary_live_shadow.hpp"
#include <array>
#include <cassert>
#include <cstddef>
#include <iostream>
using raw2shadow::BoundaryStreamObserver;
int main(){
    // Two exact 971-column Embedded-start periods, marker 16 and data 955.
    BoundaryStreamObserver s;
    for(int rec=0;rec<4;++rec){
        std::array<bool,976> flags{};
        for(std::size_t c=0;c<976;++c){
            const std::size_t pos=std::size_t(rec)*976+c;
            flags[c]=(pos>=970 && (pos-970)%971<16);
        }
        s.observe_flags(flags,rec==2);
    }
    const auto &st=s.stats();
    assert(st.host_records==4 && st.legacy_rejected==1);
    assert(st.embedded_runs_16==4 && st.intervals_971==3);
    assert(st.interval_hist[971]==3 && st.interval_gt_4096==0);
    assert(st.verified_frames==3 && st.frames_955==3 && st.frames_960==0);
    // Verify a marker runs across a host boundary without circular joining.
    BoundaryStreamObserver t;
    std::array<bool,976> a{},b{};
    for(int i=968;i<976;++i) a[i]=true;
    for(int i=0;i<8;++i) b[i]=true;
    t.observe_flags(a,true);
    t.observe_flags(b,true);
    assert(t.stats().embedded_runs_16==1 && t.stats().embedded_runs_bad==0);
    t.discontinuity();
    assert(t.stats().discontinuities==1);
    // After a sequence gap, marker pairs cannot be falsely bridged.
    std::array<bool,976> c{};
    for(int i=20;i<36;++i)c[i]=true;
    t.observe_flags(c,false);
    assert(t.stats().verified_frames==0);
    // Non-971/976 gap case, verify histogram without modifying data.
    BoundaryStreamObserver u;
    for (int r=0;r<3;++r) {
        std::array<bool,976> flags{};
        for(int i=0;i<976;++i) {
            const std::size_t pos=std::size_t(r)*976+i;
            flags[i] = (pos>=20 && pos<36) || (pos>=1010 && pos<1026) ||
                       (pos>=2020 && pos<2036);
        }
        u.observe_flags(flags,false);
    }
    assert(u.stats().intervals_other==2);
    assert(u.stats().interval_hist[990]==1);
    assert(u.stats().interval_hist[1010]==1);
    std::cout<<"PASS: histogram other intervals, 971/955, boundary split, no coordinate changes\n";
}
