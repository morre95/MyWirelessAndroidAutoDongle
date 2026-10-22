#!/bin/sh
# SPDX-License-Identifier: MIT
# The preceding radio stage must succeed in this boot's fresh log directory.
set -u
[ "$#" -eq 1 ] && [ -d "$1" ] || exit 2
logdir=$1
sysfs=${RADXA_SYSFS_ROOT:-/sys}
modules=${RADXA_MODULE_DIR:-/modules}
socket=${RADXA_DBUS_SOCKET:-/run/dbus/system_bus_socket}
export DBUS_SYSTEM_BUS_ADDRESS="unix:path=$socket"
attach_pid= bluez_pid= dbus_pid=
stage=starting
printf 'BT_PAIRING_RESULT=pending\n' >"$logdir/bluetooth-result.txt" || exit 20

cleanup() {
    for pid in "$bluez_pid" "$attach_pid" "$dbus_pid"; do
        [ -z "$pid" ] || kill "$pid" 2>/dev/null || :
    done
    [ -z "$bluez_pid$attach_pid$dbus_pid" ] || sleep 1
    for pid in "$bluez_pid" "$attach_pid" "$dbus_pid"; do
        if [ -n "$pid" ]; then
            kill -KILL "$pid" 2>/dev/null || :
            wait "$pid" 2>/dev/null || :
        fi
    done
}
trap cleanup EXIT
fail() {
    printf 'BT_PAIRING_RESULT=failed\nSTAGE=%s\nEXIT_CODE=%s\n' "$stage" "$1" \
        >"$logdir/bluetooth-result.txt"
    sync
    exit "$1"
}
trap 'fail 15' HUP INT TERM
mark() {
    stage=$1
    read -r uptime rest </proc/uptime
    printf '%s %s\n' "$uptime" "$stage" >>"$logdir/bluetooth-progress.txt" || exit 20
    sync || exit 20
}
alive() { kill -0 "$1" 2>/dev/null; }

mark prerequisite
[ "$(uname -r)" = 6.12.114 ] || fail 10
grep -qx 'RADIO_RESET_RESULT=success' "$logdir/radio-result.txt" || fail 10
for module in ecc ecdh_generic cmac bluetooth pwrseq-core btbcm btqca hci_uart; do
    mark "load_$module"
    timeout -s KILL 10 insmod "$modules/$module.ko" || fail "$?"
done

mark hci_attach
hciattach -n -t 10 -s 1500000 /dev/ttyS1 any 1500000 flow >"$logdir/hciattach.log" 2>&1 &
attach_pid=$!
attempt=0
while [ ! -d "$sysfs/class/bluetooth/hci0" ]; do
    alive "$attach_pid" && [ "$attempt" -lt 15 ] || fail 11
    attempt=$((attempt + 1)); sleep 1
done
alive "$attach_pid" || fail 11

mark dbus_start
dbus-daemon --system --nofork --nopidfile >"$logdir/dbus.log" 2>&1 &
dbus_pid=$!
attempt=0
while ! dbus-send --system --print-reply --reply-timeout=1000 \
    --dest=org.freedesktop.DBus /org/freedesktop/DBus org.freedesktop.DBus.ListNames \
    >"$logdir/dbus-ready.txt" 2>&1; do
    alive "$dbus_pid" && alive "$attach_pid" && [ "$attempt" -lt 15 ] || fail 12
    attempt=$((attempt + 1)); sleep 1
done

mark bluez_start
bluetoothd --nodetach >"$logdir/bluetoothd.log" 2>&1 &
bluez_pid=$!
attempt=0
while ! dbus-send --system --print-reply --reply-timeout=1000 --dest=org.bluez \
    /org/bluez/hci0 org.freedesktop.DBus.Properties.Get string:org.bluez.Adapter1 \
    string:Powered >"$logdir/adapter-ready.txt" 2>&1; do
    alive "$bluez_pid" && alive "$attach_pid" && alive "$dbus_pid" && \
        [ "$attempt" -lt 15 ] || fail 13
    attempt=$((attempt + 1)); sleep 1
done

mark pairing_window
if timeout -s TERM -k 10 200 aic-pairing-test "$DBUS_SYSTEM_BUS_ADDRESS" 180 \
    >"$logdir/pairing.log" 2>&1; then pairing_status=0; else pairing_status=$?; fi
printf 'PAIRING_AGENT_EXIT=%s\n' "$pairing_status" >"$logdir/pairing-exit.txt" || exit 20
mark capture_adapter
dbus-send --system --print-reply --reply-timeout=3000 --dest=org.bluez / \
    org.freedesktop.DBus.ObjectManager.GetManagedObjects >"$logdir/bluez-objects.txt" 2>&1 || fail 14
[ "$pairing_status" -eq 0 ] || fail "$pairing_status"
alive "$bluez_pid" && alive "$attach_pid" && alive "$dbus_pid" || fail 13
mark pairing_complete
printf 'BT_PAIRING_RESULT=success\nSTAGE=%s\n' "$stage" >"$logdir/bluetooth-result.txt" || exit 20
sync || exit 20
