#pragma once
#include <array>
#include <cstddef>
#include <cstdint>
#include <cstring>
#include <map>
#include <vector>

// Diagnostic only. Does NOT alter the pixel order, RAW2 format or existing renderer.
// Per original producer: 180 B/column and embedded signature at byte offset 176.
namespace raw2qa {
class EmbeddedAlignmentAudit {
public:
    static constexpr std::size_t kColumnBytes = 180;
    static constexpr std::size_t kSignatureOffset = 176;
    struct Stats {
        std::uint64_t records=0, columns=0, starts=0, complete_runs=0;
        std::uint64_t intervals_971=0, intervals_976=0, other_intervals=0;
        std::uint64_t discontinuities=0, invalid_run_length=0;
        int last_interval=0;
        int first_record_offset=-1, last_record_offset=-1;
    };
    const Stats& stats() const noexcept { return stats_; }
    const std::map<int,std::uint64_t>& interval_histogram() const noexcept { return intervals_; }
    void discontinuity() noexcept {
        ++stats_.discontinuities;
        prev_embedded_=false;
        prev_start_valid_=false;
        current_run_=0;
    }
    void observe_record(const std::uint8_t* data, std::size_t len) {
        ++stats_.records;
        const std::size_t n = len/kColumnBytes;
        stats_.first_record_offset=-1;
        stats_.last_record_offset=-1;
        for(std::size_t col=0;col<n;++col) {
            const auto* chunk=data+col*kColumnBytes;
            const bool embedded = looks_embedded(chunk);
            if(embedded && !prev_embedded_) {
                const std::uint64_t absolute=stats_.columns+col;
                if(prev_start_valid_) {
                    auto distance=static_cast<int>(absolute-prev_start_);
                    ++intervals_[distance]; stats_.last_interval=distance;
                    if(distance==971) ++stats_.intervals_971;
                    else if(distance==976) ++stats_.intervals_976;
                    else ++stats_.other_intervals;
                }
                prev_start_=absolute;
                prev_start_valid_=true;
                ++stats_.starts;
                if(stats_.first_record_offset<0) stats_.first_record_offset=static_cast<int>(col);
                stats_.last_record_offset=static_cast<int>(col);
            }
            if(embedded) {++current_run_;}
            else if(prev_embedded_) {finish_run();}
            prev_embedded_=embedded;
        }
        stats_.columns+=n;
        if(len%kColumnBytes) discontinuity();
    }
    void finalize() {if(prev_embedded_) {finish_run();prev_embedded_=false;}}
private:
    static bool looks_embedded(const std::uint8_t* p) {
        if(p[176]!=0xCC||p[177]!=0xCC||p[178]!=0xCC||p[179]!=0xCC) return false;
        // Same conservative heuristic as the existing production find_embedded_run().
        std::array<std::uint32_t,45> seen{};
        std::size_t unique=0;
        for(int i=0;i<45;++i) {
            std::uint32_t v=0;std::memcpy(&v,p+i*4,4);
            bool found=false;
            for(std::size_t j=0;j<unique;++j) if(seen[j]==v) {found=true;break;}
            if(!found) seen[unique++]=v;
        }
        return unique<=20;
    }
    void finish_run() {
        if(current_run_==16) ++stats_.complete_runs;
        else ++stats_.invalid_run_length;
        current_run_=0;
    }
    Stats stats_{};
    std::map<int,std::uint64_t> intervals_{};
    bool prev_embedded_=false,prev_start_valid_=false;
    std::uint64_t prev_start_=0;
    std::uint64_t current_run_=0;
};
} // namespace raw2qa
