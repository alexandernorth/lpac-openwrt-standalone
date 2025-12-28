# SPDX-License-Identifier: AGPL-3.0-only

include $(TOPDIR)/rules.mk

PKG_NAME:=lpac
PKG_VERSION:=2.3.0
PKG_RELEASE:=1

PKG_SOURCE:=$(PKG_NAME)-$(PKG_VERSION).tar.gz
PKG_SOURCE_URL:=https://codeload.github.com/estkme-group/lpac/tar.gz/refs/tags/v$(PKG_VERSION)?
PKG_HASH:=661dffbd1e9e5732dab4a0bb0a9837d4906c8c66bd748bda262fe3e8d3e420f6

PKG_MAINTAINER:=David Bauer <david.bauer@uniberg.com>
PKG_LICENSE:=AGPL-3.0-only LGPL-2.0-only

CMAKE_INSTALL:=1

PKG_CONFIG_DEPENDS:= \
  CONFIG_LPAC_WITH_APDU_AT \
  CONFIG_LPAC_WITH_APDU_MBIM \
  CONFIG_LPAC_WITH_APDU_PCSC \
  CONFIG_LPAC_WITH_APDU_QMI \
  CONFIG_LPAC_WITH_APDU_QMI_QRTR \
  CONFIG_LPAC_WITH_APDU_UQMI

PKG_BUILD_DEPENDS:= \
  LPAC_WITH_APDU_PCSC:pcsc-lite \
  LPAC_WITH_APDU_MBIM:libmbim \
  LPAC_WITH_APDU_QMI:libqmi \
  LPAC_WITH_APDU_QMI_QRTR:libqmi \
  libcurl-gnutls

include $(INCLUDE_DIR)/package.mk
include $(INCLUDE_DIR)/cmake.mk

define Package/lpac
  SECTION:=utils
  CATEGORY:=Utilities
  TITLE:=eUICC eSIM LPA written in C
  DEPENDS:= \
    +LPAC_WITH_APDU_PCSC:pcscd \
    +libcurl-gnutls \
    +ca-bundle \
    +minicom
  URL:=https://github.com/estkme-group/lpac
endef

define Package/lpac/description
  lpac is a eUICC eSIM LPA manager written in C. It allows to
  manage eSIM profiles on eUICC SIM cards or modules using multiple
  backends.
endef

define Package/lpac/config
  source "$(SOURCE)/Config.in"
endef

define Package/lpac/conffiles
/etc/config/lpac
endef

TARGET_CFLAGS += $(FPIC)

# libqmi 1.35.4 or newer is required for QMI over QRTR
CMAKE_OPTIONS += \
  -DLPAC_WITH_APDU_AT=$(if $(CONFIG_LPAC_WITH_APDU_AT),ON,OFF) \
  -DLPAC_WITH_APDU_GBINDER=OFF \
  -DLPAC_WITH_APDU_MBIM=$(if $(CONFIG_LPAC_WITH_APDU_MBIM),ON,OFF) \
  -DLPAC_WITH_APDU_PCSC=$(if $(CONFIG_LPAC_WITH_APDU_PCSC),ON,OFF) \
  -DLPAC_WITH_APDU_QMI=$(if $(CONFIG_LPAC_WITH_APDU_QMI),ON,OFF) \
  -DLPAC_WITH_APDU_QMI_QRTR=$(if $(CONFIG_LPAC_WITH_APDU_QMI_QRTR),ON,OFF) \
  -DLPAC_WITH_APDU_UQMI=$(if $(CONFIG_LPAC_WITH_APDU_UQMI),ON,OFF) \
  -DCURL_NO_CURL_CMAKE=ON \
  -DCURL_LIBRARY=$(STAGING_DIR)/usr/lib/libcurl-gnutls.so \
  -DCURL_INCLUDE_DIR=$(STAGING_DIR)/usr/include


define Package/lpac/install
	# wrapper
	$(INSTALL_DIR) $(1)/usr/bin
	$(INSTALL_BIN) ./files/lpac.sh $(1)/usr/bin/lpac
	$(INSTALL_BIN) ./files/sim7600g-h.sh $(1)/usr/bin/sim7600g-h

	# config
	$(INSTALL_DIR) $(1)/etc/config
	$(CP) ./files/lpac.uci $(1)/etc/config/lpac

	# payload dir
	$(INSTALL_DIR) $(1)/usr/lib/lpac
	$(INSTALL_BIN) $(PKG_INSTALL_DIR)/usr/bin/lpac $(1)/usr/lib/lpac/lpac
	$(CP) ./files/at-scripts $(1)/usr/lib/lpac/

	@echo "STAGING_DIR=$(STAGING_DIR)"
	@$(TARGET_CROSS)readelf -d $(PKG_INSTALL_DIR)/usr/bin/lpac | grep NEEDED || true

	# bundle all DT_NEEDED shared libs next to the binary
	@echo "=== bundling libs ==="

	@python3 ./files/bundle-lpac-deps.py "$(PKG_INSTALL_DIR)/usr/bin/lpac" "$(TARGET_CROSS)" "$(STAGING_DIR)" --skip 'libcurl.so*'
	@python3 ./files/bundle-lpac-deps.py "$(PKG_INSTALL_DIR)/usr/bin/lpac" "$(TARGET_CROSS)" "$(STAGING_DIR)" --skip 'libcurl.so*' | xargs -d '\n' -I{} $(CP) -L "{}" "$(1)/usr/lib/lpac/""

	@echo "=== packaged payload ==="
	@ls -l $(1)/usr/lib/lpac || true
endef


$(eval $(call BuildPackage,lpac))
