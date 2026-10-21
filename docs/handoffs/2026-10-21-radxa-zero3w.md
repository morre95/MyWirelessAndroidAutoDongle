# Radxa ZERO 3W handoff — 2026-10-21

Resume the approved Buildroot support work from this record. This is a dated
session snapshot; actual Git state and GitHub Issues take precedence.

## Read first

- Root `AGENTS.md`, `docs/agents/domain.md` and `docs/agents/issue-tracker.md`.
- [Approved plan](../../tasks/plan.md) and [ADR-0001](../adr/0001-radxa-zero3w-platform.md).
- [Parent specification #4](https://github.com/morre95/MyWirelessAndroidAutoDongle/issues/4)
  and [current platform task #5](https://github.com/morre95/MyWirelessAndroidAutoDongle/issues/5).
- [Board-local checks and reproduction commands](../../aa_wireless_dongle/board/radxa/zero3w/checks/README.md).

The owner approved the specification, plan and task breakdown. Phase 4 is
authorized in dependency order, with focused changes of at most five files.
GitHub Issues are the canonical task tracker; do not create a second task list.

## Git state at handoff

Working branch: **`feature/radxa-zero3w-hci-reset`**. The working tree was clean
before writing this handoff. The following two commits were local and unpushed:

| Commit | Content |
| --- | --- |
| `d588453` | Standalone bounded UART HCI Reset helper, 13 host tests and documentation |
| `7998da9` | Physical reset/reattach evidence and firmware-readiness ordering findings |

This handoff is saved on the same branch in a subsequent commit. At verification,
remote `main` was **`e7ef1f1`**, merging PR #19 (AIC device-tree preparation).
PR #18 had already merged the earlier kernel/module/boot-chain checks. The
current HCI-reset branch did **not** exist on the remote. Recheck before pushing,
switching or merging; preserve local work. No push or merge is authorized by
this handoff request itself.

## Hardware and current state

- Owner's board: **ZERO 3W V1.12M, RK3566, 1 GB, no eMMC, AIC8800D80 SDIO**.
- The microSD is back in the Radxa. Last observed state: booted, SSH reachable,
  hciattach and BlueZ active, Bluetooth controller powered, Wi-Fi client working.
  Recheck reachability after a break; do not assume the board stays powered.
- The installed reference is **Radxa OS `rsdk-b1`, Debian 12,
  Linux `6.1.84-10-rk2410-nocsf`**. It remains the reference system.
- **There is no complete Buildroot SD image or shipping Radxa defconfig yet.**
  No new kernel, DT, firmware or bootloader has been flashed to the card.

Private access metadata is in ignored local build output:
`buildroot/output/radxa-recovery/session-access.json`, with a persisted
`ssh_known_hosts` beside it. This records the last endpoint and account, not a
password. Use strict host-key checking. If these files are missing or access
has changed, ask the owner rather than guessing or disabling verification.
Never commit credentials, private addresses or configured card images.

## Verified results

- Pinned Buildroot **2026.02.3**, commit
  `679b9ead7620bbf193620d1ebf56f53c1764d37a`; Pi pins and shared behavior retained.
- Candidate **Linux 6.12.114** builds a full ARM64 Image, modules and upstream DT.
  USB accessory/composite and all three AIC modules pass linking/MODPOST with
  matching vermagic. Existing nonfatal SDK warnings remain. Board-local fixes are
  preparation patches, not an active target.
- The AIC reference is commit `fc7cbdd1791416c2457fa27a59e508bf325c9c3f`.
  All six relevant firmware/configuration files match the reference card.
  Apply the official Debian patch series before the board-local AIC patches;
  apply both shared accessory patches before board-local Linux patches.
- **U-Boot 2026.01**, RK3566 DDR **1.23**, RK3568 BL31 **1.44** build using
  Buildroot's existing rkbin pin. Packing/header/blob/FIT checks passed.
- The separate **V1.12M/AIC8800D80 DT** compiles; compiled-property checks pass
  and the generic ZERO 3W DTB stays byte-identical. This DT has not been booted.
- The standalone UART helper passes **13 pseudo-terminal tests**, strict host
  compilation, GCC static analysis and ARM64 cross-compilation.
- On the **Radxa OS reference**, the helper refused an already attached N_HCI
  UART, then completed one reset on the freed UART in about **5 ms**. hciattach,
  BlueZ, powered hci0 and N_HCI were restored. Selected GPIO levels were identical
  before/after. Temporary board test files and the recovery timer were removed.

These results do not establish Buildroot/mainline hardware operation, pairing,
Wi-Fi AP/Bluetooth coexistence, accessory negotiation or cold-start acceptance.
The ADR contains exact source/blob hashes, commands and evidence limits.

## Important startup finding

The reference's reset service timed out during this boot even though Bluetooth
eventually powered on. The same journal monotonic clock places reset-command
logging at 9.556 s while BT firmware patches load at 9.591–9.637 s. The unit has
no AIC-readiness dependency. This supports an ordering hypothesis, not proof of
the sole failure cause or a measurement of UART wire timing. Raw dmesg timestamps
differed from journal monotonic timestamps; do not mix those time bases.

The next startup contract is:

**AIC firmware readiness → successful bounded UART reset → hciattach → BlueZ.**

Do not substitute a fixed sleep or attach after reset failure. At the pinned AIC
source, `rwnx_mod_init()` calls BSP power/firmware setup before Wi-Fi-driver
registration. Investigate a concrete readiness gate around that path; interface
presence/module-load completion is a candidate to verify, not an accepted proof.

The vendor `bt_default` rfkill instance was blocked with PC1 output low while
hci0 was powered. The reference loaded BSP/fdrv, **not** `aic8800_btlpm`. Do not
infer that the vendor Bluetooth GPIO/RTS transitions or driving PC1 high are
required. Mainline pin defaults and radio bring-up still need verification.

## Firmware question and approvals

The owner explicitly approved publishing the prepared question. It was published
as [radxa-pkg/aic8800#109](https://github.com/radxa-pkg/aic8800/issues/109), and its
title/body were verified against the approved draft. It is linked from #5.
At handoff it is **open with zero comments**. Check for a response when resuming.

The maintainer's earlier #54 discussion clarifies GPL v2 driver source versus
GPL v3 packaging. It does not establish the selected opaque firmware's binary
redistribution/source obligations. Publication of #109 is not a license grant.
Keep task #5 open and retain downstream dependencies while these remain unresolved.
The approval covered this specific question; do not send further external
messages or repeated follow-ups without authorization.

## Next work

1. Read actual Git state, #5 and the latest #109 response. Preserve the local
   commits; do not restart the source investigation or reflash the reference.
2. Continue the remaining platform-feasibility slice: establish a concrete
   firmware-readiness gate and mainline pin/power requirements using the source
   and physical evidence above. Keep experimental preparation scoped and tested.
3. Resolve and record firmware terms from authoritative evidence. If a response
   requires a source change or new approval, surface that explicitly.
4. Once #5 is actually complete, update the ADR/task and proceed in the approved
   order: **#6 Pi initialization isolation → #7 Radxa kernel/boot integration →
   #8 complete SD image**. Later tasks cover accessory, wireless and release checks.

Any new radio-interrupting test should check for connected devices, preserve the
working SSH path and restore Bluetooth automatically. The last test used both
`finally` restoration and a transient systemd fallback timer. Never reuse the
diagnostic DT as an unreviewed drop-in for the vendor kernel.

## Local artifacts and verification

The full configured-card backup is
`buildroot/output/radxa-recovery/radxa-os-20261021-172921.img.zst` with adjacent
JSON metadata. It contains **31,266,439,168 decompressed bytes**, occupies about
1.9 GiB and was verified by decompression/SHA-256. Files are mode 0600 in a private
directory. They can contain local configuration; keep them out of Git/public uploads.

Other ignored local outputs:

- `buildroot/output/radxa-platform-check/linux`: full LLVM ARM64 kernel output.
- `buildroot/output/radxa-bootchain-check`: U-Boot/Bootlin outputs and ARM64 helper.
- `/tmp/radxa-build-check`: verified source downloads, extracted trees, logs and
  temporary reproduction scripts, including `hci-hardware-check.log`.

`/tmp` and build artifacts may disappear. Recreate from the ADR/checks README;
they are not release assets. The Compose output volume is distinct from these
host output directories; prior experiment commands used an explicit bind mount.

Host helper check from the repository root:

```sh
cc -std=c11 -Wall -Wextra -Werror -Wconversion -Wshadow \
    aa_wireless_dongle/board/radxa/zero3w/checks/aic-hci-reset.c \
    -o /tmp/radxa-hci-reset
python3 tests/radxa_hci_reset_test.py
```

All 13 passed; the helper source has not changed since that verification. The
existing proxy diagnostics regression test also passed earlier. Rerun affected
checks after source changes or when the recorded baseline is unavailable;
documentation-only handoff work does not need another full kernel/Pi build.
