#pragma once

#include <cstdint>
#include <cstdio>
#include <string>
#include <vector>

class DVSRenderer {
public:
    DVSRenderer() = default;
    ~DVSRenderer();

    DVSRenderer(const DVSRenderer&) = delete;
    DVSRenderer& operator=(const DVSRenderer&) = delete;

    bool open_ffplay(uint32_t width, uint32_t height, uint32_t fps, std::string& error);
    bool render(const std::vector<uint8_t>& frame);
    void close();
    bool active() const { return pipe_ != nullptr; }

private:
    FILE* pipe_ = nullptr;
};

bool save_pgm(
    const std::string& path,
    uint32_t width,
    uint32_t height,
    const std::vector<uint8_t>& frame,
    std::string& error);
bool save_bmp_gray(
    const std::string& path,
    uint32_t width,
    uint32_t height,
    const std::vector<uint8_t>& frame,
    std::string& error);