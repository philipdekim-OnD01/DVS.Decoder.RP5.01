#include "visual_presentation.hpp"
#include <cassert>
#include <cstdlib>
#include <iostream>
#include <fstream>
#include <vector>
int main() {
    // 5x5: centre isolated pixel and a neighboring pair.
    dvsvis::Visualizer v(5,5);
    dvsvis::Settings legacy;legacy.legacy=true;
    v.set_settings(legacy);
    std::vector<uint8_t> codes(25,0);
    codes[4]=1;codes[6]=2;codes[7]=1;codes[24]=3;
    const auto snapshot=codes;
    auto image=v.render(&codes);
    assert(image[0]==0 && image[4]==255 && image[6]==64 && image[7]==255 && image[24]==128);
    assert(codes==snapshot);

    dvsvis::Settings jetson;jetson.legacy=false;jetson.denoise=0;jetson.persistence_ms=17;
    v.set_settings(jetson);
    image=v.render(&codes);
    assert(image[0]==128 && image[4]==255 && image[6]==0 && image[7]==255 && image[24]==128);
    image=v.render(nullptr);
    assert(image[4]==128 && image[6]==128);

    jetson.denoise=1;jetson.persistence_ms=50;
    v.set_settings(jetson);
    image=v.render(&codes);
    assert(image[4]==128 && image[6]==0 && image[7]==255 && v.last_removed()==1);
    image=v.render(nullptr);
    assert(image[6]>0 && image[6]<128 && image[7]<255 && image[7]>128);
    image=v.render(nullptr);
    image=v.render(nullptr);
    assert(image[6]==128 && image[7]==128);
    assert(codes==snapshot);

    const std::string cfg="/tmp/dvs_vis_test.conf";
    {std::ofstream out(cfg);out<<"mode=jetson\ndenoise=2\npersistence_ms=150\n";}
    dvsvis::Settings parsed; std::string error;
    assert(dvsvis::load_settings(cfg,parsed,error));
    assert(!parsed.legacy && parsed.denoise==2 && parsed.persistence_ms==150);
    {std::ofstream out(cfg);out<<"denoise=100\n";}
    assert(!dvsvis::load_settings(cfg,parsed,error));
    assert(parsed.persistence_ms==150); // invalid input is rejected atomically
    std::remove(cfg.c_str());
    std::cout << "PASS: display legacy identity, Jetson polarity, temporal fade, "
                 "denoise, input immutability, config validation\n";
}
