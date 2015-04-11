LIBS_NAMES = cookie hmac http-simple
PKGNAME = ngx_openresty
PKGVER = 1.7.10.1
DEST = ../lua-resty-extra-lib.tar.gz


LIBS = $(addprefix lua-resty-, $(LIBS_NAMES))
LIBS_MAKEFILES = $(addsuffix -makefile, $(LIBS))
ROOTDIR = $(PKGNAME)-$(PKGVER)
BUNDLEDIR = $(ROOTDIR)/bundle

GIT = git
GITCLONE = $(GIT) clone --depth=1
CP = cp
SED = sed
TAR = tar
MKDIR = mkdir

all: $(DEST)

lua-resty-cookie:
	$(GITCLONE) git@github.com:cloudflare/lua-resty-cookie.git

lua-resty-hmac:
	$(GITCLONE) git@github.com:jkeys089/lua-resty-hmac.git

lua-resty-http-simple:
	$(GITCLONE) git@github.com:bakins/lua-resty-http-simple.git

lua-resty-cookie-makefile: lua-resty-cookie
	$(CP) Makefile.inroot "$</Makefile"

lua-resty-hmac-makefile: lua-resty-hmac
	$(CP) Makefile.inroot "$</Makefile"

lua-resty-http-simple-makefile: lua-resty-http-simple
	$(CP) Makefile.insubfolder "$</Makefile"
	$(SED) -i s/%PKGNAME%/http/ "$</Makefile"

$(DEST): $(LIBS_MAKEFILES)
	$(RM) -r $(addsuffix /.git, $(LIBS))
	$(MKDIR) -p $(BUNDLEDIR)
	$(CP) -r $(LIBS) $(BUNDLEDIR)
	$(TAR) -czf "$@" $(ROOTDIR)

clean:
	$(RM) -r "$(ROOTDIR)" "$(DEST)" $(LIBS)

.PHONY: all clean
