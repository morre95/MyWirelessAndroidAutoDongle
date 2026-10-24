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

$(eval $(kernel-module))
$(eval $(generic-package))
