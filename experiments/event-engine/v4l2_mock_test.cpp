// All six OS entry points are replaced before the adapter is compiled here.
#include <linux/videodev2.h>
#include <sys/ioctl.h>
#include <sys/mman.h>
#include <poll.h>
#include <fcntl.h>
#include <unistd.h>
#include <cassert>
#include <cstring>
#include <cerrno>
#include <string>
#include <vector>
#include <iostream>
struct Fake {
 std::string fault;int opened=0,closed=0,mapped=0,stream_on=0,stream_off=0,qbuf=0,dqbuf=0,poll_calls=0,mmap_calls=0;
};
static Fake fake;
static int mock_open(const char* path,int){assert(std::string(path)=="mock://camera");++fake.opened;return 99;}
static int mock_close(int fd){assert(fd==99);++fake.closed;return 0;}
static void* mock_mmap(void*,size_t n,int,int,int fd,off_t){assert(fd==99);++fake.mmap_calls;if(fake.fault=="mmap"||(fake.fault=="mmap-second"&&fake.mmap_calls==2)){errno=ENOMEM;return MAP_FAILED;}++fake.mapped;auto* memory=new unsigned char[n]{};memory[0]=1;memory[1]=2;memory[2]=3;memory[3]=4;return memory;}
static int mock_munmap(void* p,size_t){--fake.mapped;delete[] static_cast<unsigned char*>(p);return 0;}
static int mock_poll(pollfd* p,nfds_t,int){++fake.poll_calls;if(fake.fault=="poll-eintr"&&fake.poll_calls==1){errno=EINTR;return -1;}if(fake.fault=="poll-timeout")return 0;p->revents=fake.fault=="poll-error"?POLLERR:POLLIN;return 1;}
static int mock_ioctl(int fd,unsigned long op,void* ptr){
 assert(fd==99);
 if(op==VIDIOC_QUERYCAP){auto& c=*static_cast<v4l2_capability*>(ptr);strcpy(reinterpret_cast<char*>(c.driver),"rp1-cfe");strcpy(reinterpret_cast<char*>(c.card),"rp1-cfe-csi2_ch0");strcpy(reinterpret_cast<char*>(c.bus_info),fake.fault=="identity"?"wrong":"mock-bus");c.capabilities=V4L2_CAP_DEVICE_CAPS;c.device_caps=V4L2_CAP_VIDEO_CAPTURE|V4L2_CAP_STREAMING;if(fake.fault=="capability")c.device_caps=0;if(fake.fault=="unterminated")memset(c.driver,88,sizeof(c.driver));}
 else if(op==VIDIOC_S_FMT){auto& p=static_cast<v4l2_format*>(ptr)->fmt.pix;p.bytesperline=16;p.sizeimage=32;if(fake.fault=="format")p.pixelformat=V4L2_PIX_FMT_YUYV;if(fake.fault=="stride")p.bytesperline=8;}
 else if(op==VIDIOC_REQBUFS){static_cast<v4l2_requestbuffers*>(ptr)->count=fake.fault=="count"?1:2;}
 else if(op==VIDIOC_QUERYBUF){auto& b=*static_cast<v4l2_buffer*>(ptr);b.length=fake.fault=="map-size"?16:32;b.m.offset=b.index*32;}
 else if(op==VIDIOC_QBUF){++fake.qbuf;if(fake.fault=="setup-qbuf"&&fake.qbuf==2){errno=EIO;return -1;}if(fake.fault=="requeue"&&fake.dqbuf){errno=EIO;return -1;}}
 else if(op==VIDIOC_STREAMON){++fake.stream_on;if(fake.fault=="streamon"){errno=EIO;return -1;}}
 else if(op==VIDIOC_STREAMOFF){++fake.stream_off;}
 else if(op==VIDIOC_DQBUF){++fake.dqbuf;if(fake.fault=="dq-eintr"&&fake.dqbuf==1){errno=EINTR;return -1;}if(fake.fault=="again"){errno=EAGAIN;return -1;}auto& b=*static_cast<v4l2_buffer*>(ptr);b.index=fake.fault=="index"?5:0;b.bytesused=fake.fault=="bytesused"?33:(fake.fault=="empty"?0:4);b.sequence=7;b.flags=fake.fault=="driver-error"?V4L2_BUF_FLAG_ERROR:0;}
 else assert(false);
 return 0;
}
#define open mock_open
#define close mock_close
#define mmap mock_mmap
#define munmap mock_munmap
#define poll mock_poll
#define ioctl mock_ioctl
#include "v4l2_capture.hpp"
#undef open
#undef close
#undef mmap
#undef munmap
#undef poll
#undef ioctl
int main(){
 int tests=0;
 for(const std::string fault:{"","identity","format","stride","count","map-size","mmap","streamon","poll-timeout","poll-error","again","index","bytesused","requeue","driver-error","capability","unterminated","mmap-second","setup-qbuf","empty","poll-eintr","dq-eintr"}){
  fake=Fake{};fake.fault=fault;bool failed=false;
  try{V4L2Capture capture("mock://camera","mock-bus",16,2);Packet packet;bool got=capture.next(packet);
   if(fault=="poll-timeout"||fault=="again"){assert(!got);}else{assert(got&&packet.sequence==7&&packet.data.size()==4);assert(packet.data[0]==std::byte{1}&&packet.data[3]==std::byte{4});assert(packet.driver_error==(fault=="driver-error"));assert(packet.gap==packet.driver_error);assert(fake.qbuf==3);}
  }catch(const std::exception&){failed=true;}
  bool expect=fault!=""&&fault!="poll-timeout"&&fault!="again"&&fault!="driver-error"&&fault!="poll-eintr"&&fault!="dq-eintr";
  assert(failed==expect);assert(fake.opened==1&&fake.closed==1&&fake.mapped==0);
  if(fake.stream_on&&fault!="streamon")assert(fake.stream_off==1);
  if(fault=="identity")assert(fake.qbuf==0&&fake.stream_on==0);
  ++tests;
 }
 std::cout<<"{\"adapter_mock_cases\":"<<tests<<",\"pass\":true,\"real_device_opens\":0}\n";
}
