
import sys
import os.path
import string

import gobject
import glib
import gtk
import pango

import samba
from samba.dcerpc import svcctl
from samba.dcerpc import winreg

from objects import User
from objects import Group
from objects import Service
from objects import Task
from objects import RegistryKey
from objects import RegistryValue


class AboutDialog(gtk.AboutDialog):
    
    def __init__(self, name, description, icon):
        super(AboutDialog, self).__init__()
        
        self.set_name(name)
        self.set_version(samba.version)
        self.set_logo(icon)
        self.set_copyright("Copyright \xc2\xa9 2009 Calin Crisan <ccrisan@gmail.com>")
        self.set_authors(["Calin Crisan <ccrisan@gmail.com>", "Jelmer Vernooij <jelmer@samba.org>"])
        self.set_comments(description)
        self.set_wrap_license(True)
        self.set_license(
            "This program is free software; you can redistribute it and/or modify " +
            "it under the terms of the GNU General Public License as published by " +
            "the Free Software Foundation; either version 3 of the License, or " +
            "(at your option) any later version. \n\n" +
            "This program is distributed in the hope that it will be useful, " +
            "but WITHOUT ANY WARRANTY; without even the implied warranty of " +
            "MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the " +
            "GNU General Public License for more details. \n\n" +
            "You should have received a copy of the GNU General Public License " +
            "along with this program. If not, see <http://www.gnu.org/licenses/>."
        );



class UserEditDialog(gtk.Dialog):
    
    def __init__(self, pipe_manager, user = None):
        super(UserEditDialog, self).__init__()

        if (user == None):
            self.brand_new = True
            self.user = User("", "", "", 0)
        else:
            self.brand_new = False
            self.user = user
        
        self.pipe_manager = pipe_manager
        self.create()
        
        self.user_to_values()
        self.update_sensitivity()
        
    def create(self):
        self.set_title(["Edit user", "New user"][self.brand_new] + " " + self.user.username)
        self.set_border_width(5)
        self.set_icon_from_file(os.path.join(sys.path[0], "images", "user.png"))
        
        notebook = gtk.Notebook()
        self.vbox.pack_start(notebook, True, True, 0)
        
        table = gtk.Table (10, 2, False)
        table.set_border_width(5)
        table.set_col_spacings(5)
        table.set_row_spacings(5)
        notebook.add(table)
        
        label = gtk.Label("Username")
        label.set_alignment(0, 0.5)
        table.attach(label, 0, 1, 0, 1, gtk.FILL, 0, 0, 0)
        
        label = gtk.Label("Full name")
        label.set_alignment(0, 0.5)
        table.attach(label, 0, 1, 1, 2, gtk.FILL, 0, 0, 0)
        
        label = gtk.Label("Description")
        label.set_alignment(0, 0.5)
        table.attach(label, 0, 1, 2, 3, gtk.FILL, 0, 0, 0)

        label = gtk.Label("Password")
        label.set_alignment(0, 0.5)
        table.attach(label, 0, 1, 3, 4, gtk.FILL, 0, 0, 0)

        label = gtk.Label("Confirm password")
        label.set_alignment(0, 0.5)
        table.attach(label, 0, 1, 4, 5, gtk.FILL, 0, 0, 0)

        self.username_entry = gtk.Entry()
        self.username_entry.set_activates_default(True)
        table.attach(self.username_entry, 1, 2, 0, 1, gtk.FILL, 0, 0, 0)

        self.fullname_entry = gtk.Entry()
        self.fullname_entry.set_activates_default(True)
        table.attach(self.fullname_entry, 1, 2, 1, 2, gtk.FILL | gtk.EXPAND, 0, 0, 0)

        self.description_entry = gtk.Entry()
        self.description_entry.set_activates_default(True)
        table.attach(self.description_entry, 1, 2, 2, 3, gtk.FILL | gtk.EXPAND, 0, 0, 0)

        self.password_entry = gtk.Entry()
        self.password_entry.set_visibility(False)
        self.password_entry.set_activates_default(True)
        table.attach(self.password_entry, 1, 2, 3, 4, gtk.FILL | gtk.EXPAND, 0, 0, 0)
        
        self.confirm_password_entry = gtk.Entry()
        self.confirm_password_entry.set_visibility(False)
        self.confirm_password_entry.set_activates_default(True)
        table.attach(self.confirm_password_entry, 1, 2, 4, 5, gtk.FILL | gtk.EXPAND, 0, 0, 0)
        
        self.must_change_password_check = gtk.CheckButton("_User Must Change Password at Next Logon")
        self.must_change_password_check.set_active(self.brand_new)
        table.attach(self.must_change_password_check, 1, 2, 5, 6, gtk.FILL, 0, 0, 0)

        self.cannot_change_password_check = gtk.CheckButton("User Cannot Change Password")
        table.attach(self.cannot_change_password_check, 1, 2, 6, 7, gtk.FILL, 0, 0, 0)

        self.password_never_expires_check = gtk.CheckButton("Password Never Expires")
        table.attach(self.password_never_expires_check, 1, 2, 7, 8, gtk.FILL, 0, 0, 0)
        
        self.account_disabled_check = gtk.CheckButton("Account Disabled")
        self.account_disabled_check.set_active(self.brand_new)
        table.attach(self.account_disabled_check, 1, 2, 8, 9, gtk.FILL, 0, 0, 0)

        self.account_locked_out_check = gtk.CheckButton("Account Locked Out")
        table.attach(self.account_locked_out_check, 1, 2, 9, 10, gtk.FILL, 0, 0, 0)

        notebook.set_tab_label(notebook.get_nth_page(0), gtk.Label("Main"))
        
        hbox = gtk.HBox(False, 5)
        notebook.add(hbox)
        
        scrolledwindow = gtk.ScrolledWindow(None, None)
        scrolledwindow.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        scrolledwindow.set_shadow_type(gtk.SHADOW_IN)
        hbox.pack_start(scrolledwindow, True, True, 0)
        
        self.existing_groups_tree_view = gtk.TreeView()
        scrolledwindow.add(self.existing_groups_tree_view)
        
        column = gtk.TreeViewColumn()
        column.set_title("Existing groups")
        renderer = gtk.CellRendererText()
        column.pack_start(renderer, True)
        self.existing_groups_tree_view.append_column(column)
        column.add_attribute(renderer, "text", 0)
                
        self.existing_groups_store = gtk.ListStore(gobject.TYPE_STRING)
        self.existing_groups_store.set_sort_column_id(0, gtk.SORT_ASCENDING)
        self.existing_groups_tree_view.set_model(self.existing_groups_store)
        
        vbox = gtk.VBox(True, 0)
        hbox.pack_start(vbox, True, True, 0)
        
        self.add_group_button = gtk.Button("Add", gtk.STOCK_ADD)
        vbox.pack_start(self.add_group_button, False, False, 0)
        
        self.del_group_button = gtk.Button("Remove", gtk.STOCK_REMOVE)
        vbox.pack_start(self.del_group_button, False, False, 0)
        
        scrolledwindow = gtk.ScrolledWindow(None, None)
        scrolledwindow.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        scrolledwindow.set_shadow_type(gtk.SHADOW_IN)
        hbox.pack_start(scrolledwindow, True, True, 0)
        
        self.available_groups_tree_view = gtk.TreeView()
        scrolledwindow.add(self.available_groups_tree_view)

        column = gtk.TreeViewColumn()
        column.set_title("Available groups")
        renderer = gtk.CellRendererText()
        column.pack_start(renderer, True)
        self.available_groups_tree_view.append_column(column)
        column.add_attribute(renderer, "text", 0)
                
        self.available_groups_store = gtk.ListStore(gobject.TYPE_STRING)
        self.available_groups_store.set_sort_column_id(0, gtk.SORT_ASCENDING)
        self.available_groups_tree_view.set_model(self.available_groups_store)
        
        notebook.set_tab_label(notebook.get_nth_page(1), gtk.Label("Groups"))
        
        vbox = gtk.VBox(False, 0)
        notebook.add(vbox)
        
        frame = gtk.Frame("User Profiles")
        frame.set_border_width(5)
        vbox.pack_start(frame, True, True, 0)
        
        table = gtk.Table(2, 2, False)
        table.set_border_width(5)
        table.set_col_spacings(5)
        table.set_row_spacings(5)
        frame.add(table)
        
        label = gtk.Label("User Profile Path")
        label.set_alignment(0, 0.5)
        table.attach(label, 0, 1, 0, 1, gtk.FILL, 0, 0, 0)

        label = gtk.Label("Logon Script Name")
        label.set_alignment(0, 0.5)
        table.attach(label, 0, 1, 1, 2, gtk.FILL, 0, 0, 0)

        self.profile_path_entry = gtk.Entry()
        self.profile_path_entry.set_activates_default(True)
        table.attach(self.profile_path_entry, 1, 2, 0, 1, gtk.FILL | gtk.EXPAND, 0, 0, 0)

        self.logon_script_entry = gtk.Entry()
        self.logon_script_entry.set_activates_default(True)
        table.attach(self.logon_script_entry, 1, 2, 1, 2, gtk.FILL | gtk.EXPAND, 0, 0, 0)
        
        frame = gtk.Frame("Home Directory")
        frame.set_border_width(5)
        vbox.pack_start(frame, True, True, 0)

        table = gtk.Table(2, 2, False)
        table.set_border_width(5)
        table.set_col_spacings(5)
        table.set_row_spacings(5)
        frame.add(table)

        label = gtk.Label("Path")
        label.set_alignment(0, 0.5)
        table.attach(label, 0, 1, 0, 1, gtk.FILL, 0, 0, 0)
        
        self.homedir_path_entry = gtk.Entry()
        self.homedir_path_entry.set_activates_default(True)
        table.attach(self.homedir_path_entry, 1, 2, 0, 1, gtk.FILL | gtk.EXPAND, 0, 0, 0)
        
        self.map_homedir_drive_check = gtk.CheckButton("Map homedir to drive")
        table.attach(self.map_homedir_drive_check, 0, 1, 1, 2, gtk.FILL, 0, 0, 0)
        
        self.map_homedir_drive_combo = gtk.combo_box_new_text()
        table.attach(self.map_homedir_drive_combo, 1, 2, 1, 2, gtk.FILL, gtk.FILL, 0, 0)
        
        for i in range(ord('Z') - ord('A') + 1):
            self.map_homedir_drive_combo.append_text(chr(i + ord('A')) + ':')

        notebook.set_tab_label(notebook.get_nth_page(2), gtk.Label("Profile"))
        
        self.action_area.set_layout(gtk.BUTTONBOX_END)
        
        self.cancel_button = gtk.Button("Cancel", gtk.STOCK_CANCEL)
        self.cancel_button.set_flags(gtk.CAN_DEFAULT)
        self.add_action_widget(self.cancel_button, gtk.RESPONSE_CANCEL)
        
        self.apply_button = gtk.Button("Apply", gtk.STOCK_APPLY)
        self.apply_button.set_flags(gtk.CAN_DEFAULT)
        self.apply_button.set_sensitive(not self.brand_new) # disabled for new user
        self.add_action_widget(self.apply_button, gtk.RESPONSE_APPLY)
        
        self.ok_button = gtk.Button("OK", gtk.STOCK_OK)
        self.ok_button.set_flags(gtk.CAN_DEFAULT)
        self.add_action_widget(self.ok_button, gtk.RESPONSE_OK)
        
        self.set_default_response(gtk.RESPONSE_OK)
        
        
        # signals/events
        
        self.must_change_password_check.connect("toggled", self.on_update_sensitivity)
        self.cannot_change_password_check.connect("toggled", self.on_update_sensitivity)
        self.password_never_expires_check.connect("toggled", self.on_update_sensitivity)
        self.account_disabled_check.connect("toggled", self.on_update_sensitivity)
        self.account_locked_out_check.connect("toggled", self.on_update_sensitivity)
        
        self.add_group_button.connect("clicked", self.on_add_group_button_clicked)
        self.del_group_button.connect("clicked", self.on_del_group_button_clicked)
        self.existing_groups_tree_view.get_selection().connect("changed", self.on_update_sensitivity)
        self.available_groups_tree_view.get_selection().connect("changed", self.on_update_sensitivity)
        self.map_homedir_drive_check.connect("toggled", self.on_update_sensitivity)
        
    def check_for_problems(self):
        if (self.password_entry.get_text() != self.confirm_password_entry.get_text()):
            return "The password was not correctly confirmed. Please ensure that the password and confirmation match exactly."
        
        if (len(self.username_entry.get_text()) == 0):
            return "Username may not be empty!"
        
        if (self.brand_new):
            for user in self.pipe_manager.user_list:
                if (user.username == self.username_entry.get_text()):
                    return "Choose another username, this one already exists!"
        
        return None

    def update_sensitivity(self):
        existing_selected = (self.existing_groups_tree_view.get_selection().count_selected_rows() > 0)
        available_selected = (self.available_groups_tree_view.get_selection().count_selected_rows() > 0)

        self.must_change_password_check.set_sensitive(not self.password_never_expires_check.get_active())
        self.cannot_change_password_check.set_sensitive(not self.must_change_password_check.get_active())
        self.password_never_expires_check.set_sensitive(not self.must_change_password_check.get_active())
        
        self.add_group_button.set_sensitive(available_selected)
        self.del_group_button.set_sensitive(existing_selected)
        
        self.map_homedir_drive_combo.set_sensitive(self.map_homedir_drive_check.get_active())

    def user_to_values(self):
        if (self.user == None):
            raise Exception("user not set")
        
        self.username_entry.set_text(self.user.username)
        self.username_entry.set_sensitive(len(self.user.username) == 0)
        self.fullname_entry.set_text(self.user.fullname)
        self.description_entry.set_text(self.user.description)
        self.must_change_password_check.set_active(self.user.must_change_password)
        self.cannot_change_password_check.set_active(self.user.cannot_change_password)
        self.password_never_expires_check.set_active(self.user.password_never_expires)
        self.account_disabled_check.set_active(self.user.account_disabled)
        self.account_locked_out_check.set_active(self.user.account_locked_out)
        self.profile_path_entry.set_text(self.user.profile_path)
        self.logon_script_entry.set_text(self.user.logon_script)
        self.homedir_path_entry.set_text(self.user.homedir_path)
        
        if (self.user.map_homedir_drive != -1):
            self.map_homedir_drive_check.set_active(True)
            self.map_homedir_drive_combo.set_active(self.user.map_homedir_drive)
            self.map_homedir_drive_combo.set_sensitive(True)
        else:
            self.map_homedir_drive_check.set_active(False)
            self.map_homedir_drive_combo.set_active(-1)
            self.map_homedir_drive_combo.set_sensitive(False)
            
        self.existing_groups_store.clear()
        for group in self.user.group_list:
            self.existing_groups_store.append([group.name])
        
        self.available_groups_store.clear()
        for group in self.pipe_manager.group_list:
            if (not group in self.user.group_list):
                self.available_groups_store.append([group.name])
    
    def values_to_user(self):
        if (self.user == None):
            raise Exception("user not set")
        
        self.user.username = self.username_entry.get_text()
        self.user.fullname = self.fullname_entry.get_text()
        self.user.description = self.description_entry.get_text()
        self.user.password = (None, self.password_entry.get_text())[len(self.password_entry.get_text()) > 0]
        self.user.must_change_password = self.must_change_password_check.get_active()
        self.user.cannot_change_password = self.cannot_change_password_check.get_active()
        self.user.password_never_expires = self.password_never_expires_check.get_active()
        self.user.account_disabled = self.account_disabled_check.get_active()
        self.user.account_locked_out = self.account_locked_out_check.get_active()
        self.user.profile_path = self.profile_path_entry.get_text()
        self.user.logon_script = self.logon_script_entry.get_text()
        self.user.homedir_path = self.homedir_path_entry.get_text()
        
        if (self.map_homedir_drive_check.get_active()) and (self.map_homedir_drive_combo.get_active() != -1):
            self.user.map_homedir_drive = self.map_homedir_drive_combo.get_active()
        else:
            self.user.map_homedir_drive = -1

        del self.user.group_list[:]
        
        iter = self.existing_groups_store.get_iter_first()
        while (iter != None):
            value = self.existing_groups_store.get_value(iter, 0)
            self.user.group_list.append([group for group in self.pipe_manager.group_list if group.name == value][0])
            iter = self.existing_groups_store.iter_next(iter)
            
    def on_add_group_button_clicked(self, widget):
        (model, iter) = self.available_groups_tree_view.get_selection().get_selected()
        if (iter == None):
            return
        
        group_name = model.get_value(iter, 0)
        self.existing_groups_store.append([group_name])
        self.available_groups_store.remove(iter)
    
    def on_del_group_button_clicked(self, widget):
        (model, iter) = self.existing_groups_tree_view.get_selection().get_selected()
        if (iter == None):
            return
        
        group_name = model.get_value(iter, 0)
        self.available_groups_store.append([group_name])
        self.existing_groups_store.remove(iter)

    def on_update_sensitivity(self, widget):
        self.update_sensitivity()


class GroupEditDialog(gtk.Dialog):
    
    def __init__(self, pipe_manager, group = None):
        super(GroupEditDialog, self).__init__()

        if (group == None):
            self.brand_new = True
            self.thegroup = Group("", "", 0)
        else:
            self.brand_new = False
            self.thegroup = group
        
        self.pipe_manager = pipe_manager
        self.create()

        if (not self.brand_new):
            self.group_to_values()
                
    def create(self):        
        self.set_title(["Edit group", "New group"][self.brand_new] + " " + self.thegroup.name)
        self.set_border_width(5)
        self.set_icon_from_file(os.path.join(sys.path[0], "images", "group.png"))
        
        table = gtk.Table (2, 2, False)
        table.set_border_width(5)
        table.set_col_spacings(5)
        table.set_row_spacings(5)
        self.vbox.pack_start(table, True, True, 0)
        
        label = gtk.Label("Name")
        label.set_alignment(0, 0.5)
        table.attach(label, 0, 1, 0, 1, gtk.FILL, 0, 0, 0)
        
        label = gtk.Label("Description")
        label.set_alignment(0, 0.5)
        table.attach(label, 0, 1, 1, 2, gtk.FILL, 0, 0, 0)

        self.name_entry = gtk.Entry()
        self.name_entry.set_activates_default(True)
        table.attach(self.name_entry, 1, 2, 0, 1, gtk.FILL, 0, 0, 0)

        self.description_entry = gtk.Entry()
        self.description_entry.set_activates_default(True)
        table.attach(self.description_entry, 1, 2, 1, 2, gtk.FILL | gtk.EXPAND, 0, 0, 0)
        
        self.action_area.set_layout(gtk.BUTTONBOX_END)
        
        self.cancel_button = gtk.Button("Cancel", gtk.STOCK_CANCEL)
        self.cancel_button.set_flags(gtk.CAN_DEFAULT)
        self.add_action_widget(self.cancel_button, gtk.RESPONSE_CANCEL)
        
        self.apply_button = gtk.Button("Apply", gtk.STOCK_APPLY)
        self.apply_button.set_flags(gtk.CAN_DEFAULT)
        self.apply_button.set_sensitive(not self.brand_new) # disabled for new group
        self.add_action_widget(self.apply_button, gtk.RESPONSE_APPLY)
        
        self.ok_button = gtk.Button("OK", gtk.STOCK_OK)
        self.ok_button.set_flags(gtk.CAN_DEFAULT)
        self.add_action_widget(self.ok_button, gtk.RESPONSE_OK)
        
        self.set_default_response(gtk.RESPONSE_OK)
        
                
    def check_for_problems(self):
        if (len(self.name_entry.get_text()) == 0):
            return "Name may not be empty!"

        if (self.brand_new):
            for group in self.pipe_manager.group_list:
                if (group.name == self.name_entry.get_text()):
                    return "Choose another group name, this one already exists!"
        
        return None

    def group_to_values(self):
        if (self.thegroup == None):
            raise Exception("group not set")
        
        self.name_entry.set_text(self.thegroup.name)
        self.name_entry.set_sensitive(len(self.thegroup.name) == 0)
        self.description_entry.set_text(self.thegroup.description)
        
    def values_to_group(self):
        if (self.thegroup == None):
            raise Exception("group not set")
        
        self.thegroup.name = self.name_entry.get_text()
        self.thegroup.description = self.description_entry.get_text()


class ServiceEditDialog(gtk.Dialog):
        
    def __init__(self, service = None):
        super(ServiceEditDialog, self).__init__()

        if (service == None):
            self.brand_new = True
            self.service = Service()
        else:
            self.brand_new = False
            self.service = service
        
        self.create()
        
        if (not self.brand_new):
            self.service_to_values()
        self.update_sensitivity()

    def create(self):  
        self.set_title("Edit service " + self.service.name)
        self.set_border_width(5)
        self.icon_pixbuf = gtk.gdk.pixbuf_new_from_file(os.path.join(sys.path[0], "images", "service.png"))
        self.set_icon(self.icon_pixbuf)
        self.set_resizable(False)
        self.set_size_request(450, 350)
        
        notebook = gtk.Notebook()
        self.vbox.pack_start(notebook, True, True, 0)


        # general tab

        table = gtk.Table(6, 2, False)
        table.set_border_width(5)
        table.set_col_spacings(5)
        table.set_row_spacings(5)
        notebook.add(table)

        label = gtk.Label("Name")
        label.set_alignment(0, 0.5)
        table.attach(label, 0, 1, 0, 1, gtk.FILL, 0, 5, 0)

        label = gtk.Label("Display name")
        label.set_alignment(0, 0.5)
        table.attach(label, 0, 1, 1, 2, gtk.FILL, 0, 5, 0)

        label = gtk.Label("Description")
        label.set_alignment(0, 0.5)
        table.attach(label, 0, 1, 2, 3, gtk.FILL, 0, 5, 0)

        label = gtk.Label("Path to executable")
        label.set_alignment(0, 0.5)
        table.attach(label, 0, 1, 3, 4, gtk.FILL, 0, 5, 0)

        label = gtk.Label("Startup type")
        label.set_alignment(0, 0.5)
        table.attach(label, 0, 1, 4, 5, gtk.FILL, 0, 5, 0)

        label = gtk.Label("Start parameters")
        label.set_alignment(0, 0.5)
        table.attach(label, 0, 1, 5, 6, gtk.FILL, 0, 5, 0)

        self.name_label = gtk.Label()
        self.name_label.set_alignment(0, 0.5)
        table.attach(self.name_label, 1, 2, 0, 1, gtk.FILL, 0, 0, 5)
        
        self.display_name_entry = gtk.Entry()
        self.display_name_entry.set_editable(False)
        table.attach(self.display_name_entry, 1, 2, 1, 2, gtk.FILL, 0, 0, 5)

        scrolledwindow = gtk.ScrolledWindow(None, None)
        scrolledwindow.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        scrolledwindow.set_shadow_type(gtk.SHADOW_IN)
        scrolledwindow.set_size_request(0, 50)
        table.attach(scrolledwindow, 1, 2, 2, 3, gtk.FILL | gtk.EXPAND, gtk.FILL, 0, 5)
        
        self.description_text_view = gtk.TextView()
        self.description_text_view.set_editable(False)
        self.description_text_view.set_wrap_mode(gtk.WRAP_WORD)
        scrolledwindow.add(self.description_text_view)

        self.exe_path_entry = gtk.Entry()
        self.exe_path_entry.set_editable(False)
        table.attach(self.exe_path_entry, 1, 2, 3, 4, gtk.FILL, 0, 0, 0)
        
        self.startup_type_combo = gtk.combo_box_new_text()
        self.startup_type_combo.append_text(Service.get_start_type_string(svcctl.SVCCTL_BOOT_START))
        self.startup_type_combo.append_text(Service.get_start_type_string(svcctl.SVCCTL_SYSTEM_START))
        self.startup_type_combo.append_text(Service.get_start_type_string(svcctl.SVCCTL_AUTO_START))
        self.startup_type_combo.append_text(Service.get_start_type_string(svcctl.SVCCTL_DEMAND_START))
        self.startup_type_combo.append_text(Service.get_start_type_string(svcctl.SVCCTL_DISABLED))
        table.attach(self.startup_type_combo, 1, 2, 4, 5, gtk.FILL, 0, 0, 0)

        self.start_params_entry = gtk.Entry()
        self.start_params_entry.set_activates_default(True)
        table.attach(self.start_params_entry, 1, 2, 5, 6, gtk.FILL, 0, 0, 0)
        
        notebook.set_tab_label(notebook.get_nth_page(0), gtk.Label("General"))
        
        
        # log on tab
        
        table = gtk.Table(8, 3, False)
        table.set_border_width(5)
        table.set_col_spacings(5)
        table.set_row_spacings(5)
        notebook.add(table)
        
        self.local_account_radio = gtk.RadioButton(None, "_Local System account")
        table.attach(self.local_account_radio, 0, 1, 0, 1, gtk.FILL, 0, 0, 0)
        
        self.allow_desktop_interaction_check = gtk.CheckButton("Allo_w service to interact with desktop")
        table.attach(self.allow_desktop_interaction_check, 0, 2, 1, 2, gtk.FILL, 0, 20, 0)
        
        self.this_account_radio = gtk.RadioButton(self.local_account_radio, "_This account:")
        table.attach(self.this_account_radio, 0, 1, 2, 3, gtk.FILL, 0, 0, 0)
        
        self.account_entry = gtk.Entry()
        self.account_entry.set_activates_default(True)
        table.attach(self.account_entry, 1, 2, 2, 3, gtk.FILL, 0, 0, 0)
        
        label = gtk.Label("Password:")
        label.set_alignment(0, 0.5)
        table.attach(label, 0, 1, 3, 4, gtk.FILL, 0, 20, 0)
        
        self.password_entry = gtk.Entry()
        self.password_entry.set_activates_default(True)
        self.password_entry.set_visibility(False)
        table.attach(self.password_entry, 1, 2, 3, 4, gtk.FILL, 0, 0, 0)
        
        label = gtk.Label("Confirm password:")
        label.set_alignment(0, 0.5)
        table.attach(label, 0, 1, 4, 5, gtk.FILL, 0, 20, 0)
        
        self.confirm_password_entry = gtk.Entry()
        self.confirm_password_entry.set_activates_default(True)
        self.confirm_password_entry.set_visibility(False)
        table.attach(self.confirm_password_entry, 1, 2, 4, 5, gtk.FILL, 0, 0, 0)
        
        
        # TODO: implement hw profiles functionality
        
        label = gtk.Label("You can enable or disable this service for the hardware profiles listed below :")
        #table.attach(label, 0, 3, 5, 6, 0, 0, 0, 5)
        
        scrolledwindow = gtk.ScrolledWindow(None, None)
        scrolledwindow.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        scrolledwindow.set_shadow_type(gtk.SHADOW_IN)
        #table.attach(scrolledwindow, 0, 3, 6, 7, gtk.FILL | gtk.EXPAND, gtk.FILL | gtk.EXPAND, 0, 0)
        
        self.profiles_tree_view = gtk.TreeView()
        scrolledwindow.add(self.profiles_tree_view)

        column = gtk.TreeViewColumn()
        column.set_title("Hardware profile")
        renderer = gtk.CellRendererText()
        column.pack_start(renderer, True)
        self.profiles_tree_view.append_column(column)
        column.add_attribute(renderer, "text", 0)
                
        column = gtk.TreeViewColumn()
        column.set_title("Status")
        renderer = gtk.CellRendererText()
        column.pack_start(renderer, True)
        self.profiles_tree_view.append_column(column)
        column.add_attribute(renderer, "text", 1)
        
        self.profiles_store = gtk.ListStore(gobject.TYPE_STRING, gobject.TYPE_STRING)
        self.profiles_store.set_sort_column_id(0, gtk.SORT_ASCENDING)
        self.profiles_tree_view.set_model(self.profiles_store)
        
        hbox = gtk.HBox(2, False)
#        table.attach(hbox, 0, 1, 7, 8, 0, 0, 0, 0)
        
        self.enable_button = gtk.Button("Enable")
        hbox.pack_start(self.enable_button, False, False, 0) 
        
        self.disable_button = gtk.Button("Disable")
        hbox.pack_start(self.disable_button, False, False, 0) 
        
        notebook.set_tab_label(notebook.get_nth_page(1), gtk.Label("Log On"))
        
                        
        # dialog buttons
        
        self.action_area.set_layout(gtk.BUTTONBOX_END)
        
        self.cancel_button = gtk.Button("Cancel", gtk.STOCK_CANCEL)
        self.cancel_button.set_flags(gtk.CAN_DEFAULT)
        self.add_action_widget(self.cancel_button, gtk.RESPONSE_CANCEL)
        
        self.apply_button = gtk.Button("Apply", gtk.STOCK_APPLY)
        self.apply_button.set_flags(gtk.CAN_DEFAULT)
        self.apply_button.set_sensitive(not self.brand_new) # disabled for new group
        self.add_action_widget(self.apply_button, gtk.RESPONSE_APPLY)
        
        self.ok_button = gtk.Button("OK", gtk.STOCK_OK)
        self.ok_button.set_flags(gtk.CAN_DEFAULT)
        self.add_action_widget(self.ok_button, gtk.RESPONSE_OK)
        
        self.set_default_response(gtk.RESPONSE_OK)


        # signals/events
        
        self.local_account_radio.connect("toggled", self.on_local_account_radio_clicked)
        #self.profiles_tree_view.get_selection().connect("changed", self.on_profiles_tree_view_selection_changed)
        #self.enable_button.connect("clicked", self.on_enable_button_click)
        #self.disable_button.connect("clicked", self.on_disable_button_click)

    def check_for_problems(self):
        if (self.password_entry.get_text() != self.confirm_password_entry.get_text()) and self.this_account_radio.get_active():
            return "The password was not correctly confirmed. Please ensure that the password and confirmation match exactly."
        
        return None

    def update_sensitivity(self):
        local_account = self.local_account_radio.get_active()
        
        self.allow_desktop_interaction_check.set_sensitive(local_account)
        self.account_entry.set_sensitive(not local_account)
        self.password_entry.set_sensitive(not local_account)
        self.confirm_password_entry.set_sensitive(not local_account)
        
#        profile = self.get_selected_profile()
#        if (profile == None):
#            self.enable_button.set_sensitive(False)
#            self.disable_button.set_sensitive(False)
#        else:
#            self.enable_button.set_sensitive(not profile[1])
#            self.disable_button.set_sensitive(profile[1])
        
    def service_to_values(self):
        if (self.service == None):
            raise Exception("service not set")
 
        self.name_label.set_text(self.service.name)
        self.display_name_entry.set_text(self.service.display_name)
        self.description_text_view.get_buffer().set_text(self.service.description)
        self.exe_path_entry.set_text(self.service.path_to_exe)
        
        temp_dict = {svcctl.SVCCTL_BOOT_START:0, svcctl.SVCCTL_SYSTEM_START:1, svcctl.SVCCTL_AUTO_START:2, svcctl.SVCCTL_DEMAND_START:3, svcctl.SVCCTL_DISABLED:4}

        self.startup_type_combo.set_active(temp_dict[self.service.start_type])
        self.start_params_entry.set_text(self.service.start_params)
        
        if (self.service.account == None):
            self.local_account_radio.set_active(True)
            self.allow_desktop_interaction_check.set_active(self.service.allow_desktop_interaction)
        else:
            self.this_account_radio.set_active(True)
            self.account_entry.set_text(self.service.account)
            
            if (self.service.account_password != None):
                self.password_entry.set_text(self.service.account_password)
                self.confirm_password_entry.set_text(self.service.account_password)
            
        #self.refresh_profiles_tree_view()
        
    def values_to_service(self):
        if (self.service == None):
            raise Exception("service not set")
        
        temp_dict = {0:svcctl.SVCCTL_BOOT_START, 1:svcctl.SVCCTL_SYSTEM_START, 2:svcctl.SVCCTL_AUTO_START, 3:svcctl.SVCCTL_DEMAND_START, 4:svcctl.SVCCTL_DISABLED}

        self.service.start_type = temp_dict[self.startup_type_combo.get_active()]
        self.service.start_params = self.start_params_entry.get_text()
        
        if (self.local_account_radio.get_active()):
            self.service.account = None
            self.service.account_password = None
            self.service.allow_desktop_interaction = self.allow_desktop_interaction_check.get_active()
        else:
            self.service.account = self.account_entry.get_text()
            self.service.account_password = self.password_entry.get_text()
            
#        del self.service.hw_profile_list[:]
#        
#        iter = self.profiles_store.get_iter_first()
#        while (iter != None):
#            name = self.profiles_store.get_value(iter, 0)
#            enabled = self.profiles_store.get_value(iter, 1)
#            self.service.hw_profile_list.append([name, [False, True][enabled == "Enabled"]])
#            iter = self.profiles_store.iter_next(iter)

#    def refresh_profiles_tree_view(self):
#        (model, paths) = self.profiles_tree_view.get_selection().get_selected_rows()
#        
#        self.profiles_store.clear()
#        for profile in self.service.hw_profile_list:
#            self.profiles_store.append((profile[0], ["Disabled", "Enabled"][profile[1]]))
#        
#        if (len(paths) > 0):
#            self.profiles_tree_view.get_selection().select_path(paths[0])

#    def get_selected_profile(self):
#        (model, iter) = self.profiles_tree_view.get_selection().get_selected()
#        if (iter == None): # no selection
#            return None
#        else:
#            name = model.get_value(iter, 0)
#            return [profile for profile in self.service.hw_profile_list if profile[0] == name][0]

    def on_local_account_radio_clicked(self, widget):
        self.update_sensitivity()

#    def on_enable_button_click(self, widget):
#        profile = self.get_selected_profile()
#        if (profile == None): # no selection
#            return 
#        
#        profile[1] = True
#        self.refresh_profiles_tree_view()
#    
#    def on_disable_button_click(self, widget):
#        profile = self.get_selected_profile()
#        if (profile == None): # no selection
#            return 
#        
#        profile[1] = False
#        self.refresh_profiles_tree_view()
#
#    def on_profiles_tree_view_selection_changed(self, widget):
#        self.update_sensitivity()


class ServiceControlDialog(gtk.Dialog):

    def __init__(self, service, control):
        super(ServiceControlDialog, self).__init__()

        self.service = service
        self.control = control
        self.cancel_callback = None
        self.progress_speed = 0.1

        self.create()
        
    def create(self):
        self.set_title("Service Control")
        self.set_border_width(10)
        self.set_icon_from_file(os.path.join(sys.path[0], "images", "service.png"))
        self.set_resizable(False)
        self.set_size_request(400, 150)
        
        self.control_label = gtk.Label()
        self.control_label.set_markup("<b>" + ServiceControlDialog.get_control_string(self) + "</b> " + self.service.display_name + "...")
        self.control_label.set_padding(10, 10)
        self.control_label.set_ellipsize(pango.ELLIPSIZE_END)
        self.vbox.pack_start(self.control_label, False, True, 5)

        self.progress_bar = gtk.ProgressBar()
        self.progress_bar.set_fraction(0.0)
        self.vbox.pack_start(self.progress_bar, False, True, 5)
        

        # dialog buttons
        
        self.action_area.set_layout(gtk.BUTTONBOX_CENTER)
        
        self.close_button = gtk.Button("Close", gtk.STOCK_CLOSE)
        self.close_button.set_flags(gtk.CAN_DEFAULT)
        self.add_action_widget(self.close_button, gtk.RESPONSE_CANCEL)
        
        self.set_default_response(gtk.RESPONSE_CANCEL)
        
        
        # signals/events

        self.close_button.connect("clicked", self.on_close_button_clicked)

    def get_control_string(self):
        if (self.control == None):
            return "Starting"
        elif (self.control == svcctl.SVCCTL_CONTROL_STOP):
            return "Stopping"
        elif (self.control == svcctl.SVCCTL_CONTROL_PAUSE):
            return "Pausing"
        elif (self.control == svcctl.SVCCTL_CONTROL_CONTINUE):
            return "Resuming"
        else:
            return ""
        
    def set_close_callback(self, close_callback):
        self.close_callback = close_callback
    
    def progress(self, to_the_end = False):
        fraction = self.progress_bar.get_fraction()
        
        if ((fraction + self.progress_speed >= 1.0) or to_the_end):
            self.progress_bar.set_fraction(1.0)
        else:
            self.progress_bar.set_fraction(fraction + self.progress_speed)

    def set_progress_speed(self, progress_speed):
        self.progress_speed = progress_speed

    def on_close_button_clicked(self, widget):
        if (self.close_callback != None):
            self.close_callback()


class TaskEditDialog(gtk.Dialog):
    
    def __init__(self, task = None):
        super(TaskEditDialog, self).__init__()

        if (task == None):
            self.brand_new = True
            self.task = Task("", -1)
        else:
            self.brand_new = False
            self.task = task
        
        self.disable_signals = True

        self.create()
        
        if (not self.brand_new):
            self.task_to_values()
        self.update_sensitivity()
        self.update_captions()

        self.disable_signals = False
        
    def create(self):
        self.set_title(["Edit task", "New task"][self.brand_new])
        self.set_border_width(5)
        self.set_icon_from_file(os.path.join(sys.path[0], "images", "crontab.png"))
        self.set_resizable(False)
        self.set_size_request(500, -1)

        
        # scheduled description label

        self.scheduled_label = gtk.Label()
        self.scheduled_label.set_line_wrap(True)
        self.scheduled_label.set_padding(10, 10)
        self.vbox.pack_start(self.scheduled_label, True, True, 0)
        
        separator = gtk.HSeparator()
        self.vbox.pack_start(separator, False, True, 10)
        
        
        # command
        hbox = gtk.HBox()
        self.vbox.pack_start(hbox, False, False, 10)
        
        label = gtk.Label("Command:")
        hbox.pack_start(label, False, True, 5)
        
        self.command_entry = gtk.Entry()
        self.command_entry.set_activates_default(True)
        hbox.pack_start(self.command_entry, True, True, 5)

        separator = gtk.HSeparator()
        self.vbox.pack_start(separator, False, True, 10)

        table = gtk.Table(2, 3)
        table.set_border_width(5)
        table.set_row_spacings(5)
        table.set_col_spacings(5)
        self.vbox.pack_start(table, True, True, 0)
        
        label = gtk.Label("Schedule Task:")
        table.attach(label, 0, 1, 0, 1, gtk.FILL | gtk.EXPAND, gtk.FILL, 0, 0)
        
        label = gtk.Label("Start Time:")
        table.attach(label, 1, 2, 0, 1, gtk.FILL, gtk.FILL, 0, 0)
        
        table.attach(gtk.Label(), 2, 3, 0, 1, gtk.FILL | gtk.EXPAND, gtk.FILL, 0, 0)
        
        self.scheduled_combo = gtk.combo_box_new_text()
        self.scheduled_combo.append_text("Daily")
        self.scheduled_combo.append_text("Weekly")
        self.scheduled_combo.append_text("Monthly")
        self.scheduled_combo.set_active(0)
        table.attach(self.scheduled_combo, 0, 1, 1, 2, gtk.FILL | gtk.EXPAND, gtk.FILL, 0, 0)
        
        hbox = gtk.HBox()
        table.attach(hbox, 1, 2, 1, 2, gtk.FILL, gtk.FILL, 10, 0)
        
        self.hour_spin_button = gtk.SpinButton()
        self.hour_spin_button.set_range(0, 23)
        self.hour_spin_button.set_numeric(True)
        self.hour_spin_button.set_increments(1, 1)
        self.hour_spin_button.set_width_chars(2)
        hbox.pack_start(self.hour_spin_button, True, True, 0)
        
        label = gtk.Label(":")
        hbox.pack_start(label, False, False, 0)
        
        self.minute_spin_button = gtk.SpinButton()
        self.minute_spin_button.set_range(0, 59)
        self.minute_spin_button.set_numeric(True)
        self.minute_spin_button.set_increments(1, 1)
        self.minute_spin_button.set_width_chars(2)
        hbox.pack_start(self.minute_spin_button, True, True, 0)

        table.attach(gtk.Label(), 2, 3, 1, 2, gtk.FILL | gtk.EXPAND, gtk.FILL, 0, 0)
        
        table = gtk.Table(2, 2)
        self.vbox.pack_start(table, True, True, 5)
        
        
        # weekly stuff
        
        self.weekly_label = gtk.Label(" Run weekly on: ")
        table.attach(self.weekly_label, 0, 1, 0, 1, gtk.FILL | gtk.EXPAND, gtk.FILL, 0, 0)
        
        scrolledwindow = gtk.ScrolledWindow(None, None)
        scrolledwindow.set_border_width(5)
        scrolledwindow.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        scrolledwindow.set_shadow_type(gtk.SHADOW_IN)
        table.attach(scrolledwindow, 0, 1, 1, 2, gtk.FILL | gtk.EXPAND, gtk.FILL | gtk.EXPAND, 5, 5)
        
        self.weekly_tree_view = gtk.TreeView()
        self.weekly_tree_view.set_size_request(0, 150)
        self.weekly_tree_view.set_headers_visible(False)
        scrolledwindow.add(self.weekly_tree_view)
        
        column = gtk.TreeViewColumn()
        column.set_title("Checked")
        self.weekly_toggle_renderer = gtk.CellRendererToggle()
        column.pack_start(self.weekly_toggle_renderer, True)
        self.weekly_tree_view.append_column(column)
        column.add_attribute(self.weekly_toggle_renderer, "active", 0)
                
        column = gtk.TreeViewColumn()
        column.set_title("Day")
        renderer = gtk.CellRendererText()
        column.pack_start(renderer, True)
        self.weekly_tree_view.append_column(column)
        column.add_attribute(renderer, "text", 1)
        
        self.weekly_store = gtk.ListStore(gobject.TYPE_BOOLEAN, gobject.TYPE_STRING)
        self.weekly_tree_view.set_model(self.weekly_store)
        
        self.weekly_store.append([False, "Monday"])
        self.weekly_store.append([False, "Tuesday"])
        self.weekly_store.append([False, "Wednesday"])
        self.weekly_store.append([False, "Thursday"])
        self.weekly_store.append([False, "Friday"])
        self.weekly_store.append([False, "Saturday"])
        self.weekly_store.append([False, "Sunday"])
            
        
        # monthly stuff
        
        self.monthly_label = gtk.Label(" Run monthly on the: ")
        table.attach(self.monthly_label, 1, 2, 0, 1, gtk.FILL | gtk.EXPAND, gtk.FILL, 0, 0)
        
        scrolledwindow = gtk.ScrolledWindow(None, None)
        scrolledwindow.set_border_width(5)
        scrolledwindow.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        scrolledwindow.set_shadow_type(gtk.SHADOW_IN)
        table.attach(scrolledwindow, 1, 2, 1, 2, gtk.FILL | gtk.EXPAND, gtk.FILL, 5, 5)
        
        self.monthly_tree_view = gtk.TreeView()
        self.monthly_tree_view.set_headers_visible(False)
        scrolledwindow.add(self.monthly_tree_view)
        
        column = gtk.TreeViewColumn()
        column.set_title("Checked")
        self.monthly_toggle_renderer = gtk.CellRendererToggle()
        column.pack_start(self.monthly_toggle_renderer, True)
        self.monthly_tree_view.append_column(column)
        column.add_attribute(self.monthly_toggle_renderer, "active", 0)

        column = gtk.TreeViewColumn()
        column.set_title("Day")
        renderer = gtk.CellRendererText()
        column.pack_start(renderer, True)
        self.monthly_tree_view.append_column(column)
        column.add_attribute(renderer, "text", 1)
        
        self.monthly_store = gtk.ListStore(gobject.TYPE_BOOLEAN, gobject.TYPE_STRING)
        self.monthly_tree_view.set_model(self.monthly_store)
        
        for day_no in xrange(0, 31):
            self.monthly_store.append([False, Task.get_day_of_month_name(day_no)])
            
        self.run_periodically_check = gtk.CheckButton("Repeating schedule (run periodically)")
        self.run_periodically_check.connect("toggled", self.on_update_captions)
        self.vbox.pack_start(self.run_periodically_check, False, True, 5)

        self.non_interactive_check = gtk.CheckButton("Don't interact with the logged-on user")
        self.vbox.pack_start(self.non_interactive_check, False, True, 5)


        # dialog buttons
        
        self.action_area.set_layout(gtk.BUTTONBOX_END)
        
        self.cancel_button = gtk.Button("Cancel", gtk.STOCK_CANCEL)
        self.cancel_button.set_flags(gtk.CAN_DEFAULT)
        self.add_action_widget(self.cancel_button, gtk.RESPONSE_CANCEL)
        
        self.apply_button = gtk.Button("Apply", gtk.STOCK_APPLY)
        self.apply_button.set_flags(gtk.CAN_DEFAULT)
        self.apply_button.set_sensitive(not self.brand_new) # disabled for new task
        self.add_action_widget(self.apply_button, gtk.RESPONSE_APPLY)
        
        self.ok_button = gtk.Button("OK", gtk.STOCK_OK)
        self.ok_button.set_flags(gtk.CAN_DEFAULT)
        self.add_action_widget(self.ok_button, gtk.RESPONSE_OK)
        
        self.set_default_response(gtk.RESPONSE_OK)
        
        
        # signals/events

        self.scheduled_combo.connect("changed", self.on_update_sensitivity)
        self.scheduled_combo.connect("changed", self.on_update_captions)
        self.weekly_toggle_renderer.connect("toggled", self.on_renderer_toggled, self.weekly_store)
        self.monthly_toggle_renderer.connect("toggled", self.on_renderer_toggled, self.monthly_store)
        self.hour_spin_button.connect("value-changed", self.on_update_captions)
        self.minute_spin_button.connect("value-changed", self.on_update_captions)
        
    def check_for_problems(self):
        if (len(self.command_entry.get_text().strip()) == 0):
            return "Please specify a command."
        
        index = self.scheduled_combo.get_active()
        last_active_row = None
        
        if (index == 1): # weekly schedule
            for row in self.weekly_store:
                if (row[0]):
                    last_active_row = row
                    break
            if (last_active_row == None):
                return "You need to select at least one day of the week, for a weekly schedule."
        elif (index == 2): # monthly schedule
            for row in self.monthly_store:
                if (row[0]):
                    last_active_row = row
                    break
            if (last_active_row == None):
                return "You need to select at least one day of the month, for a monthly schedule."
        
        return None

    def update_sensitivity(self):
        index = self.scheduled_combo.get_active()
        
        self.weekly_label.set_sensitive(index == 1) # weekly
        self.monthly_label.set_sensitive(index == 2) # monthly
        
        self.weekly_tree_view.set_sensitive(index == 1) # weekly
        self.monthly_tree_view.set_sensitive(index == 2) # monthly
        
    def update_captions(self):
        self.values_to_task()
        self.scheduled_label.set_text(self.task.get_scheduled_description())
        
        if (self.run_periodically_check.get_active()):
            self.weekly_label.set_label(" Run weekly on: ")
            self.monthly_label.set_label(" Run monthly on the: ")
            
            self.weekly_toggle_renderer.set_property("radio", False)
            self.monthly_toggle_renderer.set_property("radio", False)
        else:
            self.weekly_label.set_label(" Run on next: ")
            self.monthly_label.set_label(" Run on the next: ")

            self.weekly_toggle_renderer.set_property("radio", True)
            self.monthly_toggle_renderer.set_property("radio", True)
            
            # make sure there's exactly one checked item when working with radios
            first_active_row = None 
            for row in self.weekly_store:
                if (row[0]):
                    if (first_active_row != None):
                        row[0] = False
                    else:
                        first_active_row = row
            if (first_active_row == None):
                self.weekly_store[0][0] = True

            # make sure there's exactly one checked item when working with radios
            first_active_row = None 
            for row in self.monthly_store:
                if (row[0]):
                    if (first_active_row != None):
                        row[0] = False
                    else:
                        first_active_row = row
            if (first_active_row == None):
                self.monthly_store[0][0] = True

        # needed for an immediate visual update
        self.weekly_tree_view.queue_draw()
        self.monthly_tree_view.queue_draw()
        
    def task_to_values(self):
        if (self.task == None):
            raise Exception("task not set")
        
        self.scheduled_label.set_text(self.task.get_scheduled_description())
        self.command_entry.set_text(self.task.command)
        
        (hour, minutes, seconds) = self.task.get_time()
        
        self.hour_spin_button.set_value(hour)
        self.minute_spin_button.set_value(minutes)
        
        index = self.task.get_scheduled_index()
        self.scheduled_combo.set_active(index)
        if (index == 1): # weekly schedule
            for day_no in self.task.get_scheduled_days_of_week():
                self.weekly_store[day_no][0] = True 
        elif (index == 2): # monthly schedule
            for day_no in self.task.get_scheduled_days_of_month():
                self.monthly_store[day_no][0] = True

        self.run_periodically_check.set_active(self.task.run_periodically)
        self.non_interactive_check.set_active(self.task.non_interactive)
        
    def values_to_task(self):
        if (self.task == None):
            raise Exception("task not set")
        
        self.task.command = self.command_entry.get_text()
                
        self.task.set_time(self.hour_spin_button.get_value(), self.minute_spin_button.get_value(), 0)
        
        index = self.scheduled_combo.get_active()
        
        self.task.set_scheduled_days_of_week([])
        self.task.set_scheduled_days_of_month([])

        if (index == 0): # daily schedule            
            dom_list = []
            for day_no in xrange(0, 31):
                dom_list.append(day_no)
            self.task.set_scheduled_days_of_month(dom_list)
        elif (index == 1): # weekly schedule
            dow_list = []
            for day_no in xrange(0, 7):
                if (self.weekly_store[day_no][0]):
                    dow_list.append(day_no)
            self.task.set_scheduled_days_of_week(dow_list) 
        elif (index == 2): # monthly schedule
            dom_list = []
            for day_no in xrange(0, 31):
                if (self.monthly_store[day_no][0]):
                    dom_list.append(day_no)
            self.task.set_scheduled_days_of_month(dom_list)

        self.task.run_periodically = self.run_periodically_check.get_active()
        self.task.non_interactive = self.non_interactive_check.get_active()
        
    def on_renderer_toggled(self, widget, path, store):
        if (self.disable_signals):
            return

        if (widget.get_radio()):
            for row in store:
                row[0] = False
            store[path][0] = True
        else:
            store[path][0] = not store[path][0]
            
        self.update_captions()

    def on_update_sensitivity(self, widget):
        if (self.disable_signals):
            return

        self.update_sensitivity()

    def on_update_captions(self, widget):
        if (self.disable_signals):
            return

        self.update_captions()


class RegValueEditDialog(gtk.Dialog):
    
    def __init__(self, reg_value, type):
        super(RegValueEditDialog, self).__init__()

        if (reg_value == None):
            self.brand_new = True
            self.reg_value = RegistryValue("", type, [], None)

        else:
            self.brand_new = False
            self.reg_value = reg_value
            
        self.disable_signals = False
        
        self.create()
        self.reg_value_to_values()
        
    def create(self):
        self.set_title(["Edit registry value", "New registry value"][self.brand_new])
        self.set_border_width(5)
        
        self.icon_registry_number_filename = os.path.join(sys.path[0], "images", "registry-number.png")
        self.icon_registry_string_filename = os.path.join(sys.path[0], "images", "registry-string.png")
        self.icon_registry_binary_filename = os.path.join(sys.path[0], "images", "registry-binary.png")

        self.set_resizable(False)


        # value name
        
        hbox = gtk.HBox()
        self.vbox.pack_start(hbox, False, False, 10)
        
        label = gtk.Label("Value name:")
        hbox.pack_start(label, False, True, 10)
        
        self.name_entry = gtk.Entry()
        self.name_entry.set_activates_default(True)
        self.name_entry.set_editable(self.brand_new)
        hbox.pack_start(self.name_entry, True, True, 10)
        

        separator = gtk.HSeparator()
        self.vbox.pack_start(separator, False, True, 5)
        

        # data

        frame = gtk.Frame(" Value data: ")
        self.vbox.pack_start(frame, True, True, 10)

        self.type_notebook = gtk.Notebook()
        self.type_notebook.set_border_width(5)
        self.type_notebook.set_show_tabs(False)
        self.type_notebook.set_show_border(False)
        frame.add(self.type_notebook)


        # string type page
       
        self.string_data_entry = gtk.Entry()
        self.string_data_entry.set_activates_default(True)
        self.type_notebook.append_page(self.string_data_entry)
        
        
        # binary type page
        
        # TODO: rewrite the hex editor - it sucks big time atm!!!
        
        scrolledwindow = gtk.ScrolledWindow(None, None)
        scrolledwindow.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        scrolledwindow.set_shadow_type(gtk.SHADOW_NONE)
        self.type_notebook.append_page(scrolledwindow)

        hbox = gtk.HBox()
        scrolledwindow.add_with_viewport(hbox)
        
        self.binary_data_addr_text_view = gtk.TextView()
        self.binary_data_addr_text_view.set_wrap_mode(gtk.WRAP_WORD)
        self.binary_data_addr_text_view.set_editable(False)
        self.binary_data_addr_text_view.modify_font(pango.FontDescription("mono 10"))
        self.binary_data_addr_text_view.set_size_request(100, -1)
        hbox.pack_start(self.binary_data_addr_text_view, False, False, 0)

        self.binary_data_hex_text_view = gtk.TextView()
        self.binary_data_hex_text_view.set_wrap_mode(gtk.WRAP_WORD)
        self.binary_data_hex_text_view.set_accepts_tab(False)
        self.binary_data_hex_text_view.modify_font(pango.FontDescription("mono bold 10"))
        self.binary_data_hex_text_view.set_size_request(200, -1)
        hbox.pack_start(self.binary_data_hex_text_view, False, False, 0)

        self.binary_data_ascii_text_view = gtk.TextView()
        self.binary_data_ascii_text_view.set_wrap_mode(gtk.WRAP_CHAR)
        self.binary_data_ascii_text_view.set_editable(False)
        self.binary_data_ascii_text_view.modify_font(pango.FontDescription("mono 10"))
        self.binary_data_ascii_text_view.set_accepts_tab(False)
        self.binary_data_ascii_text_view.set_size_request(100, -1)
        hbox.pack_start(self.binary_data_ascii_text_view, False, False, 0)


        # number type page
        
        hbox = gtk.HBox()
        self.type_notebook.append_page(hbox)
        
        self.number_data_entry = gtk.Entry()
        self.number_data_entry.set_activates_default(True)
        hbox.pack_start(self.number_data_entry, True, True, 5)
        
        self.number_data_dec_radio = gtk.RadioButton(None, "Decimal")
        hbox.pack_start(self.number_data_dec_radio, False, True, 5)
        
        self.number_data_hex_radio = gtk.RadioButton(self.number_data_dec_radio, "Hexadecimal")
        hbox.pack_start(self.number_data_hex_radio, False, True, 5)
        
        self.number_data_hex_radio.set_active(True)
        
        
        # multi-string type page
        
        scrolledwindow = gtk.ScrolledWindow(None, None)
        scrolledwindow.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        scrolledwindow.set_shadow_type(gtk.SHADOW_IN)
        self.type_notebook.append_page(scrolledwindow)

        self.multi_string_data_text_view = gtk.TextView()
        self.multi_string_data_text_view.set_wrap_mode(gtk.WRAP_NONE)
        scrolledwindow.add(self.multi_string_data_text_view)


        # dialog buttons
        
        self.action_area.set_layout(gtk.BUTTONBOX_END)
        
        self.cancel_button = gtk.Button("Cancel", gtk.STOCK_CANCEL)
        self.cancel_button.set_flags(gtk.CAN_DEFAULT)
        self.add_action_widget(self.cancel_button, gtk.RESPONSE_CANCEL)
        
        self.apply_button = gtk.Button("Apply", gtk.STOCK_APPLY)
        self.apply_button.set_flags(gtk.CAN_DEFAULT)
        self.apply_button.set_sensitive(not self.brand_new) # disabled for new task
        self.add_action_widget(self.apply_button, gtk.RESPONSE_APPLY)
        
        self.ok_button = gtk.Button("OK", gtk.STOCK_OK)
        self.ok_button.set_flags(gtk.CAN_DEFAULT)
        self.add_action_widget(self.ok_button, gtk.RESPONSE_OK)
        
        self.set_default_response(gtk.RESPONSE_OK)
        
        
        # signals/events

        self.binary_data_hex_text_view.get_buffer().connect("changed", self.on_binary_data_hex_text_view_buffer_changed)
        self.binary_data_hex_text_view.connect("focus-out-event", self.on_binary_data_hex_text_view_focus_out)
        self.number_data_dec_radio.connect("toggled", self.on_number_data_dec_radio_toggled)
        self.number_data_hex_radio.connect("toggled", self.on_number_data_hex_radio_toggled)
        self.number_data_entry.connect("changed", self.on_number_data_entry_changed)

    def check_for_problems(self):
        if (len(self.name_entry.get_text().strip()) == 0):
            return "Please specify a name."
        
        if (self.reg_value.type in [winreg.REG_DWORD, winreg.REG_DWORD_BIG_ENDIAN, winreg.REG_QWORD]):
            number_str = self.number_data_entry.get_text()
            if (len(number_str) == 0):
                return "Please enter a number."
            
            if (self.number_data_dec_radio.get_active()):
                try:
                    number = string.atoi(number_str, 10)
                    number_str_hex = "%X" % number
                    
                    if (self.reg_value.type in [winreg.REG_DWORD, winreg.REG_DWORD_BIG_ENDIAN]):
                        max_hex_len = 8
                    else:
                        max_hex_len = 16
                    
                    if (len(number_str_hex) > max_hex_len):
                        return "Please enter a smaller decimal number."
                
                except Exception:
                    return "Please enter a valid decimal number."
        
        return None

    def reg_value_to_values(self):
        if (self.reg_value == None):
            raise Exception("registry value not set")
        
        self.name_entry.set_text(self.reg_value.name)
        
        if (self.reg_value.type in [winreg.REG_SZ, winreg.REG_EXPAND_SZ]):
            self.set_icon_from_file(self.icon_registry_string_filename)
            self.set_size_request(430, 200)
            
            self.string_data_entry.set_text(self.reg_value.get_interpreted_data())
            
        elif (self.reg_value.type == winreg.REG_BINARY):
            self.set_icon_from_file(self.icon_registry_binary_filename)
            self.set_size_request(430, 400)
            
            self.binary_data_hex_text_view.get_buffer().set_text(RegValueEditDialog.byte_array_to_hex(self.reg_value.get_interpreted_data(), 8))
            self.on_binary_data_hex_text_view_buffer_changed(None)
        
        elif (self.reg_value.type in [winreg.REG_DWORD, winreg.REG_DWORD_BIG_ENDIAN, winreg.REG_QWORD]):
            self.set_icon_from_file(self.icon_registry_number_filename)
            self.set_size_request(430, 200)

            if (self.reg_value.type == winreg.REG_QWORD):
                self.number_data_entry.set_text("%016X" % self.reg_value.get_interpreted_data())
            else:
                self.number_data_entry.set_text("%08X" % self.reg_value.get_interpreted_data())
        
        elif (self.reg_value.type == winreg.REG_MULTI_SZ):
            self.set_icon_from_file(self.icon_registry_string_filename)
            self.set_size_request(430, 400)
            
            text = ""
            for line in self.reg_value.get_interpreted_data():
                text += line + "\n"
                
            self.multi_string_data_text_view.get_buffer().set_text(text)
            
    def values_to_reg_value(self):
        if (self.reg_value == None):
            raise Exception("registry value not set")
        
        self.reg_value.name = self.name_entry.get_text()
        
        if (self.reg_value.type in [winreg.REG_SZ, winreg.REG_EXPAND_SZ]):
            self.reg_value.set_interpreted_data(self.string_data_entry.get_text())

        elif (self.reg_value.type == winreg.REG_BINARY):
            buffer = self.binary_data_hex_text_view.get_buffer()
            text = buffer.get_text(buffer.get_start_iter(), buffer.get_end_iter())
            self.reg_value.set_interpreted_data(RegValueEditDialog.hex_to_byte_array(text))
        
        elif (self.reg_value.type in [winreg.REG_DWORD, winreg.REG_DWORD_BIG_ENDIAN, winreg.REG_QWORD]):
            if (self.number_data_dec_radio.get_active()):
                self.reg_value.set_interpreted_data(string.atoi(self.number_data_entry.get_text(), 10))
            else:
                self.reg_value.set_interpreted_data(string.atoi(self.number_data_entry.get_text(), 0x10))
                
        elif (self.reg_value.type == winreg.REG_MULTI_SZ):
            lines = []
            line = ""
        
            buffer = self.multi_string_data_text_view.get_buffer()
            for ch in buffer.get_text(buffer.get_start_iter(), buffer.get_end_iter()):
                if (ch != "\n"):
                    line += ch
                else:
                    lines.append(line)
                    line = ""
            
            if (len(line) > 0):
                lines.append(line)
                    
            self.reg_value.set_interpreted_data(lines)

    def update_type_page_after_show(self):
        if (self.reg_value.type == winreg.REG_SZ):
            self.type_notebook.set_current_page(0)
            self.string_data_entry.grab_focus()
            
        if (self.reg_value.type == winreg.REG_EXPAND_SZ):
            self.type_notebook.set_current_page(0)
            self.string_data_entry.grab_focus()
            
        if (self.reg_value.type == winreg.REG_BINARY):
            self.type_notebook.set_current_page(1)
            self.binary_data_hex_text_view.grab_focus()
                
        if (self.reg_value.type == winreg.REG_DWORD):
            self.type_notebook.set_current_page(2)
            self.number_data_entry.grab_focus()
                
        if (self.reg_value.type == winreg.REG_DWORD_BIG_ENDIAN):
            self.type_notebook.set_current_page(2)
            self.number_data_entry.grab_focus()
                
        if (self.reg_value.type == winreg.REG_MULTI_SZ):
            self.type_notebook.set_current_page(3)
            self.multi_string_data_text_view.grab_focus()
                
        if (self.reg_value.type == winreg.REG_QWORD):
            self.type_notebook.set_current_page(2)    
            self.number_data_entry.grab_focus()
            
        if (self.brand_new):
            self.name_entry.grab_focus()

    def on_binary_data_hex_text_view_buffer_changed(self, widget):
        if (self.disable_signals):
            return 
        
        self.disable_signals = True
        
        hex_buffer = self.binary_data_hex_text_view.get_buffer()
        ascii_buffer = self.binary_data_ascii_text_view.get_buffer()
        addr_buffer = self.binary_data_addr_text_view.get_buffer()

        insert_mark = hex_buffer.get_insert()
        insert_iter = hex_buffer.get_iter_at_mark(insert_mark)
        insert_char_offs = insert_iter.get_offset()

        text = hex_buffer.get_text(hex_buffer.get_start_iter(), hex_buffer.get_end_iter())
        before_len = len(text)
        text = RegValueEditDialog.check_hex_string(text, 8)
        after_len = len(text)
        
        hex_buffer.set_text(text)
        ascii_buffer.set_text(RegValueEditDialog.hex_to_ascii(text, 8))
        addr_buffer.set_text(RegValueEditDialog.hex_to_addr(text, 8))
        
        #print insert_char_offs
        #if (insert_char_offs >= len(text)):
        #    insert_char_offs += 1
        hex_buffer.place_cursor(hex_buffer.get_iter_at_offset(insert_char_offs + (after_len - before_len)))
        
        self.disable_signals = False
        
    def on_binary_data_hex_text_view_focus_out(self, widget, event):
        hex_buffer = self.binary_data_hex_text_view.get_buffer()
        ascii_buffer = self.binary_data_ascii_text_view.get_buffer()
        addr_buffer = self.binary_data_addr_text_view.get_buffer()
        
        text = hex_buffer.get_text(hex_buffer.get_start_iter(), hex_buffer.get_end_iter())
        text = RegValueEditDialog.check_hex_string(text, 8, True)
        
        hex_buffer.set_text(text)
        ascii_buffer.set_text(RegValueEditDialog.hex_to_ascii(text, 8))
        addr_buffer.set_text(RegValueEditDialog.hex_to_addr(text, 8))
        
    def on_number_data_hex_radio_toggled(self, widget):
        if (not widget.get_active()):
            return
        
        if (self.reg_value.type == winreg.REG_QWORD):
            digits = 16
        else:
            digits = 8
            
        number_str = self.number_data_entry.get_text()
        if (len(number_str) == 0):
            number_str = "0"

        number = string.atoi(number_str, 10)

        format = "%0" + str(digits) + "X"

        self.number_data_entry.set_text(format % number)
        
    def on_number_data_dec_radio_toggled(self, widget):
        if (not widget.get_active()):
            return
        
        if (self.reg_value.type == winreg.REG_QWORD):
            digits = 16
        else:
            digits = 8
            
        number_str = self.number_data_entry.get_text()
        if (len(number_str) == 0):
            number_str = "0"

        number = string.atoi(number_str, 0x10)

        format = "%0" + str(digits) + "d"

        self.number_data_entry.set_text(format % number)
        
    def on_number_data_entry_changed(self, widget):
        old_text = self.number_data_entry.get_text()

        if (self.reg_value.type in [winreg.REG_DWORD, winreg.REG_DWORD_BIG_ENDIAN]):
            max_len = 8
        else:
            max_len = 16

        new_text = ""
        if (self.number_data_hex_radio.get_active()):
            for ch in old_text:
                if (ch in string.hexdigits):
                    new_text += ch
            if (len(new_text) > max_len):
                new_text = new_text[:max_len]

        else:
            for ch in old_text:
                if (ch in string.digits):
                    new_text += ch

        self.number_data_entry.set_text(new_text)
        
    @staticmethod
    def check_hex_string(old_string, line_length, remove_orphaned = False):
        new_string = ""
        
        length = 0
        insert_space = False
        for ch in old_string:
            if (ch in string.hexdigits):
                new_string += str.upper(ch)
                if (insert_space):
                    new_string += " "
                    length += 1
                insert_space = not insert_space
            
            if (length >= line_length):
                new_string += "\n"
                length = 0
                
        if (insert_space and remove_orphaned):
            new_string = new_string.strip()[:len(new_string) - 1]
        
        return new_string
    
    @staticmethod
    def hex_to_ascii(old_string, line_length):
        new_string = ""
        
        digits = ""
        length = 0
        for ch in old_string:
            if (ch in string.hexdigits):
                digits += ch
            
            if (len(digits) >= 2):
                new_chr = chr(string.atol(digits, 0x10))
                if (new_chr in (string.punctuation + string.ascii_letters + ' ')):
                    new_string += new_chr
                else:
                    new_string += "."
                length += 1
                digits = ""
            
            if (length >= line_length):
                new_string += "\n"
                length = 0

        return new_string
                    
    @staticmethod
    def ascii_to_hex(old_string):
        new_string = ""
        
        for ch in old_string:
            byte = ord(ch)
            new_string += "%X" % ((byte >> 4) & 0x0F)
            new_string += "%X " % (byte & 0x0F)

        return new_string.strip()

    @staticmethod
    def hex_to_addr(old_string, line_length):
        new_string = ""
        
        digits = ""
        length = 0
        addr = 0
        for ch in old_string:
            if (ch in string.hexdigits):
                digits += ch
                
            if (len(digits) >= 2):
                
                if (length % line_length) == 0:
                    new_string += "%04X\n" % addr
                    addr += line_length

                length += 1
                digits = ""

        return new_string

    @staticmethod
    def byte_array_to_hex(array, line_length):
        new_string = ""
        
        for byte in array:
            new_string += "%02x" % byte
        
        return RegValueEditDialog.check_hex_string(new_string, line_length, False)

    @staticmethod
    def hex_to_byte_array(hex_string):
        array = []
        
        digits = ""
        for ch in hex_string:
            if (ch in string.hexdigits):
                digits += ch
            
            if (len(digits) >= 2):
                byte = string.atol(digits, 0x10)
                array.append(byte)
                digits = ""
            
        return array


class RegKeyEditDialog(gtk.Dialog):
    
    def __init__(self, reg_key):
        super(RegKeyEditDialog, self).__init__()

        if (reg_key == None):
            self.brand_new = True
            self.reg_key = RegistryKey("", None)

        else:
            self.brand_new = False
            self.reg_key = reg_key
            
        self.create()
        self.reg_key_to_values()
        
    def create(self):
        self.set_title(["Edit registry key", "New registry key"][self.brand_new])
        self.set_border_width(5)
        
        self.icon_registry_filename = os.path.join(sys.path[0], "images", "registry.png")
        self.set_icon_from_file(self.icon_registry_filename)

        self.set_resizable(False)


        # value name
        
        hbox = gtk.HBox()
        self.vbox.pack_start(hbox, False, False, 10)
        
        label = gtk.Label("Key name:")
        hbox.pack_start(label, False, True, 10)
        
        self.name_entry = gtk.Entry()
        self.name_entry.set_activates_default(True)
        hbox.pack_start(self.name_entry, True, True, 10)
        

        # dialog buttons
        
        self.action_area.set_layout(gtk.BUTTONBOX_END)
        
        self.cancel_button = gtk.Button("Cancel", gtk.STOCK_CANCEL)
        self.cancel_button.set_flags(gtk.CAN_DEFAULT)
        self.add_action_widget(self.cancel_button, gtk.RESPONSE_CANCEL)
        
        self.apply_button = gtk.Button("Apply", gtk.STOCK_APPLY)
        self.apply_button.set_flags(gtk.CAN_DEFAULT)
        self.apply_button.set_sensitive(not self.brand_new) # disabled for new task
        self.add_action_widget(self.apply_button, gtk.RESPONSE_APPLY)
        
        self.ok_button = gtk.Button("OK", gtk.STOCK_OK)
        self.ok_button.set_flags(gtk.CAN_DEFAULT)
        self.add_action_widget(self.ok_button, gtk.RESPONSE_OK)
        
        self.set_default_response(gtk.RESPONSE_OK)
        
        
        # signals/events

    def check_for_problems(self):
        if (len(self.name_entry.get_text().strip()) == 0):
            return "Please specify a name."
        
        return None

    def reg_key_to_values(self):
        if (self.reg_key == None):
            raise Exception("registry key not set")
        
        self.name_entry.set_text(self.reg_key.name)
            
    def values_to_reg_key(self):
        if (self.reg_key == None):
            raise Exception("registry key not set")
        
        self.reg_key.name = self.name_entry.get_text()


class RegRenameDialog(gtk.Dialog):
    
    def __init__(self, reg_key, reg_value):
        super(RegRenameDialog, self).__init__()

        self.reg_key = reg_key
        self.reg_value = reg_value
            
        self.create()
        self.reg_to_values()
        
    def create(self):
        self.set_title(["Rename registry key", "Rename registry value"][self.reg_value != None])
        self.set_border_width(5)
        
        self.icon_registry_filename = os.path.join(sys.path[0], "images", "registry.png")
        self.set_icon_from_file(self.icon_registry_filename)

        self.set_resizable(False)


        # name
        
        hbox = gtk.HBox()
        self.vbox.pack_start(hbox, False, False, 10)
        
        label = gtk.Label("Name:")
        hbox.pack_start(label, False, True, 10)
        
        self.name_entry = gtk.Entry()
        self.name_entry.set_activates_default(True)
        hbox.pack_start(self.name_entry, True, True, 10)
        

        # dialog buttons
        
        self.action_area.set_layout(gtk.BUTTONBOX_END)
        
        self.cancel_button = gtk.Button("Cancel", gtk.STOCK_CANCEL)
        self.cancel_button.set_flags(gtk.CAN_DEFAULT)
        self.add_action_widget(self.cancel_button, gtk.RESPONSE_CANCEL)
        
        self.apply_button = gtk.Button("Apply", gtk.STOCK_APPLY)
        self.apply_button.set_flags(gtk.CAN_DEFAULT)
        self.add_action_widget(self.apply_button, gtk.RESPONSE_APPLY)
        
        self.ok_button = gtk.Button("OK", gtk.STOCK_OK)
        self.ok_button.set_flags(gtk.CAN_DEFAULT)
        self.add_action_widget(self.ok_button, gtk.RESPONSE_OK)
        
        self.set_default_response(gtk.RESPONSE_OK)
        
        
        # signals/events

    def check_for_problems(self):
        if (len(self.name_entry.get_text().strip()) == 0):
            return "Please specify a name."
        
        return None

    def reg_to_values(self):
        if (self.reg_key == None):
            self.name_entry.set_text(self.reg_value.name)
        else:
            self.name_entry.set_text(self.reg_key.name)
            
    def values_to_reg(self):
        if (self.reg_key == None):
            self.reg_value.name = self.name_entry.get_text()
        else:
            self.reg_key.name = self.name_entry.get_text()


class SAMConnectDialog(gtk.Dialog):
    
    def __init__(self, server_address, transport_type, username):
        super(SAMConnectDialog, self).__init__()

        self.server_address = server_address
        self.transport_type = transport_type
        self.username = username
        self.domains = None
        
        self.create()
        
        self.update_sensitivity()

    def create(self):  
        self.set_title("Connect to SAM server")
        self.set_border_width(5)
        self.set_icon_name(gtk.STOCK_CONNECT)
        self.set_resizable(False)
        
        # server frame
        
        self.vbox.set_spacing(5)

        self.server_frame = gtk.Frame("Server")
        self.vbox.pack_start(self.server_frame, False, True, 0)
                
        table = gtk.Table(3, 2)
        table.set_border_width(5)
        self.server_frame.add(table)
        
        label = gtk.Label(" Server address: ")
        label.set_alignment(0, 0.5)
        table.attach(label, 0, 1, 0, 1, gtk.FILL, gtk.FILL | gtk.EXPAND, 0, 0)
        
        self.server_address_entry = gtk.Entry()
        self.server_address_entry.set_text(self.server_address)
        self.server_address_entry.set_activates_default(True)
        table.attach(self.server_address_entry, 1, 2, 0, 1, gtk.FILL | gtk.EXPAND, gtk.FILL | gtk.EXPAND, 1, 1)
        
        label = gtk.Label(" Username: ")
        label.set_alignment(0, 0.5)
        table.attach(label, 0, 1, 1, 2, gtk.FILL, gtk.FILL | gtk.EXPAND, 0, 0)
        
        self.username_entry = gtk.Entry()
        self.username_entry.set_text(self.username)
        self.username_entry.set_activates_default(True)
        table.attach(self.username_entry, 1, 2, 1, 2, gtk.FILL | gtk.EXPAND, gtk.FILL | gtk.EXPAND, 1, 1)
        
        label = gtk.Label(" Password: ")
        label.set_alignment(0, 0.5)
        table.attach(label, 0, 1, 2, 3, gtk.FILL, gtk.FILL | gtk.EXPAND, 0, 0)
        
        self.password_entry = gtk.Entry()
        self.password_entry.set_visibility(False)
        self.password_entry.set_activates_default(True)
        table.attach(self.password_entry, 1, 2, 2, 3, gtk.FILL | gtk.EXPAND, gtk.FILL | gtk.EXPAND, 1, 1)
        
        
        # transport frame

        self.transport_frame = gtk.Frame(" Transport type ")
        self.vbox.pack_start(self.transport_frame, False, True, 0)

        vbox = gtk.VBox()
        vbox.set_border_width(5)
        self.transport_frame.add(vbox)
        
        self.rpc_smb_tcpip_radio_button = gtk.RadioButton(None, "RPC over SMB over TCP/IP")
        self.rpc_smb_tcpip_radio_button.set_active(self.transport_type == 0)
        vbox.pack_start(self.rpc_smb_tcpip_radio_button)
        
        self.rpc_tcpip_radio_button = gtk.RadioButton(self.rpc_smb_tcpip_radio_button, "RPC over TCP/IP")
        self.rpc_tcpip_radio_button.set_active(self.transport_type == 1)
        vbox.pack_start(self.rpc_tcpip_radio_button)
        
        self.localhost_radio_button = gtk.RadioButton(self.rpc_tcpip_radio_button, "Localhost")
        self.localhost_radio_button.set_active(self.transport_type == 2)
        vbox.pack_start(self.localhost_radio_button)
        
        
        # domain frame
        
        self.domains_frame = gtk.Frame(" Domain ")
        self.domains_frame.set_no_show_all(True)
        self.vbox.pack_start(self.domains_frame, False, True, 0)
        
        table = gtk.Table(1, 2)
        table.set_border_width(5)
        self.domains_frame.add(table)
        
        label = gtk.Label("Select domain: ")
        label.set_alignment(0, 0.5)
        table.attach(label, 0, 1, 0, 1, gtk.FILL, gtk.FILL | gtk.EXPAND, 0, 0)
        
        self.domain_combo_box = gtk.combo_box_new_text()
        table.attach(self.domain_combo_box, 1, 2, 0, 1, gtk.FILL | gtk.EXPAND, gtk.FILL | gtk.EXPAND, 1, 1)
        
        
        # dialog buttons
        
        self.action_area.set_layout(gtk.BUTTONBOX_END)
        
        self.cancel_button = gtk.Button("Cancel", gtk.STOCK_CANCEL)
        self.add_action_widget(self.cancel_button, gtk.RESPONSE_CANCEL)
        
        self.connect_button = gtk.Button("Connect", gtk.STOCK_CONNECT)
        self.connect_button.set_flags(gtk.CAN_DEFAULT)
        self.add_action_widget(self.connect_button, gtk.RESPONSE_OK)
        
        self.set_default_response(gtk.RESPONSE_OK)
        
        
        # signals/events
        
        self.rpc_smb_tcpip_radio_button.connect("toggled", self.on_radio_button_toggled)
        self.rpc_tcpip_radio_button.connect("toggled", self.on_radio_button_toggled)
        self.localhost_radio_button.connect("toggled", self.on_radio_button_toggled)
        
    def update_sensitivity(self):
        server_required = not self.localhost_radio_button.get_active()
        
        self.server_address_entry.set_sensitive(server_required)
    
    def set_domains(self, domains, domain_index = -1):
        if (domains != None):
            self.server_frame.set_sensitive(False)
            self.transport_frame.set_sensitive(False)
            
            self.domains_frame.set_no_show_all(False)
            self.domains_frame.show_all()
            self.domains_frame.set_no_show_all(True)
            self.domain_combo_box.get_model().clear()
            for domain in domains:
                self.domain_combo_box.append_text(domain)
                
            if (domain_index != -1):
                self.domain_combo_box.set_active(domain_index)
        else:
            self.server_frame.set_sensitive(True)
            self.transport_frame.set_sensitive(True)
            self.domains_frame.hide_all()
            
    def get_server_address(self):
        return self.server_address_entry.get_text().strip()
    
    def get_transport_type(self):
        if (self.rpc_smb_tcpip_radio_button.get_active()):
            return 0
        elif (self.rpc_tcpip_radio_button.get_active()):
            return 1
        elif (self.localhost_radio_button.get_active()):
            return 2
        else:
            return -1
    
    def get_username(self):
        return self.username_entry.get_text().strip()
    
    def get_password(self):
        return self.password_entry.get_text()
    
    def get_domain_index(self):
        return self.domain_combo_box.get_active()
    
    def on_radio_button_toggled(self, widget):
        self.update_sensitivity()


class SvcCtlConnectDialog(gtk.Dialog):
    
    def __init__(self, server_address, transport_type, username):
        super(SvcCtlConnectDialog, self).__init__()

        self.server_address = server_address
        self.transport_type = transport_type
        self.username = username
        
        self.create()
        
        self.update_sensitivity()

    def create(self):  
        self.set_title("Connect to a server")
        self.set_border_width(5)
        self.set_icon_name(gtk.STOCK_CONNECT)
        self.set_resizable(False)
        
        # server frame
        
        self.vbox.set_spacing(5)

        self.server_frame = gtk.Frame("Server")
        self.vbox.pack_start(self.server_frame, False, True, 0)
                
        table = gtk.Table(3, 2)
        table.set_border_width(5)
        self.server_frame.add(table)
        
        label = gtk.Label(" Server address: ")
        label.set_alignment(0, 0.5)
        table.attach(label, 0, 1, 0, 1, gtk.FILL, gtk.FILL | gtk.EXPAND, 0, 0)
        
        self.server_address_entry = gtk.Entry()
        self.server_address_entry.set_text(self.server_address)
        self.server_address_entry.set_activates_default(True)
        table.attach(self.server_address_entry, 1, 2, 0, 1, gtk.FILL | gtk.EXPAND, gtk.FILL | gtk.EXPAND, 1, 1)
        
        label = gtk.Label(" Username: ")
        label.set_alignment(0, 0.5)
        table.attach(label, 0, 1, 1, 2, gtk.FILL, gtk.FILL | gtk.EXPAND, 0, 0)
        
        self.username_entry = gtk.Entry()
        self.username_entry.set_text(self.username)
        self.username_entry.set_activates_default(True)
        table.attach(self.username_entry, 1, 2, 1, 2, gtk.FILL | gtk.EXPAND, gtk.FILL | gtk.EXPAND, 1, 1)
        
        label = gtk.Label(" Password: ")
        label.set_alignment(0, 0.5)
        table.attach(label, 0, 1, 2, 3, gtk.FILL, gtk.FILL | gtk.EXPAND, 0, 0)
        
        self.password_entry = gtk.Entry()
        self.password_entry.set_visibility(False)
        self.password_entry.set_activates_default(True)
        table.attach(self.password_entry, 1, 2, 2, 3, gtk.FILL | gtk.EXPAND, gtk.FILL | gtk.EXPAND, 1, 1)
        
        
        # transport frame

        self.transport_frame = gtk.Frame(" Transport type ")
        self.vbox.pack_start(self.transport_frame, False, True, 0)

        vbox = gtk.VBox()
        vbox.set_border_width(5)
        self.transport_frame.add(vbox)
        
        self.rpc_smb_tcpip_radio_button = gtk.RadioButton(None, "RPC over SMB over TCP/IP")
        self.rpc_smb_tcpip_radio_button.set_active(self.transport_type == 0)
        vbox.pack_start(self.rpc_smb_tcpip_radio_button)
        
        self.rpc_tcpip_radio_button = gtk.RadioButton(self.rpc_smb_tcpip_radio_button, "RPC over TCP/IP")
        self.rpc_tcpip_radio_button.set_active(self.transport_type == 1)
        vbox.pack_start(self.rpc_tcpip_radio_button)
        
        self.localhost_radio_button = gtk.RadioButton(self.rpc_tcpip_radio_button, "Localhost")
        self.localhost_radio_button.set_active(self.transport_type == 2)
        vbox.pack_start(self.localhost_radio_button)
        
        
        # dialog buttons
        
        self.action_area.set_layout(gtk.BUTTONBOX_END)
        
        self.cancel_button = gtk.Button("Cancel", gtk.STOCK_CANCEL)
        self.add_action_widget(self.cancel_button, gtk.RESPONSE_CANCEL)
        
        self.connect_button = gtk.Button("Connect", gtk.STOCK_CONNECT)
        self.connect_button.set_flags(gtk.CAN_DEFAULT)
        self.add_action_widget(self.connect_button, gtk.RESPONSE_OK)
        
        self.set_default_response(gtk.RESPONSE_OK)
        
        
        # signals/events
        
        self.rpc_smb_tcpip_radio_button.connect("toggled", self.on_radio_button_toggled)
        self.rpc_tcpip_radio_button.connect("toggled", self.on_radio_button_toggled)
        self.localhost_radio_button.connect("toggled", self.on_radio_button_toggled)
        
    def update_sensitivity(self):
        server_required = not self.localhost_radio_button.get_active()
        
        self.server_address_entry.set_sensitive(server_required)
    
    def get_server_address(self):
        return self.server_address_entry.get_text().strip()
    
    def get_transport_type(self):
        if (self.rpc_smb_tcpip_radio_button.get_active()):
            return 0
        elif (self.rpc_tcpip_radio_button.get_active()):
            return 1
        elif (self.localhost_radio_button.get_active()):
            return 2
        else:
            return -1
    
    def get_username(self):
        return self.username_entry.get_text().strip()
    
    def get_password(self):
        return self.password_entry.get_text()
    
    def on_radio_button_toggled(self, widget):
        self.update_sensitivity()


class ATSvcConnectDialog(gtk.Dialog):
    
    def __init__(self, server_address, transport_type, username):
        super(ATSvcConnectDialog, self).__init__()

        self.server_address = server_address
        self.transport_type = transport_type
        self.username = username
        
        self.create()
        
        self.update_sensitivity()

    def create(self):  
        self.set_title("Connect to a server")
        self.set_border_width(5)
        self.set_icon_name(gtk.STOCK_CONNECT)
        self.set_resizable(False)
        
        # server frame
        
        self.vbox.set_spacing(5)

        self.server_frame = gtk.Frame("Server")
        self.vbox.pack_start(self.server_frame, False, True, 0)
                
        table = gtk.Table(3, 2)
        table.set_border_width(5)
        self.server_frame.add(table)
        
        label = gtk.Label(" Server address: ")
        label.set_alignment(0, 0.5)
        table.attach(label, 0, 1, 0, 1, gtk.FILL, gtk.FILL | gtk.EXPAND, 0, 0)
        
        self.server_address_entry = gtk.Entry()
        self.server_address_entry.set_text(self.server_address)
        self.server_address_entry.set_activates_default(True)
        table.attach(self.server_address_entry, 1, 2, 0, 1, gtk.FILL | gtk.EXPAND, gtk.FILL | gtk.EXPAND, 1, 1)
        
        label = gtk.Label(" Username: ")
        label.set_alignment(0, 0.5)
        table.attach(label, 0, 1, 1, 2, gtk.FILL, gtk.FILL | gtk.EXPAND, 0, 0)
        
        self.username_entry = gtk.Entry()
        self.username_entry.set_text(self.username)
        self.username_entry.set_activates_default(True)
        table.attach(self.username_entry, 1, 2, 1, 2, gtk.FILL | gtk.EXPAND, gtk.FILL | gtk.EXPAND, 1, 1)
        
        label = gtk.Label(" Password: ")
        label.set_alignment(0, 0.5)
        table.attach(label, 0, 1, 2, 3, gtk.FILL, gtk.FILL | gtk.EXPAND, 0, 0)
        
        self.password_entry = gtk.Entry()
        self.password_entry.set_visibility(False)
        self.password_entry.set_activates_default(True)
        table.attach(self.password_entry, 1, 2, 2, 3, gtk.FILL | gtk.EXPAND, gtk.FILL | gtk.EXPAND, 1, 1)
        
        
        # transport frame

        self.transport_frame = gtk.Frame(" Transport type ")
        self.vbox.pack_start(self.transport_frame, False, True, 0)

        vbox = gtk.VBox()
        vbox.set_border_width(5)
        self.transport_frame.add(vbox)
        
        self.rpc_smb_tcpip_radio_button = gtk.RadioButton(None, "RPC over SMB over TCP/IP")
        self.rpc_smb_tcpip_radio_button.set_active(self.transport_type == 0)
        vbox.pack_start(self.rpc_smb_tcpip_radio_button)
        
        self.rpc_tcpip_radio_button = gtk.RadioButton(self.rpc_smb_tcpip_radio_button, "RPC over TCP/IP")
        self.rpc_tcpip_radio_button.set_sensitive(False)
        self.rpc_tcpip_radio_button.set_active(self.transport_type == 1)
        vbox.pack_start(self.rpc_tcpip_radio_button)
        
        self.localhost_radio_button = gtk.RadioButton(self.rpc_tcpip_radio_button, "Localhost")
        self.localhost_radio_button.set_sensitive(False)
        self.localhost_radio_button.set_active(self.transport_type == 2)
        vbox.pack_start(self.localhost_radio_button)
        
        
        # dialog buttons
        
        self.action_area.set_layout(gtk.BUTTONBOX_END)
        
        self.cancel_button = gtk.Button("Cancel", gtk.STOCK_CANCEL)
        self.add_action_widget(self.cancel_button, gtk.RESPONSE_CANCEL)
        
        self.connect_button = gtk.Button("Connect", gtk.STOCK_CONNECT)
        self.connect_button.set_flags(gtk.CAN_DEFAULT)
        self.add_action_widget(self.connect_button, gtk.RESPONSE_OK)
        
        self.set_default_response(gtk.RESPONSE_OK)
        
        
        # signals/events
        
        self.rpc_smb_tcpip_radio_button.connect("toggled", self.on_radio_button_toggled)
        self.rpc_tcpip_radio_button.connect("toggled", self.on_radio_button_toggled)
        self.localhost_radio_button.connect("toggled", self.on_radio_button_toggled)
        
    def update_sensitivity(self):
        server_required = not self.localhost_radio_button.get_active()
        
        self.server_address_entry.set_sensitive(server_required)
    
    def get_server_address(self):
        return self.server_address_entry.get_text().strip()
    
    def get_transport_type(self):
        if (self.rpc_smb_tcpip_radio_button.get_active()):
            return 0
        elif (self.rpc_tcpip_radio_button.get_active()):
            return 1
        elif (self.localhost_radio_button.get_active()):
            return 2
        else:
            return -1
    
    def get_username(self):
        return self.username_entry.get_text().strip()
    
    def get_password(self):
        return self.password_entry.get_text()
    
    def on_radio_button_toggled(self, widget):
        self.update_sensitivity()


class WinRegConnectDialog(gtk.Dialog):
    
    def __init__(self, server_address, transport_type, username):
        super(WinRegConnectDialog, self).__init__()

        self.server_address = server_address
        self.transport_type = transport_type
        self.username = username
        
        self.create()
        
        self.update_sensitivity()

    def create(self):  
        self.set_title("Connect to a server")
        self.set_border_width(5)
        self.set_icon_name(gtk.STOCK_CONNECT)
        self.set_resizable(False)
        
        
        # server frame
        
        self.vbox.set_spacing(5)

        self.server_frame = gtk.Frame("Server")
        self.vbox.pack_start(self.server_frame, False, True, 0)
                
        table = gtk.Table(3, 2)
        table.set_border_width(5)
        self.server_frame.add(table)
        
        label = gtk.Label(" Server address: ")
        label.set_alignment(0, 0.5)
        table.attach(label, 0, 1, 0, 1, gtk.FILL, gtk.FILL | gtk.EXPAND, 0, 0)
        
        self.server_address_entry = gtk.Entry()
        self.server_address_entry.set_text(self.server_address)
        self.server_address_entry.set_activates_default(True)
        table.attach(self.server_address_entry, 1, 2, 0, 1, gtk.FILL | gtk.EXPAND, gtk.FILL | gtk.EXPAND, 1, 1)
        
        label = gtk.Label(" Username: ")
        label.set_alignment(0, 0.5)
        table.attach(label, 0, 1, 1, 2, gtk.FILL, gtk.FILL | gtk.EXPAND, 0, 0)
        
        self.username_entry = gtk.Entry()
        self.username_entry.set_text(self.username)
        self.username_entry.set_activates_default(True)
        table.attach(self.username_entry, 1, 2, 1, 2, gtk.FILL | gtk.EXPAND, gtk.FILL | gtk.EXPAND, 1, 1)
        
        label = gtk.Label(" Password: ")
        label.set_alignment(0, 0.5)
        table.attach(label, 0, 1, 2, 3, gtk.FILL, gtk.FILL | gtk.EXPAND, 0, 0)
        
        self.password_entry = gtk.Entry()
        self.password_entry.set_visibility(False)
        self.password_entry.set_activates_default(True)
        table.attach(self.password_entry, 1, 2, 2, 3, gtk.FILL | gtk.EXPAND, gtk.FILL | gtk.EXPAND, 1, 1)
        
        
        # transport frame

        self.transport_frame = gtk.Frame(" Transport type ")
        self.vbox.pack_start(self.transport_frame, False, True, 0)

        vbox = gtk.VBox()
        vbox.set_border_width(5)
        self.transport_frame.add(vbox)
        
        self.rpc_smb_tcpip_radio_button = gtk.RadioButton(None, "RPC over SMB over TCP/IP")
        self.rpc_smb_tcpip_radio_button.set_active(self.transport_type == 0)
        vbox.pack_start(self.rpc_smb_tcpip_radio_button)
        
        self.rpc_tcpip_radio_button = gtk.RadioButton(self.rpc_smb_tcpip_radio_button, "RPC over TCP/IP")
        self.rpc_tcpip_radio_button.set_active(self.transport_type == 1)
        vbox.pack_start(self.rpc_tcpip_radio_button)
        
        self.localhost_radio_button = gtk.RadioButton(self.rpc_tcpip_radio_button, "Localhost")
        self.localhost_radio_button.set_active(self.transport_type == 2)
        vbox.pack_start(self.localhost_radio_button)
        
        
        # dialog buttons
        
        self.action_area.set_layout(gtk.BUTTONBOX_END)
        
        self.cancel_button = gtk.Button("Cancel", gtk.STOCK_CANCEL)
        self.add_action_widget(self.cancel_button, gtk.RESPONSE_CANCEL)
        
        self.connect_button = gtk.Button("Connect", gtk.STOCK_CONNECT)
        self.connect_button.set_flags(gtk.CAN_DEFAULT)
        self.add_action_widget(self.connect_button, gtk.RESPONSE_OK)
        
        self.set_default_response(gtk.RESPONSE_OK)
        
        
        # signals/events
        
        self.rpc_smb_tcpip_radio_button.connect("toggled", self.on_radio_button_toggled)
        self.rpc_tcpip_radio_button.connect("toggled", self.on_radio_button_toggled)
        self.localhost_radio_button.connect("toggled", self.on_radio_button_toggled)
        
    def update_sensitivity(self):
        server_required = not self.localhost_radio_button.get_active()
        
        self.server_address_entry.set_sensitive(server_required)
    
    def get_server_address(self):
        return self.server_address_entry.get_text().strip()
    
    def get_transport_type(self):
        if (self.rpc_smb_tcpip_radio_button.get_active()):
            return 0
        elif (self.rpc_tcpip_radio_button.get_active()):
            return 1
        elif (self.localhost_radio_button.get_active()):
            return 2
        else:
            return -1
    
    def get_username(self):
        return self.username_entry.get_text().strip()
    
    def get_password(self):
        return self.password_entry.get_text()
    
    def on_radio_button_toggled(self, widget):
        self.update_sensitivity()


#dialog = RegValueEditDialog(winreg.REG_BINARY)
#dialog.show_all()
#dialog.update_type_page_after_show()
#dialog.run()
#dialog.values_to_reg_value()
#dialog.hide()
#
#value = dialog.reg_value
#
##for line in value.get_interpreted_data():
##    print "[%s]" % line
#
#dialog = RegValueEditDialog(value.type, value)
#dialog.show_all()
#dialog.update_type_page_after_show()
#dialog.run()
