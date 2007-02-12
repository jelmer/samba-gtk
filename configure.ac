AC_INIT(samba-gtk, 0.0.1, [jelmer@samba.org])
AC_PROG_CC
AC_PROG_INSTALL
AC_PATH_PROG(XSLTPROC, xsltproc)

PKG_CHECK_MODULES(GTK, [glib-2.0 gtk+-2.0 >= 2.4])
PKG_CHECK_MODULES(TALLOC, [talloc])
PKG_CHECK_MODULES(DCERPC, [dcerpc])
PKG_CHECK_MODULES(GENSEC, [gensec])

AC_CONFIG_FILES([Makefile.settings gtksamba.pc])
AC_OUTPUT
