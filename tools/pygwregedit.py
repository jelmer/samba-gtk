#!/usr/bin/python

import sys
import os.path
import traceback
import gtk, gobject
import sambagtk

from samba.dcerpc import mgmt, epmapper
from objects import RegistryKey
from objects import RegistryValue
#from dialogs import ServiceEditDialog


class WinRegPipeManager:
    
    def __init__(self):
        self.pipe = sambagtk.gtk_connect_rpc_interface("winreg")
        self.key_list = []
        self.value_list = []
        
    def close(self):
        if (self.pipe != None):
            self.pipe.close()
            
    def fetch_key_content(self, key):
        pass
    
    def new_key(self, key):
        pass
    
    def new_value(self, value):
        pass
        
    def update_key(self, key):
        pass

    def update_value(self, value):
        pass

    def delete_key(self, key):
        pass

    def delete_value(self, value):
        pass


class RegEditWindow(gtk.Window):

    def __init__(self):
        super(RegEditWindow, self).__init__()
        
        self.create()
        self.pipe_manager = None
        self.update_sensitivity()
        
    def create(self):
        
        # main window  

        accel_group = gtk.AccelGroup()
        
        self.set_title("Registry Editor")
        self.set_default_size(800, 600)
        self.connect("delete_event", self.on_self_delete)
        self.set_icon_from_file(os.path.join(sys.path[0], "images", "registry.png"))
        
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
        
        self.import_item = gtk.MenuItem("_Import", accel_group)
        file_menu.add(self.import_item)
        
        self.export_item = gtk.MenuItem("_Export", accel_group)
        file_menu.add(self.export_item)
        
        self.quit_item = gtk.ImageMenuItem(gtk.STOCK_QUIT, accel_group)
        file_menu.add(self.quit_item)
        
        self.edit_item = gtk.MenuItem("_Edit")
        menubar.add(self.edit_item)
        
        edit_menu = gtk.Menu()
        self.edit_item.set_submenu(edit_menu)

        self.modify_item = gtk.ImageMenuItem("_Modify", accel_group)
        edit_menu.add(self.modify_item)

        self.modify_binary_item = gtk.MenuItem("Modify _Binary", accel_group)
        edit_menu.add(self.modify_binary_item)

        edit_menu.add(gtk.SeparatorMenuItem())

        self.new_item = gtk.ImageMenuItem(gtk.STOCK_NEW, accel_group)
        edit_menu.add(self.new_item)

        new_menu = gtk.Menu()
        self.new_item.set_submenu(new_menu)
        
        self.new_key_item = gtk.MenuItem("_Key", accel_group)
        new_menu.add(self.new_key_item)

        new_menu.add(gtk.SeparatorMenuItem())
        
        self.new_string_item = gtk.MenuItem("_String Value", accel_group)
        new_menu.add(self.new_string_item)

        self.new_binary_item = gtk.MenuItem("_Binary Value", accel_group)
        new_menu.add(self.new_binary_item)

        self.new_dword_item = gtk.MenuItem("_DWORD Value", accel_group)
        new_menu.add(self.new_dword_item)

        self.new_multi_string_item = gtk.MenuItem("_Multi-String Value", accel_group)
        new_menu.add(self.new_multi_string_item)

        self.new_expandable_item = gtk.MenuItem("_Expandable String Value", accel_group)
        new_menu.add(self.new_expandable_item)

        edit_menu.add(gtk.SeparatorMenuItem())

        self.permissions_item = gtk.MenuItem("_Permissions", accel_group)
        edit_menu.add(self.permissions_item)

        edit_menu.add(gtk.SeparatorMenuItem())
        
        self.delete_item = gtk.ImageMenuItem(gtk.STOCK_DELETE, accel_group)
        edit_menu.add(self.delete_item)

        self.rename_item = gtk.ImageMenuItem(gtk.STOCK_EDIT, accel_group)
        edit_menu.add(self.rename_item)

        edit_menu.add(gtk.SeparatorMenuItem())

        self.copy_item = gtk.MenuItem("_Copy Key Name", accel_group)
        edit_menu.add(self.copy_item)

        edit_menu.add(gtk.SeparatorMenuItem())

        self.find_item = gtk.ImageMenuItem(gtk.STOCK_FIND, accel_group)
        self.find_item.get_child().set_text("Find...")
        edit_menu.add(self.find_item)

        self.find_next_item = gtk.MenuItem("Find _Next", accel_group)
        edit_menu.add(self.find_next_item)

        self.view_item = gtk.MenuItem("_View")
        menubar.add(self.view_item)
        
        view_menu = gtk.Menu()
        self.view_item.set_submenu(view_menu)

        self.refresh_item = gtk.ImageMenuItem(gtk.STOCK_REFRESH, accel_group)
        view_menu.add(self.refresh_item)

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
        
        self.new_key_button = gtk.ToolButton(gtk.STOCK_NEW)
        self.new_key_button.set_label("New Key")
        self.new_key_button.set_tooltip_text("Create a new registry key")
        self.new_key_button.set_is_important(True)
        toolbar.insert(self.new_key_button, 3)
                
        self.new_string_button = gtk.ToolButton(gtk.STOCK_NEW)
        self.new_string_button.set_label("New Value")
        self.new_string_button.set_tooltip_text("Create a new string registry value")
        self.new_string_button.set_is_important(True)
        toolbar.insert(self.new_string_button, 4)
                
        self.rename_button = gtk.ToolButton(gtk.STOCK_EDIT)
        self.rename_button.set_label("Rename")
        self.rename_button.set_tooltip_text("Rename the selected key or value")
        self.rename_button.set_is_important(True)
        toolbar.insert(self.rename_button, 5)
        
        self.delete_button = gtk.ToolButton(gtk.STOCK_DELETE)
        self.delete_button.set_tooltip_text("Delete the selected key or value")
        self.delete_button.set_is_important(True)
        toolbar.insert(self.delete_button, 5)
        
        
        # registry tree
        
        hpaned = gtk.HPaned()
        vbox.pack_start(hpaned)
        
        scrolledwindow = gtk.ScrolledWindow(None, None)
        scrolledwindow.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        scrolledwindow.set_shadow_type(gtk.SHADOW_IN)
        scrolledwindow.set_size_request(250, 0)
        hpaned.add1(scrolledwindow)
        
        self.keys_tree_view = gtk.TreeView()
        self.keys_tree_view.set_headers_visible(False)
        scrolledwindow.add(self.keys_tree_view)

        column = gtk.TreeViewColumn()
        column.set_title("Icon")
        renderer = gtk.CellRendererPixbuf()
        column.pack_start(renderer, True)
        self.keys_tree_view.append_column(column)
        column.add_attribute(renderer, "stock-id", 0)

        column = gtk.TreeViewColumn()
        column.set_title("Name")
        renderer = gtk.CellRendererText()
        column.pack_start(renderer, True)
        self.keys_tree_view.append_column(column)
        column.add_attribute(renderer, "text", 1)

        self.keys_store = gtk.TreeStore(gobject.TYPE_STRING, gobject.TYPE_STRING)
        self.keys_tree_view.set_model(self.keys_store)
        
        
        # -------
        #pixbuf = self.render_icon(gtk.STOCK_DIRECTORY, gtk.ICON_SIZE_MENU)
        
        iter = self.keys_store.append(None, [gtk.STOCK_DIRECTORY, "Root"])
        self.keys_store.append(iter, [gtk.STOCK_DIRECTORY, "Child1"])
        # -------


        # value list
        
        scrolledwindow = gtk.ScrolledWindow(None, None)
        scrolledwindow.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        scrolledwindow.set_shadow_type(gtk.SHADOW_IN)
        hpaned.add2(scrolledwindow)
        
        self.values_tree_view = gtk.TreeView()
        scrolledwindow.add(self.values_tree_view)

        column = gtk.TreeViewColumn()
        column.set_title("Name")
        renderer = gtk.CellRendererText()
        column.pack_start(renderer, True)
        self.values_tree_view.append_column(column)
        column.add_attribute(renderer, "text", 0)
                
        column = gtk.TreeViewColumn()
        column.set_title("Type")
        renderer = gtk.CellRendererText()
        column.pack_start(renderer, True)
        self.values_tree_view.append_column(column)
        column.add_attribute(renderer, "text", 1)
        
        column = gtk.TreeViewColumn()
        column.set_title("Data")
        renderer = gtk.CellRendererText()
        column.pack_start(renderer, True)
        self.values_tree_view.append_column(column)
        column.add_attribute(renderer, "text", 2)

        self.values_store = gtk.ListStore(gobject.TYPE_STRING, gobject.TYPE_STRING, gobject.TYPE_STRING)
        self.values_tree_view.set_model(self.values_store)
        

        # status bar

        self.statusbar = gtk.Statusbar()
        self.statusbar.set_has_resize_grip(True)
        vbox.pack_start(self.statusbar, False, False, 0)
        
        
        # signals/events
        
        self.connect_item.connect("activate", self.on_connect_item_activate)
        self.disconnect_item.connect("activate", self.on_disconnect_item_activate)
        self.import_item.connect("activate", self.on_import_item_activate)
        self.export_item.connect("activate", self.on_export_item_activate)
        self.quit_item.connect("activate", self.on_quit_item_activate)        
        self.modify_item.connect("activate", self.on_modify_item_activate)
        self.modify_binary_item.connect("activate", self.on_modify_binary_item_activate)
        self.new_key_item.connect("activate", self.on_new_key_item_activate)
        self.new_string_item.connect("activate", self.on_new_string_item_activate)
        self.new_binary_item.connect("activate", self.on_new_binary_item_activate)
        self.new_dword_item.connect("activate", self.on_new_dword_item_activate)
        self.new_multi_string_item.connect("activate", self.on_new_multi_string_item_activate)
        self.new_expandable_item.connect("activate", self.on_new_expandable_item_activate)
        self.permissions_item.connect("activate", self.on_permissions_item_activate)
        self.delete_item.connect("activate", self.on_delete_item_activate)
        self.rename_item.connect("activate", self.on_rename_item_activate)
        self.copy_item.connect("activate", self.on_copy_item_activate)
        self.find_item.connect("activate", self.on_find_item_activate)
        self.find_next_item.connect("activate", self.on_find_next_item_activate)
        self.refresh_item.connect("activate", self.on_refresh_item_activate)
        self.about_item.connect("activate", self.on_about_item_activate)

        self.connect_button.connect("clicked", self.on_connect_item_activate)
        self.disconnect_button.connect("clicked", self.on_disconnect_item_activate)
        self.new_key_button.connect("clicked", self.on_new_key_item_activate)
        self.new_string_button.connect("clicked", self.on_new_string_item_activate)
        self.delete_button.connect("clicked", self.on_delete_item_activate)        
        self.rename_button.connect("clicked", self.on_rename_item_activate)        
        
        self.keys_tree_view.get_selection().connect("changed", self.on_keys_tree_view_selection_changed)
        self.values_tree_view.get_selection().connect("changed", self.on_values_tree_view_selection_changed)
        self.values_tree_view.connect("button_press_event", self.on_values_tree_view_button_press)
        
        self.add_accel_group(accel_group)

    def refresh_keys_tree_view(self):
        pass

    def refresh_values_tree_view(self):
        pass
#        (model, paths) = self.services_tree_view.get_selection().get_selected_rows()
#        
#        self.services_store.clear()
#        for service in self.pipe_manager.service_list:
#            self.services_store.append(service.list_view_representation())
#        
#        if (len(paths) > 0):
#            self.services_tree_view.get_selection().select_path(paths[0])
#
    def get_selected_registry_key(self):
        if (self.pipe_manager == None): # not connected
            return None
        
        (model, iter) = self.keys_tree_view.get_selection().get_selected()
        if (iter == None): # no selection
            return None
        else:
            name = model.get_value(iter, 1)
            return [key for key in self.pipe_manager.key_list if key.name == name][0]
    
    def get_selected_registry_value(self):
        if (self.pipe_manager == None): # not connected
            return None
        
        (model, iter) = self.values_tree_view.get_selection().get_selected()
        if (iter == None): # no selection
            return None
        else:
            name = model.get_value(iter, 0)
            return [value for value in self.pipe_manager.value_list if value.name == name][0]

    def set_status(self, message):
        self.statusbar.pop(0)
        self.statusbar.push(0, message)

    def update_sensitivity(self):
        connected = (self.pipe_manager != None)
        
        key_selected = (self.get_selected_registry_key() != None)
        value_selected = (self.get_selected_registry_value() != None)

        self.connect_item.set_sensitive(not connected)
        self.disconnect_item.set_sensitive(connected)
        self.import_item.set_sensitive(connected)
        self.export_item.set_sensitive(connected)
        self.modify_item.set_sensitive(connected and value_selected)
        self.modify_binary_item.set_sensitive(connected and value_selected)
        self.new_key_item.set_sensitive(connected and key_selected)
        self.new_string_item.set_sensitive(connected and key_selected)
        self.new_binary_item.set_sensitive(connected and key_selected)
        self.new_dword_item.set_sensitive(connected and key_selected)
        self.new_multi_string_item.set_sensitive(connected and key_selected)
        self.new_expandable_item.set_sensitive(connected and key_selected)
        self.permissions_item.set_sensitive(connected and (key_selected or value_selected))
        self.delete_item.set_sensitive(connected and (key_selected or value_selected))
        self.rename_item.set_sensitive(connected and (key_selected or value_selected))
        self.copy_item.set_sensitive(connected and key_selected)
        self.find_item.set_sensitive(connected)
        self.find_next_item.set_sensitive(connected)
        self.refresh_item.set_sensitive(connected)

        self.connect_button.set_sensitive(not connected)
        self.disconnect_button.set_sensitive(connected)
        self.new_key_button.set_sensitive(connected and key_selected)
        self.new_string_button.set_sensitive(connected and key_selected)
        self.rename_button.set_sensitive(connected and (key_selected or value_selected))
        self.delete_button.set_sensitive(connected and (key_selected or value_selected))
        
    def run_message_dialog(self, type, buttons, message):
        message_box = gtk.MessageDialog(self, gtk.DIALOG_MODAL, type, buttons, message)
        response = message_box.run()
        message_box.hide()
        
        return response

#    def run_service_edit_dialog(self, service = None, apply_callback = None):
#        dialog = ServiceEditDialog(self.pipe_manager, service)
#        dialog.show_all()
#        
#        # loop to handle the applies
#        while True:
#            response_id = dialog.run()
#            
#            if (response_id in [gtk.RESPONSE_OK, gtk.RESPONSE_APPLY]):
#                problem_msg = dialog.check_for_problems()
#                
#                if (problem_msg != None):
#                    self.run_message_dialog(gtk.MESSAGE_ERROR, gtk.BUTTONS_OK, problem_msg)
#                else:
#                    dialog.values_to_service()
#                    if (apply_callback != None):
#                        apply_callback()
#                    if (response_id == gtk.RESPONSE_OK):
#                        dialog.hide()
#                        break
#                        
#            else:
#                dialog.hide()
#                return None
#        
#        return dialog.service
#    
    def on_self_delete(self, widget, event):
        if (self.pipe_manager != None):
            self.on_disconnect_item_activate(self.disconnect_item)
        
        gtk.main_quit()
        return False

    def on_connect_item_activate(self, widget):
        try:
            self.pipe_manager = WinRegPipeManager()
            
        except Exception:
            print "failed to connect"
            traceback.print_exc()
            self.pipe_manager = None
            return
        
        self.refresh_keys_tree_view()
        self.refresh_values_tree_view()
        self.update_sensitivity()

    def on_disconnect_item_activate(self, widget):
        if (self.pipe_manager != None):
            self.pipe_manager.close()
            self.pipe_manager = None
        
        self.keys_store.clear()       
        self.values_store.clear()       
        self.update_sensitivity()
    
    def on_export_item_activate(self, widget):
        pass
    
    def on_import_item_activate(self, widget):
        pass
    
    def on_quit_item_activate(self, widget):
        self.on_self_delete(None, None)

    def on_modify_item_activate(self, widget):
        pass

    def on_modify_binary_item_activate(self, widget):
        pass
    
    def on_new_key_item_activate(self, widget):
        pass

    def on_new_string_item_activate(self, widget):
        pass
    
    def on_new_binary_item_activate(self, widget):
        pass
    
    def on_new_dword_item_activate(self, widget):
        pass
    
    def on_new_multi_string_item_activate(self, widget):
        pass
    
    def on_new_expandable_item_activate(self, widget):
        pass

    def on_permissions_item_activate(self, widget):
        pass

    def on_delete_item_activate(self, widget):
        pass

    def on_rename_item_activate(self, widget):
        pass
    
    def on_copy_item_activate(self, widget):
        pass
    
    def on_find_item_activate(self, widget):
        pass
    
    def on_find_next_item_activate(self, widget):
        pass

    def on_refresh_item_activate(self, widget):
        self.pipe_manager.get_from_pipe()
        self.refresh_services_list_view()

    def on_about_item_activate(self, widget):
        aboutwin = sambagtk.AboutDialog("PyGWRegEdit")
        aboutwin.run()
        aboutwin.destroy()

    def on_keys_tree_view_selection_changed(self, widget):
        self.update_sensitivity()

    def on_values_tree_view_selection_changed(self, widget):
        self.update_sensitivity()

    def on_values_tree_view_button_press(self, widget, event):
        pass
        #if (event.type == gtk.gdk._2BUTTON_PRESS):
            #self.on_edit_item_activate(self.edit_item)

        
win = RegEditWindow()
win.show_all()
gtk.main()
