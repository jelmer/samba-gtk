#!/usr/bin/python

import sys
import os.path
import traceback
import threading

import gobject
import gtk
import pango

from samba import credentials
from samba.dcerpc import winreg

from objects import RegistryKey
from objects import RegistryValue

from dialogs import WinRegConnectDialog
from dialogs import AboutDialog


class WinRegPipeManager:
    
    def __init__(self, server_address, transport_type, username, password):
        self.service_list = []
#        self.lock = threading.Lock()
        
        creds = credentials.Credentials()
        if (username.count("\\") > 0):
            creds.set_domain(username.split("\\")[0])
            creds.set_username(username.split("\\")[1])
        elif (username.count("@") > 0):
            creds.set_domain(username.split("@")[1])
            creds.set_username(username.split("@")[0])
        else:
            creds.set_domain("")
            creds.set_username(username)
        creds.set_workstation("")
        creds.set_password(password)
        
        binding = ["ncacn_np:%s", "ncacn_ip_tcp:%s", "ncalrpc:%s"][transport_type]
        self.pipe = winreg.winreg(binding % (server_address), credentials = creds)
        
        self.open_well_known_keys()
        
    def close(self):
        pass # apparently there's no .Close() method for this pipe

    def ls_key(self, key):
        key_list = []
        value_list = []
        
        path_handles = self.open_path(key)
        key_handle = path_handles[len(path_handles) - 1]

        index = 0
        while True:
            try:
                (subkey_name, subkey_class, subkey_changed_time) = self.pipe.EnumKey(
                                                                                     key_handle, 
                                                                                     index, 
                                                                                     WinRegPipeManager.winreg_string_buf(""), 
                                                                                     WinRegPipeManager.winreg_string_buf(""), 
                                                                                     None
                                                                                     )
                
                subkey = RegistryKey(subkey_name.name, key)
                key_list.append(subkey)
                
                index += 1

            except RuntimeError as re:
                if (re.args[0] == 0x103): # no more items
                    break
                else:
                    raise re

        index = 0
        while True:
            try:
                (value_name, value_type, value_data, value_length) = self.pipe.EnumValue(
                                                                                         key_handle,
                                                                                         index, 
                                                                                         WinRegPipeManager.winreg_val_name_buf(""), 
                                                                                         0, 
                                                                                         [], 
                                                                                         8192
                                                                                         )
                
                value = RegistryValue(value_name.name, value_type, value_data, key)
                value_list.append(value)
                
                index += 1

            except RuntimeError as re:
                if (re.args[0] == 0x103): # no more items
                    break
                else:
                    raise re

        self.close_path(path_handles)
        
        default_value_list = [value for value in value_list if value.name == ""]
        if (len(default_value_list) == 0):
            value = RegistryValue("(Default)", winreg.REG_SZ, None, key)
            value_list.append(value)
        else:
            default_value_list[0].name = "(Default)"
        
        return (key_list, value_list)

    #def mv_key(self, key, new_name):    

    def rm_key(self, key):
        (key_list, value_list) = self.ls_key(key)
        
        for key in key_list:
            self.rm_key(key)
        
        path_handles = self.open_path(key)
        key_handle = path_handles[len(path_handles) - 2]
        
        self.pipe.DeleteKey(key_handle, WinRegPipeManager.winreg_string(key.name))
        self.close_path(path_handles)

    def set_value(self, parent_key, value):
        path_handles = self.open_path(parent_key)
        key_handle = path_handles[len(path_handles) - 1]
        
        self.pipe.SetValue(key_handle, WinRegPipeManager.winreg_string(value.name), value.type, value.data)
        self.close_path(path_handles)

    def unset_value(self, parent_key, value):
        path_handles = self.open_path(parent_key)
        key_handle = path_handles[len(path_handles) - 1]
        
        self.pipe.DeleteValue(key_handle, WinRegPipeManager.winreg_string(value.name))
        self.close_path(path_handles)

    def open_well_known_keys(self):
        self.well_known_keys = []
        
        key_handle = self.pipe.OpenHKLM(None, winreg.KEY_ENUMERATE_SUB_KEYS | winreg.KEY_CREATE_SUB_KEY | winreg.KEY_QUERY_VALUE | winreg.KEY_SET_VALUE)
        key = RegistryKey("HKEY_LOCAL_MACHINE", None)
        key.handle = key_handle
        self.well_known_keys.append(key)
    
        key_handle = self.pipe.OpenHKCR(None, winreg.KEY_ENUMERATE_SUB_KEYS | winreg.KEY_CREATE_SUB_KEY | winreg.KEY_QUERY_VALUE | winreg.KEY_SET_VALUE)
        key = RegistryKey("HKEY_CLASSES_ROOT", None)
        key.handle = key_handle
        self.well_known_keys.append(key)
    
        key_handle = self.pipe.OpenHKCU(None, winreg.KEY_ENUMERATE_SUB_KEYS | winreg.KEY_CREATE_SUB_KEY | winreg.KEY_QUERY_VALUE | winreg.KEY_SET_VALUE)
        key = RegistryKey("HKEY_CURRENT_USER", None)
        key.handle = key_handle
        self.well_known_keys.append(key)
    
        key_handle = self.pipe.OpenHKCC(None, winreg.KEY_ENUMERATE_SUB_KEYS | winreg.KEY_CREATE_SUB_KEY | winreg.KEY_QUERY_VALUE | winreg.KEY_SET_VALUE)
        key = RegistryKey("HKEY_CURRENT_CONFIG", None)
        key.handle = key_handle
        self.well_known_keys.append(key)
    
        key_handle = self.pipe.OpenHKU(None, winreg.KEY_ENUMERATE_SUB_KEYS | winreg.KEY_CREATE_SUB_KEY | winreg.KEY_QUERY_VALUE | winreg.KEY_SET_VALUE)
        key = RegistryKey("HKEY_USERS", None)
        key.handle = key_handle
        self.well_known_keys.append(key)
    
    def open_path(self, key):
        if (key.parent == None):
            return [key.handle]
        else:
            path = self.open_path(key.parent)
            parent_handle = path[len(path) - 1]
            
            key_handle = self.pipe.OpenKey(
                                      parent_handle,
                                      WinRegPipeManager.winreg_string(key.name), 
                                      0, 
                                      winreg.KEY_ENUMERATE_SUB_KEYS | winreg.KEY_CREATE_SUB_KEY | winreg.KEY_QUERY_VALUE | winreg.KEY_SET_VALUE
                                      )
            
            return path + [key_handle]
        
    def close_path(self, path_handles):
        for handle in path_handles[:0:-1]:
            self.pipe.CloseKey(handle)

    @staticmethod
    def winreg_string(string):
        ws = winreg.String()
        ws.name = unicode(string)
        ws.name_len = len(string)
        ws.name_size = 8192
        
        return ws
    
    @staticmethod
    def winreg_string_buf(string):
        wsb = winreg.StringBuf()
        wsb.name = unicode(string)
        wsb.length = len(string)
        wsb.size = 8192
        
        return wsb
        
    @staticmethod
    def winreg_val_name_buf(string):
        wvnb = winreg.ValNameBuf()
        wvnb.name = unicode(string)
        wvnb.length = len(string)
        wvnb.size = 8192
        
        return wvnb


#class FetchKeyThread(threading.Thread):
#    
#    def __init__(self, pipe_manager, regedit_window, key_to_fetch, finish_callback):
#        super(FetchKeyThread, self).__init__()
#        
#        self.pipe_manager = pipe_manager
#        self.regedit_window = regedit_window
#        self.key_to_fetch = key_to_fetch
#        self.finish_callback = finish_callback
#        
#    def run(self):
#        try:
#            print " trying to enter critical region: " + self.key_to_fetch.name
#            self.pipe_manager.lock.acquire()
#            print " entered critical region: " + self.key_to_fetch.name
#
##            gtk.gdk.threads_enter()
##            self.regedit_window.set_status("Fetching key '" + self.key_to_fetch.get_absolute_path() + "'...")
##            gtk.gdk.threads_leave()
#            
#            print " before RPC call: " + self.key_to_fetch.name
#            (self.key_list, self.value_list) = self.pipe_manager.ls_key(self.key_to_fetch)
#            print " after RPC call: " + self.key_to_fetch.name
#       
#        except RuntimeError, re:
#            msg = "Failed to fetch registry key: " + re.args[1] + "."
#            print msg
#            traceback.print_exc()
#            
#            gtk.gdk.threads_enter()
#            self.regedit_window.set_status(msg)
#            self.regedit_window.run_message_dialog(gtk.MESSAGE_ERROR, gtk.BUTTONS_OK, msg)
#            gtk.gdk.threads_leave()
#        
#        except Exception, ex:
#            msg = "Failed to fetch registry key: " + str(ex) + "."
#            print msg
#            traceback.print_exc()
#            
#            gtk.gdk.threads_enter()
#            self.regedit_window.set_status(msg)
#            self.regedit_window.run_message_dialog(gtk.MESSAGE_ERROR, gtk.BUTTONS_OK, msg)
#            gtk.gdk.threads_leave()
#        
#        finally:
#            self.pipe_manager.lock.release()
#            print "released critical region: " + self.key_to_fetch.name
#        
#        gtk.gdk.threads_enter()
#        self.regedit_window.set_status("Key fetch done.")
#        if (self.finish_callback != None):
#            self.finish_callback(self.key_to_fetch, self.key_list, self.value_list)
#        gtk.gdk.threads_leave()


class RegEditWindow(gtk.Window):

    def __init__(self):
        super(RegEditWindow, self).__init__()
        
        self.create()
        
        self.pipe_manager = None
        self.server_address = ""
        self.transport_type = 0
        self.username = ""

        self.update_sensitivity()
        
    def create(self):
        
        # main window  

        accel_group = gtk.AccelGroup()
        
        self.set_title("Registry Editor")
        self.set_default_size(800, 600)
        self.connect("delete_event", self.on_self_delete)

        self.icon_filename = os.path.join(sys.path[0], "images", "registry.png")
        self.icon_registry_number_filename = os.path.join(sys.path[0], "images", "registry-number.png")
        self.icon_registry_string_filename = os.path.join(sys.path[0], "images", "registry-string.png")
        self.icon_registry_binary_filename = os.path.join(sys.path[0], "images", "registry-binary.png")
        
        self.icon_pixbuf = gtk.gdk.pixbuf_new_from_file(self.icon_filename)
        self.icon_registry_number_pixbuf = gtk.gdk.pixbuf_new_from_file_at_size(self.icon_registry_number_filename, 22, 22)
        self.icon_registry_string_pixbuf = gtk.gdk.pixbuf_new_from_file_at_size(self.icon_registry_string_filename, 22, 22)
        self.icon_registry_binary_pixbuf = gtk.gdk.pixbuf_new_from_file_at_size(self.icon_registry_binary_filename, 22, 22)

        self.set_icon(self.icon_pixbuf)
        
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
        column.set_title("")
        column.set_resizable(False)
        renderer = gtk.CellRendererPixbuf()
        renderer.set_property("stock-id", gtk.STOCK_DIRECTORY)
        column.pack_start(renderer, True)
        self.keys_tree_view.append_column(column)

        column = gtk.TreeViewColumn()
        column.set_title("Name")
        renderer = gtk.CellRendererText()
        column.pack_start(renderer, True)
        self.keys_tree_view.append_column(column)
        column.add_attribute(renderer, "text", 0)

        self.keys_store = gtk.TreeStore(gobject.TYPE_STRING, gobject.TYPE_PYOBJECT)
        self.keys_tree_view.set_model(self.keys_store)
        
        
        # value list
        
        scrolledwindow = gtk.ScrolledWindow(None, None)
        scrolledwindow.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        scrolledwindow.set_shadow_type(gtk.SHADOW_IN)
        hpaned.add2(scrolledwindow)
        
        self.values_tree_view = gtk.TreeView()
        scrolledwindow.add(self.values_tree_view)

        column = gtk.TreeViewColumn()
        column.set_title("")
        column.set_resizable(False)
        renderer = gtk.CellRendererPixbuf()
        column.pack_start(renderer, True)
        self.values_tree_view.append_column(column)
        column.add_attribute(renderer, "pixbuf", 0)
                
        column = gtk.TreeViewColumn()
        column.set_title("Name")
        column.set_resizable(True)
        column.set_fixed_width(300)
        column.set_sizing(gtk.TREE_VIEW_COLUMN_FIXED)
        column.set_sort_column_id(1)
        renderer = gtk.CellRendererText()
        renderer.set_property("ellipsize", pango.ELLIPSIZE_END)
        column.pack_start(renderer, True)
        self.values_tree_view.append_column(column)
        column.add_attribute(renderer, "text", 1)
                
        column = gtk.TreeViewColumn()
        column.set_title("Type")
        column.set_resizable(True)
        column.set_fixed_width(200)
        column.set_sizing(gtk.TREE_VIEW_COLUMN_FIXED)
        column.set_sort_column_id(2)
        renderer = gtk.CellRendererText()
        renderer.set_property("ellipsize", pango.ELLIPSIZE_END)
        column.pack_start(renderer, True)
        self.values_tree_view.append_column(column)
        column.add_attribute(renderer, "text", 2)
        
        column = gtk.TreeViewColumn()
        column.set_title("Data")
        column.set_resizable(True)
        column.set_sort_column_id(3)
        renderer = gtk.CellRendererText()
        renderer.set_property("ellipsize", pango.ELLIPSIZE_END)
        column.pack_start(renderer, True)
        self.values_tree_view.append_column(column)
        column.add_attribute(renderer, "text", 3)

        self.values_store = gtk.ListStore(gtk.gdk.Pixbuf, gobject.TYPE_STRING, gobject.TYPE_STRING, gobject.TYPE_STRING, gobject.TYPE_PYOBJECT)
        self.values_store.set_sort_column_id(1, gtk.SORT_ASCENDING)
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
        self.keys_tree_view.connect("row-collapsed", self.on_keys_tree_view_row_collapsed_expanded)
        self.keys_tree_view.connect("row-expanded", self.on_keys_tree_view_row_collapsed_expanded)
        self.keys_tree_view.connect("button_press_event", self.on_keys_tree_view_button_press)
        self.values_tree_view.get_selection().connect("changed", self.on_values_tree_view_selection_changed)
        self.values_tree_view.connect("button_press_event", self.on_values_tree_view_button_press)
        
        self.add_accel_group(accel_group)

    def refresh_keys_tree_view(self, iter, key_list):
        if (not self.connected()):
            return
        
        if (iter == None): # well known keys
            for key in self.pipe_manager.well_known_keys:
                self.keys_store.append(None, key.list_view_representation())
                
            was_expanded = False

        else:
            was_expanded = self.keys_tree_view.row_expanded(self.keys_store.get_path(iter))

            while (self.keys_store.iter_children(iter)):
                self.keys_store.remove(self.keys_store.iter_children(iter))

            for key in key_list:
                self.keys_store.append(iter, key.list_view_representation())

        if (was_expanded):
            self.keys_tree_view.expand_row(self.keys_store.get_path(iter), False)
        
        self.keys_tree_view.columns_autosize()

    def refresh_values_tree_view(self, value_list):
        if (not self.connected()):
            return
        
        type_pixmaps = {
                        winreg.REG_SZ:self.icon_registry_string_pixbuf,
                        winreg.REG_EXPAND_SZ:self.icon_registry_string_pixbuf,
                        winreg.REG_BINARY:self.icon_registry_binary_pixbuf,
                        winreg.REG_DWORD:self.icon_registry_number_pixbuf,
                        winreg.REG_DWORD_BIG_ENDIAN:self.icon_registry_number_pixbuf,
                        winreg.REG_MULTI_SZ:self.icon_registry_string_pixbuf,
                        winreg.REG_QWORD:self.icon_registry_number_pixbuf
                        }

        self.values_store.clear()
        
        for value in value_list:
            self.values_store.append([type_pixmaps[value.type]] + value.list_view_representation())

    def get_selected_registry_key(self):
        if (self.pipe_manager == None): # not connected
            return (None, None)

        (model, iter) = self.keys_tree_view.get_selection().get_selected()
        if (iter == None): # no selection
            return (None, None)
        else:
            return (iter, model.get_value(iter, 1))
    
    def get_selected_registry_value(self):
        if (self.pipe_manager == None): # not connected
            return (None, None)
        
        (model, iter) = self.values_tree_view.get_selection().get_selected()
        if (iter == None): # no selection
            return (None, None)
        else:
            return (iter, model.get_value(iter, 4))

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
        
    def run_message_dialog(self, type, buttons, message, parent = None):
        if (parent == None):
            parent = self
        
        message_box = gtk.MessageDialog(parent, gtk.DIALOG_MODAL, type, buttons, message)
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

    def run_connect_dialog(self, pipe_manager, server_address, transport_type, username):
        dialog = WinRegConnectDialog(server_address, transport_type, username)
        dialog.show_all()
        
        # loop to handle the failures
        while True:
            response_id = dialog.run()
            
            if (response_id != gtk.RESPONSE_OK):
                dialog.hide()
                return None
            else:
                try:
                    self.server_address = dialog.get_server_address()
                    self.transport_type = dialog.get_transport_type()
                    self.username = dialog.get_username()
                    password = dialog.get_password()
                    
                    pipe_manager = WinRegPipeManager(self.server_address, self.transport_type, self.username, password)
                    
                    break
                
                except RuntimeError, re:
                    msg = "Failed to connect: " + re.args[1] + "."
                    print msg
                    traceback.print_exc()                        
                    self.run_message_dialog(gtk.MESSAGE_ERROR, gtk.BUTTONS_OK, msg, dialog)
                    
                except Exception, ex:
                    msg = "Failed to connect: " + str(ex) + "."
                    print msg
                    traceback.print_exc()
                    self.run_message_dialog(gtk.MESSAGE_ERROR, gtk.BUTTONS_OK, msg, dialog)

        dialog.hide()
        return pipe_manager
    
    def connected(self):
        return self.pipe_manager != None
    
#    def update_service_callback(self, service):
#        try:
#            self.pipe_manager.lock.acquire()
#            self.pipe_manager.update_service(service)
#            self.pipe_manager.fetch_service_status(service)
#            
#            self.set_status("Service '" + service.display_name + "' updated.")
#            
#        except RuntimeError, re:
#            msg = "Failed to update service: " + re.args[1] + "."
#            print msg
#            self.set_status(msg)
#            traceback.print_exc()
#            self.run_message_dialog(gtk.MESSAGE_ERROR, gtk.BUTTONS_OK, msg)
#            
#        except Exception, ex:
#            msg = "Failed to update service: " + str(ex) + "."
#            print msg
#            self.set_status(msg)
#            traceback.print_exc()
#            self.run_message_dialog(gtk.MESSAGE_ERROR, gtk.BUTTONS_OK, msg)
#            
#        finally:
#            self.pipe_manager.lock.release()
#        
#        self.refresh_services_tree_view()

    def on_self_delete(self, widget, event):
        if (self.pipe_manager != None):
            self.on_disconnect_item_activate(self.disconnect_item)
        
        gtk.main_quit()
        return False

    def on_connect_item_activate(self, widget):
        self.pipe_manager = self.run_connect_dialog(None, self.server_address, self.transport_type, self.username)

        self.refresh_keys_tree_view(None, None)
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
        pass

    def on_about_item_activate(self, widget):
        dialog = AboutDialog(
                             "PyGWRegEdit", 
                             "A tool to remotely edit a Windows Registry.\n Based on Jelmer Vernooij's original Samba-GTK",
                             self.icon_pixbuf
                             )
        dialog.run()
        dialog.hide()

    def on_keys_tree_view_selection_changed(self, widget):
        (iter, selected_key) = self.get_selected_registry_key()
        
        if (selected_key != None):
            try :
                (key_list, value_list) = self.pipe_manager.ls_key(selected_key)
                self.refresh_keys_tree_view(iter, key_list)
                self.refresh_values_tree_view(value_list)
                self.keys_tree_view.columns_autosize()                
                self.set_status("Selected key '" + selected_key.get_absolute_path() + "'.")

            except RuntimeError, re:
                msg = "Failed to fetch key '" + selected_key.get_absolute_path() + "': " + re.args[1] + "."
                print msg
                self.set_status(msg)
                traceback.print_exc()
                self.run_message_dialog(gtk.MESSAGE_ERROR, gtk.BUTTONS_OK, msg)
                
            except Exception, ex:
                msg = "Failed to fetch key '" + selected_key.get_absolute_path() + "': " + str(ex) + "."
                print msg
                self.set_status(msg)
                traceback.print_exc()
                self.run_message_dialog(gtk.MESSAGE_ERROR, gtk.BUTTONS_OK, msg)    
            
        self.update_sensitivity()

    def on_keys_tree_view_row_collapsed_expanded(self, widget, iter, path):
        self.keys_tree_view.columns_autosize()

    def on_keys_tree_view_button_press(self, widget, event):
        if (event.type == gtk.gdk._2BUTTON_PRESS):
            (iter, selected_key) = self.get_selected_registry_key()
            if (selected_key == None):
                return
        
            expanded = self.keys_tree_view.row_expanded(self.keys_store.get_path(iter))
            
            if (expanded):
                self.keys_tree_view.collapse_row(self.keys_store.get_path(iter))
            else:
                self.keys_tree_view.expand_row(self.keys_store.get_path(iter), False)

    def on_values_tree_view_selection_changed(self, widget):
        (iter, selected_key) = self.get_selected_registry_key()
        (iter, selected_value) = self.get_selected_registry_value()
        
        if (selected_key != None and selected_value != None):
            self.set_status("Selected path '" + selected_key.get_absolute_path() + "\\" + selected_value.name + "'.")
            
        self.update_sensitivity()

    def on_values_tree_view_button_press(self, widget, event):
        pass
        #if (event.type == gtk.gdk._2BUTTON_PRESS):
            #self.on_edit_item_activate(self.edit_item)

win = RegEditWindow()
win.show_all()
gtk.main()
