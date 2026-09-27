#include <cassert>
#include <cstdarg>
#include <cstdio>
#include <string>
#include <vector>
#include <unistd.h>

#include "proxyDiagnostics.h"

static std::vector<std::string> messages;
Logger::Logger() = default;
Logger::~Logger() = default;
Logger* Logger::instance() {
    static Logger logger;
    return &logger;
}
void Logger::info(const char* format, ...) {
    char message[1024];
    va_list args;
    va_start(args, format);
    vsnprintf(message, sizeof(message), format, args);
    va_end(args);
    messages.emplace_back(message);
    errno = EIO; // Simulate a logger changing errno.
}

int main() {
    // Exercise the actual socket option on an accepted TCP connection.
    const int listener = socket(AF_INET, SOCK_STREAM, 0);
    assert(listener >= 0);
    sockaddr_in address = {};
    address.sin_family = AF_INET;
    address.sin_addr.s_addr = htonl(INADDR_LOOPBACK);
    assert(bind(listener, reinterpret_cast<sockaddr*>(&address), sizeof(address)) == 0);
    assert(listen(listener, 1) == 0);
    socklen_t address_length = sizeof(address);
    assert(getsockname(listener, reinterpret_cast<sockaddr*>(&address), &address_length) == 0);
    const int phone = socket(AF_INET, SOCK_STREAM, 0);
    assert(phone >= 0);
    assert(connect(phone, reinterpret_cast<sockaddr*>(&address), sizeof(address)) == 0);
    const int proxy = accept(listener, nullptr, nullptr);
    assert(proxy >= 0);
    for (bool enabled : {true, false}) {
        assert(setProxyTcpNoDelay(proxy, enabled) == 0);
        int value = -1;
        socklen_t length = sizeof(value);
        assert(getsockopt(proxy, IPPROTO_TCP, TCP_NODELAY, &value, &length) == 0);
        assert(value == (enabled ? 1 : 0));
        const char payload[] = "headunit response";
        assert(write(proxy, payload, sizeof(payload)) == sizeof(payload));
        char received[sizeof(payload)] = {};
        assert(recv(phone, received, sizeof(received), MSG_WAITALL) == sizeof(received));
        assert(std::string(received) == payload);
    }
    assert(setProxyTcpNoDelay(-1, true) == -1);

    // Check aggregation, the five-second rate limit, final flushing and errno.
    using Clock = ProxyDiagnostics::Clock;
    using namespace std::chrono_literals;
    const auto start = Clock::now();
    ProxyDiagnostics diagnostics(true, "TCP->USB", proxy, start);
    diagnostics.readCompleted(Clock::now() - 25ms, 1234);
    diagnostics.writeCompleted(Clock::now() - 25ms, 1234);
    diagnostics.report(false, start + 4s);
    assert(messages.empty());
    errno = EPIPE;
    diagnostics.report(false, start + 5s);
    assert(errno == EPIPE);
    assert(messages.size() == 2);
    assert(messages[0].find("read_calls=1 read_bytes=1234") != std::string::npos);
    assert(messages[0].find("read_wait_ge20ms=1") != std::string::npos);
    assert(messages[0].find("write_ge20ms=1") != std::string::npos);
    assert(messages[1].find("Proxy TCP: rtt_us=") != std::string::npos);
    diagnostics.report(false, start + 10s);
    assert(messages.size() == 2);
    diagnostics.readCompleted(Clock::now(), -1);
    diagnostics.report(true, start + 11s);
    assert(messages.size() == 4);
    assert(messages[2].find("TCP->USB final") != std::string::npos);
    assert(messages[2].find("read_calls=1 read_bytes=0") != std::string::npos);
    assert(messages[2].find("write_calls=0 write_bytes=0") != std::string::npos);

    ProxyDiagnostics disabled(false, "USB->TCP", -1);
    disabled.readCompleted(disabled.begin(), 1234);
    disabled.writeCompleted(disabled.begin(), 1234);
    disabled.report(true);
    assert(messages.size() == 4);

    close(proxy);
    close(phone);
    close(listener);
    puts("Proxy socket and diagnostic tests passed");
}
