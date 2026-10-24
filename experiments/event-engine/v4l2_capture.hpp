#pragma once
#include <linux/videodev2.h>
#include <sys/ioctl.h>
#include <sys/mman.h>
#include <poll.h>
#include <fcntl.h>
#include <unistd.h>
#include <cerrno>
#include <cstring>
#include <stdexcept>
#include <string>
#include <vector>
#include <cstddef>
#include <chrono>
#include "packet.hpp"
class V4L2Capture {
 int fd=-1; bool streaming=false; std::vector<std::pair<void*,size_t>> maps;
 void call(unsigned long op,void* p){int r;do{r=ioctl(fd,op,p);}while(r<0&&errno==EINTR);if(r<0)throw std::runtime_error(std::string("ioctl: ")+strerror(errno));}
 void cleanup() noexcept {
  if(streaming){auto type=V4L2_BUF_TYPE_VIDEO_CAPTURE;ioctl(fd,VIDIOC_STREAMOFF,&type);streaming=false;}
  for(auto [addr,size]:maps){munmap(addr,size);}
  maps.clear();
  if(fd>=0){close(fd);fd=-1;}
 }
public:
 unsigned width=0,height=0,stride=0,sizeimage=0;
 V4L2Capture(const std::string& path,const std::string& expected_bus,unsigned w,unsigned h) {
  try {
   if(!w||!h||uint64_t(w)*h>16*1024*1024)throw std::runtime_error("invalid requested geometry");
   fd=open(path.c_str(),O_RDWR|O_NONBLOCK|O_CLOEXEC);if(fd<0)throw std::runtime_error("device open failed");
   v4l2_capability caps{};call(VIDIOC_QUERYCAP,&caps);
   unsigned c=(caps.capabilities&V4L2_CAP_DEVICE_CAPS)?caps.device_caps:caps.capabilities;
   if(std::string(reinterpret_cast<char*>(caps.driver),strnlen(reinterpret_cast<char*>(caps.driver),sizeof(caps.driver)))!="rp1-cfe" ||
      std::string(reinterpret_cast<char*>(caps.card),strnlen(reinterpret_cast<char*>(caps.card),sizeof(caps.card)))!="rp1-cfe-csi2_ch0" ||
      std::string(reinterpret_cast<char*>(caps.bus_info),strnlen(reinterpret_cast<char*>(caps.bus_info),sizeof(caps.bus_info)))!=expected_bus ||
      !(c&V4L2_CAP_VIDEO_CAPTURE)||!(c&V4L2_CAP_STREAMING))throw std::runtime_error("device identity/capability mismatch");
   v4l2_format fmt{};fmt.type=V4L2_BUF_TYPE_VIDEO_CAPTURE;fmt.fmt.pix.width=w;fmt.fmt.pix.height=h;
   fmt.fmt.pix.pixelformat=V4L2_PIX_FMT_GREY;fmt.fmt.pix.field=V4L2_FIELD_NONE;call(VIDIOC_S_FMT,&fmt);
   width=fmt.fmt.pix.width;height=fmt.fmt.pix.height;stride=fmt.fmt.pix.bytesperline;sizeimage=fmt.fmt.pix.sizeimage;
   if(width!=w||height!=h||fmt.fmt.pix.pixelformat!=V4L2_PIX_FMT_GREY||stride<w||sizeimage<stride*uint64_t(h)||sizeimage>16*1024*1024)throw std::runtime_error("GREY geometry mismatch");
   v4l2_requestbuffers req{};req.type=fmt.type;req.memory=V4L2_MEMORY_MMAP;req.count=8;call(VIDIOC_REQBUFS,&req);
   if(req.count<2||req.count>32)throw std::runtime_error("unexpected MMAP buffer count");
   for(unsigned i=0;i<req.count;++i){
    v4l2_buffer b{};b.type=fmt.type;b.memory=V4L2_MEMORY_MMAP;b.index=i;call(VIDIOC_QUERYBUF,&b);
    if(b.length<sizeimage||b.length>16*1024*1024)throw std::runtime_error("MMAP size invalid");
    void* addr=mmap(nullptr,b.length,PROT_READ|PROT_WRITE,MAP_SHARED,fd,b.m.offset);
    if(addr==MAP_FAILED){throw std::runtime_error("mmap failed");}
    maps.emplace_back(addr,b.length);call(VIDIOC_QBUF,&b);
   }
   auto type=V4L2_BUF_TYPE_VIDEO_CAPTURE;call(VIDIOC_STREAMON,&type);streaming=true;
  }catch(...){cleanup();throw;}
 }
 ~V4L2Capture(){cleanup();}
 V4L2Capture(const V4L2Capture&)=delete;
 V4L2Capture& operator=(const V4L2Capture&)=delete;
 bool next(Packet& packet) {
  pollfd p{fd,POLLIN,0};int r;do{r=poll(&p,1,200);}while(r<0&&errno==EINTR);
  if(r<0){throw std::runtime_error("poll failed");}
  if(!r)return false;
  if(p.revents&(POLLERR|POLLHUP|POLLNVAL))throw std::runtime_error("poll device error");
  v4l2_buffer b{};b.type=V4L2_BUF_TYPE_VIDEO_CAPTURE;b.memory=V4L2_MEMORY_MMAP;
  int rc;do{rc=ioctl(fd,VIDIOC_DQBUF,&b);}while(rc<0&&errno==EINTR);
  if(rc<0){if(errno==EAGAIN)return false;throw std::runtime_error("DQBUF failed");}
  auto start=std::chrono::steady_clock::now();
  if(b.index>=maps.size()||!b.bytesused||b.bytesused>maps[b.index].second||b.bytesused>sizeimage)throw std::runtime_error("DQBUF bounds invalid");
  packet.data.resize(b.bytesused);std::memcpy(packet.data.data(),maps[b.index].first,b.bytesused);
  packet.sequence=b.sequence;packet.driver_error=b.flags&V4L2_BUF_FLAG_ERROR;packet.gap=packet.driver_error;
  call(VIDIOC_QBUF,&b);packet.requeue_us=std::chrono::duration<double,std::micro>(std::chrono::steady_clock::now()-start).count();return true;
 }
};
