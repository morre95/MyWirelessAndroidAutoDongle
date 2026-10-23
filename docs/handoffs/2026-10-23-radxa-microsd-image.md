# Radxa microSD image boot test — 2026-10-23

Task [#8](https://github.com/morre95/MyWirelessAndroidAutoDongle/issues/8)
([approved spec](https://github.com/morre95/MyWirelessAndroidAutoDongle/issues/8#issuecomment-6374189409)).
Continue from the [kernel/boot-component build](../adr/0001-radxa-zero3w-platform.md#shipping-kernel-and-boot-component-build-2026-10-23).

## Image

`make -C output/radxa-zero3w` of `radxa-zero3w_defconfig` in the `aawg-buildroot`
Docker environment produced `images/sdcard.img`, **385,875,968 bytes**:

```text
SHA-256 2f3aff22279c5920609a536314d47aa097fa57eaf20796949e73181d305f0117
```

| Area | Offset / size | Contents |
| --- | --- | --- |
| Raw, outside the table | 32 KiB, 9,632,768 bytes | `u-boot-rockchip.bin` |
| p1, FAT `WirelessAA`, 0xC, bootable | 16 MiB, 64 MiB | `extlinux/extlinux.conf`, `Image`, AIC DTB, `aawgd.conf` |
| p2, ext4 `rootfs` | 256 MiB | Common application rootfs, mounted read-only |
| p3, ext4 `persist` | 32 MiB | Pairing data and seedrng seed through the common `/var/lib` links |

`tests/radxa_image_test.py` (12 cases) and `tests/radxa_platform_build_test.py`
(11 cases) pass against this build. The rootfs uses about 107 MB of 256 MiB; the
ARM64 defconfig modules account for about 69 MB.

## Card write

The owner approved overwriting the Radxa OS reference card. Its verified full-card
backup (`radxa-recovery/radxa-os-20261021-172921.img.zst`) remains the recovery point.

1. 20:50:47–20:51:09 UTC: written over the reference layout, backup-GPT signature
   cleared, exclusive and fresh readbacks both matched the image hash.
2. The desktop automounter then mounted the new partitions read-write and the card
   was removed while mounted. Because the card no longer matched the verified image,
   it was written again at 21:06:29–21:06:51 UTC. Both readbacks matched, and the
   reader was powered off before the automounters resumed.

## Headless boots

There is no serial adapter, so no console was captured. The owner booted the card
twice from a computer USB port, removing power after about two minutes each time
without shutting down. After each boot the card's first 385,875,968 bytes were
copied through an exclusive read-only descriptor:

| Copy | Captured (UTC) | SHA-256 |
| --- | --- | --- |
| Boot 1 | 21:11:17–21:11:26 | `f2bc9983614da7fe4a9421bb2498f33a881343d2a3dcdd40440bdddb84a4c61b` |
| Boot 2 | 21:16:09–21:16:19 | `2719b4435400c82ff4333acd080d8e2e59ac2a543615a212a5be3255bcd82bca` |

**Host mounts before each copy.** In both rounds an earlier capture attempt exited
while the reader was enumerating (21:11:16 and 21:15:17 UTC). Its exit resumed the
automounters, which mounted all three partitions read-write. The host replayed the
`persist` journal left by the power cut and updated the ext4 mount counts and times.
Before the second copy the reader was also unplugged once while mounted. A later
attempt unmounted the partitions and took the copy. The host does not run the
board's init scripts, so it cannot have produced the evidence below.

Findings, identical in both copies except the seed:

- **`persist`** holds `seedrng/seed.credit` and an empty `bluetooth/`, all dated
  1 Jan 1970. The board has no set clock; host writes carry 2026 times.
  `fstab` therefore mounted `/dev/mmcblk1p3` read-write, `S00persist` and
  `S01seedrng` ran, and their writes survived power removal.
- **Seed** SHA-256 prefix `cfe3c999…` after boot 1 and `b7d3638e…` after boot 2,
  so the second boot also reached init and wrote `persist`.
- **`WirelessAA`** passes `fsck.fat -n`, holds the expected boot files, and its
  `aawgd.conf` is byte-identical to the build. The host mounted it as a normal
  computer volume.
- **U-Boot area** is byte-identical to `u-boot-rockchip.bin` in both copies.

## Not established

- The boot log. Without a serial console or network it is deferred to the first
  task with SSH over Wi-Fi (#10).
- That the board left `rootfs` unmodified. The host's read-write mounts changed it,
  so the copies cannot show that the board mounted it read-only.
- Radio, USB gadget and `aawgd` behaviour (#9–#12), car power, and the LED state,
  which was not recorded.

## State and recovery

The card in the owner's possession now carries the radxa-zero3w image after two
boots and host mounts. Private receipts and both copies are in the ignored
`buildroot/output/radxa-image-20261023/`. To return to Radxa OS, restore the
verified full-card backup with the same procedure as the 2026-10-23 Pi smoke-test
restore. A fresh reflash of the verified image is needed before using this card as
evidence again.

Any future capture must keep the automounters paused, or the reader powered off,
on every exit path, including failures.
