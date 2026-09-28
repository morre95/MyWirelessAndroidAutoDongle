#pragma once

#include <optional>
#include <mutex>
#include <thread>
#include <list>
#include <map>
#include <functional>

typedef std::map<std::string, std::string> UeventEnv;

class UeventMonitor {
public:
    static UeventMonitor& instance();

    std::optional<std::thread> start();

    /**
     * Add a handler to be called for upcoming uevents, the handler will be called on the monitor thread.
     * The handler should check if the event is interesting to it, and act on the event if interesting.
     * The handler should return a boolean. If returned true, the handler is removed and will no longer recieve any more callbacks.
     * 
     * @param handler Handler to be called for every upcoming uevent.
     */
    void addHandler(std::function<bool(UeventEnv)> handler);

private:
    UeventMonitor() {};
    UeventMonitor(UeventMonitor const&) = delete;
    UeventMonitor& operator=(UeventMonitor const&) = delete;

    void monitorLoop(int nl_socket);

    std::mutex handlersMutex;
    std::list<std::function<bool(UeventEnv)>> handlers;
};
