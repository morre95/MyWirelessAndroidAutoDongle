// SPDX-License-Identifier: MIT
// Standalone feasibility helper; run only before hciattach, after radio power/firmware setup.
#define _DEFAULT_SOURCE
#include <errno.h>
#include <fcntl.h>
#include <linux/tty.h>
#include <poll.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <sys/ioctl.h>
#include <termios.h>
#include <time.h>
#include <unistd.h>

static int64_t now_ms(void)
{
    struct timespec now;
    if (clock_gettime(CLOCK_MONOTONIC, &now) < 0)
        return -1;
    return (int64_t)now.tv_sec * 1000 + now.tv_nsec / 1000000;
}

static int transfer(int fd, uint8_t *data, size_t size, bool sending, int64_t deadline)
{
    while (size) {
        int64_t now = now_ms();
        if (now < 0)
            return -1;
        if (now >= deadline) {
            errno = ETIMEDOUT;
            return -1;
        }
        struct pollfd request = {.fd = fd, .events = sending ? POLLOUT : POLLIN};
        int ready = poll(&request, 1, (int)(deadline - now));
        if (ready < 0 && errno == EINTR)
            continue;
        if (ready < 0)
            return -1;
        if (!ready) {
            errno = ETIMEDOUT;
            return -1;
        }
        if (!(request.revents & request.events)) {
            errno = EIO;
            return -1;
        }
        ssize_t count = sending ? write(fd, data, size) : read(fd, data, size);
        if (count < 0 && (errno == EAGAIN || errno == EINTR))
            continue;
        if (count < 0)
            return -1;
        if (!count) {
            errno = EIO;
            return -1;
        }
        data += count;
        size -= (size_t)count;
    }
    return 0;
}

static int reset_controller(int fd)
{
    // H4 command packet, HCI Reset opcode 0x0c03, no command parameters.
    uint8_t command[] = {0x01, 0x03, 0x0c, 0x00};
    int64_t start = now_ms();
    if (start < 0)
        return -1;
    int64_t deadline = start + 2000;
    if (transfer(fd, command, sizeof(command), true, deadline) < 0)
        return -1;
    for (;;) {
        uint8_t header[3], payload[255];
        if (transfer(fd, header, 1, false, deadline) < 0)
            return -1;
        if (header[0] != 0x04) {
            errno = EPROTO;
            return -1;
        }
        if (transfer(fd, header + 1, 2, false, deadline) < 0 ||
            transfer(fd, payload, header[2], false, deadline) < 0)
            return -1;
        if (header[1] == 0x0e) { // Command Complete, including opcode and status.
            if (header[2] < 3) {
                errno = EPROTO;
                return -1;
            }
            if (payload[1] != 0x03 || payload[2] != 0x0c)
                continue;
            if (header[2] != 4) {
                errno = EPROTO;
                return -1;
            }
            if (payload[3] != 0) {
                errno = EIO;
                return -1;
            }
            return 0;
        }
        if (header[1] == 0x0f && header[2] == 4 &&
            payload[2] == 0x03 && payload[3] == 0x0c && payload[0] != 0) {
            errno = EIO;
            return -1;
        }
        // Other events and successful Command Status do not prove reset completion.
    }
}

int main(int argc, char **argv)
{
    if (argc != 2) {
        fprintf(stderr, "Usage: %s UART_DEVICE\n", argv[0]);
        return 2;
    }
    int fd = open(argv[1], O_RDWR | O_NOCTTY | O_NONBLOCK | O_CLOEXEC);
    if (fd < 0) {
        perror("Cannot open UART");
        return 1;
    }
    int result = 1, discipline, exclusive;
    bool locked = false, restore = false;
    struct termios original, settings;
    if (ioctl(fd, TIOCGETD, &discipline) < 0)
        goto done;
    if (discipline != N_TTY) {
        errno = EBUSY;
        goto done;
    }
    if (ioctl(fd, TIOCGEXCL, &exclusive) < 0)
        goto done;
    if (exclusive) {
        errno = EBUSY;
        goto done;
    }
    if (ioctl(fd, TIOCEXCL) < 0)
        goto done;
    locked = true;
    if (tcgetattr(fd, &original) < 0)
        goto done;
    restore = true;
    settings = original;
    cfmakeraw(&settings);
    settings.c_iflag &= ~(tcflag_t)(IXON | IXOFF | IXANY);
    settings.c_cflag &= ~(tcflag_t)(PARENB | CSTOPB | CSIZE);
    settings.c_cflag |= CS8 | CLOCAL | CREAD | CRTSCTS;
    settings.c_cc[VMIN] = 1;
    settings.c_cc[VTIME] = 0;
    if (cfsetispeed(&settings, B1500000) < 0 ||
        cfsetospeed(&settings, B1500000) < 0 ||
        tcsetattr(fd, TCSANOW, &settings) < 0 || tcflush(fd, TCIOFLUSH) < 0)
        goto done;
    if (reset_controller(fd) == 0)
        result = 0;
done:;
    int saved = errno;
    if (restore && tcsetattr(fd, TCSANOW, &original) < 0 && !result) {
        result = 1;
        saved = errno;
    }
    if (locked && ioctl(fd, TIOCNXCL) < 0 && !result) {
        result = 1;
        saved = errno;
    }
    close(fd);
    if (result) {
        errno = saved;
        perror("HCI Reset failed");
    } else {
        puts("HCI Reset complete");
    }
    return result;
}
