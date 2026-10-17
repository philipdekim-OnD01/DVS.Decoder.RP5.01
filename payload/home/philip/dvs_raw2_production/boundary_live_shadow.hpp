#pragma once
// Read-only, allocation-free Embedded marker telemetry. This observer consumes
// the SAME 976 boolean flags already produced by find_embedded_run(); it never
// changes RAW2 decoding, sensor pixel coordinates, IPC or HDMI rendering.
#include <array>
#include <algorithm>
#include <cstddef>
#include <cstdint>

namespace raw2shadow {
constexpr std::size_t kHostColumns = 976;
constexpr std::size_t kHistogramMax = 4096;
constexpr std::size_t kTraceCapacity = 128;

// kind: 'S' unusual valid-to-valid start spacing, 'B' bad marker run,
// 'R' host record rejected by the legacy circular classifier,
// 'G' sparse reference example of a valid 971-column interval.
struct TraceRow {
    std::uint64_t id = 0;
    char kind = '?';
    std::uint64_t host_record = 0;
    std::uint64_t marker_start_record = 0;
    std::uint32_t marker_start_offset = 0;
    std::uint64_t marker_end_record = 0;
    std::uint32_t marker_end_offset = 0;
    std::uint32_t marker_length = 0;
    std::uint64_t previous_marker_record = 0;
    std::uint32_t previous_marker_offset = 0;
    std::uint64_t spacing = 0;
    std::int64_t delta_from_971 = 0;
    std::uint32_t head_run = 0;
    std::uint32_t tail_run = 0;
    bool rejected_marker_host_record = false;
    bool crossed_host_boundary = false;
};

struct Stats {
    std::array<std::uint64_t,kHistogramMax+1> interval_hist{};
    std::array<std::uint64_t,257> bad_run_hist{};
    std::uint64_t interval_gt_4096=0, bad_run_gt_256=0;
    std::uint64_t host_records=0, legacy_rejected=0;
    std::uint64_t embedded_runs_16=0, embedded_runs_bad=0;
    std::uint64_t intervals_971=0, intervals_976=0, intervals_other=0;
    std::uint64_t verified_frames=0, frames_955=0, frames_960=0, frames_other=0;
    std::uint64_t discontinuities=0;
    std::uint64_t legacy_reject_wrap21=0, legacy_reject_wrap_other=0;
    std::uint64_t legacy_reject_no_wrap=0;
    std::uint64_t bad_runs_cross_host=0, good_runs_cross_host=0;
    std::uint64_t other_intervals_start_close_to_host_edge=0;
    std::uint64_t trace_saved=0, trace_spacing_seen=0, trace_bad_run_seen=0;
    std::uint64_t trace_legacy_reject_seen=0;
    std::array<TraceRow,kTraceCapacity> trace{};
};

class BoundaryStreamObserver {
public:
    const Stats& stats() const noexcept { return stats_; }
    void enable_trace(bool enabled) noexcept { trace_enabled_ = enabled; }
    void discontinuity() noexcept {
        ++stats_.discontinuities;
        have_good_=false; in_embedded_=false; run_length_=0;
        // A sequence interruption invalidates comparisons across the gap.
        last_good_start_=0;
    }
    void observe_flags(const std::array<bool,kHostColumns>& flags, bool legacy_rejected) noexcept {
        const std::uint64_t host_record = stats_.host_records++;
        record_history_[host_record % record_history_.size()]={host_record,legacy_rejected};
        std::uint32_t head=0,tail=0;
        while(head<kHostColumns && flags[head])++head;
        while(tail<kHostColumns && flags[kHostColumns-1-tail])++tail;
        if (legacy_rejected) {
            ++stats_.legacy_rejected;
            if (head>0 && tail>0 && head+tail==21) ++stats_.legacy_reject_wrap21;
            else if (head>0 && tail>0) ++stats_.legacy_reject_wrap_other;
            else ++stats_.legacy_reject_no_wrap;
            if (trace_enabled_ && (++stats_.trace_legacy_reject_seen % 4 == 1)) {
                TraceRow row{};
                row.kind='R';row.host_record=host_record;
                row.marker_start_record=host_record;
                row.marker_start_offset=0;
                row.marker_end_record=host_record;
                row.marker_end_offset=975;
                row.head_run=head;row.tail_run=tail;
                row.marker_length=head+tail;
                row.rejected_marker_host_record=true;
                save_trace(row);
            }
        }
        for (const bool embedded : flags) {
            if (embedded) {
                if (!in_embedded_) {
                    in_embedded_=true;run_start_=absolute_column_;run_length_=0;
                }
                ++run_length_;
            } else if (in_embedded_) {
                finish_run();
            }
            ++absolute_column_;
        }
    }
private:
    struct HostRecordInfo {std::uint64_t record = UINT64_MAX;bool rejected = false;};
    Stats stats_{};
    std::array<HostRecordInfo,4> record_history_{};
    std::uint64_t absolute_column_=0,run_start_=0,last_good_start_=0;
    std::uint32_t run_length_=0;
    bool in_embedded_=false,have_good_=false,trace_enabled_=false;

    bool marker_rejected(std::uint64_t rec_start,std::uint64_t rec_end) const noexcept {
        if(rec_end<rec_start || rec_end-rec_start>=record_history_.size()) return false;
        for(std::uint64_t rec=rec_start;rec<=rec_end;++rec) {
            const auto& x=record_history_[rec % record_history_.size()];
            if(x.record==rec && x.rejected)return true;
        }
        return false;
    }
    void save_trace(TraceRow row) noexcept {
        row.id=++stats_.trace_saved;
        stats_.trace[(row.id-1)%kTraceCapacity]=row;
    }
    void finish_run() noexcept {
        const std::uint64_t start_record=run_start_/kHostColumns;
        const std::uint64_t end_record=(absolute_column_-1)/kHostColumns;
        const bool crossed=start_record!=end_record;
        TraceRow row{};
        row.host_record=end_record;
        row.marker_start_record=start_record;
        row.marker_start_offset=static_cast<std::uint32_t>(run_start_%kHostColumns);
        row.marker_end_record=end_record;
        row.marker_end_offset=static_cast<std::uint32_t>((absolute_column_-1)%kHostColumns);
        row.marker_length=run_length_;
        row.crossed_host_boundary=crossed;
        row.rejected_marker_host_record=marker_rejected(start_record,end_record);
        if (run_length_==16) {
            ++stats_.embedded_runs_16;
            if(crossed)++stats_.good_runs_cross_host;
            if (have_good_) {
                const std::uint64_t spacing=run_start_-last_good_start_;
                row.previous_marker_record=last_good_start_/kHostColumns;
                row.previous_marker_offset=static_cast<std::uint32_t>(last_good_start_%kHostColumns);
                row.spacing=spacing;
                row.delta_from_971=static_cast<std::int64_t>(spacing)-971;
                if(spacing<=kHistogramMax)++stats_.interval_hist[spacing];
                else ++stats_.interval_gt_4096;
                if(spacing==971)++stats_.intervals_971;
                else if(spacing==976)++stats_.intervals_976;
                else ++stats_.intervals_other;
                if(spacing>=16) {
                    const auto data_cols=spacing-16;
                    ++stats_.verified_frames;
                    if(data_cols==955)++stats_.frames_955;
                    else if(data_cols==960)++stats_.frames_960;
                    else ++stats_.frames_other;
                }
                if (spacing!=971 && spacing!=976) {
                    ++stats_.trace_spacing_seen;
                    if(row.marker_start_offset<16 || row.marker_start_offset>=960)
                        ++stats_.other_intervals_start_close_to_host_edge;
                    // Keep at most about one sample per 32 OTHER intervals.
                    if(trace_enabled_ && stats_.trace_spacing_seen%32==1) {
                        row.kind='S';save_trace(row);
                    }
                } else if (trace_enabled_ && spacing==971 && stats_.intervals_971%2048==1) {
                    row.kind='G';save_trace(row);
                }
            }
            last_good_start_=run_start_;have_good_=true;
        } else {
            ++stats_.embedded_runs_bad;
            if(crossed)++stats_.bad_runs_cross_host;
            if(run_length_<=256)++stats_.bad_run_hist[run_length_];
            else ++stats_.bad_run_gt_256;
            ++stats_.trace_bad_run_seen;
            if(trace_enabled_) {row.kind='B';save_trace(row);}
            // Cannot bridge two valid markers over a malformed signature.
            have_good_=false;
        }
        in_embedded_=false;run_length_=0;
    }
};
} // namespace raw2shadow
