.PHONY: test test-connections package

test:
	python3 -m unittest discover -s tests

test-connections:
	tests/connections.sh

# Arch packages (omalocker, omalocker-viewer) into build/; see docs/packaging.md.
package:
	cd pkgbuild && BUILDDIR=$(CURDIR)/build/makepkg PKGDEST=$(CURDIR)/build makepkg -f --cleanbuild
