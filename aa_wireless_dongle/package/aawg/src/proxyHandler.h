#pragma once

#include <atomic>
#include <condition_variable>
#include <map>
#include <mutex>
#include <optional>
#include <thread>
#include <pthread.h>

class AAWProxy {
public:
    AAWProxy() = default;
    AAWProxy(const AAWProxy&) = delete;
    AAWProxy& operator=(const AAWProxy&) = delete;
    ~AAWProxy();

    std::optional<std::thread> startServer(int32_t port);

private:
    enum class ProxyDirection {
        TCP_to_USB,
        USB_to_TCP
    };

    void handleClient(int server_fd);
    void forward(ProxyDirection direction, std::atomic<bool>& should_exit);
    void stopForwarding(ProxyDirection finished, std::atomic<bool>& should_exit);

    ssize_t readFully(int fd, unsigned char *buf, size_t nbyte, std::atomic<bool>& should_exit);
    ssize_t writeFully(int fd, const unsigned char *buf, size_t nbyte, std::atomic<bool>& should_exit);
    ssize_t readMessage(int fd, unsigned char *buf, size_t nbyte, std::atomic<bool>& should_exit);
    void closeDescriptors();

    int m_usb_fd = -1;
    int m_tcp_fd = -1;

    // Forwarding threads that are still running, so they can be interrupted.
    // A thread removes itself before it exits, so every handle here is alive.
    std::mutex m_forwarding_threads_mutex;
    std::condition_variable m_forwarding_threads_changed;
    std::map<ProxyDirection, pthread_t> m_forwarding_threads;

    std::atomic<bool> m_log_communication = false;
};
