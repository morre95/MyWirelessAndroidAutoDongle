################################################################################
#
# aic8800-startup
#
################################################################################

AIC8800_STARTUP_SITE = $(AIC8800_STARTUP_PKGDIR)/src
AIC8800_STARTUP_SITE_METHOD = local
AIC8800_STARTUP_LICENSE = MIT

define AIC8800_STARTUP_BUILD_CMDS
	$(TARGET_CC) $(TARGET_CFLAGS) $(TARGET_LDFLAGS) -std=c11 -Wall -Wextra -Werror \
		-Wconversion -Wshadow $(@D)/aic-hci-reset.c -o $(@D)/aic-hci-reset
endef

define AIC8800_STARTUP_INSTALL_TARGET_CMDS
	$(INSTALL) -D -m 0755 $(@D)/aic-hci-reset $(TARGET_DIR)/usr/sbin/aic-hci-reset
	$(INSTALL) -D -m 0755 $(@D)/aic-firmware-ready.sh \
		$(TARGET_DIR)/usr/sbin/aic-firmware-ready.sh
endef

define AIC8800_STARTUP_INSTALL_INIT_SYSV
	$(INSTALL) -D -m 0755 $(@D)/S38radio $(TARGET_DIR)/etc/init.d/S38radio
endef

$(eval $(generic-package))
