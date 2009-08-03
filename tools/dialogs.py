
import sys
import os.path
import gtk
import gobject

from objects import User
from objects import Group
from objects import Service


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
        
        if (not self.brand_new):
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
        
        self.sam_manager = pipe_manager
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
            for group in self.sam_manager.group_list:
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
        
    def __init__(self, pipe_manager, service = None):
        super(ServiceEditDialog, self).__init__()

        if (service == None):
            self.brand_new = True
            self.service = Service("", "", False, service.STARTUP_TYPE_NORMAL)
        else:
            self.brand_new = False
            self.service = service
        
        self.pipe_manager = pipe_manager
        self.create()
        
        self.service_to_values()
        self.update_sensitivity()

    def create(self):  
        self.set_title("Edit service " + self.service.name)
        self.set_border_width(5)
        self.set_icon_from_file(os.path.join(sys.path[0], "images", "service.png"))
        self.set_resizable(False)
        self.set_size_request(520, 400)
        
        notebook = gtk.Notebook()
        self.vbox.pack_start(notebook, True, True, 0)


        # general tab

        table = gtk.Table(5, 2, False)
        table.set_border_width(5)
        table.set_col_spacings(5)
        table.set_row_spacings(5)
        notebook.add(table)

        label = gtk.Label("Name")
        label.set_alignment(0, 0.5)
        table.attach(label, 0, 1, 0, 1, gtk.FILL, 0, 5, 0)

        label = gtk.Label("Description")
        label.set_alignment(0, 0.5)
        table.attach(label, 0, 1, 1, 2, gtk.FILL, 0, 5, 0)

        label = gtk.Label("Path to executable")
        label.set_alignment(0, 0.5)
        table.attach(label, 0, 1, 2, 3, gtk.FILL, 0, 5, 0)

        label = gtk.Label("Startup type")
        label.set_alignment(0, 0.5)
        table.attach(label, 0, 1, 3, 4, gtk.FILL, 0, 5, 0)

        label = gtk.Label("Start parameters")
        label.set_alignment(0, 0.5)
        table.attach(label, 0, 1, 4, 5, gtk.FILL, 0, 5, 0)

        self.name_label = gtk.Label()
        self.name_label.set_alignment(0, 0.5)
        table.attach(self.name_label, 1, 2, 0, 1, gtk.FILL, 0, 0, 5)
        
        scrolledwindow = gtk.ScrolledWindow(None, None)
        scrolledwindow.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        scrolledwindow.set_shadow_type(gtk.SHADOW_IN)
        scrolledwindow.set_size_request(0, 50)
        table.attach(scrolledwindow, 1, 2, 1, 2, gtk.FILL | gtk.EXPAND, gtk.FILL, 0, 5)
        
        self.description_text_view = gtk.TextView()
        self.description_text_view.set_editable(False)
        self.description_text_view.set_wrap_mode(gtk.WRAP_WORD)
        scrolledwindow.add(self.description_text_view)

        self.exe_path_entry = gtk.Entry()
        self.exe_path_entry.set_editable(False)
        table.attach(self.exe_path_entry, 1, 2, 2, 3, gtk.FILL, 0, 0, 0)
        
        self.startup_type_combo = gtk.combo_box_new_text()
        self.startup_type_combo.append_text("Manual")
        self.startup_type_combo.append_text("Automatic")
        self.startup_type_combo.append_text("Disabled")
        table.attach(self.startup_type_combo, 1, 2, 3, 4, gtk.FILL, 0, 0, 0)

        self.start_params_entry = gtk.Entry()
        self.start_params_entry.set_activates_default(True)
        table.attach(self.start_params_entry, 1, 2, 4, 5, gtk.FILL, 0, 0, 0)
        
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
        
        self.browse_button = gtk.Button("Browse...")
        table.attach(self.browse_button, 2, 3, 2, 3, 0, 0, 0, 0)
        
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
        
        label = gtk.Label("You can enable or disable this service for the hardware profiles listed below :")
        table.attach(label, 0, 3, 5, 6, 0, 0, 0, 5)
        
        scrolledwindow = gtk.ScrolledWindow(None, None)
        scrolledwindow.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        scrolledwindow.set_shadow_type(gtk.SHADOW_IN)
        table.attach(scrolledwindow, 0, 3, 6, 7, gtk.FILL | gtk.EXPAND, gtk.FILL | gtk.EXPAND, 0, 0)
        
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
        table.attach(hbox, 0, 1, 7, 8, 0, 0, 0, 0)
        
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
        self.profiles_tree_view.get_selection().connect("changed", self.on_profiles_tree_view_selection_changed)
        self.enable_button.connect("clicked", self.on_enable_button_click)
        self.disable_button.connect("clicked", self.on_disable_button_click)

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
        self.browse_button.set_sensitive(not local_account)
        
        profile = self.get_selected_profile()
        if (profile == None):
            self.enable_button.set_sensitive(False)
            self.disable_button.set_sensitive(False)
        else:
            self.enable_button.set_sensitive(not profile[1])
            self.disable_button.set_sensitive(profile[1])
        
    def service_to_values(self):
        if (self.service == None):
            raise Exception("service not set")
 
        self.name_label.set_text(self.service.name)
        self.description_text_view.get_buffer().set_text(self.service.description)
        self.exe_path_entry.set_text(self.service.path_to_exe)
        self.startup_type_combo.set_active(self.service.startup_type)
        self.start_params_entry.set_text(self.service.start_params)
        
        if (self.service.account == None):
            self.local_account_radio.set_active(True)
            self.allow_desktop_interaction_check.set_active(self.service.allow_desktop_interaction)
        else:
            self.this_account_radio.set_active(True)
            self.account_entry.set_text(self.service.account)
            self.password_entry.set_text(self.service.account_password)
            self.confirm_password_entry.set_text(self.service.account_password)
            
        self.refresh_profiles_tree_view()
        
    def values_to_service(self):
        if (self.service == None):
            raise Exception("service not set")
        
        self.service.startup_type = self.startup_type_combo.get_active()
        self.service.start_params = self.start_params_entry.get_text()
        
        if (self.local_account_radio.get_active()):
            self.service.account = None
            self.service.account_password = None
            self.service.allow_desktop_interaction = self.allow_desktop_interaction_check.get_active()
        else:
            self.service.account = self.account_entry.get_text()
            self.service.account_password = self.password_entry.get_text()
            
        del self.service.hw_profile_list[:]
        
        iter = self.profiles_store.get_iter_first()
        while (iter != None):
            name = self.profiles_store.get_value(iter, 0)
            enabled = self.profiles_store.get_value(iter, 1)
            self.service.hw_profile_list.append([name, [False, True][enabled == "Enabled"]])
            iter = self.profiles_store.iter_next(iter)

    def refresh_profiles_tree_view(self):
        (model, paths) = self.profiles_tree_view.get_selection().get_selected_rows()
        
        self.profiles_store.clear()
        for profile in self.service.hw_profile_list:
            self.profiles_store.append((profile[0], ["Disabled", "Enabled"][profile[1]]))
        
        if (len(paths) > 0):
            self.profiles_tree_view.get_selection().select_path(paths[0])

    def get_selected_profile(self):
        (model, iter) = self.profiles_tree_view.get_selection().get_selected()
        if (iter == None): # no selection
            return None
        else:
            name = model.get_value(iter, 0)
            return [profile for profile in self.service.hw_profile_list if profile[0] == name][0]

    def on_local_account_radio_clicked(self, widget):
        self.update_sensitivity()

    def on_enable_button_click(self, widget):
        profile = self.get_selected_profile()
        if (profile == None): # no selection
            return 
        
        profile[1] = True
        self.refresh_profiles_tree_view()
    
    def on_disable_button_click(self, widget):
        profile = self.get_selected_profile()
        if (profile == None): # no selection
            return 
        
        profile[1] = False
        self.refresh_profiles_tree_view()

    def on_profiles_tree_view_selection_changed(self, widget):
        self.update_sensitivity()


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
        
        self.server_address_entry   .set_sensitive(server_required)
    
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
#    
    def on_radio_button_toggled(self, widget):
        self.update_sensitivity()
    