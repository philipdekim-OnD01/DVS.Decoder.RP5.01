#pragma once
#include <fcntl.h>
#include <sys/stat.h>
#include <sys/vfs.h>
#include <linux/magic.h>
#include <unistd.h>
#include <cerrno>
#include <cstddef>
#include <cstring>
#include <stdexcept>
#include <string>
#include <vector>
// Linux O_PATH pins an inode without invoking a device's file_operations.open.
// Only a verified regular inode is subsequently opened for reading via procfs.
class RegularInput {
 int fd=-1;struct stat baseline{};size_t remaining=0;
 void unchanged(){struct stat now{};if(fstat(fd,&now)||now.st_size!=baseline.st_size||now.st_mtim.tv_sec!=baseline.st_mtim.tv_sec||now.st_mtim.tv_nsec!=baseline.st_mtim.tv_nsec)throw std::runtime_error("file changed during replay");}
public:
 explicit RegularInput(const char* path){
  int pin=open(path,O_PATH|O_NOFOLLOW|O_CLOEXEC);if(pin<0)throw std::runtime_error("file open failed");
  try{
   if(fstat(pin,&baseline)||!S_ISREG(baseline.st_mode)||baseline.st_size<0)throw std::runtime_error("file mode requires a regular non-symlink file");
   struct statfs filesystem{};if(fstatfs(pin,&filesystem)||(filesystem.f_type!=EXT4_SUPER_MAGIC&&filesystem.f_type!=TMPFS_MAGIC))throw std::runtime_error("file mode requires ext/tmpfs; kernel virtual files refused");
   std::string pinned="/proc/self/fd/"+std::to_string(pin);fd=open(pinned.c_str(),O_RDONLY|O_CLOEXEC|O_NONBLOCK);if(fd<0)throw std::runtime_error("regular file read open failed");
   struct stat opened{};if(fstat(fd,&opened)||!S_ISREG(opened.st_mode)||opened.st_dev!=baseline.st_dev||opened.st_ino!=baseline.st_ino)throw std::runtime_error("file identity changed");
   unchanged();remaining=baseline.st_size;close(pin);
  }catch(...){close(pin);if(fd>=0)close(fd);throw;}
 }
 ~RegularInput(){if(fd>=0)close(fd);}
 RegularInput(const RegularInput&)=delete;RegularInput& operator=(const RegularInput&)=delete;
 bool next(std::vector<std::byte>& out,size_t chunk){
  if(!chunk||chunk>16*1024*1024){throw std::runtime_error("invalid file chunk");}
  unchanged();if(!remaining)return false;
  size_t n=remaining<chunk?remaining:chunk;out.resize(n);size_t used=0;
  while(used<n){ssize_t got=read(fd,out.data()+used,n-used);if(got<0&&errno==EINTR)continue;if(got<=0)throw std::runtime_error("file truncated/read failed");used+=got;}
  remaining-=used;unchanged();return true;
 }
};
