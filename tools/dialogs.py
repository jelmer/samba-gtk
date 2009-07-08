
import gtk
import gobject

from objects import User


class UserEditDialog(gtk.Dialog):
    
    def __init__(self, sam_manager, user):
        super(UserEditDialog, self).__init__()
        
        self.create()
        self.sam_manager = sam_manager
        self.update_sensitivity()
        self.get_from_user(user)
        
    def create(self):
        self.set_title("Edit User")
        self.set_border_width(5)
        
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
        self.add_action_widget(self.apply_button, gtk.RESPONSE_APPLY)
        
        self.ok_button = gtk.Button("OK", gtk.STOCK_OK)
        self.ok_button.set_flags(gtk.CAN_DEFAULT)
        self.add_action_widget(self.ok_button, gtk.RESPONSE_OK)
        
        
        # signals/events
        
        self.add_group_button.connect("clicked", self.on_add_group_button_clicked)
        self.del_group_button.connect("clicked", self.on_del_group_button_clicked)
        self.existing_groups_tree_view.get_selection().connect("changed", self.on_existing_groups_tree_view_selection_changed)
        self.available_groups_tree_view.get_selection().connect("changed", self.on_available_groups_tree_view_selection_changed)
        self.map_homedir_drive_check.connect("toggled", self.on_map_homedir_drive_check_toggled)
        
    def check_for_problems(self):
        if (self.password_entry.get_text() != self.confirm_password_entry.get_text()):
            return "The password was not correctly confirmed. Please ensure that the password and confirmation match exactly."

    def update_sensitivity(self):
        existing_selected = (self.existing_groups_tree_view.get_selection().count_selected_rows() > 0)
        available_selected = (self.available_groups_tree_view.get_selection().count_selected_rows() > 0)
        
        self.add_group_button.set_sensitive(available_selected)
        self.del_group_button.set_sensitive(existing_selected)

    def get_from_user(self, user):
        self.username_entry.set_text(user.username)
        self.username_entry.set_editable(len(user.username) == 0)
        self.fullname_entry.set_text(user.fullname)
        self.description_entry.set_text(user.description)
        self.must_change_password_check.set_active(user.must_change_password)
        self.cannot_change_password_check.set_active(user.cannot_change_password)
        self.password_never_expires_check.set_active(user.password_never_expires)
        self.account_disabled_check.set_active(user.account_disabled)
        self.account_locked_out_check.set_active(user.account_locked_out)
        self.profile_path_entry.set_text(user.profile_path)
        self.logon_script_entry.set_text(user.logon_script)
        self.homedir_path_entry.set_text(user.homedir_path)
        
        if (user.map_homedir_drive != None):
            self.map_homedir_drive_check.set_active(True)
            self.map_homedir_drive_combo.set_active(user.map_homedir_drive)
            self.map_homedir_drive_combo.set_sensitive(True)
        else:
            self.map_homedir_drive_check.set_active(False)
            self.map_homedir_drive_combo.set_active(-1)
            self.map_homedir_drive_combo.set_sensitive(False)
            
        self.existing_groups_store.clear()
        for group in user.group_list:
            self.existing_groups_store.append([group.name])
        
        self.available_groups_store.clear()
        for group in self.sam_manager.group_list:
            if (not group in user.group_list):
                self.available_groups_store.append([group.name])
    
    def set_to_user(self, user):
        user.username = self.username_entry.get_text()
        user.fullname = self.fullname_entry.get_text()
        user.description = self.description_entry.get_text()
        user.password = (None, self.password_entry.get_text())[len(self.password_entry.get_text()) > 0]
        user.must_change_password = self.must_change_password_check.get_active()
        user.cannot_change_password = self.cannot_change_password_check.get_active()
        user.password_never_expires = self.password_never_expires_check.get_active()
        user.account_disabled = self.account_disabled_check.get_active()
        user.account_locked_out = self.account_locked_out_check.get_active()
        user.profile_path = self.profile_path_entry.get_text()
        user.logon_script = self.logon_script_entry.get_text()
        user.homedir_path = self.homedir_path_entry.get_text()
        
        if (self.map_homedir_drive_check.get_active()) and (self.map_homedir_drive_combo.get_active() != -1):
            user.map_homedir_drive = self.map_homedir_drive_combo.get_active()
        else:
            user.map_homedir_drive = None

        del user.group_list[:]
        
        iter = self.existing_groups_store.get_iter_first()
        while (iter != None):
            value = self.existing_groups_store.get_value(iter, 0)
            user.group_list.append([group for group in self.sam_manager.group_list if group.name == value][0])
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
        self.map_homedir_drive_combo.set_sensitive(self.map_homedir_drive_check.get_active())
