#!/bin/sh
# SPDX-License-Identifier: MIT
# Diagnostic stages only: no AP, hciattach, BlueZ, network provisioning or btlpm.
set -u
[ "$#" -eq 1 ] && [ -d "$1" ] || exit 2
logdir=$1
sysfs=${RADXA_SYSFS_ROOT:-/sys}
modules=${RADXA_MODULE_DIR:-/modules}
stage=starting
printf 'RADIO_RESET_RESULT=pending\n' >"$logdir/radio-result.txt" || exit 20

mark() {
    stage=$1
    read -r uptime rest </proc/uptime
    printf '%s %s\n' "$uptime" "$stage" >>"$logdir/progress.txt" || exit 20
    sync || exit 20
}

fail() {
    printf 'RADIO_RESET_RESULT=failed\nSTAGE=%s\nEXIT_CODE=%s\n' \
        "$stage" "$1" >"$logdir/radio-result.txt" || exit 20
    sync
    exit "$1"
}

sdio_present() {
    first=0 second=0
    for device in "$sysfs"/bus/sdio/devices/*; do
        [ "$(cat "$device/vendor" 2>/dev/null)" = 0xc8a1 ] || continue
        case "$(cat "$device/device" 2>/dev/null)" in
            0x0082) first=1 ;;
            0x0182) second=1 ;;
        esac
    done
    [ "$first$second" = 11 ]
}

mark kernel
[ "$(uname -r)" = 6.12.114 ] || fail 10
mark sdio_wait
attempt=0
while ! sdio_present; do
    [ "$attempt" -lt 30 ] || fail 11
    attempt=$((attempt + 1))
    sleep 1
done

for module in rfkill cfg80211 aic8800_bsp aic8800_fdrv; do
    mark "load_$module"
    # Timeout is a userspace bound, not a guarantee against a stuck kernel task.
    timeout -s KILL 30 insmod "$modules/$module.ko" || fail "$?"
done

mark firmware_ready
attempt=0
while ! aic-firmware-ready.sh wlan0; do
    [ "$attempt" -lt 30 ] || fail 12
    attempt=$((attempt + 1))
    sleep 1
done

mark hci_reset
timeout -s KILL 5 aic-hci-reset /dev/ttyS1 || fail "$?"
mark reset_complete
printf 'RADIO_RESET_RESULT=success\nSTAGE=%s\n' "$stage" >"$logdir/radio-result.txt" || exit 20
sync || exit 20
