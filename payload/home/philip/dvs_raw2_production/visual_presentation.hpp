#pragma once
#include <algorithm>
#include <cctype>
#include <cstdint>
#include <fstream>
#include <sstream>
#include <string>
#include <vector>

// Display-only presentation of per-pixel RAW2 codes. Raw capture / IPC are untouched.
namespace dvsvis {
struct Settings {
    bool legacy = false;
    int denoise = 0;        // 0 (off), 1 or 2 neighbours in a 3x3 stencil
    int persistence_ms = 17; // 17/50/100/150/200, display-only host-paced trail
    bool operator==(const Settings& rhs) const {
        return legacy == rhs.legacy && denoise == rhs.denoise && persistence_ms == rhs.persistence_ms;
    }
    bool operator!=(const Settings& rhs) const { return !(*this == rhs); }
};
inline std::string trim(std::string s) {
    const auto begin=s.find_first_not_of(" \t\r\n");
    if(begin==std::string::npos)return {};
    const auto end=s.find_last_not_of(" \t\r\n");
    return s.substr(begin,end-begin+1);
}
inline bool load_settings(const std::string& path, Settings& out, std::string& error) {
    std::ifstream in(path);
    if(!in) { error = "cannot open " + path; return false; }
    Settings next{};
    std::string line;
    int line_no=0;
    while(std::getline(in,line)) {
        ++line_no;
        line=trim(line);
        if(line.empty() || line[0]=='#')continue;
        const auto sep=line.find('=');
        if(sep==std::string::npos) {error="missing '=' on line "+std::to_string(line_no);return false;}
        const auto key=trim(line.substr(0,sep));
        const auto value=trim(line.substr(sep+1));
        if(key=="mode") {
            if(value=="legacy")next.legacy=true;
            else if(value=="jetson")next.legacy=false;
            else {error="mode must be legacy or jetson";return false;}
        } else if(key=="denoise") {
            if(value=="0")next.denoise=0;
            else if(value=="1")next.denoise=1;
            else if(value=="2")next.denoise=2;
            else {error="denoise must be 0, 1 or 2";return false;}
        } else if(key=="persistence_ms") {
            if(value=="17")next.persistence_ms=17;
            else if(value=="50")next.persistence_ms=50;
            else if(value=="100")next.persistence_ms=100;
            else if(value=="150")next.persistence_ms=150;
            else if(value=="200")next.persistence_ms=200;
            else {error="persistence_ms must be 17,50,100,150,200";return false;}
        } else {error="unknown setting '"+key+"'";return false;}
    }
    out=next;
    return true;
}

class Visualizer {
public:
    Visualizer(int width, int height)
      : width_(width), height_(height), n_(static_cast<size_t>(width)*height),
        last_polarity_(n_,0),last_tick_(n_,0),canvas_(n_,128) {}
    void set_settings(const Settings& s) {
        if(s==settings_)return;
        settings_=s;
        std::fill(last_polarity_.begin(),last_polarity_.end(),0);
        std::fill(last_tick_.begin(),last_tick_.end(),0);
        active_=0;
    }
    const Settings& settings() const {return settings_;}
    // input may be nullptr when time advances without an incoming 60-fps display frame.
    // Rendering never changes the input codes and never alters recorded or IPC data.
    const std::vector<uint8_t>& render(const std::vector<uint8_t>* input) {
        ++tick_;
        if(settings_.legacy) {
            if(input && input->size()==n_)
                for(size_t i=0;i<n_;++i) {
                    const auto code=(*input)[i];
                    canvas_[i] = code==1?255:code==2?64:code==3?128:0;
                }
            active_=0;
            return canvas_;
        }
        if(input && input->size()==n_) {
            const auto& v=*input;
            removed_=0;
            for(size_t i=0;i<n_;++i) {
                const uint8_t code=v[i];
                if(code!=1 && code!=2)continue;
                if(settings_.denoise) {
                    const int x=int(i%size_t(width_)), y=int(i/size_t(width_));
                    int neighbours=0;
                    for(int dy=-1;dy<=1 && neighbours<settings_.denoise;++dy) {
                        const int yy=y+dy;
                        if(yy<0||yy>=height_)continue;
                        for(int dx=-1;dx<=1 && neighbours<settings_.denoise;++dx) {
                            const int xx=x+dx;
                            if((dx==0 && dy==0)||xx<0||xx>=width_)continue;
                            const uint8_t adjacent=v[size_t(yy)*width_+size_t(xx)];
                            if(adjacent==1 || adjacent==2)++neighbours;
                        }
                    }
                    if(neighbours<settings_.denoise){++removed_;continue;}
                }
                last_polarity_[i]=code;
                last_tick_[i]=tick_;
            }
        }
        const uint64_t keep=static_cast<uint64_t>(std::max(1,(settings_.persistence_ms+8)/17));
        active_=0;
        for(size_t i=0;i<n_;++i) {
            const uint8_t code=last_polarity_[i];
            if(!code) {canvas_[i]=128;continue;}
            const uint64_t age=tick_-last_tick_[i];
            if(age>=keep){last_polarity_[i]=0;canvas_[i]=128;continue;}
            ++active_;
            const int magnitude=(code==1 ? 127 : 128)*int(keep-age)/int(keep);
            canvas_[i]=static_cast<uint8_t>(code==1 ? 128+magnitude : 128-magnitude);
        }
        return canvas_;
    }
    bool has_active() const {return active_!=0;}
    size_t last_removed() const {return removed_;}
private:
    int width_,height_;
    size_t n_;
    Settings settings_{};
    uint64_t tick_=0;
    size_t active_=0,removed_=0;
    std::vector<uint8_t> last_polarity_;
    std::vector<uint64_t> last_tick_;
    std::vector<uint8_t> canvas_;
};
} // namespace dvsvis
