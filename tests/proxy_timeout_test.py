"""Exercise the production frame reader on TCP without Bluetooth or USB hardware."""
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'aa_wireless_dongle/package/aawg/src/proxyHandler.cpp'

HARNESS = r'''
#include <atomic>
#include <cassert>
#include <cerrno>
#include <chrono>
#include <csignal>
#include <cstring>
#include <thread>
#include <unistd.h>
#include <sys/socket.h>
#include <netinet/in.h>

// Compile the actual method bodies below with only their required interface.
// These readers have no member state; the full daemon requires BlueZ/USB.
class AAWProxy {
public:
    ssize_t readFully(int, unsigned char*, size_t, std::atomic<bool>&);
    ssize_t readMessage(int, unsigned char*, size_t, std::atomic<bool>&);
};

// PRODUCTION_READERS

static volatile sig_atomic_t interrupted = 0;
static void onSignal(int) { interrupted = 1; }

int main(int argc, char** argv) {
    assert(argc == 2);
    const int listener = socket(AF_INET, SOCK_STREAM, 0);
    assert(listener >= 0);
    sockaddr_in address{};
    address.sin_family = AF_INET;
    address.sin_addr.s_addr = htonl(INADDR_LOOPBACK);
    assert(bind(listener, reinterpret_cast<sockaddr*>(&address), sizeof(address)) == 0);
    assert(listen(listener, 1) == 0);
    socklen_t length = sizeof(address);
    assert(getsockname(listener, reinterpret_cast<sockaddr*>(&address), &length) == 0);
    const int phone = socket(AF_INET, SOCK_STREAM, 0);
    assert(phone >= 0);
    assert(connect(phone, reinterpret_cast<sockaddr*>(&address), sizeof(address)) == 0);
    const int proxy = accept(listener, nullptr, nullptr);
    assert(proxy >= 0);
    close(listener);
    const bool signalTest = strcmp(argv[1], "interrupted") == 0;
    const timeval timeout = signalTest ? timeval{2, 0} : timeval{0, 100000};
    assert(setsockopt(proxy, SOL_SOCKET, SO_RCVTIMEO, &timeout, sizeof(timeout)) == 0);

    const unsigned char frame[] = {1, 3, 0, 3, 'a', 'b', 'c'};
    unsigned char received[32]{};
    std::atomic<bool> stop{false};
    AAWProxy reader;
    std::thread sender;
    const bool complete = strcmp(argv[1], "fragmented") == 0 || signalTest;
    if (complete) {
        if (signalTest) {
            struct sigaction action{};
            action.sa_handler = onSignal;
            sigemptyset(&action.sa_mask);
            assert(sigaction(SIGUSR1, &action, nullptr) == 0);
        }
        const auto receiver = pthread_self();
        sender = std::thread([&] {
            if (signalTest) {
                std::this_thread::sleep_for(std::chrono::milliseconds(20));
                assert(pthread_kill(receiver, SIGUSR1) == 0);
            }
            for (const auto byte : frame) {
                std::this_thread::sleep_for(std::chrono::milliseconds(5));
                assert(write(phone, &byte, 1) == 1);
            }
        });
    } else if (strcmp(argv[1], "partial-header") == 0) {
        assert(write(phone, frame, 2) == 2);
    } else if (strcmp(argv[1], "partial-body") == 0) {
        assert(write(phone, frame, 5) == 5);
    } else if (strcmp(argv[1], "closed") == 0) {
        assert(shutdown(phone, SHUT_WR) == 0);
    } else {
        assert(strcmp(argv[1], "idle") == 0);
    }

    const ssize_t result = reader.readMessage(proxy, received, sizeof(received), stop);
    const int readError = errno;
    if (sender.joinable()) sender.join();
    if (complete) {
        assert(result == sizeof(frame));
        assert(memcmp(received, frame, sizeof(frame)) == 0);
        if (signalTest) assert(interrupted);
    } else if (strcmp(argv[1], "closed") == 0) {
        assert(result == 0);
    } else {
        assert(result == -1);
        assert(readError == EAGAIN || readError == EWOULDBLOCK);
    }
    close(proxy);
    close(phone);
}
'''


class ProxyTimeoutTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory(prefix='aawg-timeout-')
        cls.addClassCleanup(cls.tmp.cleanup)
        cls.binary = Path(cls.tmp.name) / 'proxy-timeout-test'
        source = SOURCE.read_text()
        # Extract verbatim definitions, not a reimplementation of their logic.
        readers = source[source.index('ssize_t AAWProxy::readFully('):
                         source.index('ssize_t AAWProxy::writeFully(')]
        readers += source[source.index('ssize_t AAWProxy::readMessage('):
                          source.index('void AAWProxy::forward(')]
        cpp = Path(cls.tmp.name) / 'proxy-timeout-test.cpp'
        cpp.write_text(HARNESS.replace('// PRODUCTION_READERS', readers))
        subprocess.run(['g++', '-std=c++17', '-Wall', '-Wextra', '-Werror',
                        '-pthread', str(cpp), '-o', str(cls.binary)], check=True)

    def run_case(self, case):
        # Bound the old infinite retry loop so regressions fail instead of hang.
        subprocess.run([str(self.binary), case], check=True, timeout=4)

    def test_idle_connection_times_out(self):
        self.run_case('idle')

    def test_partial_header_times_out(self):
        self.run_case('partial-header')

    def test_partial_body_times_out(self):
        self.run_case('partial-body')

    def test_fragmented_frame_is_preserved(self):
        self.run_case('fragmented')

    def test_signal_interruption_still_retries(self):
        self.run_case('interrupted')

    def test_peer_close_is_preserved(self):
        self.run_case('closed')


if __name__ == '__main__':
    unittest.main()
