#pragma once
#include <vector>
#include <cstddef>
struct Packet { std::vector<std::byte> data; bool gap=false; unsigned sequence=0; double requeue_us=0; bool driver_error=false; };
