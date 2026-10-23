#!/bin/bash

set -u
set -e
set -x

BOARD_DIR="$(dirname "$0")"

mkdir -p ${TARGET_DIR}/boot
mv ${TARGET_DIR}/etc/aawgd.conf ${BINARIES_DIR}/aawgd.conf
ln -sf /boot/aawgd.conf ${TARGET_DIR}/etc/aawgd.conf

install -m 0644 "${BOARD_DIR}/extlinux.conf" ${BINARIES_DIR}/extlinux.conf
