#include "source.h"
#include <nrv_dvs/decoder.h>
#include "v4l2_capture.hpp"
#include "regular_input.hpp"
#include <atomic>
#include <condition_variable>
#include <deque>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <thread>
#include <csignal>
#include <ctime>
#include <cstdlib>
#include <algorithm>
#include <bit>
using Clock=std::chrono::steady_clock;
static std::atomic<bool> interrupted{false};
static_assert(std::atomic<bool>::is_always_lock_free);
struct WordCounters {
 unsigned char carry[4]{};unsigned used=0;uint64_t ends=0,cid0_ends=0;
 void feed(const Packet& p){
  if(p.gap)used=0;
  for(auto byte:p.data){carry[used++]=static_cast<unsigned char>(byte);if(used!=4)continue;used=0;
   const auto* b=carry;
   if(!(b[0]&128)&&(b[0]&124)==12&&!(b[0]&1)&&!(b[1]&232)&&!(b[2]&7)&&!b[3]){++ends;if(!(b[0]&2))++cid0_ends;}
  }
 }
};
struct Queue {
 std::mutex mutex;std::condition_variable ready;std::deque<Packet> items;
 const size_t capacity;size_t high=0,drops=0;bool done=false,stop=false;std::string error;
 explicit Queue(size_t n):capacity(n){}
 bool push(Packet p,bool live){
  std::unique_lock lock(mutex);
  if(live&&items.size()==capacity){items.pop_front();++drops;if(!items.empty())items.front().gap=true;else p.gap=true;}
  ready.wait(lock,[&]{return stop||items.size()<capacity;});if(stop)return false;
  items.push_back(std::move(p));high=std::max(high,items.size());ready.notify_all();return true;
 }
};
class QueuedSource: public delta::Source {
 class Input:public Impl{
  Queue& q;
  std::error_code Produce(std::vector<std::byte>& data,bool& gap,Clock::time_point deadline)override{
   std::unique_lock lock(q.mutex);
   if(!q.ready.wait_until(lock,deadline,[&]{return q.stop||q.done||!q.items.empty();}))return std::make_error_code(std::errc::timed_out);
   if(q.items.empty())return std::make_error_code(std::errc::broken_pipe);
   auto p=std::move(q.items.front());q.items.pop_front();data=std::move(p.data);gap=p.gap;q.ready.notify_all();return {};
  }
 public:explicit Input(Queue& queue):q(queue){}
 };
public:explicit QueuedSource(Queue& queue){impl_=std::make_shared<Input>(queue);}
};
static void image(const std::filesystem::path& dir,const std::vector<unsigned char>& pixels){
 auto tmp=dir/"latest.ppm.tmp";std::ofstream out(tmp,std::ios::binary);out<<"P6\n960 720\n255\n";out.write(reinterpret_cast<const char*>(pixels.data()),pixels.size());out.close();if(!out)throw std::runtime_error("viewer write failed");std::filesystem::rename(tmp,dir/"latest.ppm");
}
int main(int argc,char**argv){
 try{
  // --file SAMPLE OUT [queue=8] [decode_delay_us=0], or --device PATH BUS W H OUT --armed
  bool live=argc>1&&std::string(argv[1])=="--device";
  if((!live&&(argc<4||argc>6||std::string(argv[1])!="--file"))||(live&&(argc!=9||std::string(argv[8])!="--armed")))throw std::runtime_error("usage: --file SAMPLE OUT [capacity] [delay_us] | --device PATH BUS W H OUT 10 --armed");
  if(live){throw std::runtime_error("PHASE_C_BLOCKED: file/mock only; live execution disabled");}
  if(live && (std::string(argv[7])!="10" || std::system("systemctl is-active --quiet dvs-raw2-production.service")!=768))throw std::runtime_error("live requires exactly 10s and production inactive (exit3)");
  std::filesystem::path dir=argv[live?6:3];if(!std::filesystem::create_directory(dir))throw std::runtime_error("output directory must not exist");
  size_t capacity=!live&&argc>=5?std::stoul(argv[4]):8;int delay=!live&&argc>=6?std::stoi(argv[5]):0;
  if(!capacity||capacity>32||delay<0||delay>1000000){throw std::runtime_error("queue/delay invalid");}
  Queue queue(capacity);
  std::signal(SIGINT,[](int){interrupted=1;});std::signal(SIGTERM,[](int){interrupted=1;});
  std::atomic<uint64_t> buffers{0},bytes{0},seq_gaps{0},buffer_errors{0};double max_requeue=0;unsigned stride=0,sizeimage=0;
  WordCounters word_counts;
  auto start=Clock::now();auto cpu_start=std::clock();
  std::thread capture([&]{try{
   std::ofstream log(dir/"buffers.csv");log<<"sequence,bytesused,requeue_us,error\n";
   unsigned previous=0;bool seen=false;
   if(live){
    V4L2Capture device(argv[2],argv[3],std::stoul(argv[4]),std::stoul(argv[5]));stride=device.stride;sizeimage=device.sizeimage;
    while(!interrupted&&Clock::now()-start<std::chrono::seconds(10)){
     {std::lock_guard lock(queue.mutex);if(queue.stop)break;}
     Packet p;if(!device.next(p))continue;
     if(seen&&p.sequence!=previous+1){++seq_gaps;throw std::runtime_error("V4L2 sequence gap: abort");}previous=p.sequence;seen=true;
     ++buffers;bytes+=p.data.size();buffer_errors+=p.driver_error;max_requeue=std::max(max_requeue,p.requeue_us);
     log<<p.sequence<<','<<p.data.size()<<','<<p.requeue_us<<','<<p.driver_error<<'\n';
     if(p.driver_error)throw std::runtime_error("V4L2 buffer error: abort");
     word_counts.feed(p);
     if(!queue.push(std::move(p),true))break;
    }
   }else{
    RegularInput file(argv[2]);
    while(!interrupted){Packet p;if(!file.next(p.data,4093))break;
     p.sequence=buffers++;bytes+=p.data.size();word_counts.feed(p);log<<p.sequence<<','<<p.data.size()<<",0,0\n";if(!queue.push(std::move(p),false))break;}

   }
   if(!log)throw std::runtime_error("buffer log write failed");
  }catch(const std::exception&e){std::lock_guard lock(queue.mutex);queue.error=e.what();}
  {std::lock_guard lock(queue.mutex);queue.done=true;}queue.ready.notify_all();});
  QueuedSource source(queue);delta::Decoder decoder(std::make_unique<delta::WaitPipe>(source,1));delta::WaitPipe output(decoder,1);
  std::vector<unsigned char> pixels(960*720*3);std::vector<std::byte> frame;bool gap;uint64_t frames=0;std::string error;
  try{
   std::ofstream decoded(dir/"frames.bin",std::ios::binary);
   if(!decoded)throw std::runtime_error("decoded file open failed");
   while(!interrupted){
    auto ec=output.Read(frame,gap,std::chrono::seconds(2));if(ec==std::errc::broken_pipe)break;if(ec)throw std::system_error(ec);
    if(live){auto health=decoder.Stats();if(health.invalid||health.unknown||health.frame_gaps)throw std::runtime_error("live decoder anomaly: abort");}
    if(delay)std::this_thread::sleep_for(std::chrono::microseconds(delay));
    delta::SensorFrame header{};if(frame.size()<sizeof(header))throw std::runtime_error("frame header truncated");std::memcpy(&header,frame.data(),sizeof(header));
    if(header.groups>(frame.size()-sizeof(header))/sizeof(delta::EventGroup)||frame.size()!=sizeof(header)+header.groups*sizeof(delta::EventGroup))throw std::runtime_error("frame bounds invalid");
    std::fill(pixels.begin(),pixels.end(),0);
    for(unsigned i=0;i<header.groups;++i){delta::EventGroup g{};std::memcpy(&g,frame.data()+sizeof(header)+i*sizeof(g),sizeof(g));
     if(g.x>=960||g.y>712||g.y%8||g.polarity>1)throw std::runtime_error("decoded coordinate invalid");
     for(unsigned k=0;k<8;++k)if(g.mask&(1<<k)){size_t at=((g.y+k)*960+g.x)*3;pixels[at+(g.polarity?0:1)]=255;}
    }
    decoded.write(reinterpret_cast<const char*>(frame.data()),frame.size());if(!decoded)throw std::runtime_error("decoded write failed");
    if(++frames%100==0)image(dir,pixels);
   }
   image(dir,pixels);
  }catch(const std::exception&e){error=e.what();}
  {std::lock_guard lock(queue.mutex);queue.stop=true;}queue.ready.notify_all();capture.join();
  if(error.empty())error=queue.error;
  double elapsed=std::chrono::duration<double>(Clock::now()-start).count();auto s=decoder.Stats();
  std::ofstream stats(dir/"metrics.json");
  stats<<"{\"mode\":\""<<(live?"v4l2":"file")<<"\",\"seconds\":"<<elapsed<<",\"input_buffers\":"<<buffers
   <<",\"bytes\":"<<bytes<<",\"buffers_per_second\":"<<buffers/elapsed<<",\"MB_per_second\":"<<bytes/elapsed/1e6
   <<",\"frames\":"<<frames<<",\"events\":"<<s.events<<",\"events_per_second\":"<<s.events/elapsed
   <<",\"cpu_percent\":"<<100.0*(std::clock()-cpu_start)/CLOCKS_PER_SEC/elapsed<<",\"queue_capacity\":"<<capacity
   <<",\"queue_high_water\":"<<queue.high<<",\"queue_drops\":"<<queue.drops<<",\"queue_final\":"<<queue.items.size()
   <<",\"sequence_gaps\":"<<seq_gaps<<",\"buffer_errors\":"<<buffer_errors<<",\"max_requeue_us\":"<<max_requeue
   <<",\"stride\":"<<stride<<",\"sizeimage\":"<<sizeimage<<",\"invalid\":"<<s.invalid<<",\"unknown\":"<<s.unknown
   <<",\"sensor_frame_end_words\":"<<word_counts.ends<<",\"sensor_frame_end_words_cid0\":"<<word_counts.cid0_ends
   <<",\"on_events\":"<<s.on<<",\"off_events\":"<<s.off<<",\"unsynced_groups\":"<<s.unsynced_groups
   <<",\"sensor_frame_gaps\":"<<s.frame_gaps<<",\"cid1_events\":"<<s.cid1_events<<",\"discontinuities\":"<<s.discontinuities
   <<",\"eof_partial_bytes\":"<<s.eof_partial_bytes<<",\"eof_incomplete_frames\":"<<s.eof_incomplete_frames
   <<",\"csi_fs\":null,\"csi_fe\":null,\"csi_crc\":null,\"csi_ecc\":null,\"error\":"<<(!error.empty()?"true":"false")<<",\"interrupted\":"<<(interrupted?"true":"false")<<"}\n";
  stats.close();if(!stats)throw std::runtime_error("metrics write failed");
  if(!error.empty()){throw std::runtime_error(error);}
  return interrupted?130:0;
 }catch(const std::exception&e){std::cerr<<e.what()<<'\n';return 1;}
}
