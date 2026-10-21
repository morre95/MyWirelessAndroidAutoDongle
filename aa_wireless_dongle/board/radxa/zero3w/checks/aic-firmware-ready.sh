#!/bin/sh
# SPDX-License-Identifier: MIT
# Read-only ordering predicate for the pinned ZERO 3W AIC SDIO candidate.
set -eu

not_ready() {
    printf 'AIC firmware not ready: %s\n' "$1" >&2
    exit 1
}

interface=${1-wlan0}
if [ "$#" -gt 1 ] || [ -z "$interface" ] || [ "${#interface}" -gt 15 ]; then
    printf 'Usage: %s [interface]\n' "$0" >&2
    exit 2
fi
case "$interface" in
    .|..|*[!a-zA-Z0-9_.-]*)
        printf 'Invalid network interface name\n' >&2
        exit 2 ;;
esac

# Override only for isolated host fixtures; runtime integration must use /sys.
sysfs=${RADXA_SYSFS_ROOT:-/sys}

expect_value() {
    value=$(cat "$1" 2>/dev/null) || not_ready "cannot read $1"
    [ "$value" = "$2" ] || not_ready "$1 must be $2"
}

# A module directory and even a netdev can appear while module_init is running.
for module in aic8800_bsp aic8800_fdrv; do
    expect_value "$sysfs/module/$module/initstate" live
done

expect_value "$sysfs/module/aic8800_bsp/parameters/testmode" 0
grep -q '^Current: 0, firmware info:$' "$sysfs/devices/platform/aic-bsp/cpmode" \
    2>/dev/null || not_ready 'BSP must report normal work mode'

device=$sysfs/class/net/$interface/device
expect_value "$device/vendor" 0xc8a1
expect_value "$device/device" 0x0082

driver=$(readlink -f "$device/driver") || not_ready 'no SDIO driver binding'
expected=$(readlink -f "$sysfs/bus/sdio/drivers/aicwf_sdio") || \
    not_ready 'no AIC SDIO driver'
[ -d "$driver" ] && [ "$driver" = "$expected" ] || \
    not_ready 'interface must use aicwf_sdio'

owner=$(readlink -f "$device/driver/module") || not_ready 'no driver module'
expected=$(readlink -f "$sysfs/module/aic8800_fdrv") || not_ready 'no fdrv module'
[ "$owner" = "$expected" ] || not_ready 'SDIO driver must belong to aic8800_fdrv'

# This does not replace a successful HCI Reset or protect against later removal.
printf 'AIC firmware load ordering ready: %s\n' "$interface"
