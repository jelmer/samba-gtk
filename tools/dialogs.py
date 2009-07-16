
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
            self.user = User("", "", "", 0x0000)
        else:
            self.brand_new = False
            self.user = user
        
        self.pipe_manager = pipe_manager
        self.create()
        
        self.update_sensitivity()
        self.user_to_values()
        
    def create(self):
        self.set_title(["Edit user", "New user"][self.user == None] + " " + self.user.username)
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

        self.must_change_password_check = gtk.CheckButton("_User Must Change Password at Next Logon")
        table.attach(self.must_change_password_check, 1, 2, 5, 6, gtk.FILL, 0, 0, 0)

        self.username_entry = gtk.Entry()
        table.attach(self.username_entry, 1, 2, 0, 1, gtk.FILL, 0, 0, 0)

        self.fullname_entry = gtk.Entry()
        table.attach(self.fullname_entry, 1, 2, 1, 2, gtk.FILL | gtk.EXPAND, 0, 0, 0)

        self.description_entry = gtk.Entry()
        table.attach(self.description_entry, 1, 2, 2, 3, gtk.FILL | gtk.EXPAND, 0, 0, 0)

        self.password_entry = gtk.Entry()
        self.password_entry.set_visibility(False)
        table.attach(self.password_entry, 1, 2, 3, 4, gtk.FILL | gtk.EXPAND, 0, 0, 0)
        
        self.confirm_password_entry = gtk.Entry()
        self.confirm_password_entry.set_visibility(False)
        table.attach(self.confirm_password_entry, 1, 2, 4, 5, gtk.FILL | gtk.EXPAND, 0, 0, 0)
        
        self.cannot_change_password_check = gtk.CheckButton("User Cannot Change Password")
        table.attach(self.cannot_change_password_check, 1, 2, 6, 7, gtk.FILL, 0, 0, 0)

        self.password_never_expires_check = gtk.CheckButton("Password Never Expires")
        table.attach(self.password_never_expires_check, 1, 2, 7, 8, gtk.FILL, 0, 0, 0)
        
        self.account_disabled_check = gtk.CheckButton("Account Disabled")
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
        table.attach(self.profile_path_entry, 1, 2, 0, 1, gtk.FILL | gtk.EXPAND, 0, 0, 0)

        self.logon_script_entry = gtk.Entry()
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
        
        self.add_group_button.connect("clicked", self.on_add_group_button_clicked)
        self.del_group_button.connect("clicked", self.on_del_group_button_clicked)
        self.existing_groups_tree_view.get_selection().connect("changed", self.on_existing_groups_tree_view_selection_changed)
        self.available_groups_tree_view.get_selection().connect("changed", self.on_available_groups_tree_view_selection_changed)
        self.map_homedir_drive_check.connect("toggled", self.on_map_homedir_drive_check_toggled)
        
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
        
        if (self.user.map_homedir_drive != None):
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
            self.user.map_homedir_drive = None

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

    def on_existing_groups_tree_view_selection_changed(self, widget):
        self.update_sensitivity()

    def on_available_groups_tree_view_selection_changed(self, widget):
        self.update_sensitivity()

    def on_map_homedir_drive_check_toggled(self, widget):
        self.update_sensitivity()


class GroupEditDialog(gtk.Dialog):
    
    def __init__(self, pipe_manager, group = None):
        super(GroupEditDialog, self).__init__()

        if (group == None):
            self.brand_new = True
            self.thegroup = Group("", "", 0x0000)
        else:
            self.brand_new = False
            self.thegroup = group
        
        self.sam_manager = pipe_manager
        self.create()
        
        self.group_to_values()
                
    def create(self):        
        self.set_title(["Edit group", "New group"][self.thegroup == None] + " " + self.thegroup.name)
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
        table.attach(self.name_entry, 1, 2, 0, 1, gtk.FILL, 0, 0, 0)

        self.description_entry = gtk.Entry()
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
        table.attach(self.exe_path_entry, 1, 2, 2, 3, gtk.FILL, 0, 0, 0)
        
        self.startup_type_combo = gtk.combo_box_new_text()
        self.startup_type_combo.append_text("Manual")
        self.startup_type_combo.append_text("Automatic")
        self.startup_type_combo.append_text("Disabled")
        table.attach(self.startup_type_combo, 1, 2, 3, 4, gtk.FILL, 0, 0, 0)

        self.start_params_entry = gtk.Entry()
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
        
        self.allow_interact_desktop_check = gtk.CheckButton("Allo_w service to interact with desktop")
        table.attach(self.allow_interact_desktop_check, 0, 2, 1, 2, gtk.FILL, 0, 20, 0)
        
        self.this_account_radio = gtk.RadioButton(self.local_account_radio, "_This account:")
        table.attach(self.this_account_radio, 0, 1, 2, 3, gtk.FILL, 0, 0, 0)
        
        self.account_entry = gtk.Entry()
        table.attach(self.account_entry, 1, 2, 2, 3, gtk.FILL, 0, 0, 0)
        
        self.browse_button = gtk.Button("Browse...")
        table.attach(self.browse_button, 2, 3, 2, 3, 0, 0, 0, 0)
        
        label = gtk.Label("Password:")
        label.set_alignment(0, 0.5)
        table.attach(label, 0, 1, 3, 4, gtk.FILL, 0, 20, 0)
        
        self.password_entry = gtk.Entry()
        self.password_entry.set_visibility(False)
        table.attach(self.password_entry, 1, 2, 3, 4, gtk.FILL, 0, 0, 0)
        
        label = gtk.Label("Confirm password:")
        label.set_alignment(0, 0.5)
        table.attach(label, 0, 1, 4, 5, gtk.FILL, 0, 20, 0)
        
        self.confirm_password_entry = gtk.Entry()
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
        column.add_attribute(renderer, "text", 0)
        
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

        
    def check_for_problems(self):
#        if (len(self.name_entry.get_text()) == 0):
#            return "Name may not be empty!"
#
#        if (self.brand_new):
#            for group in self.pipe_manager.group_list:
#                if (group.name == self.name_entry.get_text()):
#                    return "Choose another group name, this one already exists!"

        return None

    def service_to_values(self):
        if (self.service == None):
            raise Exception("service not set")
        
#        self.name_entry.set_text(self.service.name)
#        self.name_entry.set_sensitive(len(self.service.name) == 0)
#        self.description_entry.set_text(self.service.description)
        
    def values_to_service(self):
        if (self.service == None):
            raise Exception("service not set")
        
#        self.service.name = self.name_entry.get_text()
#        self.service.description = self.description_entry.get_text()
