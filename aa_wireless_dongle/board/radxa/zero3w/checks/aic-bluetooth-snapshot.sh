#!/bin/sh
# SPDX-License-Identifier: MIT
# Run under aic-bounded-run; never read packet data, process memory or bond files.
set -u
[ "$#" -eq 3 ] && [ -d "$1" ] || exit 2
logdir=$1 phase=$2 pid=$3
case "$phase" in before_attach|failure|final) ;; *) exit 2;; esac
case "$pid" in ''|*[!0-9]*) [ "$pid" = - ] || exit 2;; esac
sysfs=${RADXA_SYSFS_ROOT:-/sys}
kernel=$phase-kernel.txt hardware=$phase-hardware.txt dt=$phase-live.dtb
if [ "$phase" = final ]; then
    kernel=dmesg.txt hardware=hardware-after-cleanup.txt dt=live.dtb
fi
status=0
dmesg >"$logdir/$kernel" 2>&1 || status=20
{
    printf 'ATTACH_PID=%s\n' "$pid"
    if [ "$pid" != - ] && [ -d "/proc/$pid" ]; then
        for field in status wchan syscall stack; do
            printf '\n/proc/%s/%s\n' "$pid" "$field"
            cat "/proc/$pid/$field" || status=20
        done
    else printf 'PROCESS_PRESENT=0\n'; fi
} >"$logdir/$phase-process.txt" 2>&1 || status=20
{
    uname -a || status=20
    cat /proc/modules /proc/interrupts || status=20
    ls -l "$sysfs/class/tty/ttyS1" "$sysfs/class/bluetooth" "$sysfs/bus/sdio/devices" || status=20
} >"$logdir/$hardware" 2>&1 || status=20
cp "$sysfs/firmware/fdt" "$logdir/$dt" || status=20
printf 'SNAPSHOT_FINISHED=1\nSNAPSHOT_STATUS=%s\n' "$status" >"$logdir/$phase-snapshot.txt" || exit 20
exit "$status"
