AC_INIT(samba-gtk, 0.0.1, [jelmer@samba.org])
AC_CONFIG_HEADER([config.h])
AC_PROG_CC
AC_PROG_INSTALL
AC_PATH_PROG(XSLTPROC, xsltproc)
AC_PATH_PROG(DESKTOP_VALIDATE, desktop-file-validate)

PKG_CHECK_MODULES(GTK, [glib-2.0 gtk+-2.0 >= 2.4])
PKG_CHECK_MODULES(TALLOC, [talloc])
PKG_CHECK_MODULES(TEVENT, [tevent])
PKG_CHECK_MODULES(DCERPC, [dcerpc])
PKG_CHECK_MODULES(GENSEC, [gensec])
PKG_CHECK_MODULES(DCERPC_SAMR, [dcerpc_samr])
PKG_CHECK_MODULES(DCERPC_ATSVC, [dcerpc_atsvc])
PKG_CHECK_MODULES(REGISTRY, [registry])
PKG_CHECK_MODULES(PYGTK, [pygtk-2.0])
PKG_CHECK_MODULES(KEYRING, [gnome-keyring-1],
				  [ AC_DEFINE(HAVE_GNOME_KEYRING, 1, [Whether GNOME keyring is available]) ])

AC_ARG_VAR([PYTHON_VERSION],[The installed Python
	version to use, for example '2.3'. This string 
	will be appended to the Python interpreter
	canonical name.])

AC_PATH_PROG([PYTHON],[python[$PYTHON_VERSION]])
if test -z "$PYTHON"; then
	AC_MSG_WARN([No python found])
fi

if test -z "$PYTHON_VERSION"; then 
	AC_PATH_PROGS([PYTHON_CONFIG], [python2.6-config python2.5-config python2.4-config python-config])
else 
	AC_PATH_PROG([PYTHON_CONFIG], [python[$PYTHON_VERSION]-config])
fi

if test -z "$PYTHON_CONFIG"; then
	AC_MSG_WARN([No python-config found])
fi

AC_MSG_CHECKING(python library directory)
pythondir=`$PYTHON -c "from distutils import sysconfig; print sysconfig.get_python_lib(1, 0, '\\${prefix}')"`
AC_MSG_RESULT($pythondir)

AC_SUBST(pythondir)

AC_CONFIG_FILES([Makefile.settings gtksamba.pc])
AC_OUTPUT
