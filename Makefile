include Makefile.settings

BINS = gepdump gregedit gwcrontab gwsam gwsvcctl
CFLAGS = $(GTK_CFLAGS) $(TALLOC_CFLAGS) -I.
LIBS = $(GTK_LIBS) $(TALLOC_LIBS)
LIB = libsamba-gtk.so.0.0.1

all: $(BINS) $(LIB)

configure: 
	autoconf -f

Makefile.settings: configure
	./configure

$(LIB): $(patsubst %.c, %.o, $(wildcard common/*.c))
	$(CC) -shared -o $@ $^ $(LIBS)
	ln -s $(LIB) libsamba-gtk.so 

%.o: %.c
	$(CC) $(CFLAGS) -c $<

$(BINS): %: tools/%.o $(LIB)
	$(CC) -o $@ $< -lsamba-gtk -L. $(LIBS)

install::
	$(INSTALL)

clean::
	rm -f $(BINS) $(LIB) *.so */*.o

distclean:: clean
	rm -rf autom4te.cache
	rm -f config.log config.cache config.status
	rm -f Makefile.settings

dist:: configure distclean
