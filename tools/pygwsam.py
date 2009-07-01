#!/usr/bin/python

import gtk, gobject
import sambagtk
from samba.dcerpc import mgmt, epmapper


class UserEditDialog(gtk.Dialog):
    
    def __init__(self):
        super(UserEditDialog, self).__init__()
        self.create()
        
    def create(self):
        self.set_title("Edit User")
        self.set_border_width(5)
        
        notebook = gtk.Notebook()
        self.vbox.pack_start(notebook, True, True, 0)
        
        table = gtk.Table (10, 2, False)
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

        self.check_must_change = gtk.CheckButton("_User Must Change Password at Next Logon")
        table.attach(self.check_must_change, 1, 2, 5, 6, gtk.FILL, 0, 0, 0)

        self.label_username = gtk.Label("")
        table.attach(self.label_username, 1, 2, 0, 1, gtk.FILL, 0, 0, 0)

        self.entry_fullname = gtk.Entry()
        table.attach(self.entry_fullname, 1, 2, 1, 2, gtk.FILL | gtk.EXPAND, 0, 0, 0)

        self.entry_description = gtk.Entry()
        table.attach(self.entry_description, 1, 2, 2, 3, gtk.FILL | gtk.EXPAND, 0, 0, 0)

        self.entry_password = gtk.Entry()
        table.attach(self.entry_password, 1, 2, 3, 4, gtk.FILL | gtk.EXPAND, 0, 0, 0)
        
        self.entry_confirm_password = gtk.Entry()
        table.attach(self.entry_confirm_password, 1, 2, 4, 5, gtk.FILL | gtk.EXPAND, 0, 0, 0)
        
        self.cannot_change_password_check = gtk.CheckButton("User Cannot Change Password")
        table.attach(self.cannot_change_password_check, 1, 2, 6, 7, gtk.FILL, 0, 0, 0)

        self.password_never_expires_check = gtk.CheckButton("Password Never Expires")
        table.attach(self.password_never_expires_check, 1, 2, 7, 8, gtk.FILL, 0, 0, 0)
        
        self.account_disabled_check = gtk.CheckButton("Account Disabled")
        table.attach(self.account_disabled_check, 1, 2, 8, 9, gtk.FILL, 0, 0, 0)

        self.account_locked_out_check = gtk.CheckButton("Account Locked Out")
        table.attach(self.account_locked_out_check, 1, 2, 9, 10, gtk.FILL, 0, 0, 0)

        notebook.set_tab_label(notebook.get_nth_page(0), gtk.Label("Main"))
        
        hbox = gtk.HBox(False, 0)
        notebook.add(hbox)
        
        scrolledwindow = gtk.ScrolledWindow(None, None)
        hbox.pack_start(scrolledwindow, True, True, 0)
        
        self.existing_groups_tree_view = gtk.TreeView()
        scrolledwindow.add(self.existing_groups_tree_view)
        
        vbox = gtk.VBox(True, 0)
        hbox.pack_start(vbox, True, True, 0)
        
        self.add_group_button = gtk.Button("Add", gtk.STOCK_ADD)
        vbox.pack_start(self.add_group_button, False, False, 0)
        
        self.del_group_button = gtk.Button("Remove", gtk.STOCK_REMOVE)
        vbox.pack_start(self.del_group_button, False, False, 0)
        
        scrolledwindow = gtk.ScrolledWindow(None, None)
        hbox.pack_start(scrolledwindow, True, True, 0)
        
        self.available_groups_tree_view = gtk.TreeView()
        scrolledwindow.add(self.available_groups_tree_view)
        
        notebook.set_tab_label(notebook.get_nth_page(1), gtk.Label("Groups"))
        
        vbox = gtk.VBox(False, 0)
        notebook.add(vbox)
        
        frame = gtk.Frame("User Profiles")
        vbox.pack_start(frame, True, True, 0)
        
        table = gtk.Table(2, 2, False)
        frame.add(table)
        
        label = gtk.Label("User Profile Path:")
        label.set_alignment(0, 0.5)
        table.attach(label, 0, 1, 0, 1, gtk.FILL, 0, 0, 0)

        label = gtk.Label("Logon Script Name:")
        label.set_alignment(0, 0.5)
        table.attach(label, 0, 1, 1, 2, gtk.FILL, 0, 0, 0)

        self.profile_path_entry = gtk.Entry()
        table.attach(self.profile_path_entry, 1, 2, 0, 1, gtk.FILL | gtk.EXPAND, 0, 0, 0)

        self.script_name_entry = gtk.Entry()
        table.attach(self.script_name_entry, 1, 2, 1, 2, gtk.FILL | gtk.EXPAND, 0, 0, 0)
        
        frame = gtk.Frame("Home Directory")
        vbox.pack_start(frame, True, True, 0)

        table = gtk.Table(2, 2, False)
        frame.add(table)

        label = gtk.Label("Path")
        label.set_alignment(0, 0.5)
        table.attach(label, 0, 1, 0, 1, gtk.FILL, 0, 0, 0)
        
        self.home_dir_entry = gtk.Entry()
        table.attach(self.home_dir_entry, 1, 2, 0, 1, gtk.FILL | gtk.EXPAND, 0, 0, 0)
        
        self.check_map_drive = gtk.CheckButton("Map homedir to drive")
        table.attach(self.check_map_drive, 0, 1, 1, 2, gtk.FILL, 0, 0, 0)
        
        self.home_drive_combo = gtk.combo_box_new_text()
        table.attach(self.home_drive_combo, 1, 2, 1, 2, gtk.FILL, gtk.FILL, 0, 0)
        
        for i in range(ord('Z') - ord('A') + 1):
            self.home_drive_combo.append_text(chr(i + ord('A')) + ':')

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


class SAMWindow(gtk.Window):

    def __init__(self):
        super(SAMWindow, self).__init__()
        self.create()
        self.update_sensitivity(False)
        
    def create(self):
        
        
        # main window        

        accel_group = gtk.AccelGroup()
        
        self.set_title("User Management")
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
        
        self.connect_item = gtk.ImageMenuItem(gtk.STOCK_CONNECT, accel_group)
        file_menu.add(self.connect_item)
        
        self.disconnect_item = gtk.ImageMenuItem(gtk.STOCK_DISCONNECT, accel_group)
        self.disconnect_item.set_sensitive(False)
        file_menu.add(self.disconnect_item)
        
        self.sel_domain_item = gtk.MenuItem("_Select Domain")
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
        
        
        self.user_item = gtk.MenuItem("_User")
        menubar.add(self.user_item)
        
        user_menu = gtk.Menu()
        self.user_item.set_submenu(user_menu)

        self.new_item = gtk.ImageMenuItem(gtk.STOCK_NEW, accel_group)
        self.new_item.set_sensitive(False)
        user_menu.add(self.new_item)

        self.delete_item = gtk.ImageMenuItem(gtk.STOCK_DELETE, accel_group)
        self.delete_item.set_sensitive(False)
        user_menu.add(self.delete_item)

        self.edit_item = gtk.ImageMenuItem(gtk.STOCK_EDIT, accel_group)
        self.edit_item.set_sensitive(False)
        user_menu.add(self.edit_item)

        
        self.policies_item = gtk.MenuItem("_Policies")
        menubar.add(self.policies_item)

        policies_menu = gtk.Menu()
        self.policies_item.set_submenu(policies_menu)
        
        self.account_item = gtk.MenuItem("_Account...")
        self.account_item.set_sensitive(False)
        policies_menu.add(self.account_item)
        
        self.user_rights_item = gtk.MenuItem("_User Rights...")
        self.user_rights_item.set_sensitive(False)
        policies_menu.add(self.user_rights_item)

        self.audit_item = gtk.MenuItem("A_udit...")
        self.audit_item.set_sensitive(False)
        policies_menu.add(self.audit_item)

        menu_separator_item = gtk.SeparatorMenuItem()
        menu_separator_item.set_sensitive(False)
        policies_menu.add(menu_separator_item)
        
        self.trust_relations_item = gtk.MenuItem("_Trust relations")
        self.trust_relations_item.set_sensitive(False)
        policies_menu.add(self.trust_relations_item)
        
        
        self.help_item = gtk.MenuItem("_Help")
        menubar.add(self.help_item)

        help_menu = gtk.Menu()
        self.help_item.set_submenu(help_menu)

        self.about_item = gtk.MenuItem("_About")
        help_menu.add(self.about_item)
        
        
        # user list
        
        vpaned = gtk.VPaned()
        vbox.pack_start(vpaned, True, True, 0)
                
        scrolledwindow = gtk.ScrolledWindow(None, None)
        vpaned.pack1(scrolledwindow, False, True)
        
        self.user_tree_view = gtk.TreeView()
        scrolledwindow.add(self.user_tree_view)
        
        column = gtk.TreeViewColumn()
        column.set_title("Name")
        renderer = gtk.CellRendererText()
        column.pack_start(renderer, True)
        self.user_tree_view.append_column(column)
        column.add_attribute(renderer, "text", 0)
                
        column = gtk.TreeViewColumn()
        column.set_title("Description")
        renderer = gtk.CellRendererText()
        column.pack_start(renderer, True)
        self.user_tree_view.append_column(column)
        column.add_attribute(renderer, "text", 1)
        
        column = gtk.TreeViewColumn()
        column.set_title("RID")
        renderer = gtk.CellRendererText()
        column.pack_start(renderer, True)
        self.user_tree_view.append_column(column)
        column.add_attribute(renderer, "text", 1)
        
        self.users_store = gtk.ListStore(gobject.TYPE_STRING, gobject.TYPE_STRING, gobject.TYPE_INT)
        self.user_tree_view.set_model(self.users_store)


        # group list

        scrolledwindow = gtk.ScrolledWindow(None, None)
        vpaned.pack2(scrolledwindow, True, True)
        
        self.group_list_view = gtk.TreeView()
        scrolledwindow.add(self.group_list_view)
        
        column = gtk.TreeViewColumn()
        column.set_title("Name")
        renderer = gtk.CellRendererText()
        column.pack_start(renderer, True)
        self.group_list_view.append_column(column)
        column.add_attribute(renderer, "text", 0)
                
        column = gtk.TreeViewColumn()
        column.set_title("Description")
        renderer = gtk.CellRendererText()
        column.pack_start(renderer, True)
        self.group_list_view.append_column(column)
        column.add_attribute(renderer, "text", 1)
        
        column = gtk.TreeViewColumn()
        column.set_title("RID")
        renderer = gtk.CellRendererText()
        column.pack_start(renderer, True)
        self.group_list_view.append_column(column)
        column.add_attribute(renderer, "text", 1)

        self.groups_store = gtk.ListStore(gobject.TYPE_STRING, gobject.TYPE_STRING, gobject.TYPE_INT)
        self.group_list_view.set_model(self.groups_store)


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
        
        self.account_item.connect("activate", self.on_account_item_activate)
        self.user_rights_item.connect("activate", self.on_user_rights_item_activate)
        self.audit_item.connect("activate", self.on_audit_item_activate)
        self.trust_relations_item.connect("activate", self.on_trust_relations_item_activate)
        
        self.about_item.connect("activate", self.on_about_item_activate)
        
        self.add_accel_group(accel_group)

    def set_status(self, message):
        self.statusbar.pop(0)
        self.statusbar.push(0, message)

    def update_sensitivity(self, is_connected):
        self.connect_item.set_sensitive(not is_connected)
        self.disconnect_item.set_sensitive(is_connected)
        self.sel_domain_item.set_sensitive(is_connected)
        self.refresh_item.set_sensitive(is_connected)
        self.new_item.set_sensitive(is_connected)
        self.delete_item.set_sensitive(is_connected)
        self.edit_item.set_sensitive(is_connected)
        self.account_item.set_sensitive(is_connected)
        self.user_rights_item.set_sensitive(is_connected)
        self.audit_item.set_sensitive(is_connected)
        self.trust_relations_item.set_sensitive(is_connected)

    def on_self_delete(self, widget, event):
        gtk.main_quit()
        return False

    def on_connect_item_activate(self, widget):
        self.update_sensitivity(True)

    def on_disconnect_item_activate(self, widget):
        self.update_sensitivity(False)
    
    def on_sel_domain_item_activate(self, widget):
        None

    def on_quit_item_activate(self, widget):
        self.on_self_delete(None, None)
    
    def on_refresh_item_activate(self, widget):
        None

    def on_new_item_activate(self, widget):
        None

    def on_delete_item_activate(self, widget):
        None

    def on_edit_item_activate(self, widget):
        None

    def on_account_item_activate(self, widget):
        None
    
    def on_user_rights_item_activate(self, widget):
        None
    
    def on_audit_item_activate(self, widget):
        None
    
    def on_trust_relations_item_activate(self, widget):
        None
    
    def on_about_item_activate(self, widget):
        aboutwin = sambagtk.AboutDialog("PyGWSAM")
        aboutwin.run()
        aboutwin.destroy()

main_window = SAMWindow()
main_window.show_all()
gtk.main()
