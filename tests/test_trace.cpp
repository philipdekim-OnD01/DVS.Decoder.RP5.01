#include "boundary_live_shadow.hpp"
#include <array>
#include <cassert>
#include <cstdint>
#include <iostream>
using raw2shadow::BoundaryStreamObserver;
using raw2shadow::kTraceCapacity;
using raw2shadow::kHostColumns;

int main() {
    // Synthetic 971 -> 966 -> 971 starts, across host 976-col record edges.
    BoundaryStreamObserver t;
    t.enable_trace(true);
    const std::uint64_t starts[]={100,1071,2037,3008};
    for(std::uint64_t rec=0;rec<5;++rec) {
        std::array<bool,kHostColumns> f{};
        for(std::size_t i=0;i<f.size();++i) {
            std::uint64_t p=rec*kHostColumns+i;
            for(auto s:starts) if (p>=s && p<s+16)f[i]=true;
        }
        t.observe_flags(f,false);
    }
    const auto& s=t.stats();
    assert(s.intervals_971==2);
    assert(s.interval_hist[966]==1 && s.intervals_other==1);
    assert(s.trace_spacing_seen==1 && s.trace_saved>=2);
    bool seen966=false;
    for(std::uint64_t i=0;i<s.trace_saved;++i) {
        const auto& r=s.trace[i % kTraceCapacity];
        if(r.kind=='S' && r.spacing==966) {
            seen966=true;
            assert(r.delta_from_971==-5);
            assert(r.marker_start_record==2 && r.marker_start_offset==85);
            assert(r.previous_marker_record==1 && r.previous_marker_offset==95);
            assert(r.marker_length==16);
        }
    }
    assert(seen966);

    // Two independent marker fragments within ONE host buffer must not be
    // circularly joined to a fabricated 21-column Embedded marker.
    BoundaryStreamObserver wrap;
    wrap.enable_trace(true);
    std::array<bool,kHostColumns> w{};
    for(int j=0;j<11;++j)w[j]=true;
    for(int j=966;j<976;++j)w[j]=true;
    wrap.observe_flags(w,true);
    const auto& sw=wrap.stats();
    assert(sw.legacy_reject_wrap21==1);
    assert(sw.embedded_runs_bad==1);
    assert(sw.bad_run_hist[11]==1);
    assert(sw.trace_saved>=2);
    bool had_wrap=false, had_bad11=false;
    for(std::uint64_t i=0;i<sw.trace_saved;++i){
        const auto& r=sw.trace[i % kTraceCapacity];
        if(r.kind=='R' && r.head_run==11 && r.tail_run==10)had_wrap=true;
        if(r.kind=='B' && r.marker_length==11 && r.marker_start_offset==0)had_bad11=true;
    }
    assert(had_wrap && had_bad11);

    // A 16-column marker split across two host buffers remains one marker.
    BoundaryStreamObserver split;
    split.enable_trace(true);
    std::array<bool,kHostColumns> a{},b{};
    for(int j=970;j<976;++j)a[j]=true;
    for(int j=0;j<10;++j)b[j]=true;
    split.observe_flags(a,true);
    split.observe_flags(b,false);
    assert(split.stats().embedded_runs_16==1);
    assert(split.stats().good_runs_cross_host==1);
    assert(split.stats().embedded_runs_bad==0);

    // No false spacing over V4L2 discontinuity.
    split.discontinuity();
    std::array<bool,kHostColumns> c{};
    for(int j=100;j<116;++j)c[j]=true;
    split.observe_flags(c,false);
    assert(split.stats().verified_frames==0);

    // Ring is fixed-size and never grows with time.
    BoundaryStreamObserver ring;
    ring.enable_trace(true);
    for(std::size_t rec=0;rec<300;++rec) {
        std::array<bool,kHostColumns> f{};
        for(int j=100;j<111;++j)f[j]=true; // bad length 11
        ring.observe_flags(f,false);
    }
    assert(ring.stats().trace_saved==300);
    assert(ring.stats().trace.size()==kTraceCapacity);
    assert(ring.stats().trace[(300-1)%kTraceCapacity].id==300);
    std::cout << "PASS: 966/-5 samples; rejected wrap 11+10; split markers; discontinuity; bounded 128-row ring\n";
}
