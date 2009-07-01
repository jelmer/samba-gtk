#!/usr/bin/python

import gtk, gobject
import sambagtk
from samba.dcerpc import mgmt, epmapper


class ServiceCTLWindow(gtk.Window):

    def __init__(self):
        super(ServiceCTLWindow, self).__init__()
        self.create()
        self.update_sensitivity(False)
        
    def create(self):
        
        
        # main window  

        accel_group = gtk.AccelGroup()
        
        self.set_title("Service Management")
        self.set_default_size(642, 562)
        self.connect("delete_event", self.on_self_delete)
        
    	vbox = gtk.VBox(False, 0)
    	self.add(vbox)


        # menu
        
        menubar = gtk.MenuBar()
        vbox.pack_start(menubar, False, False, 0)
        
        self.file_item = gtk.MenuItem("_File")
        menubar.add(self.file_item)
        
        file_menu = gtk.Menu()
        self.file_item.set_submenu(file_menu)
        
        self.connect_item = gtk.ImageMenuItem(gtk.STOCK_CONNECT)
        file_menu.add(self.connect_item)
        
        self.disconnect_item = gtk.ImageMenuItem(gtk.STOCK_DISCONNECT)
        file_menu.add(self.disconnect_item)
        
        menu_separator_item = gtk.SeparatorMenuItem()
        file_menu.add(menu_separator_item)
        
        self.quit_item = gtk.ImageMenuItem(gtk.STOCK_QUIT, accel_group)
        file_menu.add(self.quit_item)
        
        self.view_item = gtk.MenuItem("_View")
        menubar.add(self.view_item)
        
        view_menu = gtk.Menu()
        self.view_item.set_submenu(view_menu)

        self.refresh_item = gtk.ImageMenuItem(gtk.STOCK_REFRESH, accel_group)
        view_menu.add(self.refresh_item)

        self.service_item = gtk.MenuItem("_Service")
        menubar.add(self.service_item)
        
        service_menu = gtk.Menu()
        self.service_item.set_submenu(service_menu)

        self.start_item = gtk.ImageMenuItem(gtk.STOCK_MEDIA_PLAY, accel_group)
        service_menu.add(self.start_item)
        
        self.stop_item = gtk.ImageMenuItem(gtk.STOCK_MEDIA_STOP, accel_group)
        service_menu.add(self.stop_item)
        
        self.edit_item = gtk.ImageMenuItem(gtk.STOCK_EDIT, accel_group)
        service_menu.add(self.edit_item)

        self.help_item = gtk.MenuItem("_Help")
        menubar.add(self.help_item)

        help_menu = gtk.Menu()
        self.help_item.set_submenu(help_menu)

        self.about_item = gtk.ImageMenuItem(gtk.STOCK_ABOUT)
        help_menu.add(self.about_item)
        
        
        # service list
        
        scrolledwindow = gtk.ScrolledWindow(None, None)
        vbox.pack_start(scrolledwindow)
        
        self.services_tree_view = gtk.TreeView()
        scrolledwindow.add(self.services_tree_view)
        
        column = gtk.TreeViewColumn()
        column.set_title("Name")
        renderer = gtk.CellRendererText()
        column.pack_start(renderer, True)
        self.services_tree_view.append_column(column)
        column.add_attribute(renderer, "text", 0)
                
        column = gtk.TreeViewColumn()
        column.set_title("Description")
        renderer = gtk.CellRendererText()
        column.pack_start(renderer, True)
        self.services_tree_view.append_column(column)
        column.add_attribute(renderer, "text", 1)
        
        column = gtk.TreeViewColumn()
        column.set_title("Status")
        renderer = gtk.CellRendererText()
        column.pack_start(renderer, True)
        self.services_tree_view.append_column(column)
        column.add_attribute(renderer, "text", 2)

        column = gtk.TreeViewColumn()
        column.set_title("Startup Type")
        renderer = gtk.CellRendererText()
        column.pack_start(renderer, True)
        self.services_tree_view.append_column(column)
        column.add_attribute(renderer, "text", 3)

        self.services_store = gtk.ListStore(gobject.TYPE_STRING, gobject.TYPE_STRING, gobject.TYPE_STRING, gobject.TYPE_STRING)
        self.services_tree_view.set_model(self.services_store)


        # status bar

        self.statusbar = gtk.Statusbar()
        self.statusbar.set_has_resize_grip(True)
        vbox.pack_start(self.statusbar, False, False, 0)
        
        
        # signals/events
        
        self.connect_item.connect("activate", self.on_connect_item_activate)
        self.disconnect_item.connect("activate", self.on_disconnect_item_activate)
        self.quit_item.connect("activate", self.on_quit_item_activate)
        
        self.refresh_item.connect("activate", self.on_refresh_item_activate)
        
        self.start_item.connect("activate", self.on_start_item_activate)
        self.stop_item.connect("activate", self.on_stop_item_activate)
        self.edit_item.connect("activate", self.on_edit_item_activate)
        
        self.about_item.connect("activate", self.on_about_item_activate)
        
        self.add_accel_group(accel_group)

    def set_status(self, message):
        self.statusbar.pop(0)
        self.statusbar.push(0, message)
        
    def update_sensitivity(self, is_connected):
        self.connect_item.set_sensitive(not is_connected)
        self.disconnect_item.set_sensitive(is_connected)
        self.refresh_item.set_sensitive(is_connected)
        self.start_item.set_sensitive(is_connected)
        self.stop_item.set_sensitive(is_connected)
        self.edit_item.set_sensitive(is_connected)

    def on_self_delete(self, widget, event):
        gtk.main_quit()
        return False

    def on_connect_item_activate(self, widget):
        self.update_sensitivity(True)

    def on_disconnect_item_activate(self, widget):
        self.update_sensitivity(False)
    
    def on_quit_item_activate(self, widget):
        self.on_self_delete(None, None)
    
    def on_refresh_item_activate(self, widget):
        None

    def on_start_item_activate(self, widget):
        None

    def on_stop_item_activate(self, widget):
        None
    
    def on_edit_item_activate(self, widget):
        None
    
    def on_about_item_activate(self, widget):
        aboutwin = sambagtk.AboutDialog("PyGWSVCCTL")
        aboutwin.run()
        aboutwin.destroy()

win = ServiceCTLWindow()
win.show_all()
gtk.main()
