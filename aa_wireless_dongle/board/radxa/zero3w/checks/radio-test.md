# AIC mainline radio diagnostic — prepared 2026-10-22

The owner authorized publishing the existing status update and preparing this
local experiment. The update was published and verified on
[#5](https://github.com/morre95/MyWirelessAndroidAutoDongle/issues/5#issuecomment-6338740112).
This preparation has not changed the running Radxa OS, interrupted its radios
or written the microSD. Issue #5 remains open pending firmware terms/review.

## Prepared artifact and scope

Private ignored output: `buildroot/output/radxa-radio-test-20261022-v2/`.
`radxa-radio-test.img` is **224 MiB / 234,881,024 bytes**, SHA-256:

```text
1d1ab91f8e31dd9ac1fa60f3159914f98c2f5b4509868b15784f42f0a22ee90f
```

The image reuses the checked U-Boot, Linux 6.12.114 Image and AIC DT from the
[boot experiment](boot-test.md). It adds only `rfkill.ko`, `cfg80211.ko`,
`aic8800_bsp.ko`, `aic8800_fdrv.ko`, the six reference-matched D80 firmware/config
files, the readiness predicate and a statically linked ARM64 reset helper.
No btlpm, AP configuration, hciattach, BlueZ, Wi-Fi credentials or SSH server is
included. A successful result establishes module/firmware initialization and
one matching HCI Reset response; pairing, AP/coexistence and Android Auto remain
later work. The image has **not been booted**.

Firmware terms are still unresolved in
[radxa-pkg/aic8800#109](https://github.com/radxa-pkg/aic8800/issues/109).
Keep this image, its firmware and raw logs private; no distribution approval is
inferred. The checked-in scripts contain hashes/paths, not firmware binaries.

The preparation statements above describe the build checkpoint. A subsequent
physical run now confirms firmware readiness and successful HCI Reset on Linux
6.12.114; see the [radio-test handoff](../../../../../docs/handoffs/2026-10-22-radxa-radio-test.md)
for evidence, warning review and current recovery state. Build manifests retain
their original build-time flags; they are not rewritten as hardware evidence.

## Startup and evidence

The PID 1 script refuses execution outside PID 1. It mounts the diagnostic FAT
partition and creates a new boot-UUID directory **before** radio actions. If
persistent logs are unavailable, no radio module is loaded.

`aic-radio-test.sh` serializes these stages, stopping on failure:

1. Require kernel `6.12.114`.
2. Poll up to 30 seconds for both SDIO IDs `c8a1:0082` and `c8a1:0182`.
3. Load rfkill, cfg80211, BSP and fdrv in order, with a 30-second userspace
   timeout per synchronous `insmod` command.
4. Poll the actual firmware-readiness predicate for up to 30 seconds on `wlan0`.
5. Require bounded HCI Reset on the unattached `/dev/ttyS1`; the helper has its
   own two-second I/O deadline and an outer five-second userspace timeout.

Each stage writes a monotonic uptime marker to `progress.txt` and calls `sync`.
Failed result/progress writes or a failed pre-stage sync abort the runner before
the next radio action. A storage failure can leave the result pending or partial;
it must not be interpreted as a successful test.
`radio-result.txt` starts as pending and becomes failed with the last stage/exit
code, or success only after readiness and a successful reset. The init script
then captures diagnostics, syncs/unmounts the log partition and requests poweroff.
The LED may go dark shortly after successful completion, as in the first test.

Timeouts cannot guarantee interruption of a kernel task stuck in uninterruptible
sleep. In that case the last flushed progress marker is evidence of the attempted
stage, not proof of its failure cause. Manual power removal/card-reader recovery
remains the recovery path. No automatic reboot or fallback OS boot is configured.

Files per completed boot: `inputs.json`, `kernel-before.txt`, `progress.txt`,
`radio.log`, `radio-result.txt`, `hardware.txt`, `dmesg.txt`, `live.dtb` and
`capture-result.txt`. Logs can contain radio identifiers; preserve them privately
before redacting a public summary. `CAPTURE_FINISHED=1` does not imply radio
success; inspect `RADIO_RESET_RESULT`, stage exit code and kernel logs together.
Missing regulatory database warnings may occur because this diagnostic does not
package a regulatory database or test AP/channel operation.

## Inputs, reproduction and verification

`make-radio-test.py` reuses the existing offline boot builder without changing it.
It refuses existing/unsafe output paths, wrong kernel configuration, changed
module/firmware/helper hashes, module vermagic mismatches and dynamic/non-ARM64
executables. It writes regular files only, never a physical block device.
`manifest.json`, `SHA256SUMS` and the embedded `radio-inputs.json` record the
image, scripts, modules, firmware and input hashes. Earlier physical-test flags
in a build manifest describe its build-time state; later evidence is separate.

Staged inputs and successful build logs are private under
`buildroot/output/radxa-radio-test-prep/`. Both source archives were verified
against [ADR-0001](../../../../../docs/adr/0001-radxa-zero3w-platform.md):
Linux 6.12.114 and AIC commit `fc7cbdd1791416c2457fa27a59e508bf325c9c3f`.
The restored Linux source is `/tmp/radxa-build-check/linux-6.12.114`; the AIC
extraction is beside it. Extract outside enclosing Git worktrees when applying
the scoped Debian SDIO patch series with `git apply --include`, so parent paths
do not change the include match. Apply the exact ADR patch order.

The full existing kernel output supplies `.config`, generated headers and
`Module.symvers`. The external module command is the ADR's
`make -C "$RADXA_LINUX_SRC" O="$RADXA_OUT" ARCH=arm64 LLVM=1 -j8 M=... modules`.
Clang 23.1.3 completed MODPOST/linking with errors enabled. Existing SDK warnings
remain. All four packaged modules report
`6.12.114 SMP preempt mod_unload aarch64`; recorded dependencies match the load
order. The audited build excludes `CONFIG_MCU_MESSAGE`, both Rockchip platform
defines and `CONFIG_GPIO_WAKEUP`; `AICBT_LPM_ENABLE_DEFAULT` remains 0.
The six firmware hashes match the reference/ADR and the source archive.

BusyBox 1.37.0 is a separate static build using the first experiment's minimal
config plus `TIMEOUT`, `INSMOD`, `GREP`, `READLINK` and
`FEATURE_READLINK_FOLLOW`. Source hash verification is unchanged. The ARM64
helper uses the existing Bootlin GCC 14.3.0 `.br_real` compiler with `-static`
and the documented strict C warning flags. The source and helper binary hashes
are checked by the builder. Build-output hashes identify this experiment;
rebuilding them requires explicit provenance/hash review, not silently accepting
new inputs.

To rebuild into a **new** directory using staged verified inputs:

```sh
python3 aa_wireless_dongle/board/radxa/zero3w/checks/make-radio-test.py \
  --output buildroot/output/radxa-radio-test-rebuilt
RADXA_RADIO_TEST_DIR=buildroot/output/radxa-radio-test-rebuilt \
  python3 tests/radxa_radio_test_test.py
```

Fifteen radio tests pass for stage ordering, missing SDIO, all four load failures,
readiness retry/failure, reset failure, log-write/sync failures, PID 1 protection,
actual image/archive contents, packaged-script freshness and changed-firmware
rejection before output creation. Removing the module-load failure guard was
detected by mutation testing; log-write/sync tests failed before adding those
guards and pass with them. The 17 readiness,
10 original boot-image and 13 native host UART-helper checks also pass.

An exploratory attempt to run the UART suite with the static ARM64 binary under
this host's QEMU user emulation failed before transmitting reset: the trace
returns `ENOTTY` for `TIOCGEXCL` (`0x80045440`). Eleven UART cases fail there;
this is not claimed as a passing ARM64 runtime check. The pinned kernel's
`drivers/tty/tty_io.c` handles that ioctl, the native host suite passes and the
earlier ARM64 helper ran on the physical reference. The newly static binary's
native ARM64 execution remains part of this pending hardware experiment.

## Later physical execution

The currently restored Radxa OS remains untouched. When the owner elects to run
the test, follow the first experiment's identity checks, exact image readback,
read-only evidence capture and full-card recovery procedure. The owner-selected
previous-day backup remains available; do not ask for a replacement backup merely
because the generic procedure says fresh. Preserve logs before restoring.

Use the same computer USB-A–USB-C setup for comparison, perform one start and
allow **six minutes** before removing power and returning the card to the reader.
Normal success can power off much earlier. The allowance covers log-partition,
SDIO and userspace stage timeouts, not an uninterruptible kernel hang. Do not
infer failure from the LED or perform repeated blind retries. This preparation
does not authorize flashing or interrupting the current reference session.

Kbuild provenance/versioning follows the [official module documentation](https://www.kernel.org/doc/html/v6.12/kbuild/modules.html)
and the pinned source's `Documentation/kbuild/modules.rst`.
