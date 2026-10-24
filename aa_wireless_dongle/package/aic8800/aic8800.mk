################################################################################
#
# aic8800
#
################################################################################

# Tag 4.0+git20241119.06da8476-1, the radio driver selected by ADR-0001.
AIC8800_VERSION = fc7cbdd1791416c2457fa27a59e508bf325c9c3f
AIC8800_SITE = $(call github,radxa-pkg,aic8800,$(AIC8800_VERSION))
# Radxa states the driver source is GPL-2.0 and the GPL-3.0 LICENSE text
# comes from its packaging template: radxa-pkg/aic8800#54.
AIC8800_LICENSE = GPL-2.0
AIC8800_LICENSE_FILES = LICENSE

AIC8800_MODULE_SUBDIRS = src/SDIO/driver_fw/driver/aic8800
# The startup contract never loads aic8800_btlpm, so do not build it.
AIC8800_MODULE_MAKE_OPTS = CONFIG_AIC8800_BTLPM_SUPPORT=n

# Radxa's Debian series goes first; the global patch dir then applies the
# board patches on top of it.
define AIC8800_APPLY_DEBIAN_PATCHES
	$(APPLY_PATCHES) $(@D) $(@D)/debian/patches
endef
AIC8800_PRE_PATCH_HOOKS += AIC8800_APPLY_DEBIAN_PATCHES

# Transmit-power table read by aic8800_fdrv next to the firmware. It is
# plain-text source, unlike the binaries, which come from aic8800-firmware.
define AIC8800_INSTALL_USERCONFIG
	$(INSTALL) -D -m 0644 $(@D)/src/SDIO/driver_fw/fw/aic8800D80/aic_userconfig_8800d80.txt \
		$(TARGET_DIR)/lib/firmware/aic8800_fw/SDIO/aic8800D80/aic_userconfig_8800d80.txt
endef
AIC8800_POST_INSTALL_TARGET_HOOKS += AIC8800_INSTALL_USERCONFIG

$(eval $(kernel-module))
$(eval $(generic-package))
