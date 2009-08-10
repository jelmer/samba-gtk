#!/usr/bin/python

import sys
import os.path
import traceback
import gtk, gobject

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
#        (user_handle, rid) = self.pipe.CreateUser(self.domain_handle, self.set_lsa_string(user.username), security.SEC_FLAG_MAXIMUM_ALLOWED)        
#        user.rid = rid
#        
#        self.update_user(user)
#        self.user_list.append(user)
        pass


    def update_task(self, task):
#        user_handle = self.pipe.OpenUser(self.domain_handle, security.SEC_FLAG_MAXIMUM_ALLOWED, user.rid)
#
#        info = self.pipe.QueryUserInfo(user_handle, samr.UserNameInformation)
#        info.account_name = self.set_lsa_string(user.username)
#        info.full_name = self.set_lsa_string(user.fullname)
#        self.pipe.SetUserInfo(user_handle, samr.UserNameInformation, info)
#        
#        info = self.pipe.QueryUserInfo(user_handle, samr.UserAdminCommentInformation)
#        info.description = self.set_lsa_string(user.description)
#        self.pipe.SetUserInfo(user_handle, samr.UserAdminCommentInformation, info)
#        
#        info = self.pipe.QueryUserInfo(user_handle, samr.UserControlInformation)
#        if (user.must_change_password):
#            info.acct_flags |= 0x00020000
#        else:
#            info.acct_flags &= ~0x00020000
#
#        if (user.password_never_expires):
#            info.acct_flags |= 0x00000200
#        else:
#            info.acct_flags &= ~0x00000200
#            
#        if (user.account_disabled):
#            info.acct_flags |= 0x00000001
#        else:
#            info.acct_flags &= ~0x00000001
#
#        if (user.account_locked_out):
#            info.acct_flags |= 0x00000400
#        else:
#            info.acct_flags &= ~0x00000400
#        # TODO: the must_change_password flag doesn't get updated, no idea why!
#        self.pipe.SetUserInfo(user_handle, samr.UserControlInformation, info)
#            
#        # TODO: cannot_change_password
#
#        info = self.pipe.QueryUserInfo(user_handle, samr.UserProfileInformation)
#        info.profile_path = self.set_lsa_string(user.profile_path)
#        self.pipe.SetUserInfo(user_handle, samr.UserProfileInformation, info)
#        
#        info = self.pipe.QueryUserInfo(user_handle, samr.UserScriptInformation)
#        info.logon_script = self.set_lsa_string(user.logon_script)
#        self.pipe.SetUserInfo(user_handle, samr.UserScriptInformation, info)
#
#        info = self.pipe.QueryUserInfo(user_handle, samr.UserHomeInformation)
#        info.home_directory = self.set_lsa_string(user.homedir_path)
#        
#        
#        if (user.map_homedir_drive == -1):
#            info.home_drive = self.set_lsa_string("")
#        else:
#            info.home_drive = self.set_lsa_string(chr(user.map_homedir_drive + ord('A')) + ":")
#        self.pipe.SetUserInfo(user_handle, samr.UserHomeInformation, info)
#        
#        
#        # update user's groups
#        group_list = self.rwa_list_to_group_list(self.pipe.GetGroupsForUser(user_handle).rids)
#        
#        # groups to remove
#        for group in group_list:
#            if (user.group_list.count(group) == 0):
#                group_handle = self.pipe.OpenGroup(self.domain_handle, security.SEC_FLAG_MAXIMUM_ALLOWED, group.rid)
#                self.pipe.DeleteGroupMember(group_handle, user.rid)
#
#        # groups to add
#        for group in user.group_list:
#            if (group_list.count(group) == 0):
#                group_handle = self.pipe.OpenGroup(self.domain_handle, security.SEC_FLAG_MAXIMUM_ALLOWED, group.rid)
#                self.pipe.AddGroupMember(group_handle, user.rid, samr.SE_GROUP_ENABLED)
        pass
        
    def delete_task(self, task):
#        user_handle = self.pipe.OpenUser(self.domain_handle, security.SEC_FLAG_MAXIMUM_ALLOWED, user.rid)
#        self.pipe.DeleteUser(user_handle)
        pass
    
    def job_info_to_task(self, job_info):
        task = Task(job_info.command, job_info.job_id)
        
        task.job_time = job_info.job_time
        self.days_of_month = job_info.days_of_month
        self.days_of_week = job_info.days_of_week
        self.run_periodically = (job_info.flags & 0x80) != 0
        self.add_current_date = (job_info.flags & 0x10) != 0
        self.non_interactive = (job_info.flags & 0x08) != 0
        
        return task


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
        self.icon_pixbuf = gtk.gdk.pixbuf_new_from_file(os.path.join(sys.path[0], "images", "crontab.png"))
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
        
        
        self.user_group_item = gtk.MenuItem("_Task")
        menubar.add(self.user_group_item)
        
        user_group_menu = gtk.Menu()
        self.user_group_item.set_submenu(user_group_menu)

        self.new_item = gtk.ImageMenuItem(gtk.STOCK_NEW, accel_group)
        user_group_menu.add(self.new_item)

        self.delete_item = gtk.ImageMenuItem(gtk.STOCK_DELETE, accel_group)
        user_group_menu.add(self.delete_item)

        self.edit_item = gtk.ImageMenuItem(gtk.STOCK_EDIT, accel_group)
        user_group_menu.add(self.edit_item)

        
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
        column.set_sort_column_id(0)
        renderer = gtk.CellRendererText()
        column.pack_start(renderer, True)
        self.tasks_tree_view.append_column(column)
        column.add_attribute(renderer, "text", 1)
        
        column = gtk.TreeViewColumn()
        column.set_title("Schedule")
        column.set_resizable(True)
        column.set_sort_column_id(1)
        renderer = gtk.CellRendererText()
        column.pack_start(renderer, True)
        self.tasks_tree_view.append_column(column)
        column.add_attribute(renderer, "text", 2)
        
        self.tasks_store = gtk.ListStore(gobject.TYPE_STRING, gobject.TYPE_STRING, gobject.TYPE_STRING)
        self.tasks_store.set_sort_column_id(0, gtk.SORT_ASCENDING)
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
            return [task for task in self.pipe_manager.task_list if task.id == id][0] # TODO: check if [0] exists

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

    def run_message_dialog(self, type, buttons, message):
        message_box = gtk.MessageDialog(self, gtk.DIALOG_MODAL, type, buttons, message)
        response = message_box.run()
        message_box.hide()
        
        return response

    def run_task_edit_dialog(self, task = None, apply_callback = None):
        dialog = TaskEditDialog(self.pipe_manager, task)
        dialog.show_all()
        
        # loop to handle the applies
        while True:
            response_id = dialog.run()
            
            if (response_id in [gtk.RESPONSE_OK, gtk.RESPONSE_APPLY]):
                problem_msg = dialog.check_for_problems()
                
                if (problem_msg != None):
                    self.run_message_dialog(gtk.MESSAGE_ERROR, gtk.BUTTONS_OK, problem_msg)
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
                    self.run_message_dialog(gtk.MESSAGE_ERROR, gtk.BUTTONS_OK, msg)
                    
                except Exception, ex:
                    msg = "Failed to connect: " + str(ex) + "."
                    print msg
                    traceback.print_exc()
                    self.run_message_dialog(gtk.MESSAGE_ERROR, gtk.BUTTONS_OK, msg)

        dialog.hide()
        return pipe_manager
    
    def connected(self):
        return self.pipe_manager != None
    
    def update_task_callback(self, user):
        try:
            self.pipe_manager.update_task(task)
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
        
        self.set_status("Connected to " + self.server_address)

    def on_disconnect_item_activate(self, widget):
        if (self.pipe_manager != None):
            self.pipe_manager.close()
            self.pipe_manager = None
            
        self.tasks_store.clear()
        self.update_sensitivity()

        self.set_status("Disconnected")
    
    def on_quit_item_activate(self, widget):
        self.on_self_delete(None, None)
    
    def on_refresh_item_activate(self, widget):
        try:
            self.pipe_manager.fetch_tasks()
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
        
        self.set_status("Connected to " + self.server_address)
        
    def on_new_item_activate(self, widget):
        new_task = self.run_task_edit_dialog()
        if (new_task == None):
            return
        
        try:
            self.pipe_manager.add_task(new_task)
            self.pipe_manager.fetch_tasks()
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

        self.set_status("Successfully created the task")
        
    def on_delete_item_activate(self, widget):
        del_task = self.get_selected_task()

        if (self.run_message_dialog(gtk.MESSAGE_QUESTION, gtk.BUTTONS_YES_NO, "Do you want to delete task with ID '%d'?" % del_task.id) != gtk.RESPONSE_YES):
            return 
        
        try:
            self.pipe_manager.delete_task(del_task)
            self.pipe_manager.fetch_tasks()
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
        
        self.set_status("Successfully deleted the task")
        
    def on_edit_item_activate(self, widget):
        edit_task = self.get_selected_task()
        self.run_task_edit_dialog(edit_task, self.update_task_callback)
        
        self.set_status("Task updated")

    def on_about_item_activate(self, widget):
        dialog = AboutDialog(
            "PyGWCronTab", 
            "A tool to remotely manage scheduled tasks.\n Based on Jelmer Vernooij's original Samba-GTK",
            self.icon_pixbuf)
        dialog.run()
        dialog.hide()

    def on_tasks_tree_view_button_press(self, widget, event):
        if (event.type == gtk.gdk._2BUTTON_PRESS):
            self.on_edit_item_activate(self.edit_item)

    def on_update_sensitivity(self, widget):
        self.update_sensitivity()


main_window = CronTabWindow()
main_window.show_all()
gtk.main()
