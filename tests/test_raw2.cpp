#define main production_main
#include "raw2_producer.cpp"
#undef main
#include <random>
#include <cassert>

std::array<uint64_t,4> reference(const uint8_t *frame,int first,std::vector<uint8_t>& pixels) {
    std::array<uint64_t,4> counts{};
    for(int serial=0;serial<kSensorWidth;++serial) {
        int chunk=(first+serial)%kRaw2Chunks;
        int x=(serial/16)*16+(15-serial%16);
        for(int byte=0;byte<kBytesPerColumn;++byte)
            for(int p=0;p<4;++p) {
                size_t pos=(chunk*kBytesPerColumn+kEmbeddedSignatureOffset+byte)%kChangedBytes;
                uint8_t code=(frame[pos]>>(6-2*p))&3;
                ++counts[code];
                if(code==1 || code==2) pixels[(719-(byte*4+p))*960+x]=code;
            }
    }
    return counts;
}

int main() {
    std::mt19937 random(177);
    std::vector<uint8_t> raw(kChangedBytes+kBytesPerColumn), actual(kLogicalPixels), expected(kLogicalPixels);
    for(int start: {0,1,15,16,960,975}) {
        for(auto& byte:raw) byte=uint8_t(random());
        std::copy_n(raw.begin(),kBytesPerColumn,raw.begin()+kChangedBytes);
        for(size_t i=0;i<actual.size();++i) actual[i]=expected[i]=uint8_t(i%3);
        auto want=reference(raw.data(),start,expected);
        auto got=decode_raw2(raw.data(),start,actual);
        assert(got==want); assert(actual==expected);
    }
    std::fill(raw.begin(),raw.end(),0xFF);
    std::fill(actual.begin(),actual.end(),1);
    auto counts=decode_raw2(raw.data(),16,actual);
    assert(counts[3]==kLogicalPixels);
    for(auto pixel:actual) assert(pixel==1); // Invalid codes cannot erase valid events.
    // Reproduce observed embedded signatures at +176. No metadata may become pixels.
    std::fill(raw.begin(),raw.end(),0);
    std::fill(actual.begin(),actual.end(),0);
    int embedded_start=950;
    for(int column=0;column<16;++column)
        for(int byte=0;byte<180;++byte)
            raw[(embedded_start*180+176+column*180+byte)%kChangedBytes]=byte<4?0xCC:0x6B;
    std::copy_n(raw.begin(),kBytesPerColumn,raw.begin()+kChangedBytes);
    counts=decode_raw2(raw.data(),(embedded_start+16)%976,actual);
    assert(counts[0]==kLogicalPixels && counts[1]==0 && counts[2]==0 && counts[3]==0);
    for(auto pixel:actual) assert(pixel==0);
    for(auto& byte:raw) byte=random()%100<99 ? 0 : uint8_t(random());
    std::copy_n(raw.begin(),kBytesPerColumn,raw.begin()+kChangedBytes);
    auto bench=[&](auto fn) {
        auto begin=std::chrono::steady_clock::now();
        uint64_t sum=0;
        for(int i=0;i<200;++i) sum+=fn(raw.data(),16,actual)[0];
        auto us=std::chrono::duration<double,std::micro>(std::chrono::steady_clock::now()-begin).count()/200;
        std::cout<<us<<" us/frame; checksum "<<sum<<'\n';
    };
    std::cout<<"PASS: code counts, packet wrap, coordinate mapping, invalid preservation\nReference: "; bench(reference);
    std::cout<<"Optimized: "; bench(decode_raw2);
}
