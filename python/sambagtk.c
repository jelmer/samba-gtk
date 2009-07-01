
#include <stdint.h>
#include <stdlib.h>
#include <stdbool.h>
#include <stdio.h>

#include <Python.h>
#include <structmember.h>
#include <pygobject.h>
#include <pygtk/pygtk.h>

#include <gen_ndr/ndr_samr_c.h>
#include <gen_ndr/ndr_atsvc_c.h>
#include <gen_ndr/ndr_svcctl_c.h>
#include <gen_ndr/ndr_epmapper_c.h>

#include <core/ntstatus.h>
#include <tevent.h>
#include <talloc.h>
#include <param.h>
#include <util/debug.h>

/* FIXME: these are directly taken from Samba4 source */
#include "lib/talloc/pytalloc.h"
#include "librpc/rpc/pyrpc.h"
#include "param/pyparam.h"

#include "common/gtk-smb.h"
#include "common/select.h"


#define SAMR_NDR_NAME           "samr"
#define ATSVC_NDR_NAME          "atsvc"
#define SVCCTL_NDR_NAME         "svcctl"
#define EPMAPPER_NDR_NAME       "epmapper"


static PyTypeObject *PyGtkDialog_Type = NULL;
static PyTypeObject *PyGObject_Type = NULL; 
static PyTypeObject *PyPolicy_Handle_Type = NULL;
static PyTypeObject *PyDCERPC_Interface_Type = NULL;
static PyTypeObject *PyLoadParm_Type = NULL;
#define PyGtkRpcBindingDialog_Type (& _PyGtkRpcBindingDialog_Type)
#define PyGtkSelectDomainDialog_Type (& _PyGtkSelectDomainDialog_Type)
#define PyGtkSelectHostDialog_Type (& _PyGtkSelectHostDialog_Type)

static struct tevent_context *ev_ctx = NULL;
static struct loadparm_context *lp_ctx = NULL;


    /* GtkRpcBindingDialog type */

static PyMemberDef gtk_rpc_binding_dialog_members[] = {
    {NULL, 0, 0 , 0, NULL}
};

static int gtk_rpc_binding_dialog_init(PyGObject *self, PyObject *args, PyObject *kwds)
{
    static char *kwlist[] = { "pipe", NULL };
    dcerpc_InterfaceObject *py_SAMPipe;

    if (!PyArg_ParseTupleAndKeywords(args, kwds,"O:GtkRpcBindingDialog.__init__", kwlist, &py_SAMPipe))
        return -1;
    self->obj = (GObject *) gtk_rpc_binding_dialog_new(py_SAMPipe->pipe);

    if (!self->obj) {
        PyErr_SetString(PyExc_RuntimeError, "could not create GtkRpcBindingDialog object");
        return -1;
    }

    pygobject_register_wrapper((PyObject *) self);

    return 0;
}


static PyObject *_wrap_gtk_rpc_binding_dialog_get_host(PyGObject *self)
{
    const gchar *ret;
    
    ret = gtk_rpc_binding_dialog_get_host(SAMBAGTK_RPC_BINDING_DIALOG(self->obj));

    if (ret != NULL)
        return PyString_FromString(ret);
    
    Py_INCREF(Py_None);
    return Py_None;
}

static PyObject *_wrap_gtk_rpc_binding_dialog_get_binding_string(PyGObject *self)
{
    const gchar *ret;
    
    ret = gtk_rpc_binding_dialog_get_binding_string(SAMBAGTK_RPC_BINDING_DIALOG(self->obj));
    
    if (ret != NULL)
        return PyString_FromString(ret);

    Py_INCREF(Py_None);
    return Py_None;
}

static PyMethodDef gtk_rpc_binding_dialog_methods[] = {
    {"get_host", (PyCFunction) _wrap_gtk_rpc_binding_dialog_get_host, METH_VARARGS, NULL},
    {"get_binding_string", (PyCFunction) _wrap_gtk_rpc_binding_dialog_get_binding_string, METH_VARARGS, NULL},
    {NULL, NULL, 0, NULL}
};

static PyTypeObject _PyGtkRpcBindingDialog_Type = {
    PyObject_HEAD_INIT(NULL)
    0,                         /*ob_size*/
    "sambagtk.GtkRpcBindingDialog",                  /*tp_name*/
    sizeof(PyGObject),      /*tp_basicsize*/
    0,                         /*tp_itemsize*/
    0,                         /*tp_dealloc*/
    0,                         /*tp_print*/
    0,                         /*tp_getattr*/
    0,                         /*tp_setattr*/
    0,                         /*tp_compare*/
    0,                         /*tp_repr*/
    0,                         /*tp_as_number*/
    0,                         /*tp_as_sequence*/
    0,                         /*tp_as_mapping*/
    0,                         /*tp_hash */
    0,                         /*tp_call*/
    0,                         /*tp_str*/
    0,                         /*tp_getattro*/
    0,                         /*tp_setattro*/
    0,                         /*tp_as_buffer*/
    Py_TPFLAGS_DEFAULT | Py_TPFLAGS_BASETYPE,        /*tp_flags*/
    0,             /* tp_doc */
    0,		               /* tp_traverse */
    0,		               /* tp_clear */
    0,		               /* tp_richcompare */
    offsetof(PyGObject, weakreflist),		               /* tp_weaklistoffset */
    0,		               /* tp_iter */
    0,		               /* tp_iternext */
    gtk_rpc_binding_dialog_methods,             /* tp_methods */
    gtk_rpc_binding_dialog_members,             /* tp_members */
    0,                         /* tp_getset */
    0,                         /* tp_base */
    0,                         /* tp_dict */
    0,                         /* tp_descr_get */
    0,                         /* tp_descr_set */
    0,                         /* tp_dictoffset */
    (initproc) gtk_rpc_binding_dialog_init,      /* tp_init */
    0,                         /* tp_alloc */
    0                 /* tp_new */
};


    /* GtkSelectDomainDialog type */

static PyMemberDef gtk_select_domain_dialog_members[] = {
    {NULL, 0, 0 , 0, NULL}
};

static int gtk_select_domain_dialog_init(PyGObject *self, PyObject *args, PyObject *kwds)
{
    static char *kwlist[] = { "pipe", NULL };
    dcerpc_InterfaceObject *py_SAMPipe;

    if (!PyArg_ParseTupleAndKeywords(args, kwds,"O:GtkSelectDomainDialog.__init__", kwlist, &py_SAMPipe))
        return -1;
    self->obj = (GObject *) gtk_select_domain_dialog_new(py_SAMPipe->pipe);

    if (!self->obj) {
        PyErr_SetString(PyExc_RuntimeError, "could not create GtkSelectDomainDialog object");
        return -1;
    }

    pygobject_register_wrapper((PyObject *) self);

    return 0;
}

static PyObject *_wrap_gtk_select_domain_dialog_get_handle(PyGObject *self)
{
    /*struct policy_handle ph;
    
    ph = gtk_select_domain_dialog_get_handle(GTK_SELECT_DOMAIN_DIALOG(self->obj));
    
    return py_talloc_new(struct policy_handle, PyPolicy_Handle_Type);*/
    return Py_None;
}

static PyMethodDef gtk_select_domain_dialog_methods[] = {
    {"get_handle", (PyCFunction) _wrap_gtk_select_domain_dialog_get_handle, METH_NOARGS, NULL},
    {NULL, NULL, 0, NULL}
};

static PyTypeObject _PyGtkSelectDomainDialog_Type = {
    PyObject_HEAD_INIT(NULL)
    0,                         /*ob_size*/
    "sambagtk.GtkSelectDomainDialog",                  /*tp_name*/
    sizeof(PyGObject),      /*tp_basicsize*/
    0,                         /*tp_itemsize*/
    0,                         /*tp_dealloc*/
    0,                         /*tp_print*/
    0,                         /*tp_getattr*/
    0,                         /*tp_setattr*/
    0,                         /*tp_compare*/
    0,                         /*tp_repr*/
    0,                         /*tp_as_number*/
    0,                         /*tp_as_sequence*/
    0,                         /*tp_as_mapping*/
    0,                         /*tp_hash */
    0,                         /*tp_call*/
    0,                         /*tp_str*/
    0,                         /*tp_getattro*/
    0,                         /*tp_setattro*/
    0,                         /*tp_as_buffer*/
    Py_TPFLAGS_DEFAULT | Py_TPFLAGS_BASETYPE,        /*tp_flags*/
    0,             /* tp_doc */
    0,		               /* tp_traverse */
    0,		               /* tp_clear */
    0,		               /* tp_richcompare */
    offsetof(PyGObject, weakreflist),		               /* tp_weaklistoffset */
    0,		               /* tp_iter */
    0,		               /* tp_iternext */
    gtk_select_domain_dialog_methods,             /* tp_methods */
    gtk_select_domain_dialog_members,             /* tp_members */
    0,                         /* tp_getset */
    0,                         /* tp_base */
    0,                         /* tp_dict */
    0,                         /* tp_descr_get */
    0,                         /* tp_descr_set */
    0,                         /* tp_dictoffset */
    (initproc) gtk_select_domain_dialog_init,      /* tp_init */
    0,                         /* tp_alloc */
    0                 /* tp_new */
};



    /* GtkSelectHostDialog type */

static PyMemberDef gtk_select_host_dialog_members[] = {
    {NULL, 0, 0 , 0, NULL}
};

static int gtk_select_host_dialog_init(PyGObject *self, PyObject *args, PyObject *kwds)
{
    static char *kwlist[] = { "pipe", NULL };
    dcerpc_InterfaceObject *py_SAMPipe;

    if (!PyArg_ParseTupleAndKeywords(args, kwds,"O:GtkSelectHostDialog.__init__", kwlist, &py_SAMPipe))
        return -1;
    self->obj = (GObject *) gtk_select_host_dialog_new(py_SAMPipe->pipe);

    if (!self->obj) {
        PyErr_SetString(PyExc_RuntimeError, "could not create GtkSelectHostDialog object");
        return -1;
    }

    pygobject_register_wrapper((PyObject *) self);

    return 0;
}

static PyObject *_wrap_gtk_select_host_dialog_get_host(PyGObject *self)
{
    const gchar *ret;
    
    ret = gtk_select_host_dialog_get_host(GTK_SELECT_HOST_DIALOG(self->obj));
    
    if (ret != NULL)
        return PyString_FromString(ret);

    Py_INCREF(Py_None);
    return Py_None;
}

static PyMethodDef gtk_select_host_dialog_methods[] = {
    {"get_host", (PyCFunction) _wrap_gtk_select_host_dialog_get_host, METH_NOARGS, NULL},
    {NULL, NULL, 0, NULL}
};

static PyTypeObject _PyGtkSelectHostDialog_Type = {
    PyObject_HEAD_INIT(NULL)
    0,                         /*ob_size*/
    "sambagtk.GtkSelectHostDialog",                  /*tp_name*/
    sizeof(PyGObject),      /*tp_basicsize*/
    0,                         /*tp_itemsize*/
    0,                         /*tp_dealloc*/
    0,                         /*tp_print*/
    0,                         /*tp_getattr*/
    0,                         /*tp_setattr*/
    0,                         /*tp_compare*/
    0,                         /*tp_repr*/
    0,                         /*tp_as_number*/
    0,                         /*tp_as_sequence*/
    0,                         /*tp_as_mapping*/
    0,                         /*tp_hash */
    0,                         /*tp_call*/
    0,                         /*tp_str*/
    0,                         /*tp_getattro*/
    0,                         /*tp_setattro*/
    0,                         /*tp_as_buffer*/
    Py_TPFLAGS_DEFAULT | Py_TPFLAGS_BASETYPE,        /*tp_flags*/
    0,             /* tp_doc */
    0,		               /* tp_traverse */
    0,		               /* tp_clear */
    0,		               /* tp_richcompare */
    offsetof(PyGObject, weakreflist),		               /* tp_weaklistoffset */
    0,		               /* tp_iter */
    0,		               /* tp_iternext */
    gtk_select_host_dialog_methods,             /* tp_methods */
    gtk_select_host_dialog_members,             /* tp_members */
    0,                         /* tp_getset */
    0,                         /* tp_base */
    0,                         /* tp_dict */
    0,                         /* tp_descr_get */
    0,                         /* tp_descr_set */
    0,                         /* tp_dictoffset */
    (initproc) gtk_select_host_dialog_init,      /* tp_init */
    0,                         /* tp_alloc */
    0                 /* tp_new */
};


    /* module functions */
    
static PyObject *_wrap_gtk_rpc_binding_dialog_get_type(PyObject *self)
{
    GType ret;

    ret = gtk_rpc_binding_dialog_get_type();
    
    return pyg_type_wrapper_new(ret);
}

static PyObject *_wrap_gtk_select_domain_dialog_get_type(PyObject *self)
{
    GType ret;

    ret = gtk_select_domain_dialog_get_type();
    
    return pyg_type_wrapper_new(ret);
}

static PyObject *_wrap_gtk_select_host_dialog_get_type(PyObject *self)
{
    GType ret;

    ret = gtk_select_host_dialog_get_type();
    
    return pyg_type_wrapper_new(ret);
}

static PyObject *_wrap_create_gtk_samba_about_dialog(PyObject *self, PyObject *args, PyObject *kwargs)
{
    static char *kwlist[] = { "appname", NULL };
    char *appname;
    GtkWidget *ret;

    if (!PyArg_ParseTupleAndKeywords(args, kwargs,"s:AboutDialog", kwlist, &appname))
        return NULL;
    
    ret = create_gtk_samba_about_dialog(appname);
    
    /* pygobject_new handles NULL checking */
    return pygobject_new((GObject *) ret);
}

static PyObject *_wrap_gtk_event_loop(PyObject *self)
{
    int ret = gtk_event_loop();
    
    return PyInt_FromLong((long) ret);
}

static PyObject *_wrap_gtk_show_ntstatus(PyObject *self, PyObject *args, PyObject *kwargs)
{
    static char *kwlist[] = { "window", "message", "status", NULL };
    PyGObject *py_widget;
    char *message;
    NTSTATUS status;

    if (!PyArg_ParseTupleAndKeywords(args, kwargs,"Osi:gtk_show_ntstatus", kwlist, &py_widget, &message, &status))
        return NULL;
        
    gtk_show_ntstatus(GTK_WIDGET(py_widget->obj), message, status);
    
    Py_INCREF(Py_None);
    return Py_None;
}

static PyObject *_wrap_gtk_connect_rpc_interface(PyObject *self, PyObject *args, PyObject *kwargs)
{
    static char *kwlist[] = { "ndr_name", NULL };

    char *ndr_name;

    if (!PyArg_ParseTupleAndKeywords(args, kwargs,"s:gtk_connect_rpc_interface", kwlist, &ndr_name))
        return NULL;

    /* FIXME: undefined reference to ndr_table_*
    const struct ndr_interface_table *table;
    
    if (strncmp(ndr_name, SAMR_NDR_NAME, strlen(SAMR_NDR_NAME)) == 0)
        table = &ndr_table_samr;
    else if (strncmp(ndr_name, ATSVC_NDR_NAME, strlen(ATSVC_NDR_NAME)) == 0)
        table = &ndr_table_atsvc;
    else if (strncmp(ndr_name, SVCCTL_NDR_NAME, strlen(SVCCTL_NDR_NAME)) == 0)
        table = &ndr_table_svcctl;
    else if (strncmp(ndr_name, EPMAPPER_NDR_NAME, strlen(EPMAPPER_NDR_NAME)) == 0)
        table = &ndr_table_epmapper;
    else {
        PyErr_SetString(PyExc_RuntimeError, "invalid ndr interface name");
        return NULL;
    }
    
    struct dcerpc_pipe *pipe = gtk_connect_rpc_interface(talloc_autofree_context(), ev_ctx, lp_ctx, table);
    if (pipe == NULL) {
        Py_INCREF(Py_None);
        return Py_None;
    }

    dcerpc_InterfaceObject *py_SAMPipe = (dcerpc_InterfaceObject *) PyObject_New(dcerpc_InterfaceObject, PyDCERPC_Interface_Type);
    py_SAMPipe->pipe = pipe;
    
    return (PyObject *) py_SAMPipe;
    */

    Py_INCREF(Py_None);
    return Py_None;
}

static PyObject *init_ctx(PyObject *self, PyObject *args, PyObject *kwargs)
{
    static char *kwlist[] = { "lp_ctx", NULL };

    PyObject *py_lp_ctx;

    if (!PyArg_ParseTupleAndKeywords(args, kwargs,"O:init_ctx", kwlist, &py_lp_ctx))
        return NULL;

    //lp_ctx = lp_from_py_object(py_lp_ctx); FIXME: undefined reference
	ev_ctx = tevent_context_init(lp_ctx);
	
	dcerpc_init(lp_ctx);
	
	Py_INCREF(Py_None);
	return Py_None;
}



PyMethodDef sambagtk_functions[] = {
    {"gtk_rpc_binding_dialog_get_type", (PyCFunction) _wrap_gtk_rpc_binding_dialog_get_type, METH_NOARGS, NULL},
    {"gtk_select_domain_dialog_get_type", (PyCFunction) _wrap_gtk_select_domain_dialog_get_type, METH_NOARGS, NULL},
    {"AboutDialog", (PyCFunction) _wrap_create_gtk_samba_about_dialog, METH_VARARGS, NULL},
    {"gtk_select_host_dialog_get_type", (PyCFunction) _wrap_gtk_select_host_dialog_get_type, METH_NOARGS, NULL},
    {"gtk_event_loop", (PyCFunction) _wrap_gtk_event_loop, METH_NOARGS, NULL},
    {"gtk_show_ntstatus", (PyCFunction) _wrap_gtk_show_ntstatus, METH_VARARGS, NULL},
    {"gtk_connect_rpc_interface", (PyCFunction) _wrap_gtk_connect_rpc_interface, METH_VARARGS, NULL},
    {"init_ctx", (PyCFunction) init_ctx, METH_VARARGS, NULL},
    {NULL, NULL, 0, NULL}
};

void initsambagtk(void)
{
    PyObject *sambagtk_module, *sambagtk_module_dict, *gtk_module, *gobject_module, *samba_dcerpc_module, *samba_dcerpc_misc_module, *samba_param_module;
	
	setup_logging("sambagtk", DEBUG_STDERR);

	sambagtk_module = Py_InitModule("sambagtk", sambagtk_functions);
	sambagtk_module_dict = PyModule_GetDict(sambagtk_module);
	
	init_pygobject();
	init_pygtk();
	
    if ((gobject_module = PyImport_ImportModule("gobject")) == NULL) {
        PyErr_SetString(PyExc_ImportError, "cannot import gobject module");
        return;
    }

    if ((gtk_module = PyImport_ImportModule("gtk")) == NULL) {
        PyErr_SetString(PyExc_ImportError, "cannot import gtk module");
        return;
    }
    
    if ((samba_dcerpc_module = PyImport_ImportModule("samba.dcerpc")) == NULL) {
        PyErr_SetString(PyExc_ImportError, "cannot import samba.dcerpc module");
        return;
    }
    
    if ((samba_dcerpc_misc_module = PyImport_ImportModule("samba.dcerpc.misc")) == NULL) {
        PyErr_SetString(PyExc_ImportError, "cannot import samba.dcerpc.misc module");
        return;
    }
    
    if ((samba_param_module = PyImport_ImportModule("samba.param")) == NULL) {
        PyErr_SetString(PyExc_ImportError, "cannot import samba.param module");
        return;
    }
    
    if ((PyGObject_Type = (PyTypeObject*) PyObject_GetAttrString(gobject_module, "GObject")) == NULL) {
        PyErr_SetString(PyExc_ImportError, "cannot import GObject from gobject");
        return;
    }

    if ((PyGtkDialog_Type = (PyTypeObject *) PyObject_GetAttrString(gtk_module, "Dialog")) == NULL) {
        PyErr_SetString(PyExc_ImportError, "cannot import Dialog from gtk");
        return;
    }

    if ((PyDCERPC_Interface_Type = (PyTypeObject *) PyObject_GetAttrString(samba_dcerpc_module, "ClientConnection")) == NULL) {
        PyErr_SetString(PyExc_ImportError, "cannot import ClientConnection from samba.dcerpc");
        return;
    }

    if ((PyPolicy_Handle_Type = (PyTypeObject *) PyObject_GetAttrString(samba_dcerpc_misc_module, "policy_handle")) == NULL) {
        PyErr_SetString(PyExc_ImportError, "cannot import policy_handle from samba.dcerpc.misc");
        return;
    }

    pygobject_register_class(sambagtk_module_dict, "GtkRpcBindingDialog", gtk_rpc_binding_dialog_get_type(), PyGtkRpcBindingDialog_Type, Py_BuildValue("(O)", PyGtkDialog_Type));
    pygobject_register_class(sambagtk_module_dict, "GtkSelectDomainDialog", gtk_select_domain_dialog_get_type(), PyGtkSelectDomainDialog_Type, Py_BuildValue("(O)", PyGtkDialog_Type));
    pygobject_register_class(sambagtk_module_dict, "GtkSelectHostDialog", gtk_select_host_dialog_get_type(), PyGtkSelectHostDialog_Type, Py_BuildValue("(O)", PyGtkDialog_Type));
}

