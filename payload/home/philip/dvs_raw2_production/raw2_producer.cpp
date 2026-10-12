#define _GNU_SOURCE
#include <algorithm>
#include <array>
#include <atomic>
#include <cerrno>
#include <chrono>
#include <csignal>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <fcntl.h>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <mutex>
#include <thread>
#include <linux/videodev2.h>
#include <poll.h>
#include <sstream>
#include <string>
#include <sys/ioctl.h>
#include <sys/mman.h>
#include <sys/socket.h>
#include <sys/un.h>
#include <sys/uio.h>
#include <unistd.h>
#include <vector>
#include "dvs_renderer.hpp"

namespace {
constexpr uint32_t kWidth = 8192;
constexpr uint32_t kHeight = 128;
constexpr size_t kFrameBytes = size_t{kWidth} * kHeight;
constexpr int kSensorWidth = 960;
constexpr int kSensorHeight = 720;
constexpr int kBytesPerColumn = 180;
// PACK_BYTES puts the 0xCCCCCCCC embedded signature at +176 in each chunk.
// Manual Fig.46: it is the first word of embedded data, not a pixel word.
constexpr int kEmbeddedSignatureOffset = kBytesPerColumn - sizeof(uint32_t);
constexpr int kColumnsPerPacket = 16;
constexpr int kRaw2Chunks = kSensorWidth + kColumnsPerPacket;
constexpr size_t kChangedBytes = size_t{kRaw2Chunks} * kBytesPerColumn;
constexpr uint8_t kSentinel = 0xA5;
constexpr auto kPublishInterval = std::chrono::microseconds(16667);
constexpr size_t kLogicalPixels = size_t{kSensorWidth} * kSensorHeight;
constexpr size_t kPackedImageBytes = kLogicalPixels / 4;

std::atomic<bool> g_running{true};

struct Buffer { void *start{}; size_t length{}; };

#pragma pack(push, 1)
struct Raw2FrameHeader {
    char magic[4];
    uint32_t on_count;
    uint32_t off_count;
    uint32_t invalid_count;
    uint64_t timestamp_us;
};
#pragma pack(pop)
static_assert(sizeof(Raw2FrameHeader) == 24);

void signal_handler(int) { g_running = false; }

int xioctl(int fd, unsigned long request, void *arg) {
    int rc;
    do { rc = ioctl(fd, request, arg); } while (rc < 0 && errno == EINTR);
    return rc;
}

[[noreturn]] void fail(const std::string &message) {
    std::cerr << message << ": " << std::strerror(errno) << '\n';
    std::exit(1);
}

uint64_t timeval_ns(const timeval &tv) {
    return uint64_t(tv.tv_sec) * 1000000000ULL + uint64_t(tv.tv_usec) * 1000ULL;
}

bool embedded_chunk(const uint8_t *chunk) {
    if (chunk[176] != 0xCC || chunk[177] != 0xCC || chunk[178] != 0xCC || chunk[179] != 0xCC)
        return false;
    std::array<uint32_t, 45> values{};
    size_t unique = 0;
    for (int i = 0; i < 45; ++i) {
        uint32_t value;
        std::memcpy(&value, chunk + i * 4, sizeof(value));
        bool seen = false;
        for (size_t j = 0; j < unique; ++j) seen |= values[j] == value;
        if (!seen) values[unique++] = value;
    }
    return unique <= 20;
}

std::pair<int, int> find_embedded_run(const uint8_t *frame) {
    std::array<bool, kRaw2Chunks> flags{};
    for (int i = 0; i < kRaw2Chunks; ++i)
        flags[i] = embedded_chunk(frame + size_t(i) * kBytesPerColumn);
    int best_start = -1, best_length = 0;
    for (int i = 0; i < kRaw2Chunks; ++i) {
        if (!flags[i] || flags[(i + kRaw2Chunks - 1) % kRaw2Chunks]) continue;
        int length = 0;
        while (length < kRaw2Chunks && flags[(i + length) % kRaw2Chunks]) ++length;
        if (length > best_length) { best_start = i; best_length = length; }
    }
    return {best_start, best_length};
}

void write_metrics(const std::string &path, double fps, double mbps,
                   double web_fps,
                   double hdmi_fps, double raw_bytes_sec,
                   uint64_t sequence, uint64_t frame_count,
                   uint64_t on_sec, uint64_t off_sec, uint64_t invalid_sec,
                   uint64_t sensor_on_sec, uint64_t sensor_off_sec,
                   uint64_t sensor_invalid_sec, uint64_t sensor_no_event_sec,
                   uint64_t alignment_errors, uint64_t dequeue_errors,
                   uint64_t sequence_gaps, uint64_t capture_buffer_errors,
                   uint64_t hdmi_errors, uint64_t send_failures,
                   uint64_t sent_events) {
    const std::string temp = path + ".tmp";
    std::ofstream out(temp, std::ios::trunc);
    out << std::fixed << std::setprecision(3)
        << "{\n"
        << "  \"mode\": \"raw2-live\",\n"
        << "  \"data_type\": \"S5KRC1S RAW2 / CSI-2 DT 0x2A\",\n"
        << "  \"mipi_mode\": \"RAW2 2-bit\",\n"
        << "  \"capture_buffers_sec\": " << fps << ",\n"
        << "  \"capture_fps\": " << fps << ",\n"
        << "  \"web_fps\": " << web_fps << ",\n"
        << "  \"hdmi_fps\": " << hdmi_fps << ",\n"
        << "  \"raw_bytes_sec\": " << raw_bytes_sec << ",\n"
        << "  \"input_MB_sec\": " << mbps << ",\n"
        << "  \"v4l2_sequence\": " << sequence << ",\n"
        << "  \"frame_count\": " << frame_count << ",\n"
        << "  \"on_events_sec\": " << on_sec << ",\n"
        << "  \"off_events_sec\": " << off_sec << ",\n"
        << "  \"invalid_11_sec\": " << invalid_sec << ",\n"
        << "  \"sensor_on_events_sec\": " << sensor_on_sec << ",\n"
        << "  \"sensor_off_events_sec\": " << sensor_off_sec << ",\n"
        << "  \"sensor_invalid_11_sec\": " << sensor_invalid_sec << ",\n"
        << "  \"sensor_no_event_sec\": " << sensor_no_event_sec << ",\n"
        << "  \"raw2_alignment_errors\": " << alignment_errors << ",\n"
        << "  \"v4l2_dequeue_errors\": " << dequeue_errors << ",\n"
        << "  \"v4l2_buffer_errors\": " << capture_buffer_errors << ",\n"
        << "  \"v4l2_sequence_gaps\": " << sequence_gaps << ",\n"
        << "  \"hdmi_write_errors\": " << hdmi_errors << ",\n"
        << "  \"ipc_send_failures\": " << send_failures << ",\n"
        << "  \"ipc_events_sent\": " << sent_events << "\n"
        << "}\n";
    out.close();
    if (std::rename(temp.c_str(), path.c_str()) != 0) fail("rename metrics");
}

struct FrameCounts {
    uint32_t on = 0;
    uint32_t off = 0;
    uint32_t invalid = 0;
};

// Count codes in each packed byte once; empty bytes need no pixel writes.
const auto kCodeCounts = [] {
    std::array<std::array<uint8_t, 4>, 256> table{};
    for (int value = 0; value < 256; ++value)
        for (int shift = 6; shift >= 0; shift -= 2)
            ++table[value][(value >> shift) & 3];
    return table;
}();

std::array<uint64_t, 4> decode_raw2(const uint8_t *frame, int first_pixel,
                                  std::vector<uint8_t> &aggregate) {
    std::array<uint32_t, 256> histogram{};
    for (int serial = 0; serial < kSensorWidth; ++serial) {
        const int source_chunk = (first_pixel + serial) % kRaw2Chunks;
        const size_t source_offset = (size_t(source_chunk) * kBytesPerColumn +
                                      kEmbeddedSignatureOffset) % kChangedBytes;
        const uint8_t *packed = frame + source_offset;
        const int x = (serial / kColumnsPerPacket) * kColumnsPerPacket +
                      (kColumnsPerPacket - 1 - serial % kColumnsPerPacket);
        for (int byte_index = 0; byte_index < kBytesPerColumn; ++byte_index) {
            const uint8_t value = packed[byte_index];
            ++histogram[value];
            if (value == 0) continue;
            for (int pixel = 0; pixel < 4; ++pixel) {
                const uint8_t code = (value >> (6 - 2 * pixel)) & 3;
                // Manual p35: 11 is unassigned, never a valid contour pixel.
                if (code == 1 || code == 2) {
                    const int y = kSensorHeight - 1 - (byte_index * 4 + pixel);
                    aggregate[size_t(y) * kSensorWidth + x] = code;
                }
            }
        }
    }
    std::array<uint64_t, 4> counts{};
    for (int value = 0; value < 256; ++value)
        for (int code = 0; code < 4; ++code)
            counts[code] += uint64_t(histogram[value]) * kCodeCounts[value][code];
    return counts;
}

class FrameSender {
  public:
    explicit FrameSender(const std::string &path) {
        fd_ = socket(AF_UNIX, SOCK_DGRAM | SOCK_NONBLOCK | SOCK_CLOEXEC, 0);
        if (fd_ < 0) fail("socket(AF_UNIX)");
        sockaddr_un addr{};
        addr.sun_family = AF_UNIX;
        if (path.size() >= sizeof(addr.sun_path)) { errno = ENAMETOOLONG; fail("IPC socket path"); }
        std::strncpy(addr.sun_path, path.c_str(), sizeof(addr.sun_path) - 1);
        if (connect(fd_, reinterpret_cast<sockaddr *>(&addr), sizeof(addr)) < 0)
            fail("connect IPC socket");
        packed_.resize(kPackedImageBytes);
    }
    ~FrameSender() { if (fd_ >= 0) close(fd_); }
    FrameCounts send_frame(const std::vector<uint8_t> &codes, uint64_t timestamp_ns) {
        FrameCounts counts;
        std::array<uint32_t, 256> histogram{};
        for (size_t i = 0; i < kPackedImageBytes; ++i) {
            const size_t base = i * 4;
            const uint8_t value = (codes[base] << 6) | (codes[base + 1] << 4) |
                                  (codes[base + 2] << 2) | codes[base + 3];
            packed_[i] = value;
            ++histogram[value];
        }
        for (int value = 0; value < 256; ++value) {
            counts.on += histogram[value] * kCodeCounts[value][1];
            counts.off += histogram[value] * kCodeCounts[value][2];
            counts.invalid += histogram[value] * kCodeCounts[value][3];
        }
        const Raw2FrameHeader header{
            {'R','2','F','1'}, counts.on, counts.off, counts.invalid, timestamp_ns / 1000
        };
        iovec vectors[2] = {
            {const_cast<Raw2FrameHeader *>(&header), sizeof(header)},
            {packed_.data(), packed_.size()}
        };
        msghdr message{};
        message.msg_iov = vectors;
        message.msg_iovlen = 2;
        const size_t bytes = sizeof(header) + packed_.size();
        const ssize_t rc = sendmsg(fd_, &message, MSG_NOSIGNAL);
        if (rc == static_cast<ssize_t>(bytes)) sent_ += counts.on + counts.off;
        else ++failures_;
        return counts;
    }
    uint64_t failures() const { return failures_; }
    uint64_t sent() const { return sent_; }
  private:
    int fd_ = -1;
    std::vector<uint8_t> packed_;
    uint64_t failures_ = 0, sent_ = 0;
};

// Display the known-good decoded RAW2 raster without blocking V4L2 capture.
class HdmiOutput {
  public:
    HdmiOutput() : surface_(kLogicalPixels, 0), worker_(&HdmiOutput::run, this) {}
    ~HdmiOutput() {
        running_ = false;
        if (worker_.joinable()) worker_.join();
    }
    void update(const std::vector<uint8_t> &codes) {
        if (codes.size() != kLogicalPixels) return;
        std::vector<uint8_t> next(kLogicalPixels);
        for (size_t i = 0; i < kLogicalPixels; ++i) {
            const uint8_t code = codes[i];
            next[i] = code == 1 ? 255 : code == 2 ? 64 : code == 3 ? 128 : 0;
        }
        std::lock_guard<std::mutex> lock(mutex_);
        surface_.swap(next);
        ++version_;
    }
    uint64_t frames() const { return frames_; }
    uint64_t errors() const { return errors_; }
  private:
    void run() {
        DVSRenderer renderer;
        std::string error;
        if (!renderer.open_ffplay(kSensorWidth, kSensorHeight, 60, error)) {
            std::cerr << "HDMI renderer: " << error << '\n';
            ++errors_;
            return;
        }
        std::vector<uint8_t> frame(kLogicalPixels);
        uint64_t rendered_version = 0;
        auto deadline = std::chrono::steady_clock::now();
        while (running_) {
            bool changed = false;
            {
                std::lock_guard<std::mutex> lock(mutex_);
                if (version_ != rendered_version) {
                    frame = surface_;
                    rendered_version = version_;
                    changed = true;
                }
            }
            if (changed && !renderer.render(frame)) {
                ++errors_;
                break;
            }
            if (changed) ++frames_;
            deadline += std::chrono::nanoseconds(16666667);
            std::this_thread::sleep_until(deadline);
            if (std::chrono::steady_clock::now() > deadline + std::chrono::milliseconds(100))
                deadline = std::chrono::steady_clock::now();
        }
    }
    std::atomic<bool> running_{true};
    std::atomic<uint64_t> frames_{0}, errors_{0};
    std::mutex mutex_;
    uint64_t version_ = 0;
    std::vector<uint8_t> surface_;
    std::thread worker_;
};

} // namespace

int main(int argc, char **argv) {
    if (argc != 4) {
        std::cerr << "usage: " << argv[0] << " DEVICE IPC_SOCKET METRICS_JSON\n";
        return 2;
    }
    std::signal(SIGINT, signal_handler);
    std::signal(SIGTERM, signal_handler);
    std::signal(SIGPIPE, SIG_IGN);

    const int fd = open(argv[1], O_RDWR | O_NONBLOCK | O_CLOEXEC);
    if (fd < 0) fail("open video device");
    v4l2_capability cap{};
    if (xioctl(fd, VIDIOC_QUERYCAP, &cap) < 0) fail("VIDIOC_QUERYCAP");
    if (!(cap.device_caps & V4L2_CAP_VIDEO_CAPTURE) || !(cap.device_caps & V4L2_CAP_STREAMING)) {
        std::cerr << "device lacks VIDEO_CAPTURE or STREAMING\n"; return 1;
    }

    v4l2_format fmt{};
    fmt.type = V4L2_BUF_TYPE_VIDEO_CAPTURE;
    fmt.fmt.pix.width = kWidth; fmt.fmt.pix.height = kHeight;
    fmt.fmt.pix.pixelformat = V4L2_PIX_FMT_GREY;
    fmt.fmt.pix.field = V4L2_FIELD_NONE;
    fmt.fmt.pix.bytesperline = kWidth;
    if (xioctl(fd, VIDIOC_S_FMT, &fmt) < 0) fail("VIDIOC_S_FMT");
    if (fmt.fmt.pix.width != kWidth || fmt.fmt.pix.height != kHeight ||
        fmt.fmt.pix.pixelformat != V4L2_PIX_FMT_GREY ||
        fmt.fmt.pix.bytesperline != kWidth || fmt.fmt.pix.sizeimage != kFrameBytes) {
        std::cerr << "driver changed requested 8192x128 GREY stride=8192 geometry\n"; return 1;
    }

    v4l2_requestbuffers req{};
    req.count = 6; req.type = V4L2_BUF_TYPE_VIDEO_CAPTURE; req.memory = V4L2_MEMORY_MMAP;
    if (xioctl(fd, VIDIOC_REQBUFS, &req) < 0) fail("VIDIOC_REQBUFS");
    if (req.count < 3) { std::cerr << "fewer than three V4L2 buffers\n"; return 1; }
    std::vector<Buffer> buffers(req.count);
    for (uint32_t i = 0; i < req.count; ++i) {
        v4l2_buffer buf{}; buf.type = V4L2_BUF_TYPE_VIDEO_CAPTURE;
        buf.memory = V4L2_MEMORY_MMAP; buf.index = i;
        if (xioctl(fd, VIDIOC_QUERYBUF, &buf) < 0) fail("VIDIOC_QUERYBUF");
        buffers[i].length = buf.length;
        buffers[i].start = mmap(nullptr, buf.length, PROT_READ | PROT_WRITE, MAP_SHARED, fd, buf.m.offset);
        if (buffers[i].start == MAP_FAILED) fail("mmap");
        std::memset(buffers[i].start, kSentinel, buffers[i].length);
        if (xioctl(fd, VIDIOC_QBUF, &buf) < 0) fail("VIDIOC_QBUF initial");
    }
    FrameSender sender(argv[2]);
    HdmiOutput hdmi;
    v4l2_buf_type type = V4L2_BUF_TYPE_VIDEO_CAPTURE;
    if (xioctl(fd, VIDIOC_STREAMON, &type) < 0) fail("VIDIOC_STREAMON");
    std::cerr << "RAW2 live producer streaming 8192x128, changed bytes=" << kChangedBytes << '\n';

    uint64_t frame_count = 0, alignment_errors = 0, dequeue_errors = 0, sequence_gaps = 0;
    uint64_t capture_buffer_errors = 0;
    uint64_t on_interval = 0, off_interval = 0, invalid_interval = 0;
    uint64_t sensor_on_interval = 0, sensor_off_interval = 0;
    uint64_t sensor_invalid_interval = 0, sensor_no_event_interval = 0;
    uint64_t raw_bytes_interval = 0, hdmi_frames_before = 0;
    uint32_t last_sequence = 0; bool have_sequence = false;
    auto interval_start = std::chrono::steady_clock::now();
    auto last_publish = interval_start;
    uint64_t interval_frames = 0, interval_published = 0;
    std::vector<uint8_t> aggregate(kLogicalPixels, 0);
    // Decode from cached RAM instead of byte-wise reads from DMA mappings.
    std::vector<uint8_t> cached_frame(kChangedBytes + kBytesPerColumn);
    int aggregate_frames = 0;
    uint64_t aggregate_timestamp = 0;
    bool saved_sample = false;

    while (g_running) {
        pollfd pfd{fd, POLLIN | POLLPRI, 0};
        int prc = poll(&pfd, 1, 2000);
        if (prc < 0 && errno == EINTR) continue;
        if (prc <= 0) { ++dequeue_errors; continue; }
        v4l2_buffer buf{}; buf.type = V4L2_BUF_TYPE_VIDEO_CAPTURE; buf.memory = V4L2_MEMORY_MMAP;
        if (xioctl(fd, VIDIOC_DQBUF, &buf) < 0) {
            if (errno == EAGAIN || errno == EINTR) continue;
            ++dequeue_errors; continue;
        }
        if (buf.index >= buffers.size()) {
            ++dequeue_errors; g_running = false; break;
        }
        if (buf.bytesused < kChangedBytes) {
            ++dequeue_errors;
        } else {
            raw_bytes_interval += kChangedBytes;
            if (buf.flags & V4L2_BUF_FLAG_ERROR) ++capture_buffer_errors;
            if (have_sequence && buf.sequence > last_sequence + 1) sequence_gaps += buf.sequence - last_sequence - 1;
            last_sequence = buf.sequence; have_sequence = true;
            std::memcpy(cached_frame.data(), buffers[buf.index].start, kChangedBytes);
            std::memcpy(cached_frame.data() + kChangedBytes, cached_frame.data(), kBytesPerColumn);
            const auto *frame = cached_frame.data();
            const auto [embedded_start, embedded_length] = find_embedded_run(frame);
            if (!saved_sample && embedded_length == kColumnsPerPacket) {
                std::ofstream sample("/tmp/dvs_raw2_first_frame.bin", std::ios::binary);
                sample.write(reinterpret_cast<const char *>(frame), kChangedBytes);
                saved_sample = true;
            }
            if (embedded_start < 0 || embedded_length != kColumnsPerPacket) {
                ++alignment_errors;
            } else {
                const auto frame_now = std::chrono::steady_clock::now();
                const int first_pixel = (embedded_start + kColumnsPerPacket) % kRaw2Chunks;
                const uint64_t timestamp = timeval_ns(buf.timestamp);
                const auto sensor_counts = decode_raw2(frame, first_pixel, aggregate);
                sensor_no_event_interval += sensor_counts[0];
                sensor_on_interval += sensor_counts[1];
                sensor_off_interval += sensor_counts[2];
                sensor_invalid_interval += sensor_counts[3];
                ++aggregate_frames;
                aggregate_timestamp = timestamp;
                if (frame_now - last_publish >= kPublishInterval) {
                    const FrameCounts counts = sender.send_frame(aggregate, aggregate_timestamp);
                    hdmi.update(aggregate);
                    on_interval += counts.on;
                    off_interval += counts.off;
                    invalid_interval += counts.invalid;
                    std::fill(aggregate.begin(), aggregate.end(), 0);
                    aggregate_frames = 0;
                    last_publish = frame_now;
                    ++interval_published;
                }
            }
            ++frame_count; ++interval_frames;
        }
        // Only the packed RAW2 region is inspected; keep its sentinel protection.
        std::memset(buffers[buf.index].start, kSentinel, kChangedBytes);
        if (xioctl(fd, VIDIOC_QBUF, &buf) < 0) { ++dequeue_errors; g_running = false; }

        const auto now = std::chrono::steady_clock::now();
        const double elapsed = std::chrono::duration<double>(now - interval_start).count();
        if (elapsed >= 1.0) {
            const uint64_t hdmi_frames_now = hdmi.frames();
            write_metrics(argv[3], interval_frames / elapsed,
                          (interval_frames * double(kChangedBytes) / (1024.0 * 1024.0)) / elapsed,
                          interval_published / elapsed,
                          (hdmi_frames_now - hdmi_frames_before) / elapsed,
                          raw_bytes_interval / elapsed,
                          last_sequence, frame_count,
                          uint64_t(on_interval / elapsed), uint64_t(off_interval / elapsed),
                          uint64_t(invalid_interval / elapsed),
                          uint64_t(sensor_on_interval / elapsed), uint64_t(sensor_off_interval / elapsed),
                          uint64_t(sensor_invalid_interval / elapsed), uint64_t(sensor_no_event_interval / elapsed),
                          alignment_errors, dequeue_errors, sequence_gaps, capture_buffer_errors,
                          hdmi.errors(), sender.failures(), sender.sent());
            hdmi_frames_before = hdmi_frames_now;
            interval_start = now;
            interval_frames = interval_published = on_interval = off_interval = invalid_interval = 0;
            sensor_on_interval = sensor_off_interval = sensor_invalid_interval = 0;
            sensor_no_event_interval = raw_bytes_interval = 0;
        }
    }

    xioctl(fd, VIDIOC_STREAMOFF, &type);
    for (auto &buffer : buffers) munmap(buffer.start, buffer.length);
    close(fd);
    std::remove(argv[3]);
    return dequeue_errors ? 1 : 0;
}
