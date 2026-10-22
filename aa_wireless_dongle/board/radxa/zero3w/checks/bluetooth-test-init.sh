#!/bin/sh
# SPDX-License-Identifier: MIT
[ "$$" -eq 1 ] || { echo 'This init must run as PID 1 in the test image.' >&2; exit 2; }
export PATH=/bin:/sbin:/usr/bin:/usr/sbin:/usr/libexec/bluetooth
export RADXA_SYSFS_ROOT=/sys RADXA_MODULE_DIR=/modules RADXA_DBUS_SOCKET=/run/dbus/system_bus_socket
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
    attempt=$((attempt + 1)); $BB sleep 1
done
if [ -n "$logdev" ] && $BB mount -t vfat -o rw "$logdev" /logs; then
    bootid=$($BB cat /proc/sys/kernel/random/boot_id)
    logdir=/logs/$bootid
    if [ -n "$bootid" ] && $BB mkdir "$logdir"; then
        setup_status=20 radio_status=20 bluetooth_status=20
        if {
            $BB cp /bluetooth-inputs.json "$logdir/inputs.json" &&
            $BB dmesg >"$logdir/kernel-before.txt" &&
            $BB sync &&
            $BB mkdir -p /run/dbus /var/lib/dbus /var/lib/bluetooth &&
            dbus-uuidgen --ensure=/var/lib/dbus/machine-id &&
            $BB cp /var/lib/dbus/machine-id /etc/machine-id
        } >"$logdir/init.log" 2>&1; then
            setup_status=0
            if /bin/sh /aic-radio-test.sh "$logdir" >"$logdir/radio.log" 2>&1; then
                radio_status=0
                if /bin/sh /aic-bluetooth-test.sh "$logdir" >"$logdir/bluetooth.log" 2>&1; then
                    bluetooth_status=0
                else bluetooth_status=$?; fi
            else radio_status=$?; fi
        else setup_status=$?; fi
        if aic-bounded-run 10 /bin/sh /aic-bluetooth-snapshot.sh "$logdir" final - \
            >"$logdir/final-snapshot-run.log" 2>&1; then
            final_status=0 capture_finished=1
        else final_status=$? capture_finished=0; fi
        printf 'SETUP_EXIT=%s\nRADIO_STAGE_EXIT=%s\nBLUETOOTH_STAGE_EXIT=%s\nFINAL_SNAPSHOT_EXIT=%s\nCAPTURE_FINISHED=%s\n' \
            "$setup_status" "$radio_status" "$bluetooth_status" "$final_status" \
            "$capture_finished" >"$logdir/capture-result.txt"
        $BB sync
    fi
    $BB umount /logs
else echo 'No writable log partition: Bluetooth test refused.'; fi
$BB sync
$BB poweroff -f
while :; do $BB sleep 60; done
