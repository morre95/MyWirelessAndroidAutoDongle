#!/bin/sh
# SPDX-License-Identifier: MIT
[ "$$" -eq 1 ] || { echo 'This init must run as PID 1 in the test image.' >&2; exit 2; }
export PATH=/bin RADXA_SYSFS_ROOT=/sys RADXA_MODULE_DIR=/modules
BB=/bin/busybox
$BB mount -t devtmpfs devtmpfs /dev
exec </dev/console >/dev/console 2>&1
$BB mount -t proc proc /proc || exec $BB sh
$BB mount -t sysfs sysfs /sys || exec $BB sh
$BB mount -t debugfs debugfs /sys/kernel/debug

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

# Refuse radio actions unless persistent diagnostic storage is available.
if [ -n "$logdev" ] && $BB mount -t vfat -o rw "$logdev" /logs; then
    bootid=$($BB cat /proc/sys/kernel/random/boot_id)
    logdir=/logs/$bootid
    if [ -n "$bootid" ] && $BB mkdir "$logdir"; then
        $BB cp /radio-inputs.json "$logdir/inputs.json"
        $BB dmesg >"$logdir/kernel-before.txt"
        $BB sync
        if /bin/sh /aic-radio-test.sh "$logdir" >"$logdir/radio.log" 2>&1; then
            status=0
        else
            status=$?
        fi
        {
            $BB uname -a
            $BB cat /proc/cmdline /proc/modules /sys/kernel/debug/gpio
            for entry in /sys/bus/sdio/devices/*/uevent; do
                [ -f "$entry" ] && { echo "$entry"; $BB cat "$entry"; }
            done
            $BB ls -l /sys/class/net /sys/class/tty/ttyS1 /sys/class/udc
        } >"$logdir/hardware.txt" 2>&1
        $BB dmesg >"$logdir/dmesg.txt"
        $BB cp /sys/firmware/fdt "$logdir/live.dtb"
        printf 'RADIO_STAGE_EXIT=%s\nCAPTURE_FINISHED=1\n' "$status" \
            >"$logdir/capture-result.txt"
        $BB sync
    fi
    $BB umount /logs
else
    echo 'No writable log partition: radio test refused.'
fi
$BB sync
$BB poweroff -f
while :; do $BB sleep 60; done
