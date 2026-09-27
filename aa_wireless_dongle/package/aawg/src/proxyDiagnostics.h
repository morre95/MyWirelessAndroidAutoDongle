#pragma once

#include <algorithm>
#include <chrono>
#include <cstdint>
#include <cerrno>
#include <netinet/in.h>
#include <netinet/tcp.h>
#include <sys/socket.h>

#include "common.h"

inline int setProxyTcpNoDelay(int fd, bool enabled) {
    const int value = enabled ? 1 : 0;
    return setsockopt(fd, IPPROTO_TCP, TCP_NODELAY, &value, sizeof(value));
}

// Owned by one forwarding thread. Read times include normal idle time and are
// not, on their own, evidence of a network fault or an audio underrun.
class ProxyDiagnostics {
public:
    using Clock = std::chrono::steady_clock;

    ProxyDiagnostics(bool enabled, const char* direction, int tcp_fd,
                     Clock::time_point now = Clock::now())
        : enabled(enabled), direction(direction), tcp_fd(tcp_fd), last_report(now) {}

    Clock::time_point begin() const {
        return enabled ? Clock::now() : Clock::time_point{};
    }

    void readCompleted(Clock::time_point start, ssize_t bytes) {
        if (enabled) record(read_stats, Clock::now() - start, bytes);
    }

    void writeCompleted(Clock::time_point start, ssize_t bytes) {
        if (enabled) record(write_stats, Clock::now() - start, bytes);
    }

    void report(bool final = false, Clock::time_point now = {}) {
        if (!enabled) return;
        if (now == Clock::time_point{}) now = Clock::now();
        if (!final && now - last_report < std::chrono::seconds(5)) return;
        if (!read_stats.calls && !write_stats.calls) return;

        // Diagnostics must not replace the errno from a failed read/write.
        const int saved_errno = errno;
        Logger::instance()->info(
            "Proxy stats %s%s: window_ms=%lld read_calls=%llu read_bytes=%llu "
            "read_wait_max_us=%lld read_wait_ge20ms=%llu "
            "write_calls=%llu write_bytes=%llu write_max_us=%lld write_ge20ms=%llu\n",
            direction, final ? " final" : "",
            static_cast<long long>(std::chrono::duration_cast<std::chrono::milliseconds>(now - last_report).count()),
            read_stats.calls, read_stats.bytes, read_stats.max_us, read_stats.slow,
            write_stats.calls, write_stats.bytes, write_stats.max_us, write_stats.slow);

        if (tcp_fd >= 0) {
            struct tcp_info info = {};
            socklen_t length = sizeof(info);
            if (getsockopt(tcp_fd, IPPROTO_TCP, TCP_INFO, &info, &length) == 0) {
                Logger::instance()->info(
                    "Proxy TCP: rtt_us=%u unacked=%u pi_retrans_total=%u\n",
                    info.tcpi_rtt, info.tcpi_unacked, info.tcpi_total_retrans);
            }
        }

        read_stats = {};
        write_stats = {};
        last_report = now;
        errno = saved_errno;
    }

private:
    struct IoStats {
        unsigned long long calls = 0, bytes = 0, slow = 0;
        long long max_us = 0;
    };

    static void record(IoStats& stats, Clock::duration elapsed, ssize_t bytes) {
        const auto us = std::chrono::duration_cast<std::chrono::microseconds>(elapsed).count();
        ++stats.calls;
        if (bytes > 0) stats.bytes += static_cast<unsigned long long>(bytes);
        stats.max_us = std::max(stats.max_us, static_cast<long long>(us));
        if (us >= 20000) ++stats.slow;
    }

    bool enabled;
    const char* direction;
    int tcp_fd;
    Clock::time_point last_report;
    IoStats read_stats, write_stats;
};
