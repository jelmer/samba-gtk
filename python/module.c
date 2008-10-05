#include "pygobject.h"

extern PyMethodDef sambagtk_functions[];

void sambagtk_register_classes(PyObject *d);

void initsambagtk(void)
{
	PyObject *m, *d;

	m = Py_InitModule("sambagtk", sambagtk_functions);
	d = PyModule_GetDict(m);

	sambagtk_register_classes(d);
}
