#pragma once

#include <string>
#include <chrono>

class UsbManager {
public:
    static UsbManager& instance();

    void init();
    bool enableDefaultAndWaitForAccessory(std::chrono::milliseconds timeout = std::chrono::milliseconds(0));
    void switchToAccessoryGadget();
    void disableGadget();

private:
    UsbManager();
    UsbManager(UsbManager const&) = delete;
    UsbManager& operator=(UsbManager const&) = delete;

    int writeGadgetFile(std::string gadgetName, std::string relativeFilePath, const char* content);
    void enableGadget(std::string name);
    void disableGadget(std::string name);

    static std::string s_udcName; 
};