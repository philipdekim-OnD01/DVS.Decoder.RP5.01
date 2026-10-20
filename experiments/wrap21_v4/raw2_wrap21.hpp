#pragma once
// Narrow opt-in correction for circular host-record marker classification.
// Does not authenticate sensor frame headers or recover missing columns.
#include <array>
#include <cstddef>
namespace raw2wrap21 {
template<std::size_t N>
int recover_first_pixel(const std::array<bool,N>& flags,int old_start,int old_length) noexcept {
    if(old_start>=0 && old_length==16) return -1;
    if(old_length!=21) return -1;
    std::size_t head=0,tail=0;
    while(head<N && flags[head])++head;
    while(tail<N && flags[N-1-tail])++tail;
    if(head==0 || tail==0 || head>16 || tail>16 || head+tail!=21 || head+tail>=N)
        return -1;
    for(std::size_t i=head;i<N-tail;++i) if(flags[i]) return -1;
    return static_cast<int>(head);
}
} // namespace raw2wrap21
