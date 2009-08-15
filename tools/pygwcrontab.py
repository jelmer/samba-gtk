#!/usr/bin/python

import sys
import os.path
import traceback

import gobject
import gtk

from samba import credentials
from samba.dcerpc import atsvc

from objects import Task

from dialogs import ATSvcConnectDialog
from dialogs import TaskEditDialog
from dialogs import AboutDialog


class ATSvcPipeManager:
    
    def __init__(self, server_address, transport_type, username, password):
        self.task_list = []
        
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
        
        self.pipe = atsvc.atsvc(binding % (server_address), credentials = creds)

    def close(self):
        None # apparently there's no .Close() method for this pipe
            
    def fetch_tasks(self):
        del self.task_list[:]
        
        (ctr, total, resume) = self.pipe.JobEnum(unicode(self.pipe.server_name), atsvc.enum_ctr(), 1000000, 0)
        if (total > 0):
            for info in ctr.first_entry:
                task = self.job_info_to_task(info)
                self.task_list.append(task)

    def add_task(self, task):
        job_id = self.pipe.JobAdd(unicode(self.pipe.server_name), self.task_to_job_info(task))
        if (job_id == 0):
            raise Exception("invalid task information")
        
        task.id = job_id
        self.task_list.append(task)

    def update_task(self, task):
        job_id = self.pipe.JobAdd(unicode(self.pipe.server_name), self.task_to_job_info(task))
        if (job_id == 0):
            raise Exception("invalid task information")

        self.pipe.JobDel(unicode(self.pipe.server_name), task.id, task.id)
        
        task.id = job_id
        
    def delete_task(self, task):
        self.pipe.JobDel(unicode(self.pipe.server_name), task.id, task.id)
    
    def job_info_to_task(self, job_info):
        task = Task(job_info.command, job_info.job_id)
        
        task.job_time = job_info.job_time
        task.days_of_month = job_info.days_of_month
        task.days_of_week = job_info.days_of_week
        task.run_periodically = (job_info.flags & 0x01) != 0
        task.non_interactive = (job_info.flags & 0x10) != 0
        
        return task

    def task_to_job_info(self, task):
        job_info = atsvc.JobInfo()
        
        job_info.command = unicode(task.command)
        job_info.job_time = task.job_time
        job_info.days_of_month = task.days_of_month
        job_info.days_of_week = task.days_of_week
        job_info.flags = 0
        
        if (task.run_periodically):
            job_info.flags |= 0x01
        if (task.non_interactive):
            job_info.flags |= 0x10
            
        return job_info


class CronTabWindow(gtk.Window):

    def __init__(self):
        super(CronTabWindow, self).__init__()

        self.create()
        
        self.pipe_manager = None
        self.server_address = ""
        self.transport_type = 0
        self.username = ""
                
        self.update_sensitivity()
        
    def create(self):
        
        # main window

        accel_group = gtk.AccelGroup()
        
        self.set_title("Scheduled Tasks")
        self.set_default_size(800, 600)
        self.connect("delete_event", self.on_self_delete)
        self.icon_filename = os.path.join(sys.path[0], "images", "crontab.png")
        self.icon_pixbuf = gtk.gdk.pixbuf_new_from_file(self.icon_filename)
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
        self.disconnect_item.set_sensitive(False)
        file_menu.add(self.disconnect_item)
        
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
        view_menu.add(self.refresh_item)
        
        
        self.task_item = gtk.MenuItem("_Task")
        menubar.add(self.task_item)
        
        task_menu = gtk.Menu()
        self.task_item.set_submenu(task_menu)

        self.new_item = gtk.ImageMenuItem(gtk.STOCK_NEW, accel_group)
        task_menu.add(self.new_item)

        self.delete_item = gtk.ImageMenuItem(gtk.STOCK_DELETE, accel_group)
        task_menu.add(self.delete_item)

        self.edit_item = gtk.ImageMenuItem(gtk.STOCK_EDIT, accel_group)
        task_menu.add(self.edit_item)

        
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

        
        # task list
        
        
        scrolledwindow = gtk.ScrolledWindow(None, None)
        scrolledwindow.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        scrolledwindow.set_shadow_type(gtk.SHADOW_IN)
        vbox.pack_start(scrolledwindow, True, True, 0)
        
        self.tasks_tree_view = gtk.TreeView()        
        scrolledwindow.add(self.tasks_tree_view)
        
        column = gtk.TreeViewColumn()
        column.set_title("")
        renderer = gtk.CellRendererPixbuf()
        renderer.set_property("pixbuf", gtk.gdk.pixbuf_new_from_file_at_size(self.icon_filename, 22, 22))
        column.pack_start(renderer, True)
        self.tasks_tree_view.append_column(column)
                
        column = gtk.TreeViewColumn()
        column.set_title("Id")
        column.set_resizable(True)
        column.set_sort_column_id(0)
        renderer = gtk.CellRendererText()
        column.pack_start(renderer, True)
        self.tasks_tree_view.append_column(column)
        column.add_attribute(renderer, "text", 0)
                
        column = gtk.TreeViewColumn()
        column.set_title("Command")
        column.set_resizable(True)
        column.set_sort_column_id(1)
        renderer = gtk.CellRendererText()
        column.pack_start(renderer, True)
        self.tasks_tree_view.append_column(column)
        column.add_attribute(renderer, "text", 1)
        
        column = gtk.TreeViewColumn()
        column.set_title("Schedule")
        column.set_resizable(True)
        column.set_sort_column_id(2)
        renderer = gtk.CellRendererText()
        column.pack_start(renderer, True)
        self.tasks_tree_view.append_column(column)
        column.add_attribute(renderer, "text", 2)
        
        self.tasks_store = gtk.ListStore(gobject.TYPE_STRING, gobject.TYPE_STRING, gobject.TYPE_STRING)
        self.tasks_store.set_sort_column_id(1, gtk.SORT_ASCENDING)
        self.tasks_tree_view.set_model(self.tasks_store)


        # status bar

        self.statusbar = gtk.Statusbar()
        self.statusbar.set_has_resize_grip(True)
        vbox.pack_start(self.statusbar, False, False, 0)
        
        
        # signals/events
        
        self.connect_item.connect("activate", self.on_connect_item_activate)
        self.disconnect_item.connect("activate", self.on_disconnect_item_activate)
        self.quit_item.connect("activate", self.on_quit_item_activate)
        self.refresh_item.connect("activate", self.on_refresh_item_activate)
        self.new_item.connect("activate", self.on_new_item_activate)
        self.delete_item.connect("activate", self.on_delete_item_activate)
        self.edit_item.connect("activate", self.on_edit_item_activate)
        self.about_item.connect("activate", self.on_about_item_activate)
        
        self.connect_button.connect("clicked", self.on_connect_item_activate)
        self.disconnect_button.connect("clicked", self.on_disconnect_item_activate)
        self.new_button.connect("clicked", self.on_new_item_activate)
        self.delete_button.connect("clicked", self.on_delete_item_activate)
        self.edit_button.connect("clicked", self.on_edit_item_activate)
        
        self.tasks_tree_view.get_selection().connect("changed", self.on_update_sensitivity)
        self.tasks_tree_view.connect("button_press_event", self.on_tasks_tree_view_button_press)
        
        self.add_accel_group(accel_group)

    def refresh_tasks_tree_view(self):
        if not self.connected():
            return None
        
        (model, paths) = self.tasks_tree_view.get_selection().get_selected_rows()
        
        self.tasks_store.clear()
        for task in self.pipe_manager.task_list:
            self.tasks_store.append(task.list_view_representation())

        if (len(paths) > 0):
            self.tasks_tree_view.get_selection().select_path(paths[0])

    def get_selected_task(self):
        if not self.connected():
            return None
        
        (model, iter) = self.tasks_tree_view.get_selection().get_selected()
        if (iter == None): # no selection
            return None
        else:            
            id = int(model.get_value(iter, 0))
            task_list = [task for task in self.pipe_manager.task_list if task.id == id]
            if (len(task_list) > 0):
                return task_list[0]
            else:
                return None

    def set_status(self, message):
        self.statusbar.pop(0)
        self.statusbar.push(0, message)
        
    def update_sensitivity(self):
        connected = (self.pipe_manager != None)
        selected = (self.get_selected_task() != None)
        
        self.connect_item.set_sensitive(not connected)
        self.disconnect_item.set_sensitive(connected)
        self.refresh_item.set_sensitive(connected)
        self.new_item.set_sensitive(connected)
        self.delete_item.set_sensitive(connected and selected)
        self.edit_item.set_sensitive(connected and selected)

        self.connect_button.set_sensitive(not connected)
        self.disconnect_button.set_sensitive(connected)
        self.new_button.set_sensitive(connected)
        self.delete_button.set_sensitive(connected and selected)
        self.edit_button.set_sensitive(connected and selected)

    def run_message_dialog(self, type, buttons, message, parent = None):
        if (parent == None):
            parent = self
        
        message_box = gtk.MessageDialog(parent, gtk.DIALOG_MODAL, type, buttons, message)
        response = message_box.run()
        message_box.hide()
        
        return response

    def run_task_edit_dialog(self, task = None, apply_callback = None):
        dialog = TaskEditDialog(task)
        dialog.show_all()
        
        # loop to handle the applies
        while True:
            response_id = dialog.run()
            
            if (response_id in [gtk.RESPONSE_OK, gtk.RESPONSE_APPLY]):
                problem_msg = dialog.check_for_problems()
                
                if (problem_msg != None):
                    self.run_message_dialog(gtk.MESSAGE_ERROR, gtk.BUTTONS_OK, problem_msg, dialog)
                else:
                    dialog.values_to_task()
                    if (apply_callback != None):
                        apply_callback(dialog.task)
                    if (response_id == gtk.RESPONSE_OK):
                        dialog.hide()
                        break
                        
            else:
                dialog.hide()
                return None
        
        return dialog.task

    def run_connect_dialog(self, pipe_manager, server_address, transport_type, username):
        dialog = ATSvcConnectDialog(server_address, transport_type, username)
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
                    
                    pipe_manager = ATSvcPipeManager(self.server_address, self.transport_type, self.username, password)
                    
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
    
    def update_task_callback(self, task):
        try:
            self.pipe_manager.update_task(task)
            self.pipe_manager.fetch_tasks()
        
            self.set_status("Task updated.")

        except RuntimeError, re:
            msg = "Failed to update task: " + re.args[1] + "."
            print msg
            self.set_status(msg)
            traceback.print_exc()
            self.run_message_dialog(gtk.MESSAGE_ERROR, gtk.BUTTONS_OK, msg)
        
        except Exception, ex:
            msg = "Failed to update task: " + str(ex) + "."
            print msg
            self.set_status(msg)
            traceback.print_exc()
            self.run_message_dialog(gtk.MESSAGE_ERROR, gtk.BUTTONS_OK, msg)
        
        self.refresh_tasks_tree_view()

    def on_self_delete(self, widget, event):
        if (self.pipe_manager != None):
            self.on_disconnect_item_activate(self.disconnect_item)
        
        gtk.main_quit()
        return False

    def on_connect_item_activate(self, widget):
        try:
            self.pipe_manager = self.run_connect_dialog(None, self.server_address, self.transport_type, self.username)
            if (self.pipe_manager != None):
                self.pipe_manager.fetch_tasks()
                
                self.set_status("Connected to " + self.server_address + ".")

        except RuntimeError, re:
            msg = "Failed to retrieve the scheduled tasks: " + re.args[1] + "."
            self.set_status(msg)
            print msg
            traceback.print_exc()
            self.run_message_dialog(gtk.MESSAGE_ERROR, gtk.BUTTONS_OK, msg)
        
        except Exception, ex:
            msg = "Failed to retrieve the scheduled tasks: " + str(ex) + "."
            self.set_status(msg)
            print msg
            traceback.print_exc()
            self.run_message_dialog(gtk.MESSAGE_ERROR, gtk.BUTTONS_OK, msg)
        
        self.refresh_tasks_tree_view()
        self.update_sensitivity()
        
    def on_disconnect_item_activate(self, widget):
        if (self.pipe_manager != None):
            self.pipe_manager.close()
            self.pipe_manager = None
            
        self.tasks_store.clear()
        self.update_sensitivity()

        self.set_status("Disconnected.")
    
    def on_quit_item_activate(self, widget):
        self.on_self_delete(None, None)
    
    def on_refresh_item_activate(self, widget):
        try:
            self.pipe_manager.fetch_tasks()
            
            self.set_status("Connected to " + self.server_address)
        
        except RuntimeError, re:
            msg = "Failed to retrieve the scheduled tasks: " + re.args[1] + "."
            self.set_status(msg)
            print msg
            traceback.print_exc()
            self.run_message_dialog(gtk.MESSAGE_ERROR, gtk.BUTTONS_OK, msg)
        
        except Exception, ex:
            msg = "Failed to retrieve the scheduled tasks: " + str(ex) + "."
            self.set_status(msg)
            print msg
            traceback.print_exc()
            self.run_message_dialog(gtk.MESSAGE_ERROR, gtk.BUTTONS_OK, msg)
            
        self.refresh_tasks_tree_view()
        
    def on_new_item_activate(self, widget):
        new_task = self.run_task_edit_dialog()
        if (new_task == None):
            return
        
        try:
            self.pipe_manager.add_task(new_task)
            self.pipe_manager.fetch_tasks()
        
            self.set_status("Successfully created the task")
        
        except RuntimeError, re:
            msg = "Failed to create task: " + re.args[1] + "."
            self.set_status(msg)
            print msg
            traceback.print_exc()
            self.run_message_dialog(gtk.MESSAGE_ERROR, gtk.BUTTONS_OK, msg)
        
        except Exception, ex:
            msg = "Failed to create task: " + str(ex) + "."
            self.set_status(msg)
            print msg
            traceback.print_exc()
            self.run_message_dialog(gtk.MESSAGE_ERROR, gtk.BUTTONS_OK, msg)
        
        self.refresh_tasks_tree_view()

    def on_delete_item_activate(self, widget):
        del_task = self.get_selected_task()

        if (self.run_message_dialog(gtk.MESSAGE_QUESTION, gtk.BUTTONS_YES_NO, "Do you want to delete task with ID '%d'?" % del_task.id) != gtk.RESPONSE_YES):
            return 
        
        try:
            self.pipe_manager.delete_task(del_task)
            self.pipe_manager.fetch_tasks()
        
            self.set_status("Successfully deleted the task.")
        
        except RuntimeError, re:
            msg = "Failed to delete task: " + re.args[1] + "."
            self.set_status(msg)
            print msg
            traceback.print_exc()
            self.run_message_dialog(gtk.MESSAGE_ERROR, gtk.BUTTONS_OK, msg)
        
        except Exception, ex:
            msg = "Failed to delete task: " + str(ex) + "."
            self.set_status(msg)
            print msg
            traceback.print_exc()
            self.run_message_dialog(gtk.MESSAGE_ERROR, gtk.BUTTONS_OK, msg)
        
        self.refresh_tasks_tree_view()
                
    def on_edit_item_activate(self, widget):
        edit_task = self.get_selected_task()
        self.run_task_edit_dialog(edit_task, self.update_task_callback)
        
    def on_about_item_activate(self, widget):
        dialog = AboutDialog(
                             "PyGWCronTab", 
                             "A tool to remotely manage scheduled tasks.\n Based on Jelmer Vernooij's original Samba-GTK",
                             self.icon_pixbuf
                             )
        dialog.run()
        dialog.hide()

    def on_tasks_tree_view_button_press(self, widget, event):
        if (self.get_selected_task() == None):
            return

        if (event.type == gtk.gdk._2BUTTON_PRESS):
            self.on_edit_item_activate(self.edit_item)

    def on_update_sensitivity(self, widget):
        self.update_sensitivity()


main_window = CronTabWindow()
main_window.set_status("Disconnected.")
main_window.show_all()
gtk.main()
