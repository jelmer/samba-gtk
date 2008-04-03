AC_INIT(samba-gtk, 0.0.1, [jelmer@samba.org])
AC_PROG_CC
AC_PROG_INSTALL
AC_PATH_PROG(XSLTPROC, xsltproc)
AC_PATH_PROG(DESKTOP_VALIDATE, desktop-file-validate)

PKG_CHECK_MODULES(GTK, [glib-2.0 gtk+-2.0 >= 2.4])
PKG_CHECK_MODULES(TALLOC, [talloc])
PKG_CHECK_MODULES(DCERPC, [dcerpc])
PKG_CHECK_MODULES(GENSEC, [gensec])
PKG_CHECK_MODULES(DCERPC_SAMR, [dcerpc_samr])
PKG_CHECK_MODULES(DCERPC_ATSVC, [dcerpc_atsvc])
PKG_CHECK_MODULES(REGISTRY, [registry])

AC_CONFIG_FILES([Makefile.settings gtksamba.pc])
AC_OUTPUT
