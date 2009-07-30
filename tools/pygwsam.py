#!/usr/bin/python

import sys
import os.path
import traceback
import gtk, gobject
import sambagtk

from samba.dcerpc import mgmt, epmapper
from objects import User
from objects import Group
from dialogs import UserEditDialog
from dialogs import GroupEditDialog


class SAMPipeManager:
    
    def __init__(self):
        self.pipe = sambagtk.gtk_connect_rpc_interface("samr")
        self.user_list = []
        self.group_list = []
        
    def close(self):
        if (self.pipe != None):
            self.pipe.close()
        
    def get_from_pipe(self):
        group1 = Group("group1", "Group Description 1", 0xAAAA)
        group2 = Group("group2", "Group Description 2", 0xBBBB)
        
        del self.group_list[:]
        self.group_list.append(group1)
        self.group_list.append(group2)
        
        user1 = User("username1", "Full Name 1", "User Description 1", 0xDEAD)
        user1.password = "password1"
        user1.must_change_password = True
        user1.cannot_change_password = False
        user1.password_never_expires = False
        user1.account_disabled = False
        user1.account_locked_out = False
        user1.group_list = [self.group_list[0]]
        user1.profile_path = "/profiles/user1"
        user1.logon_script = "script1"
        user1.homedir_path = "/home/user1"
        user1.map_homedir_drive = None
                
        user2 = User("username2", "Full Name 2", "User Description 2", 0xBEEF)
        user2.password = "password2"
        user2.must_change_password = False
        user2.cannot_change_password = True
        user2.password_never_expires = True
        user2.account_disabled = True
        user2.account_locked_out = True
        user2.group_list = [self.group_list[1]]
        user2.profile_path = "/profiles/user2"
        user2.logon_script = "script2"
        user2.homedir_path = "/home/user2"
        user2.map_homedir_drive = 4
        
        del self.user_list[:]
        self.user_list.append(user1)
        self.user_list.append(user2)
        
    def user_to_pipe(self, user):
        pass

    def group_to_pipe(self, group):
        pass

    
class SAMWindow(gtk.Window):

    def __init__(self):
        super(SAMWindow, self).__init__()

        self.create()
        self.pipe_manager = None
        self.users_groups_notebook_page_num = 0
        self.update_captions()
        self.update_sensitivity()
        
    def create(self):
        
        # main window        

        accel_group = gtk.AccelGroup()
        
        self.set_title("User/Group Management")
        self.set_default_size(800, 600)
        self.connect("delete_event", self.on_self_delete)
        self.set_icon_from_file(os.path.join(sys.path[0], "images", "group.png"))
        
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
        self.disconnect_item.set_sensitive(False)
        file_menu.add(self.disconnect_item)
        
        self.sel_domain_item = gtk.MenuItem("_Select Domain", accel_group)
        self.sel_domain_item.set_sensitive(False)
        file_menu.add(self.sel_domain_item)
        
        menu_separator_item = gtk.SeparatorMenuItem()
        menu_separator_item.set_sensitive(False)
        file_menu.add(menu_separator_item)
        
        self.quit_item = gtk.ImageMenuItem(gtk.STOCK_QUIT, accel_group)
        file_menu.add(self.quit_item)
        
        
        self.view_item = gtk.MenuItem("_View")
        menubar.add(self.view_item)
        
        view_menu = gtk.Menu()
        self.view_item.set_submenu(view_menu)
        
        self.refresh_item = gtk.ImageMenuItem(gtk.STOCK_REFRESH, accel_group)
        self.refresh_item.set_sensitive(False)
        view_menu.add(self.refresh_item)
        
        
        self.user_group_item = gtk.MenuItem("_User")
        menubar.add(self.user_group_item)
        
        user_group_menu = gtk.Menu()
        self.user_group_item.set_submenu(user_group_menu)

        self.new_item = gtk.ImageMenuItem(gtk.STOCK_NEW, accel_group)
        self.new_item.set_sensitive(False)
        user_group_menu.add(self.new_item)

        self.delete_item = gtk.ImageMenuItem(gtk.STOCK_DELETE, accel_group)
        self.delete_item.set_sensitive(False)
        user_group_menu.add(self.delete_item)

        self.edit_item = gtk.ImageMenuItem(gtk.STOCK_EDIT, accel_group)
        self.edit_item.set_sensitive(False)
        user_group_menu.add(self.edit_item)

        
        self.policies_item = gtk.MenuItem("_Policies")
        menubar.add(self.policies_item)

        policies_menu = gtk.Menu()
        self.policies_item.set_submenu(policies_menu)
        
        self.user_rights_item = gtk.MenuItem("_User Rights...", accel_group)
        self.user_rights_item.set_sensitive(False)
        policies_menu.add(self.user_rights_item)

        self.audit_item = gtk.MenuItem("A_udit...", accel_group)
        self.audit_item.set_sensitive(False)
        policies_menu.add(self.audit_item)

        menu_separator_item = gtk.SeparatorMenuItem()
        menu_separator_item.set_sensitive(False)
        policies_menu.add(menu_separator_item)
        
        self.trust_relations_item = gtk.MenuItem("_Trust relations", accel_group)
        self.trust_relations_item.set_sensitive(False)
        policies_menu.add(self.trust_relations_item)
        
        
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
        
        self.new_button = gtk.ToolButton(gtk.STOCK_NEW)
        self.new_button.set_is_important(True)
        toolbar.insert(self.new_button, 3)
                
        self.edit_button = gtk.ToolButton(gtk.STOCK_EDIT)
        self.edit_button.set_is_important(True)
        toolbar.insert(self.edit_button, 4)
                
        self.delete_button = gtk.ToolButton(gtk.STOCK_DELETE)
        self.delete_button.set_is_important(True)
        toolbar.insert(self.delete_button, 5)
                
        
        # user list
        
        self.users_groups_notebook = gtk.Notebook()
        vbox.pack_start(self.users_groups_notebook, True, True, 0)
        
        scrolledwindow = gtk.ScrolledWindow(None, None)
        scrolledwindow.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        scrolledwindow.set_shadow_type(gtk.SHADOW_IN)
        self.users_groups_notebook.append_page(scrolledwindow, gtk.Label("Users"))
        
        self.users_tree_view = gtk.TreeView()
        scrolledwindow.add(self.users_tree_view)
        
        column = gtk.TreeViewColumn()
        column.set_title("Name")
        renderer = gtk.CellRendererText()
        column.pack_start(renderer, True)
        self.users_tree_view.append_column(column)
        column.add_attribute(renderer, "text", 0)
                
        column = gtk.TreeViewColumn()
        column.set_title("Full Name")
        renderer = gtk.CellRendererText()
        column.pack_start(renderer, True)
        self.users_tree_view.append_column(column)
        column.add_attribute(renderer, "text", 1)
        
        column = gtk.TreeViewColumn()
        column.set_title("Description")
        column.set_expand(True)
        renderer = gtk.CellRendererText()
        column.pack_start(renderer, True)
        self.users_tree_view.append_column(column)
        column.add_attribute(renderer, "text", 2)
        
        column = gtk.TreeViewColumn()
        column.set_title("RID")
        renderer = gtk.CellRendererText()
        column.pack_start(renderer, True)
        self.users_tree_view.append_column(column)
        column.set_cell_data_func(renderer, self.cell_data_func_hex, 3)
        
        self.users_store = gtk.ListStore(gobject.TYPE_STRING, gobject.TYPE_STRING, gobject.TYPE_STRING, gobject.TYPE_INT)
        self.users_store.set_sort_column_id(0, gtk.SORT_ASCENDING)
        self.users_tree_view.set_model(self.users_store)


        # group list

        scrolledwindow = gtk.ScrolledWindow(None, None)
        scrolledwindow.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        scrolledwindow.set_shadow_type(gtk.SHADOW_IN)
        self.users_groups_notebook.append_page(scrolledwindow, gtk.Label("Groups"))
        
        self.groups_tree_view = gtk.TreeView()
        scrolledwindow.add(self.groups_tree_view)
        
        column = gtk.TreeViewColumn()
        column.set_title("Name")
        renderer = gtk.CellRendererText()
        column.pack_start(renderer, True)
        self.groups_tree_view.append_column(column)
        column.add_attribute(renderer, "text", 0)
                
        column = gtk.TreeViewColumn()
        column.set_title("Description")
        column.set_expand(True)
        renderer = gtk.CellRendererText()
        column.pack_start(renderer, True)
        self.groups_tree_view.append_column(column)
        column.add_attribute(renderer, "text", 1)
        
        column = gtk.TreeViewColumn()
        column.set_title("RID")
        renderer = gtk.CellRendererText()
        column.pack_start(renderer, True)
        self.groups_tree_view.append_column(column)
        column.set_cell_data_func(renderer, self.cell_data_func_hex, 2)

        self.groups_store = gtk.ListStore(gobject.TYPE_STRING, gobject.TYPE_STRING, gobject.TYPE_INT)
        self.groups_store.set_sort_column_id(0, gtk.SORT_ASCENDING)
        self.groups_tree_view.set_model(self.groups_store)


        # status bar

        self.statusbar = gtk.Statusbar()
        self.statusbar.set_has_resize_grip(True)
        vbox.pack_start(self.statusbar, False, False, 0)
        
        
        # signals/events
        
        self.connect_item.connect("activate", self.on_connect_item_activate)
        self.disconnect_item.connect("activate", self.on_disconnect_item_activate)
        self.sel_domain_item.connect("activate", self.on_sel_domain_item_activate)
        self.quit_item.connect("activate", self.on_quit_item_activate)
        self.refresh_item.connect("activate", self.on_refresh_item_activate)
        self.new_item.connect("activate", self.on_new_item_activate)
        self.delete_item.connect("activate", self.on_delete_item_activate)
        self.edit_item.connect("activate", self.on_edit_item_activate)
        self.user_rights_item.connect("activate", self.on_user_rights_item_activate)
        self.audit_item.connect("activate", self.on_audit_item_activate)
        self.trust_relations_item.connect("activate", self.on_trust_relations_item_activate)        
        self.about_item.connect("activate", self.on_about_item_activate)
        
        self.connect_button.connect("clicked", self.on_connect_item_activate)
        self.disconnect_button.connect("clicked", self.on_disconnect_item_activate)
        self.new_button.connect("clicked", self.on_new_item_activate)
        self.delete_button.connect("clicked", self.on_delete_item_activate)
        self.edit_button.connect("clicked", self.on_edit_item_activate)
        
        self.users_tree_view.get_selection().connect("changed", self.on_users_tree_view_selection_changed)
        self.users_tree_view.connect("button_press_event", self.on_users_tree_view_button_press)
        self.groups_tree_view.get_selection().connect("changed", self.on_groups_tree_view_selection_changed)
        self.groups_tree_view.connect("button_press_event", self.on_groups_tree_view_button_press)
        self.users_groups_notebook.connect("switch-page", self.on_users_groups_notebook_switch_page)
        
        self.add_accel_group(accel_group)

    def refresh_user_list_view(self):
        (model, paths) = self.users_tree_view.get_selection().get_selected_rows()
        
        self.users_store.clear()
        for user in self.pipe_manager.user_list:
            self.users_store.append(user.list_view_representation())

        if (len(paths) > 0):
            self.users_tree_view.get_selection().select_path(paths[0])

    def refresh_group_list_view(self):
        (model, paths) = self.groups_tree_view.get_selection().get_selected_rows()

        self.groups_store.clear()
        for group in self.pipe_manager.group_list:
            self.groups_store.append(group.list_view_representation())
            
        if (len(paths) > 0):
            self.groups_tree_view.get_selection().select_path(paths[0])

    def get_selected_user(self):
        if (self.pipe_manager == None): # not connected
            return None
        
        (model, iter) = self.users_tree_view.get_selection().get_selected()
        if (iter == None): # no selection
            return None
        else:            
            username = model.get_value(iter, 0)
            return [user for user in self.pipe_manager.user_list if user.username == username][0]

    def get_selected_group(self):
        if (self.pipe_manager == None): # not connected
            return None
        
        (model, iter) = self.groups_tree_view.get_selection().get_selected()
        if (iter == None): # no selection
            return None
        else:            
            name = model.get_value(iter, 0)
            return [group for group in self.pipe_manager.group_list if group.name == name][0]

    def set_status(self, message):
        self.statusbar.pop(0)
        self.statusbar.push(0, message)
        
    def update_sensitivity(self):
        connected = (self.pipe_manager != None)
        user_selected = (self.get_selected_user() != None)
        group_selected = (self.get_selected_group() != None)
        selected = [user_selected, group_selected][self.users_groups_notebook_page_num]
        
        self.connect_item.set_sensitive(not connected)
        self.disconnect_item.set_sensitive(connected)
        self.sel_domain_item.set_sensitive(connected)
        self.refresh_item.set_sensitive(connected)
        self.new_item.set_sensitive(connected)
        self.delete_item.set_sensitive(connected and selected)
        self.edit_item.set_sensitive(connected and selected)
        self.user_rights_item.set_sensitive(connected)
        self.audit_item.set_sensitive(connected)
        self.trust_relations_item.set_sensitive(connected)

        self.connect_button.set_sensitive(not connected)
        self.disconnect_button.set_sensitive(connected)
        self.new_button.set_sensitive(connected)
        self.delete_button.set_sensitive(connected and selected)
        self.edit_button.set_sensitive(connected and selected)

    def update_captions(self):
        self.user_group_item.get_child().set_text(["Users", "Groups"][self.users_groups_notebook_page_num > 0])
        self.new_button.set_tooltip_text(["Create a new user", "Create a new group"][self.users_groups_notebook_page_num > 0])
        self.edit_button.set_tooltip_text(["Edit user's properties", "Edit group's properties"][self.users_groups_notebook_page_num > 0])
        self.delete_button.set_tooltip_text(["Delete the user", "Delete the group"][self.users_groups_notebook_page_num > 0])

    def run_message_dialog(self, type, buttons, message):
        message_box = gtk.MessageDialog(self, gtk.DIALOG_MODAL, type, buttons, message)
        response = message_box.run()
        message_box.hide()
        
        return response

    def run_user_edit_dialog(self, user = None, apply_callback = None):
        dialog = UserEditDialog(self.pipe_manager, user)
        dialog.show_all()
        
        # loop to handle the applies
        while True:
            response_id = dialog.run()
            
            if (response_id in [gtk.RESPONSE_OK, gtk.RESPONSE_APPLY]):
                problem_msg = dialog.check_for_problems()
                
                if (problem_msg != None):
                    self.run_message_dialog(gtk.MESSAGE_ERROR, gtk.BUTTONS_OK, problem_msg)
                else:
                    dialog.values_to_user()
                    if (apply_callback != None):
                        apply_callback()
                    if (response_id == gtk.RESPONSE_OK):
                        dialog.hide()
                        break
                        
            else:
                dialog.hide()
                return None
        
        return dialog.user

    def run_group_edit_dialog(self, group = None, apply_callback = None):
        dialog = GroupEditDialog(self.pipe_manager, group)
        dialog.show_all()
        
        # loop to handle the applies
        while True:
            response_id = dialog.run()
            
            if (response_id in [gtk.RESPONSE_OK, gtk.RESPONSE_APPLY]):
                problem_msg = dialog.check_for_problems()
                
                if (problem_msg != None):
                    self.run_message_dialog(gtk.MESSAGE_ERROR, gtk.BUTTONS_OK, problem_msg)
                else:
                    dialog.values_to_group()
                    if (apply_callback != None):
                        apply_callback()                        
                    if (response_id == gtk.RESPONSE_OK):
                        dialog.hide()
                        break
            
            else:
                dialog.hide()
                return None
        
        return dialog.thegroup

    def cell_data_func_hex(self, column, cell, model, iter, column_no):
        cell.set_property("text", "0x%X" % model.get_value(iter, column_no))

    def on_self_delete(self, widget, event):
        if (self.pipe_manager != None):
            self.on_disconnect_item_activate(self.disconnect_item)
        
        gtk.main_quit()
        return False

    def on_connect_item_activate(self, widget):
        try:
            self.pipe_manager = SAMPipeManager()
            self.pipe_manager.get_from_pipe()
            
        except Exception:
            print "failed to connect"
            traceback.print_exc()
            self.pipe_manager = None
            return
        
        self.refresh_user_list_view()
        self.refresh_group_list_view()
        self.update_sensitivity()

    def on_disconnect_item_activate(self, widget):
        if (self.pipe_manager != None):
            self.pipe_manager.close()
            self.pipe_manager = None
            
        self.users_store.clear()
        self.groups_store.clear()       
        self.update_sensitivity()
    
    def on_sel_domain_item_activate(self, widget):
        pass

    def on_quit_item_activate(self, widget):
        self.on_self_delete(None, None)
    
    def on_refresh_item_activate(self, widget):
        self.pipe_manager.get_from_pipe()
        self.refresh_user_list_view()
        self.refresh_group_list_view()
        
    def on_new_item_activate(self, widget):
        if (self.users_groups_notebook_page_num == 0): # users tab
            new_user = self.run_user_edit_dialog()
            if (new_user == None):
                return
            
            self.pipe_manager.user_list.append(new_user)
            self.refresh_user_list_view()

        else: # groups tab
            new_group = self.run_group_edit_dialog()
            if (new_group == None):
                return
            
            self.pipe_manager.group_list.append(new_group)
            self.refresh_group_list_view()

    def on_delete_item_activate(self, widget):
        if (self.users_groups_notebook_page_num == 0): # users tab
            del_user = self.get_selected_user()
    
            if (self.run_message_dialog(gtk.MESSAGE_QUESTION, gtk.BUTTONS_YES_NO, "Do you want to delete user '%s'?" % del_user.username) != gtk.RESPONSE_YES):
                return 
            
            self.pipe_manager.user_list.remove(del_user)
            self.refresh_user_list_view()

        else: # groups tab
            del_group = self.get_selected_group()
    
            if (self.run_message_dialog(gtk.MESSAGE_QUESTION, gtk.BUTTONS_YES_NO, "Do you want to delete group '%s'?" % del_group.name) != gtk.RESPONSE_YES):
                return 
            
            self.pipe_manager.group_list.remove(del_group)
            self.refresh_group_list_view()
        
    def on_edit_item_activate(self, widget):
        if (self.users_groups_notebook_page_num == 0): # users tab
            edit_user = self.get_selected_user()
            self.run_user_edit_dialog(edit_user, self.refresh_user_list_view)
            
        else: # groups tab
            edit_group = self.get_selected_group()
            self.run_group_edit_dialog(edit_group, self.refresh_group_list_view)

    def on_user_rights_item_activate(self, widget):
        pass
    
    def on_audit_item_activate(self, widget):
        pass
    
    def on_trust_relations_item_activate(self, widget):
        pass
    
    def on_about_item_activate(self, widget):
        aboutwin = sambagtk.AboutDialog("PyGWSAM")
        aboutwin.run()
        aboutwin.destroy()

    def on_users_tree_view_selection_changed(self, widget):
        self.update_sensitivity()

    def on_users_tree_view_button_press(self, widget, event):
        if (event.type == gtk.gdk._2BUTTON_PRESS):
            self.on_edit_item_activate(self.edit_item)

    def on_groups_tree_view_selection_changed(self, widget):
        self.update_sensitivity()

    def on_groups_tree_view_button_press(self, widget, event):
        if (event.type == gtk.gdk._2BUTTON_PRESS):
            self.on_edit_item_activate(self.edit_item)

    def on_users_groups_notebook_switch_page(self, widget, page, page_num):
        self.users_groups_notebook_page_num = page_num # workaround - the signal is emitted before the actual change
        self.update_captions()
        self.update_sensitivity()


main_window = SAMWindow()
main_window.show_all()
gtk.main()
