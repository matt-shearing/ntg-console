PREFIX  ?= /usr/local
DESTDIR ?=
BINDIR  := $(DESTDIR)$(PREFIX)/bin
DATADIR := $(DESTDIR)$(PREFIX)/share/ntg-console
APPDIR  := $(DESTDIR)$(PREFIX)/share/applications
ICONDIR := $(DESTDIR)$(PREFIX)/share/icons/hicolor
LICDIR  := $(DESTDIR)$(PREFIX)/share/licenses/ntg-console
UDEVDIR := $(DESTDIR)$(PREFIX)/lib/udev/rules.d
UNITDIR := $(DESTDIR)$(PREFIX)/lib/systemd/user

.PHONY: install uninstall

install:
	install -d "$(DATADIR)/ntg_console" "$(BINDIR)" "$(APPDIR)" "$(LICDIR)" "$(UNITDIR)"
	install -m644 ntg_console/*.py "$(DATADIR)/ntg_console/"
	install -m755 ntg-console.in "$(BINDIR)/ntg-console"
	sed -i 's|@DATADIR@|$(PREFIX)/share/ntg-console|g' "$(BINDIR)/ntg-console"
	install -m644 ntg-console.desktop "$(APPDIR)/ntg-console.desktop"
	sed -i 's|^Exec=.*|Exec=ntg-console|' "$(APPDIR)/ntg-console.desktop"
	sed -i 's|^Icon=.*|Icon=ntg-console|' "$(APPDIR)/ntg-console.desktop"
	install -m644 LICENSE "$(LICDIR)/LICENSE"
	sed 's|@BINDIR@|$(PREFIX)/bin|g' packaging/ntg-console.service \
	  > "$(UNITDIR)/ntg-console.service"
	for size in 16 24 32 48 64 128 256 512 1024; do \
	  install -d "$(ICONDIR)/$${size}x$${size}/apps"; \
	  install -m644 "icons/hicolor/$${size}x$${size}/apps/ntg-console.png" \
	    "$(ICONDIR)/$${size}x$${size}/apps/ntg-console.png"; \
	done
	install -d "$(UDEVDIR)"
	install -m644 99-rode-ntg.rules "$(UDEVDIR)/99-rode-ntg.rules"

uninstall:
	rm -f "$(BINDIR)/ntg-console"
	rm -f "$(APPDIR)/ntg-console.desktop"
	rm -rf "$(DATADIR)" "$(LICDIR)"
	rm -f "$(UDEVDIR)/99-rode-ntg.rules"
	rm -f "$(UNITDIR)/ntg-console.service"
	for size in 16 24 32 48 64 128 256 512 1024; do \
	  rm -f "$(ICONDIR)/$${size}x$${size}/apps/ntg-console.png"; \
	done
