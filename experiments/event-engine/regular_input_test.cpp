#include "regular_input.hpp"
#include <filesystem>
#include <fstream>
#include <cassert>
#include <iostream>
int main(int argc,char** argv){
 assert(argc==2);std::filesystem::path root=argv[1];assert(root.string().starts_with("/tmp/"));assert(std::filesystem::create_directory(root));
 auto path=root/"sample";{std::ofstream f(path);f<<"abcdefg";}
 {RegularInput input(path.c_str());std::vector<std::byte> b;assert(input.next(b,4)&&b.size()==4&&b[0]==std::byte{'a'});assert(input.next(b,4)&&b.size()==3);assert(!input.next(b,4));}
 auto reject=[](auto path){try{RegularInput input(path.c_str());return false;}catch(const std::exception&){return true;}};
 std::filesystem::create_symlink(path,root/"link");assert(reject(root/"link"));assert(reject(root));assert(reject(root/"absent"));assert(mkfifo((root/"fifo").c_str(),0600)==0);assert(reject(root/"fifo"));assert(reject(std::filesystem::path("/proc/version")));
 {RegularInput input(path.c_str());std::ofstream f(path,std::ios::app);f<<"changed";f.close();bool failed=false;try{std::vector<std::byte>b;input.next(b,4);}catch(const std::exception&){failed=true;}assert(failed);}
 std::cout<<"{\"pass\":true,\"cases\":7,\"scope\":\"regular temp files/symlinks/FIFO only\"}\n";
}
