################################################################################
#
# aic8800-firmware
#
################################################################################

# The first linux-firmware release with AIC8800D80 firmware (v6.9.1.1).
# Buildroot's linux-firmware package predates it.
AIC8800_FIRMWARE_VERSION = 20261019
AIC8800_FIRMWARE_SITE = https://gitlab.com/kernel-firmware/linux-firmware/-/raw/$(AIC8800_FIRMWARE_VERSION)/aic/aic8800d80
AIC8800_FIRMWARE_FILES = \
	fw_adid_8800d80_u02.bin \
	fw_patch_8800d80_u02.bin \
	fw_patch_table_8800d80_u02.bin \
	fmacfw_8800d80_u02.bin
AIC8800_FIRMWARE_SOURCE = $(firstword $(AIC8800_FIRMWARE_FILES))
AIC8800_FIRMWARE_EXTRA_DOWNLOADS = \
	$(wordlist 2,$(words $(AIC8800_FIRMWARE_FILES)),$(AIC8800_FIRMWARE_FILES)) \
	https://gitlab.com/kernel-firmware/linux-firmware/-/raw/$(AIC8800_FIRMWARE_VERSION)/LICENSES/LICENSE.aic
AIC8800_FIRMWARE_LICENSE = LicenseRef-LICENSE.aic
AIC8800_FIRMWARE_LICENSE_FILES = LICENSE.aic

define AIC8800_FIRMWARE_EXTRACT_CMDS
	cp $(addprefix $(AIC8800_FIRMWARE_DL_DIR)/,$(AIC8800_FIRMWARE_FILES) LICENSE.aic) $(@D)
endef

# The driver's compiled firmware path; LICENSE.aic requires redistributed
# copies to carry the license.
define AIC8800_FIRMWARE_INSTALL_TARGET_CMDS
	$(foreach f,$(AIC8800_FIRMWARE_FILES) LICENSE.aic,\
		$(INSTALL) -D -m 0644 $(@D)/$(f) \
			$(TARGET_DIR)/lib/firmware/aic8800_fw/SDIO/aic8800D80/$(f)$(sep))
endef

$(eval $(generic-package))
