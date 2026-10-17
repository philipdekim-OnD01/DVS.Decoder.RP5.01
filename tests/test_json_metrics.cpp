// Compile production metrics writer in its own TU and validate JSON using
// Python json.load in build_and_test.sh. Does not open /dev/video0.
#define main producer_entry_renamed_for_json_smoke_test
#include "raw2_producer.cpp"
#undef main
int main(int argc,char**argv) {
    if (argc!=2) return 2;
    raw2shadow::BoundaryStreamObserver s;
    s.enable_trace(true);
    std::array<bool,976> a{};
    for(int i=0;i<11;++i)a[i]=true;
    for(int i=966;i<976;++i)a[i]=true;
    s.observe_flags(a,true);
    raw2qa::EmbeddedAlignmentAudit qa;
    write_metrics(argv[1],1234.,12.,59.,60.,123456.,
                  9,123, 1,2,3, 4,5,6,7,
                  8,9, 10,11, 12,13, 14,qa.stats(),false,s.stats(),true,true);
    return 0;
}
