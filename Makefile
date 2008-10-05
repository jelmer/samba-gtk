include Makefile.settings

BINS = gwcrontab gwsam gwsvcctl 
SCRIPTS = gtkldb gepdump gregedit
gwcrontab_LIBS = $(DCERPC_ATSVC_LIBS)
CFLAGS = $(GTK_CFLAGS) $(TALLOC_CFLAGS) $(DCERPC_CFLAGS) $(GENSEC_CFLAGS) -I. -Wall
LIBS = $(GTK_LIBS) $(TALLOC_LIBS) $(DCERPC_LIBS) $(GENSEC_LIBS) $(DCERPC_SAMR_LIBS)
# Should be determined by configure...
SHLIBEXT = so

LIB = libsamba-gtk.$(SHLIBEXT).0.0.1
MANPAGES = man/gepdump.1 man/gwcrontab.1 man/gwsvcctl.1 man/gregedit.1 man/gtkldb.1
HEADERS = $(wildcard common/*.h)
SOVERSION = 0
SONAME = libsamba-gtk.$(SHLIBEXT).$(SOVERSION)
PYMODULES = sambagtk.$(SHLIBEXT)

all:: $(BINS) $(LIB) $(SONAME) libsamba-gtk.$(SHLIBEXT) sambagtk.$(SHLIBEXT)

Makefile: Makefile.settings

install:: $(BINS) $(LIB) $(PYMODULES)
	$(INSTALL) -d $(DESTDIR)$(bindir) $(DESTDIR)$(libdir) $(DESTDIR)$(man1dir)
	$(INSTALL) -m 0755 $(BINS) $(SCRIPTS) $(DESTDIR)$(bindir)
	$(INSTALL) -m 0755 $(LIB) $(DESTDIR)$(libdir)
	ln -fs $(LIB) $(DESTDIR)$(libdir)/libsamba-gtk.$(SHLIBEXT)
	$(INSTALL) -d $(DESTDIR)$(pcdir)
	$(INSTALL) -m 0644 gtksamba.pc $(DESTDIR)$(pcdir)
	$(INSTALL) -d $(DESTDIR)$(appdir)
	$(INSTALL) -m 0644 meta/* $(DESTDIR)$(appdir)
	$(INSTALL) -d $(DESTDIR)$(includedir)
	$(INSTALL) -m 0644 $(HEADERS) $(DESTDIR)$(includedir)
	$(INSTALL) -m 0755 sambagtk.$(SHLIBEXT) $(DESTDIR)$(pythondir)

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

$(LIB): $(patsubst %.c, %.po, $(wildcard common/*.c))
	$(CC) -Wl,-soname=$(SONAME) -shared -o $@ $^ $(LIBS)

$(SONAME): $(LIB)
	ln -fs $< $@

libsamba-gtk.$(SHLIBEXT): $(LIB)
	ln -fs $< $@

DEFS = `pkg-config --variable=defsdir pygtk-2.0`

python/sambagtk.c: python/sambagtk.defs python/sambagtk.override
	pygtk-codegen-2.0 --prefix sambagtk \
		--register $(DEFS)/gdk-types.defs \
		--register $(DEFS)/gtk-types.defs \
		--override python/sambagtk.override \
		$< > $@

python/%.po: CFLAGS+=`$(PYTHON_CONFIG) --cflags` $(PYGTK_CFLAGS)

sambagtk.$(SHLIBEXT): python/sambagtk.po python/module.po $(LIB)
	$(CC) -shared -o $@ $^ `$(PYTHON_CONFIG) --libs` $(PYGTK_LIBS)

%.o: %.c
	$(CC) $(CFLAGS) -o $@ -c $<

%.po: %.c
	$(CC) $(CFLAGS) -fPIC -o $@ -c $<

$(BINS): %: tools/%.o $(LIB)
	$(CC) -o $@ $< $(LIB) $(LIBS) $($*_LIBS)

install::

clean::
	rm -f $(BINS) $(LIB) *.$(SHLIBEXT) */*.o *.o */*.po *.po

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

ctags:
	ctags -R .
