#include "raw2_wrap21.hpp"
#include <algorithm>
#include <array>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <iostream>
#include <vector>
constexpr int N=976, B=180;
using Flags=std::array<bool,N>;
static bool looks(const unsigned char* p){
    if(p[176]!=0xcc || p[177]!=0xcc ||p[178]!=0xcc ||p[179]!=0xcc) return false;
    std::array<uint32_t,45> vals{};std::size_t unique=0;
    for(int i=0;i<45;i++){
        uint32_t v;std::memcpy(&v,p+i*4,4);
        bool seen=false;
        for(std::size_t j=0;j<unique;j++)seen|=(vals[j]==v);
        if(!seen)vals[unique++]=v;
    }
    return unique<=20;
}
static std::pair<int,int> old_find(const Flags& flags){
    int start=-1,len=0;
    for(int i=0;i<N;i++){
        if(!flags[i]||flags[(i+N-1)%N])continue;
        int n=0;
        while(n<N&&flags[(i+n)%N])++n;
        if(n>len){start=i;len=n;}
    }
    return {start,len};
}
static uint32_t le32(const unsigned char*p){return (uint32_t)p[0]|((uint32_t)p[1]<<8)|((uint32_t)p[2]<<16)|((uint32_t)p[3]<<24);}
int main(int argc,char**argv){
    if(argc==2&&std::strcmp(argv[1],"--synthetic")==0){
        for(int head=5;head<=16;head++){
            Flags f{};
            for(int i=0;i<head;i++)f[i]=true;
            for(int i=N-(21-head);i<N;i++)f[i]=true;
            auto [start,len]=old_find(f);
            if(len!=21||raw2wrap21::recover_first_pixel(f,start,len)!=head) return 1;
            f[N/2]=true;
            if(raw2wrap21::recover_first_pixel(f,start,len)>=0)return 2;
        }
        Flags valid{}; for(int i=100;i<116;i++)valid[i]=true;
        auto [start,len]=old_find(valid);
        if(len!=16||raw2wrap21::recover_first_pixel(valid,start,len)!=-1)return 3;
        std::cout<<"SYNTHETIC_PASS cases=13\n";return 0;
    }
    unsigned char global[32];
    if(std::fread(global,1,32,stdin)!=32||std::memcmp(global,"DVSRAW01",8)!=0){std::cerr<<"bad file";return 2;}
    const uint32_t payload=le32(global+16), records=le32(global+24);
    if(payload!=N*B){std::cerr<<"wrong length";return 2;}
    std::vector<unsigned char>data(payload);
    std::uint64_t legacy_rejected=0,recovered=0,remaining=0,original_accepted=0,changed_valid=0,seq_gaps=0;
    uint32_t prev=0;
    for(uint32_t rec=0;rec<records;rec++){
        unsigned char hdr[32];
        if(std::fread(hdr,1,32,stdin)!=32||std::fread(data.data(),1,payload,stdin)!=payload){std::cerr<<"truncated at "<<rec;return 2;}
        const uint32_t seq=le32(hdr+16);
        if(rec&&seq!=prev+1)seq_gaps++;
        prev=seq;
        Flags f{};
        for(int i=0;i<N;i++)f[i]=looks(data.data()+i*B);
        auto [start,len]=old_find(f);
        if(start>=0&&len==16){original_accepted++;if(raw2wrap21::recover_first_pixel(f,start,len)!=-1)changed_valid++;}
        else {legacy_rejected++;if(raw2wrap21::recover_first_pixel(f,start,len)>=0)recovered++;else remaining++;}
    }
    std::cout<<"records="<<records<<" legacy_rejected="<<legacy_rejected
      <<" wrap21_recovered="<<recovered<<" remaining_rejected="<<remaining
      <<" original_accepted_unchanged="<<original_accepted
      <<" changed_valid="<<changed_valid<<" seq_gaps="<<seq_gaps<<"\n";
    if(records==16140)
        return legacy_rejected==200&&recovered==200&&remaining==0&&changed_valid==0&&seq_gaps==0?0:1;
    return changed_valid==0&&seq_gaps==0?0:1;
}
