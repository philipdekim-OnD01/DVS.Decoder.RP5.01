#pragma once
// Observation-only bridge. Private raw/event output stays outside the repository.
#include <cstdint>
#include <fstream>
#include <cstdlib>
#include <stdexcept>
namespace ab {
inline std::ofstream events,unsynced;
inline std::uint64_t offset=0,current=0;
inline int x=-1,mo=0,ref_ok=0,sub_ok=0,epoch=0;
inline unsigned cid=0,ref=0;
inline void start(){const char* p=std::getenv("AB_TRACE_PREFIX");if(!p)throw std::runtime_error("AB_TRACE_PREFIX required");events.open(std::string(p)+".events",std::ios::binary);unsynced.open(std::string(p)+".unsynced.csv");if(!events||!unsynced)throw std::runtime_error("trace open");}
inline void begin(const std::uint8_t* b){current=offset;offset+=4;cid=(b[0]>>1)&1;x=-1;mo=ref_ok=sub_ok=epoch=0;ref=0;}
inline void context(int a,int b,int c,int d,int e,unsigned f){x=a;mo=b;ref_ok=c;sub_ok=d;epoch=e;ref=f;}
inline void event(unsigned c,unsigned a,unsigned y,unsigned mask,unsigned pol){for(unsigned bit=0;bit<8;++bit)if(mask&(1u<<bit)){std::uint64_t o=current;std::uint16_t xy[2]={static_cast<std::uint16_t>(a),static_cast<std::uint16_t>(y+bit)};std::uint8_t pc[4]={static_cast<std::uint8_t>(pol),static_cast<std::uint8_t>(c),0,0};events.write(reinterpret_cast<char*>(&o),8);events.write(reinterpret_cast<char*>(xy),4);events.write(reinterpret_cast<char*>(pc),4);}}
struct Guard{std::uint64_t &u;std::uint64_t before;explicit Guard(std::uint64_t&v):u(v),before(v){}~Guard(){if(u!=before)unsynced<<current<<','<<cid<<','<<x<<','<<ref_ok<<','<<sub_ok<<','<<epoch<<'\n';}};
}
