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

finished() {
    if aic-bounded-run --signal 0 "$1"; then probe_status=0; else probe_status=$?; fi
    case "$probe_status" in 1) return 0;; 0) ;; *) return 1;; esac
    IFS= read -r child_stat <"/proc/$1/stat" 2>/dev/null || return 1
    case "$child_stat" in *') Z '*) return 0;; esac
    return 1
}
snapshot() {
    if aic-bounded-run 5 /bin/sh "${RADXA_BT_SNAPSHOT:-/aic-bluetooth-snapshot.sh}" \
        "$logdir" "$1" "${attach_pid:--}" >"$logdir/$1-snapshot-run.log" 2>&1; then
        snapshot_status=0
    else snapshot_status=$?; fi
    printf 'SNAPSHOT_EXIT=%s\n' "$snapshot_status" >"$logdir/$1-snapshot-exit.txt"
    return "$snapshot_status"
}
cleanup() {
    original_status=$?
    trap - EXIT
    for pid in "$bluez_pid" "$attach_pid" "$dbus_pid"; do
        [ -z "$pid" ] || aic-bounded-run --signal TERM "$pid" 2>/dev/null || :
    done
    [ -z "$bluez_pid$attach_pid$dbus_pid" ] || sleep 1
    for pid in "$bluez_pid" "$attach_pid" "$dbus_pid"; do
        if [ -n "$pid" ]; then
            aic-bounded-run --signal KILL "$pid" 2>/dev/null || :
        fi
    done
    cleanup_attempt=0
    while [ "$cleanup_attempt" -lt 3 ]; do
        remaining=
        for pid in "$bluez_pid" "$attach_pid" "$dbus_pid"; do
            [ -z "$pid" ] || finished "$pid" || remaining="$remaining $pid"
        done
        [ -n "$remaining" ] || break
        cleanup_attempt=$((cleanup_attempt + 1)); sleep 1
    done
    : >"$logdir/cleanup-result.txt"
    for pid in "$bluez_pid" "$attach_pid" "$dbus_pid"; do
        [ -n "$pid" ] || continue
        if finished "$pid"; then
            if wait "$pid" 2>/dev/null; then child_status=0; else child_status=$?; fi
            printf 'CHILD_PID=%s EXIT=%s\n' "$pid" "$child_status" >>"$logdir/cleanup-result.txt"
        else
            printf 'UNREAPED_PID=%s\n' "$pid" >>"$logdir/cleanup-result.txt"
            original_status=16
        fi
    done
    if [ "$original_status" -eq 16 ]; then
        printf 'BT_PAIRING_RESULT=failed\nSTAGE=cleanup\nEXIT_CODE=16\n' >"$logdir/bluetooth-result.txt"
        printf 'CLEANUP_FINISHED=0\n' >>"$logdir/cleanup-result.txt"
    else printf 'CLEANUP_FINISHED=1\n' >>"$logdir/cleanup-result.txt"; fi
    exit "$original_status"
}
trap cleanup EXIT
fail() {
    printf 'BT_PAIRING_RESULT=failed\nSTAGE=%s\nEXIT_CODE=%s\n' "$stage" "$1" \
        >"$logdir/bluetooth-result.txt"
    cp "$logdir/bluetooth-result.txt" "$logdir/failure-result.txt" || :
    snapshot failure || :
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
alive() { aic-bounded-run --signal 0 "$1"; }

mark prerequisite
[ "$(uname -r)" = 6.12.114 ] || fail 10
aic-bounded-run --signal 0 "$$" || fail 20
grep -qx 'RADIO_RESET_RESULT=success' "$logdir/radio-result.txt" || fail 10
for module in ecc ecdh_generic cmac bluetooth pwrseq-core btbcm btqca hci_uart; do
    mark "load_$module"
    aic-bounded-run 10 insmod "$modules/$module.ko" || fail "$?"
done

snapshot before_attach || fail 20
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
if aic-bounded-run 210 aic-pairing-test "$DBUS_SYSTEM_BUS_ADDRESS" 180 \
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
