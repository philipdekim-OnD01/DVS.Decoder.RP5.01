#define main engine_entry_for_test
#include "engine.cpp"
#undef main
#include <cassert>
int main(){
 Queue q(2);Packet a,b,c;a.sequence=1;b.sequence=2;c.sequence=3;
 assert(q.push(std::move(a),true));assert(q.push(std::move(b),true));assert(q.push(std::move(c),true));
 assert(q.items.size()==2&&q.high==2&&q.drops==1&&q.items.front().sequence==2&&q.items.front().gap);
 Queue single(1);Packet x,y;x.sequence=1;y.sequence=2;single.push(std::move(x),true);single.push(std::move(y),true);
 assert(single.items.size()==1&&single.items.front().gap&&single.drops==1);
 Queue stopping(1);Packet z;stopping.push(std::move(z),false);std::atomic<bool> finished=false;
 std::thread blocked([&]{Packet p;assert(!stopping.push(std::move(p),false));finished=true;});
 std::this_thread::sleep_for(std::chrono::milliseconds(10));{std::lock_guard lock(stopping.mutex);stopping.stop=true;}
 stopping.ready.notify_all();blocked.join();assert(finished);
}
