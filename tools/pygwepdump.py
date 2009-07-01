#!/usr/bin/python

import gtk, gobject
import sambagtk
from samba.dcerpc import mgmt, epmapper


class NewJobDialog(gtk.Dialog):

    def __init__(self):
        super(NewJobDialog, self).__init__()
        self.create()
        
    def create(self):
        self.set_title("New Job")
        self.set_border_width(5)
        
        frame = gtk.Frame("Moment")
        self.vbox.pack_start(frame, True, True, 0)
        
        table = gtk.Table(4, 2, False)
        frame.add(table)
    
        label = gtk.Label("Time:")
        label.set_alignment(0, 0.5)
        table.attach(label, 0, 1, 1, 2, gtk.FILL, 0, 0, 0)

        self.day_calendar = gtk.Calendar()
        self.day_calendar.set_display_options(gtk.CALENDAR_SHOW_HEADING | gtk.CALENDAR_SHOW_DAY_NAMES)
        table.attach(self.day_calendar, 1, 2, 0, 1, gtk.EXPAND | gtk.FILL, gtk.FILL, 0, 0)

        label = gtk.Label("Date")
        label.set_alignment(0, 0.5)
        table.attach(label, 0, 1, 0, 1, gtk.FILL | gtk.EXPAND, 0, 0, 0)

        self.time_entry = gtk.Entry()
        table.attach(self.time_entry, 1, 2, 1, 2, gtk.FILL | gtk.EXPAND, 0, 0, 0)

        self.repeat_weekly_check = gtk.CheckButton("Repeat weekly")
        table.attach(self.repeat_weekly_check, 0, 1, 2, 3, gtk.FILL, 0, 0, 0)
        
        self.repeat_weekly_entry = gtk.Entry()
        table.attach(self.repeat_weekly_entry, 1, 2, 2, 3, gtk.FILL | gtk.EXPAND, 0, 0, 0)
        
        self.repeat_monthly_check = gtk.CheckButton("Repeat monthly")
        table.attach(self.repeat_monthly_check, 0, 1, 3, 4, gtk.FILL, 0, 0, 0)
        
        self.repeat_monthly_entry = gtk.Entry()
        table.attach(self.repeat_monthly_entry, 1, 2, 3, 4, gtk.FILL | gtk.EXPAND, 0, 0, 0)
        
        frame = gtk.Frame("Command")
        self.vbox.pack_start(frame, True, True, 0)
        
        hbox = gtk.HBox(False, 0)
        frame.add(hbox)
        
        label = gtk.Label("Command to execute")
        hbox.pack_start(label, True, True, 0)
        
        self.command_entry = gtk.Entry()
        hbox.pack_start(self.command_entry, True, True, 0)
        
        self.action_area.set_layout(gtk.BUTTONBOX_END)
        
        self.cancel_button = gtk.Button("Cancel", gtk.STOCK_CANCEL)
        self.cancel_button.set_flags(gtk.CAN_DEFAULT)
        self.add_action_widget(self.cancel_button, gtk.RESPONSE_CANCEL)

        self.ok_button = gtk.Button("OK", gtk.STOCK_OK)
        self.ok_button.set_flags(gtk.CAN_DEFAULT)
        self.add_action_widget(self.ok_button, gtk.RESPONSE_OK)
        
        self.repeat_weekly_check.connect("toggled", self.on_repeat_weekly_check_toggled)
        self.repeat_monthly_check.connect("toggled", self.on_repeat_monthly_check_toggled)
        
    def on_repeat_weekly_check_toggled(self, widget):
        self.repeat_weekly_entry.set_sensitive(widget.get_active())
        
    def on_repeat_monthly_check_toggled(self, widget):
        self.repeat_monthly_entry.set_sensitive(widget.get_active())


class EndpointWindow(gtk.Window):

    def __init__(self):
        super(EndpointWindow, self).__init__()
        self.create()
        self.update_sensitivity(False)
        
    def create(self):
        
        
        # main window        

        accel_group = gtk.AccelGroup()
        
        self.set_title("Endpoint Mapper Viewer")
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

        
        self.help_item = gtk.MenuItem("_Help")
        menubar.add(self.help_item)

        help_menu = gtk.Menu()
        self.help_item.set_submenu(help_menu)

        self.about_item = gtk.MenuItem("_About")
        help_menu.add(self.about_item)


        # endpoint list
        
        hbox = gtk.HBox(False, 0)
        vbox.pack_start(hbox)
        
        scrolledwindow = gtk.ScrolledWindow(None, None)
        hbox.pack_start(scrolledwindow, True, True, 0)
        
        self.endpoints_tree_view = gtk.TreeView()
        
        column = gtk.TreeViewColumn()
        column.set_title("Name")
        renderer = gtk.CellRendererText()
        column.pack_start(renderer, True)
        self.endpoints_tree_view.append_column(column)
        column.add_attribute(renderer, "text", 0)
        
        column = gtk.TreeViewColumn()
        column.set_title("Binding String")
        renderer = gtk.CellRendererText()
        column.pack_start(renderer, True)
        self.endpoints_tree_view.append_column(column)
        column.add_attribute(renderer, "text", 1)
        
        self.endpoints_store = gtk.ListStore(gobject.TYPE_STRING, gobject.TYPE_STRING, gobject.TYPE_POINTER)
        self.endpoints_tree_view.set_model(self.endpoints_store)
        scrolledwindow.add(self.endpoints_tree_view)


        # interface

        vbox = gtk.VBox(False, 0)
        hbox.pack_start(vbox)
        
        frame = gtk.Frame("Interface")
        vbox.pack_start(frame)
        
        vbox2 = gtk.VBox(False, 0)
        frame.add(vbox2)
        
        self.iface_uuid_label = gtk.Label("")
        vbox2.pack_start(self.iface_uuid_label)

        self.iface_version_label = gtk.Label("")
        vbox2.pack_start(self.iface_version_label)
        
        self.iface_name_label = gtk.Label("")
        vbox2.pack_start(self.iface_name_label)
        
        frame = gtk.Frame("Statistics")
        vbox.pack_start(frame)
        
        table = gtk.Table(4, 2, True)
        frame.add(table)

        table.attach(gtk.Label("Calls In: "), 0, 1, 0, 1)
        self.calls_in_label = gtk.Label("")
        table.attach(self.calls_in_label, 1, 2, 0, 1)
        
        table.attach(gtk.Label("Calls Out: "), 0, 1, 1, 2)
        self.calls_out_label = gtk.Label("")
        table.attach(self.calls_out_label, 1, 2, 1, 2)
        
        table.attach(gtk.Label("Packets In: "), 0, 1, 2, 3)
        self.packets_in_label = gtk.Label("")
        table.attach(self.packets_in_label, 1, 2, 2, 3)
        
        table.attach(gtk.Label("Packets Out: "), 0, 1, 3, 4)
        self.packets_out_label = gtk.Label("")
        table.attach(self.packets_out_label, 1, 2, 3, 4)
        
        frame = gtk.Frame("Authentication")
        vbox.pack_start(frame)
        
        self.principal_names_tree_view = gtk.TreeView()

        column = gtk.TreeViewColumn()
        column.set_title("Protocol")
        renderer = gtk.CellRendererText()
        column.pack_start(renderer, True)
        self.principal_names_tree_view.append_column(column)
        column.add_attribute(renderer, "text", 0)
        
        column = gtk.TreeViewColumn()
        column.set_title("Principal Name")
        renderer = gtk.CellRendererText()
        column.pack_start(renderer, True)
        self.principal_names_tree_view.append_column(column)
        column.add_attribute(renderer, "text", 1)
        
        frame.add(self.principal_names_tree_view)

        self.principal_names_store = gtk.ListStore(gobject.TYPE_STRING, gobject.TYPE_STRING, gobject.TYPE_STRING, gobject.TYPE_POINTER)
        self.principal_names_tree_view.set_model(self.principal_names_store)
        
        
        # status bar
        
        self.statusbar = gtk.Statusbar()
        vbox.pack_start(self.statusbar, False, False, 0)
        
        
        # signals/events
        
        self.connect_item.connect("activate", self.on_connect_item_activate)
        self.disconnect_item.connect("activate", self.on_disconnect_item_activate)
        self.quit_item.connect("activate", self.on_quit_item_activate)
        
        self.refresh_item.connect("activate", self.on_refresh_item_activate)

        self.about_item.connect("activate", self.on_about_item_activate)        
        
        self.endpoints_tree_view.get_selection().set_select_function(self.on_endpoints_tree_view_select, None, None)

        self.add_accel_group(accel_group)

    def set_status(self, message):
        self.statusbar.pop(0)
        self.statusbar.push(0, message)

    def update_sensitivity(self, is_connected):
        self.connect_item.set_sensitive(not is_connected)
        self.disconnect_item.set_sensitive(is_connected)
        self.refresh_item.set_sensitive(is_connected)

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

    def on_about_item_activate(self, widget):
        aboutwin = sambagtk.AboutDialog("PyGWEPDump")
        aboutwin.run()
        aboutwin.destroy()

    def on_endpoints_tree_view_select(self, widget):
        None


win = EndpointWindow()
win.show_all()
gtk.main()
