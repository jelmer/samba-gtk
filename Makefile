include Makefile.settings

BINS = gepdump gregedit gwcrontab gwsam gwsvcctl
CFLAGS = $(GTK_CFLAGS) $(TALLOC_CFLAGS) $(DCERPC_CFLAGS) $(GENSEC_CFLAGS) -I.
LIBS = $(GTK_LIBS) $(TALLOC_LIBS) $(DCERPC_LIBS) $(GENSEC_LIBS) 

LIB = libsamba-gtk.so.0.0.1
MANPAGES = man/gepdump.1 man/gwcrontab.1 man/gwsvcctl.1 man/gregedit.1

all: $(BINS) $(LIB)

install:: $(BINS) $(LIB)
	$(INSTALL) -d $(bindir) $(libdir) $(man1dir)
	$(INSTALL) -m 0755 $(BINS) $(bindir)
	$(INSTALL) -m 0755 $(LIBDIR) $(libdir)

install-doc::
	$(INSTALL) -m 0644 $(MANPAGES) $(man1dir)

configure: 
	aclocal
	autoconf -f

Makefile.settings: configure
	./configure

$(LIB): $(patsubst %.c, %.o, $(wildcard common/*.c))
	$(CC) -shared -o $@ $^ $(LIBS)
	ln -s $(LIB) libsamba-gtk.so 

%.o: %.c
	$(CC) $(CFLAGS) -o $@ -c $<

$(BINS): %: tools/%.o $(LIB)
	$(CC) -o $@ $< -lsamba-gtk -L. $(LIBS)

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

