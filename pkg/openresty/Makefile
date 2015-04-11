all: package

lua-resty-extra-lib.tar.gz:
	make -C lua-resty-extra-lib clean all

package: lua-resty-extra-lib.tar.gz
	makepkg --clean

clean:
	$(RM) -r src/ pkg/ ngx_openresty-*.tar.gz openresty-*.tar.gz openresty-*.tar.xz

.PHONY: all package clean