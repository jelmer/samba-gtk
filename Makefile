include Makefile.settings

BINS = gepdump gregedit gwcrontab gwsam gwsvcctl
gepdump_LIBS = $(DCERPC_MGMT_LIBS)
gregedit_LIBS = $(REGISTRY_LIBS)
gwcrontab_LIBS = $(DCERPC_ATSVC_LIBS)
CFLAGS = $(GTK_CFLAGS) $(TALLOC_CFLAGS) $(DCERPC_CFLAGS) $(GENSEC_CFLAGS) -I.
LIBS = $(GTK_LIBS) $(TALLOC_LIBS) $(DCERPC_LIBS) $(GENSEC_LIBS) $(DCERPC_SAMR_LIBS)

LIB = libsamba-gtk.so.0.0.1
MANPAGES = man/gepdump.1 man/gwcrontab.1 man/gwsvcctl.1 man/gregedit.1
HEADERS = $(wildcard common/*.h)

all: $(BINS) $(LIB)

Makefile: Makefile.settings

install:: $(BINS) $(LIB)
	$(INSTALL) -d $(DESTDIR)$(bindir) $(DESTDIR)$(libdir) $(DESTDIR)$(man1dir)
	$(INSTALL) -m 0755 $(BINS) $(DESTDIR)$(bindir)
	$(INSTALL) -m 0755 $(LIB) $(DESTDIR)$(libdir)
	$(INSTALL) -d $(DESTDIR)$(pcdir)
	$(INSTALL) -m 0644 gtksamba.pc $(DESTDIR)$(pcdir)
	$(INSTALL) -d $(DESTDIR)$(appdir)
	$(INSTALL) -m 0644 meta/* $(DESTDIR)$(appdir)
	$(INSTALL) -d $(DESTDIR)$(includedir)
	$(INSTALL) -m 0644 $(HEADERS) $(DESTDIR)$(includedir)

install-doc:: doc
	$(INSTALL) -m 0644 $(MANPAGES) $(DESTDIR)$(man1dir)

configure: configure.ac
	aclocal
	autoconf -f

check:: test

%.desktop-validate: %.desktop
	$(DESKTOP_VALIDATE) $<

test:: $(patsubst %.desktop,%.desktop-validate,$(wildcard meta/*.desktop))

Makefile.settings: configure
	./configure

$(LIB): $(patsubst %.c, %.o, $(wildcard common/*.c))
	$(CC) -Wl,-soname=libsamba-gtk.so.0 -shared -o $@ $^ $(LIBS)

libsamba-gtk.so: $(LIB)
	ln -fs $< $@

%.o: %.c
	$(CC) $(CFLAGS) -o $@ -c $<

$(BINS): %: tools/%.o $(LIB)
	$(CC) -o $@ $< $(LIB) $(LIBS) $($*_LIBS)

install::

clean::
	rm -f $(BINS) $(LIB) *.so */*.o

distclean:: clean
	rm -rf autom4te.cache
	rm -f config.log config.cache config.status
	rm -f Makefile.settings

dist:: configure distclean

doc:: $(MANPAGES)

DOCBOOK_MANPAGE_URL = http://docbook.sourceforge.net/release/xsl/current/manpages/docbook.xsl

.SUFFIXES: .1 .1.xml

.1.xml.1:
	$(XSLTPROC) -o $@ $(DOCBOOK_MANPAGE_URL) $<

