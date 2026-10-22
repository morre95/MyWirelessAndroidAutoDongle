#!/bin/sh
# SPDX-License-Identifier: MIT
# PID 1 for the offline boot-only experiment. No modules, firmware or network.
[ "$$" -eq 1 ] || { echo 'This init must run as PID 1 in the test image.' >&2; exit 2; }
export PATH=/bin
BB=/bin/busybox
$BB mount -t devtmpfs devtmpfs /dev
exec </dev/console >/dev/console 2>&1
$BB mount -t proc proc /proc || exec $BB sh
$BB mount -t sysfs sysfs /sys || exec $BB sh
$BB mount -t debugfs debugfs /sys/kernel/debug

capture() {
    echo 'INIT_REACHED=1'
    $BB uname -a
    echo '--- command line and device-tree identity ---'
    $BB cat /proc/cmdline /proc/device-tree/model /proc/device-tree/compatible
    echo
    echo '--- MMC and SDIO ---'
    $BB cat /proc/partitions
    for entry in /sys/bus/sdio/devices/*/uevent; do
        [ -f "$entry" ] && { echo "$entry"; $BB cat "$entry"; }
    done
    echo '--- GPIO ownership and levels ---'
    $BB cat /sys/kernel/debug/gpio
    echo '--- pin configuration ---'
    for entry in /sys/kernel/debug/pinctrl/*/pinconf-pins; do
        [ -f "$entry" ] && { echo "$entry"; $BB cat "$entry"; }
    done
    echo '--- UART1 and USB device controllers ---'
    $BB cat /proc/device-tree/aliases/serial1
    echo
    $BB ls -l /sys/class/tty/ttyS1 /sys/class/udc
    echo '--- loaded modules (none are requested by this init) ---'
    $BB cat /proc/modules
}

# Poll for the diagnostic log partition, never a hard-coded MMC index.
logdev=
attempt=0
while [ "$attempt" -lt 60 ] && [ -z "$logdev" ]; do
    for partition in /dev/mmcblk*p2; do
        [ -b "$partition" ] || continue
        case "$($BB blkid "$partition")" in
            *'LABEL="AICBOOTLOGS"'*) logdev=$partition; break ;;
        esac
    done
    [ -n "$logdev" ] && break
    attempt=$((attempt + 1))
    $BB sleep 1
done

if [ -n "$logdev" ] && $BB mount -t vfat -o rw "$logdev" /logs; then
    bootid=$($BB cat /proc/sys/kernel/random/boot_id)
    logdir=/logs/$bootid
    if $BB mkdir "$logdir"; then
        capture >"$logdir/hardware.txt" 2>&1
        $BB dmesg >"$logdir/dmesg.txt"
        $BB cp /sys/firmware/fdt "$logdir/live.dtb"
        if [ "$($BB uname -r)" = '6.12.114' ]; then
            echo 'EXPECTED_KERNEL=1' >"$logdir/result.txt"
        else
            echo 'EXPECTED_KERNEL=0' >"$logdir/result.txt"
        fi
        echo 'CAPTURE_FINISHED=1' >>"$logdir/result.txt"
        $BB sync
    fi
    $BB umount /logs
else
    echo 'No writable diagnostic log partition; console evidence only.'
    capture
    $BB dmesg
fi

# No automatic reboot loop. Successful poweroff may depend on board support.
$BB sync
$BB poweroff -f
while :; do $BB sleep 60; done
