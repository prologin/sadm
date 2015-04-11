lua-resty-extra-lib.tar.gz:
	make -C lua-resty-extra-lib clean all

update_pkgsums:
	updpkgsumes || ( echo "updpkgsums not found. Please update PKGBUILD manually:" && makepkg --geninteg )

package: lua-resty-extra-lib.tar.gz
	makepkg --clean

all: package

clean:
	$(RM) -r src/ pkg/ ngx_openresty-*.tar.gz openresty-*.tar.gz openresty-*.tar.xz

.PHONY: all clean package update_pkgsums
