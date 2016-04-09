all: package

lua-resty-extra-lib.tar.gz:
	make -C lua-resty-extra-lib clean all

package: lua-resty-extra-lib.tar.gz
	makepkg

clean:
	$(RM) -r src/ pkg/ openresty-*.tar.gz openresty-*.tar.xz

.PHONY: all package clean
