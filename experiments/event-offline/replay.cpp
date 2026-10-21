#include "source.h"
#include <nrv_dvs/decoder.h>
#include <fstream>
#include <iostream>
#include <algorithm>
#include <cstring>
class FileSource : public delta::Source {
  class Input : public Impl {
    std::ifstream file;
    size_t chunk;
    std::error_code Produce(std::vector<std::byte>& out, bool& gap,
      std::chrono::steady_clock::time_point) override {
      out.resize(chunk); file.read(reinterpret_cast<char*>(out.data()), chunk);
      out.resize(file.gcount()); gap=false;
      return out.empty() ? std::make_error_code(std::errc::broken_pipe) : std::error_code{};
    }
  public: Input(const char* path, size_t n):file(path,std::ios::binary),chunk(n) {
    if(!file) throw std::runtime_error("cannot open sample");
  }
  };
public: FileSource(const char* path,size_t n){impl_=std::make_shared<Input>(path,n);}
};
int main(int argc,char** argv) {
 try {
  if(argc!=4) throw std::runtime_error("usage: replay sample.bin chunk output.bin");
  size_t chunk=std::stoull(argv[2]);
  if(!chunk || chunk>16*1024*1024) throw std::runtime_error("invalid chunk");
  FileSource source(argv[1],chunk);
  delta::Decoder decoder(std::make_unique<delta::WaitPipe>(source,1));
  delta::WaitPipe output(decoder,1);
  std::ofstream file(argv[3],std::ios::binary);
  if(!file) throw std::runtime_error("cannot open output");
  std::vector<std::byte> data; bool gap; uint64_t count=0;
  while(true){
    auto ec=output.Read(data,gap,std::chrono::seconds(30));
    if(ec==std::errc::broken_pipe) break;
    if(ec) throw std::system_error(ec);
    file.write(reinterpret_cast<const char*>(data.data()),data.size()); ++count;
  }
  file.close(); if(!file) throw std::runtime_error("output write failed");
  auto s=decoder.Stats();
  std::cout<<"{\"chunk\":"<<chunk<<",\"frames\":"<<count<<",\"events\":"<<s.events
    <<",\"invalid\":"<<s.invalid<<",\"unknown\":"<<s.unknown
    <<",\"frame_gaps\":"<<s.frame_gaps<<",\"buffers\":"<<s.buffers<<"}\n";
 }catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}
}
