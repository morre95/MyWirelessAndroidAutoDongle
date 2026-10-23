#!/bin/sh
# SPDX-License-Identifier: MIT
# Emit reference-OS diagnostic configuration into a new directory; install nothing.
set -eu
if [ "$#" -ne 1 ]; then
    printf 'Usage: %s new-output-directory\n' "$0" >&2
    exit 2
fi
umask 077
mkdir -- "$1"

cat > "$1/reset.conf" <<'UNIT'
[Service]
UnsetEnvironment=RADXA_SYSFS_ROOT
ExecStart=
# Radxa's Debian package filenames have _sdio; sysfs uses internal module names.
ExecStartPre=/usr/sbin/modprobe aic8800_fdrv_sdio
ExecStartPre=/bin/sh /var/lib/radxa-aic-startup-test/aic-firmware-ready.sh wlan0
ExecStart=/var/lib/radxa-aic-startup-test/aic-hci-reset /dev/ttyS1
TimeoutStartSec=30s
RemainAfterExit=yes
UNIT

cat > "$1/attach.conf" <<'UNIT'
[Unit]
Requires=rsetup-aic8800-reset@ttyS1.service
After=rsetup-aic8800-reset@ttyS1.service
UNIT

cat > "$1/bluez.conf" <<'UNIT'
[Unit]
Requires=rsetup-hciattach@ttyS1.service
After=rsetup-hciattach@ttyS1.service
UNIT

cat > "$1/radxa-aic-startup-rollback.service" <<'UNIT'
[Unit]
Description=Restore reference Bluetooth after the Radxa AIC startup experiment
StartLimitIntervalSec=180s
StartLimitBurst=3

[Service]
Type=oneshot
ExecStart=/bin/sh /var/lib/radxa-aic-startup-test/rollback.sh
TimeoutStartSec=60s
Restart=on-failure
RestartSec=10s
UNIT

cat > "$1/radxa-aic-startup-rollback.timer" <<'UNIT'
[Unit]
Description=Restore reference Bluetooth three minutes after boot

[Timer]
OnBootSec=180s
AccuracySec=1s
Unit=radxa-aic-startup-rollback.service

[Install]
WantedBy=timers.target
UNIT

cat > "$1/rollback.sh" <<'SCRIPT'
#!/bin/sh
# The experiment owns only these three named drop-ins. Keep vendor files intact.
set -eu
base=/var/lib/radxa-aic-startup-test
printf 'Restoring the reference Bluetooth service configuration\n'
rm -f -- \
    /etc/systemd/system/rsetup-aic8800-reset@ttyS1.service.d/90-radxa-aic-startup-test.conf \
    /etc/systemd/system/rsetup-hciattach@ttyS1.service.d/90-radxa-aic-startup-test.conf \
    /etc/systemd/system/bluetooth.service.d/90-radxa-aic-startup-test.conf
systemctl disable --now radxa-aic-startup-rollback.timer
systemctl daemon-reload
systemctl stop bluetooth.service rsetup-hciattach@ttyS1.service rsetup-aic8800-reset@ttyS1.service
# A never-started BlueZ unit may be unloaded after daemon-reload. Starting it
# below loads it; reset-failed on an unloaded unit would abort recovery.
systemctl start rsetup-hciattach@ttyS1.service
systemctl start bluetooth.service
timeout 10 bluetoothctl power on >/dev/null
touch "$base/rolled-back"
printf 'Reference hciattach and BlueZ restored\n'
SCRIPT
