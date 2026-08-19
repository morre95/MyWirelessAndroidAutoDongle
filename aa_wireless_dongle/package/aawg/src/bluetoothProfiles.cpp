#include <stdio.h>
#include <thread>
#include <unistd.h>
#include <fcntl.h>
#include <errno.h>
#include <string.h>
#include <arpa/inet.h>
#include <vector>

#include "common.h"
#include "bluetoothHandler.h"
#include "bluetoothProfiles.h"

#include <google/protobuf/message_lite.h>
#include "proto/WifiStartRequest.pb.h"
#include "proto/WifiInfoResponse.pb.h"

static constexpr const char* INTERFACE_BLUEZ_PROFILE = "org.bluez.Profile1";


#pragma region BluezProfile
BluezProfile::BluezProfile(DBus::Path path): DBus::Object(path) {
    this->create_method<void(void)>(INTERFACE_BLUEZ_PROFILE, "Release", sigc::mem_fun(*this, &BluezProfile::Release));
    this->create_method<void(DBus::Path, std::shared_ptr<DBus::FileDescriptor>, DBus::Properties)>(INTERFACE_BLUEZ_PROFILE ,"NewConnection", sigc::mem_fun(*this, &BluezProfile::NewConnection));
    this->create_method<void(DBus::Path)>(INTERFACE_BLUEZ_PROFILE, "RequestDisconnection", sigc::mem_fun(*this, &BluezProfile::RequestDisconnection));
}
#pragma endregion BluezProfile


#pragma region AAWirelessLauncher
class AAWirelessLauncher {
public:
    AAWirelessLauncher(int fd): m_fd(fd) {};

    void launch() {
        // Make fd blocking
        int fd_flags = fcntl(m_fd, F_GETFL);
        fcntl(m_fd, F_SETFL, fd_flags & ~O_NONBLOCK);

        WifiInfo wifiInfo = Config::instance()->getWifiInfo();

        Logger::instance()->info("Sending WifiStartRequest (ip: %s, port: %d)\n", wifiInfo.ipAddress.c_str(), wifiInfo.port);
        WifiStartRequest wifiStartRequest;
        wifiStartRequest.set_ip_address(wifiInfo.ipAddress);
        wifiStartRequest.set_port(wifiInfo.port);

        if (!SendMessage(MessageId::WifiStartRequest, &wifiStartRequest)) {
            return;
        }

        MessageId messageId = ReadMessage();

        if (messageId != MessageId::WifiInfoRequest) {
            Logger::instance()->info("Expected WifiInfoRequest, got %s (%d). Abort.\n", MessageName(messageId).c_str(), static_cast<int>(messageId));
            return;
        }

        Logger::instance()->info("Sending WifiInfoResponse (ssid: %s, bssid: %s)\n", wifiInfo.ssid.c_str(), wifiInfo.bssid.c_str());
        WifiInfoResponse wifiInfoResponse;
        wifiInfoResponse.set_ssid(wifiInfo.ssid);
        wifiInfoResponse.set_key(wifiInfo.key);
        wifiInfoResponse.set_bssid(wifiInfo.bssid);
        wifiInfoResponse.set_security_mode(wifiInfo.securityMode);
        wifiInfoResponse.set_access_point_type(wifiInfo.accessPointType);

        if (!SendMessage(MessageId::WifiInfoResponse, &wifiInfoResponse)) {
            return;
        }

        ReadMessage();
        ReadMessage();
    }

private:
    enum class MessageId {
        Invalid = -1,
        WifiStartRequest = 1,
        WifiInfoRequest = 2,
        WifiInfoResponse = 3,
        WifiVersionRequest = 4,
        WifiVersionResponse = 5,
        WifiConnectStatus = 6,
        WifiStartResponse = 7,
    };
    std::string MessageName(MessageId messageId) {
        switch (messageId) {
            case MessageId::WifiStartRequest:
                return "WifiStartRequest";
            case MessageId::WifiInfoRequest:
                return "WifiInfoRequest";
            case MessageId::WifiInfoResponse:
                return "WifiInfoResponse";
            case MessageId::WifiVersionRequest:
                return "WifiVersionRequest";
            case MessageId::WifiVersionResponse:
                return "WifiVersionResponse";
            case MessageId::WifiConnectStatus:
                return "WifiConnectStatus";
            case MessageId::WifiStartResponse:
                return "WifiStartResponse";
            default:
                return "UNKNOWN";
        }
    }

    bool WriteFully(const unsigned char* buffer, size_t length) {
        size_t remainingBytes = length;
        while (remainingBytes > 0) {
            ssize_t wrote = write(m_fd, buffer, remainingBytes);

            if (wrote < 0 && errno == EINTR) {
                continue;
            }
            if (wrote < 0) {
                return false;
            }
            if (wrote == 0) {
                errno = EIO;
                return false;
            }

            buffer += wrote;
            remainingBytes -= wrote;
        }

        return true;
    }

    bool ReadFully(unsigned char* buffer, size_t length) {
        size_t remainingBytes = length;
        while (remainingBytes > 0) {
            ssize_t readBytes = read(m_fd, buffer, remainingBytes);

            if (readBytes < 0 && errno == EINTR) {
                continue;
            }
            if (readBytes < 0) {
                return false;
            }
            if (readBytes == 0) {
                errno = ECONNRESET;
                return false;
            }

            buffer += readBytes;
            remainingBytes -= readBytes;
        }

        return true;
    }

    bool SendMessage(MessageId messageId, google::protobuf::MessageLite* message) {
        uint16_t messageSize = (uint16_t)message->ByteSizeLong();
        uint16_t length = messageSize + 4;

        std::vector<unsigned char> buffer(length);

        uint16_t networkShort = 0;
        networkShort = htons(messageSize);
        memcpy(buffer.data(), &networkShort, sizeof(networkShort));

        networkShort = htons(static_cast<uint16_t>(messageId));
        memcpy(buffer.data() + 2, &networkShort, sizeof(networkShort));

        if (!message->SerializeToArray(buffer.data() + 4, messageSize)) {
            Logger::instance()->info("Error serializing %s, messageId: %d\n", MessageName(messageId).c_str(), static_cast<int>(messageId));
            return false;
        }

        if (!WriteFully(buffer.data(), buffer.size())) {
            Logger::instance()->info("Error sending %s, messageId: %d: %s\n", MessageName(messageId).c_str(), static_cast<int>(messageId), strerror(errno));
            return false;
        }

        Logger::instance()->info("Sent %s, messageId: %d, wrote %zu bytes\n", MessageName(messageId).c_str(), static_cast<int>(messageId), buffer.size());
        return true;
    }

    MessageId ReadMessage() {
        uint16_t networkShort = 0;
        if (!ReadFully(reinterpret_cast<unsigned char*>(&networkShort), sizeof(networkShort))) {
            Logger::instance()->info("Error reading message length: %s\n", strerror(errno));
            return MessageId::Invalid;
        }
        uint16_t length = ntohs(networkShort);

        if (!ReadFully(reinterpret_cast<unsigned char*>(&networkShort), sizeof(networkShort))) {
            Logger::instance()->info("Error reading message id: %s\n", strerror(errno));
            return MessageId::Invalid;
        }
        MessageId messageId = static_cast<MessageId>(ntohs(networkShort));

        Logger::instance()->info("Read %s. length: %d, messageId: %d\n", MessageName(messageId).c_str(), length, static_cast<int>(messageId));

        std::vector<unsigned char> buffer(length);
        if (length > 0 && !ReadFully(buffer.data(), buffer.size())) {
            Logger::instance()->info("Error reading %s payload: %s\n", MessageName(messageId).c_str(), strerror(errno));
            return MessageId::Invalid;
        }

        return messageId;
    }

    int m_fd;
};
#pragma endregion AAWirelessLauncher

#pragma region AAWirelessProfile
void AAWirelessProfile::Release() {
    Logger::instance()->info("AA Wireless Release\n");
}

void AAWirelessProfile::NewConnection(DBus::Path path, std::shared_ptr<DBus::FileDescriptor> fd, DBus::Properties fdProperties) {
    Logger::instance()->info("AA Wireless NewConnection\n");
    Logger::instance()->info("Path: %s, fd: %d\n", path.c_str(), fd->descriptor());

    AAWirelessLauncher(fd->descriptor()).launch();
    Logger::instance()->info("Bluetooth launch sequence completed\n");
}

void AAWirelessProfile::RequestDisconnection(DBus::Path path) {
    Logger::instance()->info("AA Wireless RequestDisconnection\n");
    Logger::instance()->info("Path: %s\n", path.c_str());
}

AAWirelessProfile::AAWirelessProfile(DBus::Path path): BluezProfile(path) {};

/* static */ std::shared_ptr<AAWirelessProfile> AAWirelessProfile::create(DBus::Path path) {
    return std::shared_ptr<AAWirelessProfile>(new AAWirelessProfile(path));
}
#pragma endregion AAWirelessProfile

#pragma region HSPHSProfile
void HSPHSProfile::Release() {
    Logger::instance()->info("HSP HS Release\n");
}

void HSPHSProfile::NewConnection(DBus::Path path, std::shared_ptr<DBus::FileDescriptor> fd, DBus::Properties fdProperties) {
    Logger::instance()->info("HSP HS NewConnection\n");
    Logger::instance()->info("Path: %s, fd: %d\n", path.c_str(), fd->descriptor());
}

void HSPHSProfile::RequestDisconnection(DBus::Path path) {
    Logger::instance()->info("HSP HS RequestDisconnection\n");
    Logger::instance()->info("Path: %s\n", path.c_str());
}

HSPHSProfile::HSPHSProfile(DBus::Path path): BluezProfile(path) {};

/* static */ std::shared_ptr<HSPHSProfile> HSPHSProfile::create(DBus::Path path) {
    return std::shared_ptr<HSPHSProfile>(new HSPHSProfile(path));
}
#pragma endregion HSPHSProfile
