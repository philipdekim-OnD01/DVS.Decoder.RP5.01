#include "dvs_renderer.hpp"

#include <sys/wait.h>

#include <cerrno>
#include <cstring>
#include <cstdio>
#include <fstream>
#include <vector>


namespace {

void write_le16(std::vector<uint8_t>& out, uint16_t value)
{
    out.push_back(uint8_t(value & 0xff));
    out.push_back(uint8_t((value >> 8) & 0xff));
}

void write_le32(std::vector<uint8_t>& out, uint32_t value)
{
    out.push_back(uint8_t(value & 0xff));
    out.push_back(uint8_t((value >> 8) & 0xff));
    out.push_back(uint8_t((value >> 16) & 0xff));
    out.push_back(uint8_t((value >> 24) & 0xff));
}

} // namespace
DVSRenderer::~DVSRenderer()
{
    close();
}

bool DVSRenderer::open_ffplay(uint32_t width, uint32_t height, uint32_t fps, std::string& error)
{
    close();
    const std::string command =
        "DISPLAY=:0 XAUTHORITY=/home/philip/.Xauthority QT_QPA_PLATFORM=xcb "
        "/home/philip/dvs_web_app/.venv/bin/python "
        "/home/philip/dvs_raw2_production/hdmi_controls.py "
        "2>>/home/philip/dvs_raw2_production/logs/hdmi-controls.log";

    pipe_ = popen(command.c_str(), "w");
    if (pipe_ == nullptr) {
        error = std::string("popen ffplay failed: ") + std::strerror(errno);
        return false;
    }
    setvbuf(pipe_, nullptr, _IONBF, 0);
    return true;
}

bool DVSRenderer::render(const std::vector<uint8_t>& frame)
{
    if (pipe_ == nullptr) {
        return false;
    }
    const size_t written = fwrite(frame.data(), 1, frame.size(), pipe_);
    return written == frame.size();
}

void DVSRenderer::close()
{
    if (pipe_ != nullptr) {
        pclose(pipe_);
        pipe_ = nullptr;
    }
}

bool save_pgm(
    const std::string& path,
    uint32_t width,
    uint32_t height,
    const std::vector<uint8_t>& frame,
    std::string& error)
{
    if (frame.size() != size_t(width) * size_t(height)) {
        error = "PGM frame size does not match dimensions";
        return false;
    }

    std::ofstream out(path, std::ios::binary);
    if (!out) {
        error = "open " + path + " failed";
        return false;
    }
    out << "P5\n" << width << " " << height << "\n255\n";
    out.write(reinterpret_cast<const char*>(frame.data()), std::streamsize(frame.size()));
    if (!out) {
        error = "write " + path + " failed";
        return false;
    }
    return true;
}
bool save_bmp_gray(
    const std::string& path,
    uint32_t width,
    uint32_t height,
    const std::vector<uint8_t>& frame,
    std::string& error)
{
    if (frame.size() != size_t(width) * size_t(height)) {
        error = "BMP frame size does not match dimensions";
        return false;
    }

    const uint32_t row_stride = (width * 3u + 3u) & ~3u;
    const uint32_t pixel_bytes = row_stride * height;
    const uint32_t pixel_offset = 14u + 40u;
    const uint32_t file_size = pixel_offset + pixel_bytes;

    std::vector<uint8_t> header;
    header.reserve(pixel_offset);
    header.push_back('B');
    header.push_back('M');
    write_le32(header, file_size);
    write_le16(header, 0);
    write_le16(header, 0);
    write_le32(header, pixel_offset);
    write_le32(header, 40);
    write_le32(header, width);
    write_le32(header, height);
    write_le16(header, 1);
    write_le16(header, 24);
    write_le32(header, 0);
    write_le32(header, pixel_bytes);
    write_le32(header, 2835);
    write_le32(header, 2835);
    write_le32(header, 0);
    write_le32(header, 0);

    const std::string tmp_path = path + ".tmp";
    std::ofstream out(tmp_path, std::ios::binary);
    if (!out) {
        error = "open " + tmp_path + " failed";
        return false;
    }
    out.write(reinterpret_cast<const char*>(header.data()), std::streamsize(header.size()));

    std::vector<uint8_t> row(row_stride, 0);
    for (int y = int(height) - 1; y >= 0; --y) {
        const size_t src = size_t(y) * width;
        for (uint32_t x = 0; x < width; ++x) {
            const uint8_t v = frame[src + x];
            row[x * 3 + 0] = v;
            row[x * 3 + 1] = v;
            row[x * 3 + 2] = v;
        }
        out.write(reinterpret_cast<const char*>(row.data()), std::streamsize(row.size()));
    }
    out.close();
    if (!out) {
        error = "write " + tmp_path + " failed";
        std::remove(tmp_path.c_str());
        return false;
    }
    if (std::rename(tmp_path.c_str(), path.c_str()) != 0) {
        error = "rename " + tmp_path + " to " + path + " failed: " + std::strerror(errno);
        std::remove(tmp_path.c_str());
        return false;
    }
    return true;
}
