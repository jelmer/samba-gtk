#!/usr/bin/python

# Unix SMB/CIFS implementation.
# Copyright (C) Jelmer Vernooij <jelmer@samba.org> 2007
#   
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#   
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#   
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

"""Simple GTK+ frontend for LDB."""

import gtk
import gobject
import ldb
import os
import sys

class LdbURLDialog(gtk.Dialog):
    """Dialog that prompts for a LDB URL.

    Ideally this should remember LDB urls and list them in a combo box.
    """
    def __init__(self, parent=None):
        """Create a new LdbURLDialog. 

        :param parent: Parent window.
        """
        super(LdbURLDialog, self).__init__(parent=parent, 
                buttons=(gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL, gtk.STOCK_OPEN, gtk.RESPONSE_OK)
                )
        self.vbox.add(gtk.Label("Enter URL:"))
        self.url = gtk.Entry()
        self.vbox.add(self.url)
        self.show_all()

    def get_url(self):
        return self.url.get_text()


def Ldb(url):
    """Create a new LDB object.
    
    :param url: LDB URL to connect to.
    """
    ret = ldb.Ldb()
    path = os.getenv("LDB_MODULES_PATH")
    if path is not None:
        ret.set_modules_dir(path)
    ret.connect(url)
    return ret


class LdbBrowser(gtk.Window):
    """GTK+ based LDB browser.
    """
    def set_ldb(self, ldb):
        """Change the LDB object displayed.

        Will refresh the window.
        
        :param ldb: New LDB object to use.
        """
        self.ldb = ldb
        self.menu_disconnect.set_sensitive(True)
        self._fill_tree()

    def _cb_connect(self, button):
        dialog = LdbURLDialog()
        if dialog.run() == gtk.RESPONSE_OK:
            self.set_ldb(Ldb(dialog.get_url()))
        dialog.destroy()

    def _cb_open(self, button):
        dialog = gtk.FileChooserDialog(title="Please choose a file", 
                                       parent=self,
                                      buttons=(gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL, gtk.STOCK_OPEN, gtk.RESPONSE_OK))
        if dialog.run() == gtk.RESPONSE_OK:
            self.set_ldb(Ldb(dialog.get_filename()))

        dialog.destroy()

    def _cb_disconnect(self, button):
        self.treemodel.clear()
        self.attributemodel.clear()
        self.menu_disconnect.set_sensitive(False)
        self.ldb = None

    def _fill_tree(self, hide_special=False):
        self.treemodel.clear()
        paths = {}
        def add_node(dn):
            if dn.is_special() and hide_special:
                return None
            if paths.has_key(str(dn)):
                return paths[str(dn)]
            parent_dn = dn.parent()
            text = str(dn)
            if parent_dn is not None and str(parent_dn) != '':
                parent = add_node(parent_dn)
                text = text[:-len(str(parent_dn))].rstrip(",")
            else:
                parent = None
            paths[str(dn)] = self.treemodel.append(parent, [text, dn])

        for msg in self.ldb.search(None, ldb.SCOPE_SUBTREE, None, ["dn"]):
            add_node(msg.dn)

    def _toggle_special_entries(self, item):
        self._fill_tree(item.get_active())

    def _treeview_cursor_cb(self, item):
        (model, iter) = item.get_selection().get_selected()
        dn = model.get_value(iter, 1)
        self.attributemodel.clear()
        msg = self.ldb.search(dn, ldb.SCOPE_BASE)[0]
        for name in msg:
            el = msg[name]
            for val in set(el):
                self.attributemodel.append([name, val, el])

    def __init__(self):
        super(LdbBrowser, self).__init__()
        vbox = gtk.VBox(spacing=0)
        
        # Menu
        self.menu = gtk.MenuBar()
        menuitem_db = gtk.MenuItem("_Database")
        menu_db = gtk.Menu()
        menuitem_db.set_submenu(menu_db)
        self.menu.add(menuitem_db)

        # Database menu
        menu_connect = gtk.MenuItem("Connect to _URL...")
        menu_connect.connect('activate', self._cb_connect)
        menu_db.add(menu_connect)

        menu_open = gtk.MenuItem("Open _File...")
        menu_open.connect('activate', self._cb_open)
        menu_db.add(menu_open)

        self.menu_disconnect = gtk.MenuItem("_Disconnect")
        self.menu_disconnect.connect('activate', self._cb_disconnect)
        self.menu_disconnect.set_sensitive(False)
        menu_db.add(self.menu_disconnect)

        menu_db.add(gtk.SeparatorMenuItem())
        menu_hide_special = gtk.CheckMenuItem("_Hide special entries")
        menu_hide_special.connect('toggled', self._toggle_special_entries)
        menu_db.add(menu_hide_special)

        menu_db.add(gtk.SeparatorMenuItem())
        menu_exit = gtk.ImageMenuItem(gtk.STOCK_QUIT)
        menu_exit.connect('activate', lambda x: gtk.main_quit())

        menu_db.add(menu_exit)

        vbox.pack_start(self.menu, expand=False)

        self.treeview = gtk.TreeView()
        self.treemodel = gtk.TreeStore(gobject.TYPE_STRING, gobject.TYPE_PYOBJECT)
        self.treeview.set_model(self.treemodel)
        self.treeview.set_headers_visible(False)
        self.treeview.append_column(gtk.TreeViewColumn("_Dn", 
                                    gtk.CellRendererText(), text=0))
        self.treeview.connect("cursor-changed", self._treeview_cursor_cb)
        self.attributeview = gtk.TreeView()
        self.attributemodel = gtk.ListStore(str, str, gobject.TYPE_PYOBJECT)
        self.attributeview.set_model(self.attributemodel)
        self.attributeview.append_column(gtk.TreeViewColumn("_Name", 
                                         gtk.CellRendererText(), text=0))
        self.attributeview.append_column(gtk.TreeViewColumn("_Value", 
                                         gtk.CellRendererText(), text=1))
        pane = gtk.HPaned()
        pane.set_position(200)
        treeview_window = gtk.ScrolledWindow()
        treeview_window.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        treeview_window.add(self.treeview)
        pane.pack1(treeview_window, resize=False, shrink=True)
        attributeview_window = gtk.ScrolledWindow()
        attributeview_window.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        attributeview_window.add(self.attributeview)
        pane.pack2(attributeview_window, shrink=True)
        vbox.pack_start(pane, fill=True, expand=True)

        self.statusbar = gtk.Statusbar()
        vbox.pack_end(self.statusbar, expand=False)

        self.add(vbox)
        self.set_default_size(700, 500)
        self.show_all()


browser = LdbBrowser()
if len(sys.argv) > 1:
    browser.set_ldb(Ldb(sys.argv[1]))
gtk.main()
