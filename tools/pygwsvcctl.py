#!/usr/bin/python

import sys
import os.path
import traceback
import gtk, gobject
import sambagtk

from samba.dcerpc import mgmt, epmapper
from objects import Service
from dialogs import ServiceEditDialog


class SVCCTLPipeManager:
    
    def __init__(self):
        self.pipe = sambagtk.gtk_connect_rpc_interface("svrsvc")
        self.service_list = []
        
    def close(self):
        if (self.pipe != None):
            self.pipe.close()
        
    def get_from_pipe(self):
        service1 = Service("service1", "Service Description 1", False, Service.STARTUP_TYPE_NORMAL)
        service2 = Service("service2", "Service Description 2", True, Service.STARTUP_TYPE_AUTOMATIC)
        
        del self.service_list[:]
        self.service_list.append(service1)
        self.service_list.append(service2)
        
    def service_to_pipe(self, service):
        pass

    def start_service(self, service):
        pass

    def stop_service(self, service):
        pass


class SVCCTLWindow(gtk.Window):

    def __init__(self):
        super(SVCCTLWindow, self).__init__()
        
        self.create()
        self.pipe_manager = None
        self.update_sensitivity()
        
    def create(self):
        
        
        # main window  

        accel_group = gtk.AccelGroup()
        
        self.set_title("Service Management")
        self.set_default_size(800, 600)
        self.connect("delete_event", self.on_self_delete)
        self.set_icon_from_file(os.path.join(sys.path[0], "images", "service.png"))
        
    	vbox = gtk.VBox(False, 0)
    	self.add(vbox)


        # menu
        
        menubar = gtk.MenuBar()
        vbox.pack_start(menubar, False, False, 0)
        
        self.file_item = gtk.MenuItem("_File")
        menubar.add(self.file_item)
        
        file_menu = gtk.Menu()
        self.file_item.set_submenu(file_menu)
        
        self.connect_item = gtk.ImageMenuItem(gtk.STOCK_CONNECT, accel_group)
        file_menu.add(self.connect_item)
        
        self.disconnect_item = gtk.ImageMenuItem(gtk.STOCK_DISCONNECT, accel_group)
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
        self.start_item.get_child().set_text("Start")
        service_menu.add(self.start_item)
        
        self.stop_item = gtk.ImageMenuItem(gtk.STOCK_MEDIA_STOP, accel_group)
        self.stop_item.get_child().set_text("Stop")
        service_menu.add(self.stop_item)
        
        self.edit_item = gtk.ImageMenuItem(gtk.STOCK_EDIT, accel_group)
        service_menu.add(self.edit_item)

        self.help_item = gtk.MenuItem("_Help")
        menubar.add(self.help_item)

        help_menu = gtk.Menu()
        self.help_item.set_submenu(help_menu)

        self.about_item = gtk.ImageMenuItem(gtk.STOCK_ABOUT, accel_group)
        help_menu.add(self.about_item)
        
        
        # toolbar
        
        toolbar = gtk.Toolbar()
        vbox.pack_start(toolbar, False, False, 0)
        
        self.connect_button = gtk.ToolButton(gtk.STOCK_CONNECT)
        self.connect_button.set_is_important(True)
        self.connect_button.set_tooltip_text("Connect to a server")
        toolbar.insert(self.connect_button, 0)
        
        self.disconnect_button = gtk.ToolButton(gtk.STOCK_DISCONNECT)
        self.disconnect_button.set_is_important(True)
        self.disconnect_button.set_tooltip_text("Disconnect from the server")
        toolbar.insert(self.disconnect_button, 1)
        
        toolbar.insert(gtk.SeparatorToolItem(), 2)
        
        self.start_button = gtk.ToolButton(gtk.STOCK_MEDIA_PLAY)
        self.start_button.set_label("Start")
        self.start_button.set_tooltip_text("Start the service")
        self.start_button.set_is_important(True)
        toolbar.insert(self.start_button, 3)
                
        self.stop_button = gtk.ToolButton(gtk.STOCK_MEDIA_STOP)
        self.stop_button.set_tooltip_text("Stop the service")
        self.stop_button.set_is_important(True)
        toolbar.insert(self.stop_button, 4)
                
        self.edit_button = gtk.ToolButton(gtk.STOCK_EDIT)
        self.edit_button.set_tooltip_text("Edit the service's properties")
        self.edit_button.set_is_important(True)
        toolbar.insert(self.edit_button, 5)
        
        
        # service list
        
        scrolledwindow = gtk.ScrolledWindow(None, None)
        scrolledwindow.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        scrolledwindow.set_shadow_type(gtk.SHADOW_IN)
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

        self.connect_button.connect("clicked", self.on_connect_item_activate)
        self.disconnect_button.connect("clicked", self.on_disconnect_item_activate)
        self.start_button.connect("clicked", self.on_start_item_activate)
        self.stop_button.connect("clicked", self.on_stop_item_activate)
        self.edit_button.connect("clicked", self.on_edit_item_activate)        
        
        self.services_tree_view.get_selection().connect("changed", self.on_services_tree_view_selection_changed)
        self.services_tree_view.connect("button_press_event", self.on_services_tree_view_button_press)
        
        self.add_accel_group(accel_group)

    def refresh_services_list_view(self):
        (model, paths) = self.services_tree_view.get_selection().get_selected_rows()
        
        self.services_store.clear()
        for service in self.pipe_manager.service_list:
            self.services_store.append(service.list_view_representation())
        
        if (len(paths) > 0):
            self.services_tree_view.get_selection().select_path(paths[0])

    def get_selected_service(self):
        if (self.pipe_manager == None): # not connected
            return None
        
        (model, iter) = self.services_tree_view.get_selection().get_selected()
        if (iter == None): # no selection
            return None
        else:            
            name = model.get_value(iter, 0)
            return [service for service in self.pipe_manager.service_list if service.name == name][0]

    def set_status(self, message):
        self.statusbar.pop(0)
        self.statusbar.push(0, message)
        
    def update_sensitivity(self):
        connected = (self.pipe_manager != None)
        
        selected_service = self.get_selected_service()
        if (selected_service == None): # no selection
            started = False
            selected = False
        else:
            started = selected_service.started
            selected = True

        self.connect_item.set_sensitive(not connected)
        self.disconnect_item.set_sensitive(connected)
        self.refresh_item.set_sensitive(connected)
        self.start_item.set_sensitive(connected and selected and not started)
        self.stop_item.set_sensitive(connected and selected and started)
        self.edit_item.set_sensitive(connected and selected)

        self.connect_button.set_sensitive(not connected)
        self.disconnect_button.set_sensitive(connected)
        self.start_button.set_sensitive(connected and selected and not started)
        self.stop_button.set_sensitive(connected and selected and started)
        self.edit_button.set_sensitive(connected and selected)
        
    def run_message_dialog(self, type, buttons, message):
        message_box = gtk.MessageDialog(self, gtk.DIALOG_MODAL, type, buttons, message)
        response = message_box.run()
        message_box.hide()
        
        return response

    def run_service_edit_dialog(self, service = None, apply_callback = None):
        dialog = ServiceEditDialog(self.pipe_manager, service)
        dialog.show_all()
        
        # loop to handle the applies
        while True:
            response_id = dialog.run()
            
            if (response_id in [gtk.RESPONSE_OK, gtk.RESPONSE_APPLY]):
                problem_msg = dialog.check_for_problems()
                
                if (problem_msg != None):
                    self.run_message_dialog(gtk.MESSAGE_ERROR, gtk.BUTTONS_OK, problem_msg)
                else:
                    dialog.values_to_service()
                    if (apply_callback != None):
                        apply_callback()
                    if (response_id == gtk.RESPONSE_OK):
                        dialog.hide()
                        break
                        
            else:
                dialog.hide()
                return None
        
        return dialog.service
    
    def on_self_delete(self, widget, event):
        if (self.pipe_manager != None):
            self.on_disconnect_item_activate(self.disconnect_item)
        
        gtk.main_quit()
        return False

    def on_connect_item_activate(self, widget):
        try:
            self.pipe_manager = SVCCTLPipeManager()
            self.pipe_manager.get_from_pipe()
            
        except Exception:
            print "failed to connect"
            traceback.print_exc()
            self.pipe_manager = None
            return
        
        self.refresh_services_list_view()
        self.update_sensitivity()

    def on_disconnect_item_activate(self, widget):
        if (self.pipe_manager != None):
            self.pipe_manager.close()
            self.pipe_manager = None
        
        self.services_store.clear()       
        self.update_sensitivity()
    
    def on_quit_item_activate(self, widget):
        self.on_self_delete(None, None)
    
    def on_refresh_item_activate(self, widget):
        self.pipe_manager.get_from_pipe()
        self.refresh_services_list_view()

    def on_start_item_activate(self, widget):
        service = self.get_selected_service()
        if (service == None): # no selection
            return 
        
        if (service.started): # already started
            return
        
        self.pipe_manager.start_service(service)
        service.started = True
        
        self.refresh_services_list_view()
        self.update_sensitivity()

    def on_stop_item_activate(self, widget):
        service = self.get_selected_service()
        if (service == None): # no selection
            return 
        
        if (not service.started): # already stopped
            return
        
        self.pipe_manager.stop_service(service)
        service.started = False

        self.refresh_services_list_view()
        self.update_sensitivity()
    
    def on_edit_item_activate(self, widget):
        edit_service = self.get_selected_service()
        self.run_service_edit_dialog(edit_service, self.refresh_services_list_view)
    
    def on_about_item_activate(self, widget):
        aboutwin = sambagtk.AboutDialog("PyGWSVCCTL")
        aboutwin.run()
        aboutwin.destroy()

    def on_services_tree_view_selection_changed(self, widget):
        self.update_sensitivity()

    def on_services_tree_view_button_press(self, widget, event):
        if (event.type == gtk.gdk._2BUTTON_PRESS):
            self.on_edit_item_activate(self.edit_item)

        
win = SVCCTLWindow()
win.show_all()
gtk.main()
