#!/usr/bin/python

import sys
import os.path
import traceback
import threading
import time
import getopt

import gobject
import gtk
import pango

from samba import credentials
from samba.dcerpc import svcctl

from objects import Service

from dialogs import SvcCtlConnectDialog
from dialogs import ServiceEditDialog
from dialogs import ServiceControlDialog
from dialogs import AboutDialog


class SvcCtlPipeManager():
    
    def __init__(self, server_address, transport_type, username, password):
        self.service_list = []
        self.lock = threading.Lock()
        
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
        
        self.pipe = svcctl.svcctl(binding % (server_address), credentials = creds)
        self.scm_handle = self.pipe.OpenSCManagerA(None, None, svcctl.SC_MANAGER_ALL_ACCESS)

    def close(self):
        pass # apparently there's no .Close() method for this pipe
            
    def fetch_services(self, svcctl_window):
        """Feteches a list of services from the server. svcctl_window is used to update the GUI."""
        #note: this function is designed to be called by a secondary thread only. 
        #      If the main thread calls this then THERE WILL BE A DEADLOCK!
        del self.service_list[:]
        
        (buffer, needed, count, resume_handle) = self.pipe.EnumServicesStatusW(self.scm_handle,
            svcctl.SERVICE_TYPE_WIN32_OWN_PROCESS | svcctl.SERVICE_TYPE_WIN32_SHARE_PROCESS,
            svcctl.SERVICE_STATE_ALL, 256 * 1024,
            0)

        runtime_error = None
        current = 0.0
        gtk.gdk.threads_enter()
        svcctl_window.progressbar.show()
        gtk.gdk.threads_leave()
        
        for enum_service_status in SvcCtlPipeManager.enum_service_status_list_from_buffer(buffer, count):
            try:
                gtk.gdk.threads_enter()
                svcctl_window.set_status("Fetching service: %s." % (enum_service_status.service_name))
                svcctl_window.progressbar.set_fraction(current / count)
                gtk.gdk.threads_leave()
                current += 1.0
                service = SvcCtlPipeManager.fetch_service(self, enum_service_status.service_name)
                self.service_list.append(service)
            except RuntimeError as re:
                if re.args[0] == 5: #5 is WERR_ACCESS_DENIED
                    print "Failed to fetch service \'%s\': Access Denied." % (enum_service_status.service_name)
                else:
                    #we do this so we can continue fetching services, even if a few fetches fail.
                    print "Failed to fetch service %s: %s." % (enum_service_status.service_name, re.args[1])
                    traceback.print_exc()

        gtk.gdk.threads_enter()
        svcctl_window.progressbar.hide()
        gtk.gdk.threads_leave()

    def start_service(self, service):
        self.pipe.StartServiceW(service.handle, service.start_params.split())

    def control_service(self, service, control):
        self.pipe.ControlService(service.handle, control)

    def update_service(self, service):
        (service_config, needed) = self.pipe.QueryServiceConfigW(service.handle, 8192)
        # TODO: this gives a "DCERPC Fault NDR" error
        #TODO: this gives me a "NT_STATUS_RPC_BAD_STUB_DATA" error
        self.pipe.ChangeServiceConfigW(
            service.handle,                      #policy_handle *handle
            service_config.service_type,                #uint32 type
            service.start_type,               #svcctl_StartType start_type
            service_config.error_control,  #svcctl_ErrorControl error_control
            unicode(service.path_to_exe),               #uint16 *binary_path
            unicode(service_config.loadordergroup),     #uint16 *load_order_group
            unicode(service_config.dependencies),       #uint16 *dependencies
            unicode(service.account),                                #uint16 *service_start_name
            unicode(service.account_password),          #uint16 *password
            unicode(service.display_name))              #uint16 *display_name

        service_status = self.pipe.QueryServiceStatus(service.handle)
        
        if (service.allow_desktop_interaction):
            service_status.type |= svcctl.SERVICE_TYPE_INTERACTIVE_PROCESS
        else:
            service_status.type &= ~svcctl.SERVICE_TYPE_INTERACTIVE_PROCESS
        
        # TODO: apparently this call is not implemented    
        self.pipe.SetServiceStatus(service.handle, service_status)
        
        self.pipe.CloseServiceHandle(service.handle)

    def fetch_service(self, service_name):
        service = Service()
        service.name = service_name.strip()
        service.handle = self.pipe.OpenServiceW(self.scm_handle, unicode(service_name), svcctl.SERVICE_ALL_ACCESS)
        
        service_status = self.pipe.QueryServiceStatus(service.handle)
        service.state = service_status.state
        service.wait_hint = service_status.wait_hint
        service.check_point = service_status.check_point
        service.accepts_pause = (service_status.controls_accepted & svcctl.SVCCTL_ACCEPT_PAUSE_CONTINUE) != 0
        service.accepts_stop = (service_status.controls_accepted & svcctl.SVCCTL_ACCEPT_STOP) != 0
        
        (service_config, needed) = self.pipe.QueryServiceConfigW(service.handle, 8192)
        service.display_name = service_config.displayname.strip()
        service.start_type = service_config.start_type
        service.path_to_exe = service_config.executablepath
        
        if (service_config.startname == "LocalSystem"):
            service.account = None
        else:
            service.account = service_config.startname
            
        service.allow_desktop_interaction = (service_status.type & svcctl.SERVICE_TYPE_INTERACTIVE_PROCESS != 0)
        
        (service_config2_buffer, needed) = self.pipe.QueryServiceConfig2W(service.handle, svcctl.SERVICE_CONFIG_DESCRIPTION, 8192)
        service_description = SvcCtlPipeManager.service_description_from_buffer(service_config2_buffer)
        service.description = service_description.description.strip()
        
        return service

    def fetch_service_status(self, service):        
        service_status = self.pipe.QueryServiceStatus(service.handle)

        service.state = service_status.state
        service.wait_hint = service_status.wait_hint
        service.check_point = service_status.check_point
        service.accepts_pause = (service_status.controls_accepted & svcctl.SVCCTL_ACCEPT_PAUSE_CONTINUE) != 0
        service.accepts_stop = (service_status.controls_accepted & svcctl.SVCCTL_ACCEPT_STOP) != 0

    @staticmethod
    def enum_service_status_list_from_buffer(buffer, count):
        enum_service_status_list = []
        offset = 0

        while (count > 0):
            enum_service_status = svcctl.ENUM_SERVICE_STATUSW()

            addr = SvcCtlPipeManager.get_nbo_long(buffer, offset)
            enum_service_status.service_name = SvcCtlPipeManager.get_nbo_ustring(buffer, addr)            
            offset += 4
            
            addr = SvcCtlPipeManager.get_nbo_long(buffer, offset)
            enum_service_status.display_name = SvcCtlPipeManager.get_nbo_ustring(buffer, addr)            
            offset += 4

            enum_service_status.status = svcctl.SERVICE_STATUS()
            enum_service_status.status.type = SvcCtlPipeManager.get_nbo_long(buffer, offset)            
            offset += 4

            enum_service_status.status.state = SvcCtlPipeManager.get_nbo_long(buffer, offset)
            offset += 4
            
            enum_service_status.status.controls_accepted = SvcCtlPipeManager.get_nbo_long(buffer, offset)
            offset += 4
            
            enum_service_status.status.win32_exit_code = SvcCtlPipeManager.get_nbo_long(buffer, offset)
            offset += 4
            
            enum_service_status.status.service_exit_code = SvcCtlPipeManager.get_nbo_long(buffer, offset)
            offset += 4
            
            enum_service_status.status.check_point = SvcCtlPipeManager.get_nbo_long(buffer, offset)
            offset += 4
            
            enum_service_status.status.wait_hint = SvcCtlPipeManager.get_nbo_long(buffer, offset)
            offset += 4
            
            enum_service_status_list.append(enum_service_status)
            
            count -= 1
            
        return enum_service_status_list
    
    @staticmethod
    def service_description_from_buffer(buffer):
        service_description = svcctl.SERVICE_DESCRIPTION()
        
        addr = SvcCtlPipeManager.get_nbo_long(buffer, 0)
        service_description.description = SvcCtlPipeManager.get_nbo_ustring(buffer, addr)
        
        return service_description
        
    @staticmethod
    def get_nbo_short(buffer, offset):
        return ((buffer[offset + 1] << 8) + buffer[offset])
    
    @staticmethod
    def get_nbo_long(buffer, offset):
        return ((((((buffer[offset + 3] << 8) + buffer[offset + 2]) << 8) + buffer[offset + 1]) << 8) + buffer[offset])
    
    @staticmethod
    def get_nbo_ustring(buffer, offset):
        index = 0
        string = u""
        
        short = SvcCtlPipeManager.get_nbo_short(buffer, offset + index)
        index += 2
        while (short != 0):
            string += unichr(short)
            short = SvcCtlPipeManager.get_nbo_short(buffer, offset + index)
            index += 2
        
        return string


class FetchServicesThread(threading.Thread):
    
    def __init__(self, pipe_manager, svcctl_window):
        super(FetchServicesThread, self).__init__()
        
        self.pipe_manager = pipe_manager
        self.svcctl_window = svcctl_window
        
    def run(self):
        self.pipe_manager.lock.acquire()
        try:
            #This function handles runtime errors on it's own. This way it can continue running after an error.
            self.pipe_manager.fetch_services(self.svcctl_window)
        finally:
            self.pipe_manager.lock.release()
        
        gtk.gdk.threads_enter()
        self.svcctl_window.set_status("Connected to %s." % (self.svcctl_window.server_address))
        self.svcctl_window.refresh_services_tree_view()
        gtk.gdk.threads_leave()


class ServiceControlThread(threading.Thread):
    
    def __init__(self, pipe_manager, service, control, svcctl_window, service_control_dialog):
        super(ServiceControlThread, self).__init__()
        
        self.pipe_manager = pipe_manager
        self.service = service
        self.control = control
        self.svcctl_window = svcctl_window
        self.service_control_dialog = service_control_dialog
        self.running = False
        self.pending = False
        
    def stop(self):
        self.pending = True
        self.running = False
        
    def run(self):
        self.running = True
        
        control_string = {None: "start", svcctl.SVCCTL_CONTROL_STOP: "stop", svcctl.SVCCTL_CONTROL_PAUSE: "pause", svcctl.SVCCTL_CONTROL_CONTINUE: "resume"}
        control_string2 = {None: "started", svcctl.SVCCTL_CONTROL_STOP: "stopped", svcctl.SVCCTL_CONTROL_PAUSE: "paused", svcctl.SVCCTL_CONTROL_CONTINUE: "resumed"}
        final_state = {None: svcctl.SVCCTL_RUNNING, svcctl.SVCCTL_CONTROL_STOP: svcctl.SVCCTL_STOPPED, svcctl.SVCCTL_CONTROL_PAUSE: svcctl.SVCCTL_PAUSED, svcctl.SVCCTL_CONTROL_CONTINUE: svcctl.SVCCTL_RUNNING}
        sleep_delay = 0.1

        try:
            self.pipe_manager.lock.acquire()
            
            if (self.control == None): # starting
                self.pipe_manager.start_service(self.service)
            else:
                self.pipe_manager.control_service(self.service, self.control)
            
            self.pipe_manager.fetch_service_status(self.service)
            if (self.service.wait_hint == 0):
                self.service_control_dialog.set_progress_speed(0.5)
            else:
                self.service_control_dialog.set_progress_speed(1.0 / ((self.service.wait_hint / 1000.0) / sleep_delay))
            
        except RuntimeError, re:
            msg = "Failed to %s service \'%s\': %s." % (control_string[self.control], self.service.display_name, re.args[1])
            print msg
            traceback.print_exc()
            
            gtk.gdk.threads_enter()
            self.service_control_dialog.hide()
            self.svcctl_window.set_status(msg)
            self.svcctl_window.run_message_dialog(gtk.MESSAGE_ERROR, gtk.BUTTONS_OK, msg, self.service_control_dialog)
            gtk.gdk.threads_leave()
            
            return

        except Exception, ex:
            msg = "Failed to %s service \'%s\': %s." % (control_string[self.control], self.service.display_name, str(ex))
            print msg
            traceback.print_exc()
            
            gtk.gdk.threads_enter()
            self.service_control_dialog.hide()
            self.svcctl_window.set_status(msg)
            self.svcctl_window.run_message_dialog(gtk.MESSAGE_ERROR, gtk.BUTTONS_OK, msg, self.service_control_dialog)
            gtk.gdk.threads_leave()
            
            return
            
        finally:
            self.pipe_manager.lock.release()
        
        while self.running:
            try:
                self.pipe_manager.lock.acquire()
                self.pipe_manager.fetch_service_status(self.service)
                
            except RuntimeError, re:
                msg = "Failed to %s service \'%s\': %s." % (control_string[self.control], self.service.display_name, re.args[1])
                print msg
                traceback.print_exc()
                          
                gtk.gdk.threads_enter()
                self.service_control_dialog.hide()
                self.svcctl_window.set_status(msg)
                self.svcctl_window.run_message_dialog(gtk.MESSAGE_ERROR, gtk.BUTTONS_OK, msg, self.service_control_dialog)
                gtk.gdk.threads_leave()
                
                return
                
            except Exception, ex:
                msg = "Failed to %s service \'%s\': %s." % (control_string[self.control], self.service.display_name, str(ex))
                print msg
                traceback.print_exc()
                
                gtk.gdk.threads_enter()
                self.service_control_dialog.hide()
                self.svcctl_window.set_status(msg)
                self.svcctl_window.run_message_dialog(gtk.MESSAGE_ERROR, gtk.BUTTONS_OK, msg, self.service_control_dialog)
                gtk.gdk.threads_leave()
                
                return
            
            finally:
                self.pipe_manager.lock.release()
            
            if (self.service.state != svcctl.SVCCTL_START_PENDING and 
                self.service.state != svcctl.SVCCTL_STOP_PENDING and 
                self.service.state != svcctl.SVCCTL_PAUSE_PENDING and 
                self.service.state != svcctl.SVCCTL_CONTINUE_PENDING): # no pending operation => done
                
                self.running = False
                gtk.gdk.threads_enter()
                self.service_control_dialog.progress(True)
                gtk.gdk.threads_leave()
                
            else:
                gtk.gdk.threads_enter()
                self.service_control_dialog.progress()
                gtk.gdk.threads_leave()

            time.sleep(sleep_delay)
            
        gtk.gdk.threads_enter()
        self.service_control_dialog.hide()
        self.svcctl_window.refresh_services_tree_view()

        if (self.service.state == final_state[self.control]):        
            self.svcctl_window.set_status("Successfully %s \'%s\' service." % (control_string2[self.control], self.service.display_name))
        else:
            if (self.pending):
                self.svcctl_window.set_status("The %s operation on the \'%s\' service is still pending." % (control_string[self.control], self.service.display_name))
            else:
                msg = "Failed to %s the \'%s\' service." % (control_string[self.control], self.service.display_name)
                self.svcctl_window.set_status(msg)
                self.svcctl_window.run_message_dialog(gtk.MESSAGE_ERROR, gtk.BUTTONS_OK, msg, self.svcctl_window)
        gtk.gdk.threads_leave()


class SvcCtlWindow(gtk.Window):

    def __init__(self, info_callback = None, server = "", username = "", password = "", transport_type = 0, connect_now = False):
        super(SvcCtlWindow, self).__init__()
        #Note: Any change to these arguments should probably also be changed in on_connect_item_activate()

        self.create()
        self.pipe_manager = None
        self.update_sensitivity()
        self.update_captions()
        self.set_status("Disconnected.")
        
        #It's nice to have this info saved when a user wants to reconnect
        self.server_address = server
        self.username = username
        self.transport_type = transport_type
        
        self.on_connect_item_activate(None, server, transport_type, username, password, connect_now)
        
        #This is used so the parent program can grab the server info after we've connected.
        if info_callback != None:
            info_callback(server = self.server_address, username = self.username, transport_type = self.transport_type)
        
    def create(self):
        
        # main window

        accel_group = gtk.AccelGroup()
        
        self.set_title("Service Control Management")
        self.set_default_size(800, 600)
        self.icon_filename = os.path.join(sys.path[0], "images", "service.png")
        self.icon_pixbuf = gtk.gdk.pixbuf_new_from_file(self.icon_filename)
        self.set_icon(self.icon_pixbuf)
        
    	vbox = gtk.VBox(False, 0)
    	self.add(vbox)


        # menu
        
        self.menubar = gtk.MenuBar()
        vbox.pack_start(self.menubar, False, False, 0)
        

        self.file_item = gtk.MenuItem("_File")
        self.menubar.add(self.file_item)
        
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
        self.menubar.add(self.view_item)
        
        view_menu = gtk.Menu()
        self.view_item.set_submenu(view_menu)
        
        self.refresh_item = gtk.ImageMenuItem(gtk.STOCK_REFRESH, accel_group)
        view_menu.add(self.refresh_item)
        
        
        self.service_item = gtk.MenuItem("_Service")
        self.menubar.add(self.service_item)
        
        service_menu = gtk.Menu()
        self.service_item.set_submenu(service_menu)

        self.start_item = gtk.ImageMenuItem(gtk.STOCK_MEDIA_PLAY, accel_group)
        self.start_item.get_child().set_text("Start")
        service_menu.add(self.start_item)

        self.stop_item = gtk.ImageMenuItem(gtk.STOCK_MEDIA_STOP, accel_group)
        self.stop_item.get_child().set_text("Stop")
        service_menu.add(self.stop_item)

        self.pause_resume_item = gtk.ImageMenuItem(gtk.STOCK_MEDIA_PAUSE, accel_group)
        service_menu.add(self.pause_resume_item)
        
        menu_separator_item = gtk.SeparatorMenuItem()
        service_menu.add(menu_separator_item)
        
        self.properties_item = gtk.ImageMenuItem(gtk.STOCK_PROPERTIES, accel_group)
        service_menu.add(self.properties_item)

        self.help_item = gtk.MenuItem("_Help")
        self.menubar.add(self.help_item)

        help_menu = gtk.Menu()
        self.help_item.set_submenu(help_menu)

        self.about_item = gtk.ImageMenuItem(gtk.STOCK_ABOUT, accel_group)
        help_menu.add(self.about_item)
        
        
        # toolbar
        
        self.toolbar = gtk.Toolbar()
        vbox.pack_start(self.toolbar, False, False, 0)
        
        self.connect_button = gtk.ToolButton(gtk.STOCK_CONNECT)
        self.connect_button.set_is_important(True)
        self.connect_button.set_tooltip_text("Connect to a server")
        self.toolbar.insert(self.connect_button, 0)
        
        self.disconnect_button = gtk.ToolButton(gtk.STOCK_DISCONNECT)
        self.disconnect_button.set_is_important(True)
        self.disconnect_button.set_tooltip_text("Disconnect from the server")
        self.toolbar.insert(self.disconnect_button, 1)
        
        self.toolbar.insert(gtk.SeparatorToolItem(), 2)
        
        self.start_button = gtk.ToolButton(gtk.STOCK_MEDIA_PLAY)
        self.start_button.set_label("Start")
        self.start_button.set_tooltip_text("Start the service")
        self.start_button.set_is_important(True)
        self.toolbar.insert(self.start_button, 3)
                
        self.stop_button = gtk.ToolButton(gtk.STOCK_MEDIA_STOP)
        self.stop_button.set_label("Stop")
        self.stop_button.set_tooltip_text("Stop the service")
        self.stop_button.set_is_important(True)
        self.toolbar.insert(self.stop_button, 4)
                
        self.pause_resume_button = gtk.ToolButton(gtk.STOCK_MEDIA_PAUSE)
        self.pause_resume_button.set_is_important(True)
        self.toolbar.insert(self.pause_resume_button, 5)

        
        # sevices list
        
        self.scrolledwindow = gtk.ScrolledWindow(None, None)
        self.scrolledwindow.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        self.scrolledwindow.set_shadow_type(gtk.SHADOW_IN)
        vbox.pack_start(self.scrolledwindow, True, True, 0)
        
        self.services_tree_view = gtk.TreeView()        
        self.scrolledwindow.add(self.services_tree_view)
        
        column = gtk.TreeViewColumn()
        column.set_title("")
        column.set_resizable(False)
        renderer = gtk.CellRendererPixbuf()
        renderer.set_property("pixbuf", gtk.gdk.pixbuf_new_from_file_at_size(self.icon_filename, 22, 22))
        column.pack_start(renderer, True)
        self.services_tree_view.append_column(column)
                
        column = gtk.TreeViewColumn()
        column.set_title("Name")
        column.set_resizable(True)
        column.set_fixed_width(80)
        column.set_expand(True)
        column.set_sizing(gtk.TREE_VIEW_COLUMN_FIXED)
        column.set_sort_column_id(1)
        renderer = gtk.CellRendererText()
        renderer.set_property("ellipsize", pango.ELLIPSIZE_END)
        column.pack_start(renderer, True)
        self.services_tree_view.append_column(column)
        column.add_attribute(renderer, "text", 1)
                
        column = gtk.TreeViewColumn()
        column.set_title("Description")
        column.set_resizable(True)
        column.set_expand(True)
        column.set_sizing(gtk.TREE_VIEW_COLUMN_FIXED)
        column.set_sort_column_id(2)
        renderer = gtk.CellRendererText()
        renderer.set_property("ellipsize", pango.ELLIPSIZE_END)
        column.pack_start(renderer, True)
        self.services_tree_view.append_column(column)
        column.add_attribute(renderer, "text", 2)
        
        column = gtk.TreeViewColumn()
        column.set_title("State")
        column.set_resizable(True)
        column.set_sort_column_id(3)
        renderer = gtk.CellRendererText()
        column.pack_start(renderer, True)
        self.services_tree_view.append_column(column)
        column.add_attribute(renderer, "text", 3)
        
        column = gtk.TreeViewColumn()
        column.set_title("Start Type")
        column.set_resizable(True)
        column.set_sort_column_id(4)
        renderer = gtk.CellRendererText()
        column.pack_start(renderer, True)
        self.services_tree_view.append_column(column)
        column.add_attribute(renderer, "text", 4)
        
        self.services_store = gtk.ListStore(gobject.TYPE_STRING, gobject.TYPE_STRING, gobject.TYPE_STRING, gobject.TYPE_STRING, gobject.TYPE_STRING)
        self.services_store.set_sort_column_id(1, gtk.SORT_ASCENDING)
        self.services_tree_view.set_model(self.services_store)


        # status bar & progress bar
        
        self.statusbar = gtk.Statusbar()
        self.statusbar.set_has_resize_grip(True)
        
        self.progressbar = gtk.ProgressBar()
        self.progressbar.set_no_show_all(True)
        self.progressbar.hide()
        
        hbox = gtk.HBox(False, 0)
        hbox.pack_start(self.progressbar, False, False, 0)
        hbox.pack_start(self.statusbar, True, True, 0)
        
        vbox.pack_start(hbox, False, False, 0)
        
        
        # signals/events
        
        self.connect("delete_event", self.on_self_delete)
        self.connect("key-press-event", self.on_key_press)
        
        self.connect_item.connect("activate", self.on_connect_item_activate)
        self.disconnect_item.connect("activate", self.on_disconnect_item_activate)
        self.quit_item.connect("activate", self.on_quit_item_activate)
        self.refresh_item.connect("activate", self.on_refresh_item_activate)
        self.start_item.connect("activate", self.on_start_item_activate)
        self.stop_item.connect("activate", self.on_stop_item_activate)
        self.pause_resume_item.connect("activate", self.on_pause_resume_item_activate)
        self.properties_item.connect("activate", self.on_properties_item_activate)
        self.about_item.connect("activate", self.on_about_item_activate)
        
        self.connect_button.connect("clicked", self.on_connect_item_activate)
        self.disconnect_button.connect("clicked", self.on_disconnect_item_activate)
        self.start_button.connect("clicked", self.on_start_item_activate)
        self.stop_button.connect("clicked", self.on_stop_item_activate)
        self.pause_resume_button.connect("clicked", self.on_pause_resume_item_activate)
        
        self.services_tree_view.get_selection().connect("changed", self.on_update_sensitivity)
        self.services_tree_view.get_selection().connect("changed", self.on_update_captions)
        self.services_tree_view.connect("button_press_event", self.on_services_tree_view_button_press)
        
        self.add_accel_group(accel_group)
        

    def refresh_services_tree_view(self):
        if not self.connected():
            return None
        
        (model, paths) = self.services_tree_view.get_selection().get_selected_rows()
        
        self.services_store.clear()
        
        self.pipe_manager.lock.acquire()
        for sevice in self.pipe_manager.service_list:
            self.services_store.append(sevice.list_view_representation())
        self.pipe_manager.lock.release()

        if (len(paths) > 0):
            self.services_tree_view.get_selection().select_path(paths[0])
            
    def get_selected_service(self):
        if not self.connected():
            return None
        
        (model, iter) = self.services_tree_view.get_selection().get_selected()
        if (iter == None): # no selection
            return None
        else:
            name = model.get_value(iter, 0)
            
            self.pipe_manager.lock.acquire()
            service_list = [service for service in self.pipe_manager.service_list if service.name == name]
            self.pipe_manager.lock.release()
            
            if (len(service_list) == 0):
                return None
            else:
                return service_list[0]

    def set_status(self, message):
        self.statusbar.pop(0)
        self.statusbar.push(0, message)
        
    def update_sensitivity(self):
        connected = (self.pipe_manager != None)
        
        service = self.get_selected_service()
        if (service != None):
            selected = True
            pausable = service.accepts_pause
            stoppable = service.accepts_stop
            startable = (service.start_type != svcctl.SVCCTL_DISABLED)
            
            stopped = (service.state == svcctl.SVCCTL_STOPPED)            
            running = (service.state == svcctl.SVCCTL_RUNNING)
            paused = (service.state == svcctl.SVCCTL_PAUSED)
        else:
            selected = False
        
        self.connect_item.set_sensitive(not connected)
        self.disconnect_item.set_sensitive(connected)
        self.refresh_item.set_sensitive(connected)
        self.start_item.set_sensitive(connected and selected and stopped and startable)
        self.stop_item.set_sensitive(connected and selected and running and stoppable)
        self.pause_resume_item.set_sensitive(connected and selected and pausable and (running or paused))
        self.properties_item.set_sensitive(connected and selected)

        self.connect_button.set_sensitive(not connected)
        self.disconnect_button.set_sensitive(connected)
        self.start_button.set_sensitive(connected and selected and stopped and startable)
        self.stop_button.set_sensitive(connected and selected and running and stoppable)
        self.pause_resume_button.set_sensitive(connected and selected and pausable and (running or paused))
    
    def update_captions(self):
        service = self.get_selected_service()
        if (service == None):
            paused = False
        else:
            paused = (service.state == svcctl.SVCCTL_PAUSED)
        
        self.pause_resume_item.get_child().set_text(["Pause", "Resume"][paused])
        self.pause_resume_button.set_tooltip_text(["Pause the service", "Resume the service"][paused])
        self.pause_resume_button.set_label(["Pause", "Resume"][paused])

    def run_message_dialog(self, type, buttons, message, parent = None):
        if (parent == None):
            parent = self
        
        message_box = gtk.MessageDialog(parent, gtk.DIALOG_MODAL, type, buttons, message)
        response = message_box.run()
        message_box.hide()
        
        return response

    def run_service_edit_dialog(self, service = None, apply_callback = None):
        dialog = ServiceEditDialog(service)
        dialog.show_all()
        
        # loop to handle the applies
        while True:
            response_id = dialog.run()
            
            if (response_id in [gtk.RESPONSE_OK, gtk.RESPONSE_APPLY]):
                problem_msg = dialog.check_for_problems()
                
                if (problem_msg != None):
                    self.run_message_dialog(gtk.MESSAGE_ERROR, gtk.BUTTONS_OK, problem_msg, dialog)
                else:
                    dialog.values_to_service()
                    if (apply_callback != None):
                        apply_callback(dialog.service)
                    if (response_id == gtk.RESPONSE_OK):
                        dialog.hide()
                        break
                        
            else:
                dialog.hide()
                return None
        
        return dialog.service

    def run_service_control_dialog(self, service, control):
        dialog = ServiceControlDialog(service, control)
        thread = ServiceControlThread(self.pipe_manager, service, control, self, dialog)
        dialog.set_close_callback(thread.stop)
        
        dialog.show_all()
        thread.start()
        
        return dialog.service

    def run_connect_dialog(self, pipe_manager, server_address, transport_type, username, password = "", connect_now = False):
        dialog = SvcCtlConnectDialog(server_address, transport_type, username, password)
        dialog.show_all()
        
        # loop to handle the failures
        while True:
            if (connect_now):
                connect_now = False
                response_id = gtk.RESPONSE_OK
            else:
                response_id = dialog.run()
            
            if (response_id != gtk.RESPONSE_OK):
                dialog.hide()
                return None
            else:
                try:
                    server_address = dialog.get_server_address()
                    self.server_address = server_address
                    transport_type = dialog.get_transport_type()
                    self.transport_type = transport_type
                    username = dialog.get_username()
                    self.username = username
                    password = dialog.get_password()
                    
                    pipe_manager = SvcCtlPipeManager(server_address, transport_type, username, password)
                    
                    break
                
                except RuntimeError, re:
                    if re.args[1] == 'Logon failure': #user got the password wrong
                        self.run_message_dialog(gtk.MESSAGE_ERROR, gtk.BUTTONS_OK, "Failed to connect: Invalid username or password.", dialog)
                        dialog.password_entry.grab_focus()
                        dialog.password_entry.select_region(0, -1) #select all the text in the password box
                    elif re.args[0] == 5 or re.args[1] == 'Access denied':
                        self.run_message_dialog(gtk.MESSAGE_ERROR, gtk.BUTTONS_OK, "Failed to connect: Access Denied.", dialog)
                        dialog.username_entry.grab_focus()
                        dialog.username_entry.select_region(0, -1)
                    elif re.args[1] == 'NT_STATUS_HOST_UNREACHABLE':
                        self.run_message_dialog(gtk.MESSAGE_ERROR, gtk.BUTTONS_OK, "Failed to connect: Could not contact the server.", dialog)
                        dialog.server_address_entry.grab_focus()
                        dialog.server_address_entry.select_region(0, -1)
                    elif re.args[1] == 'NT_STATUS_NETWORK_UNREACHABLE':
                        self.run_message_dialog(gtk.MESSAGE_ERROR, gtk.BUTTONS_OK, "Failed to connect: The network is unreachable.\n\nPlease check your network connection.", dialog)
                    elif re.args[1] == 'NT_STATUS_CONNECTION_REFUSED':
                        self.run_message_dialog(gtk.MESSAGE_ERROR, gtk.BUTTONS_OK, "Failed to connect: The connection was refused.", dialog)
                    else:
                        msg = "Failed to connect: %s." % (re.args[1])
                        print msg
                        traceback.print_exc()                        
                        self.run_message_dialog(gtk.MESSAGE_ERROR, gtk.BUTTONS_OK, msg, dialog)
                    
                except Exception, ex:
                    msg = "Failed to connect: %s." % (str(ex))
                    print msg
                    traceback.print_exc()
                    self.run_message_dialog(gtk.MESSAGE_ERROR, gtk.BUTTONS_OK, msg, dialog)

        dialog.hide()
        return pipe_manager
    
    def connected(self):
        return self.pipe_manager != None
    
    def update_service_callback(self, service):
        try:
            self.pipe_manager.lock.acquire()
            self.pipe_manager.update_service(service)
            self.pipe_manager.fetch_service_status(service)
            
            self.set_status("Service \'%s\' updated.") % (service.display_name)
            
        except RuntimeError, re:
            msg = "Failed to update service: %s." % (re.args[1])
            print msg
            self.set_status(msg)
            traceback.print_exc()
            self.run_message_dialog(gtk.MESSAGE_ERROR, gtk.BUTTONS_OK, msg)
            
        except Exception, ex:
            msg = "Failed to update service: %s." % (str(ex))
            print msg
            self.set_status(msg)
            traceback.print_exc()
            self.run_message_dialog(gtk.MESSAGE_ERROR, gtk.BUTTONS_OK, msg)
            
        finally:
            self.pipe_manager.lock.release()
        
        self.refresh_services_tree_view()
        
    def on_key_press(self, widget, event):
        if event.keyval == gtk.keysyms.F5: #refresh when F5 is pressed
            self.on_refresh_item_activate(None)
        elif event.keyval == gtk.keysyms.Return:
            myev = gtk.gdk.Event(gtk.gdk._2BUTTON_PRESS) #emulate a double-click
            self.on_services_tree_view_button_press(None, myev)

    def on_self_delete(self, widget, event):
        if (self.pipe_manager != None):
            self.on_disconnect_item_activate(self.disconnect_item)
        
        gtk.main_quit()
        return False

    def on_connect_item_activate(self, widget, server = "", transport_type = 0, username = "", password = "", connect_now = False):
        server = server or self.server_address
        transport_type = transport_type or self.transport_type
        username = username or self.username
        
        self.pipe_manager = self.run_connect_dialog(None, server, transport_type, username, password, connect_now)
        if (self.pipe_manager != None):
            self.set_status("Fetching services from %s..." % (server))

            FetchServicesThread(self.pipe_manager, self).start()
            #After this thread runs it will post a connected message.
            #It's not ideal, but it's probably the best solution.
                    
        self.update_sensitivity()
        self.update_captions()
        
    def on_disconnect_item_activate(self, widget):
        if (self.pipe_manager != None):
            self.pipe_manager.close()
            self.pipe_manager = None
            
        self.services_store.clear()
        self.update_sensitivity()
        self.update_captions()

        self.set_status("Disconnected.")
    
    def on_quit_item_activate(self, widget):
        self.on_self_delete(None, None)
    
    def on_refresh_item_activate(self, widget):
        self.set_status("Fetching services from %s..." % (self.server_address))
        FetchServicesThread(self.pipe_manager, self).start()
            
    def on_start_item_activate(self, widget):
        start_service = self.get_selected_service()
        if (start_service == None):
            return

        self.run_service_control_dialog(start_service, None)
        
    def on_stop_item_activate(self, widget):
        stop_service = self.get_selected_service()
        if (stop_service == None):
            return

        self.run_service_control_dialog(stop_service, svcctl.SVCCTL_CONTROL_STOP)

    def on_pause_resume_item_activate(self, widget):
        try:
            pause_resume_service = self.get_selected_service()
            if (pause_resume_service == None):
                return
            
            self.pipe_manager.lock.acquire()
            self.pipe_manager.fetch_service_status(pause_resume_service)
    
        except RuntimeError, re:
            msg = "Failed to fetch service status: %s." % (re.args[1])
            self.set_status(msg)
            print msg
            traceback.print_exc()
            self.run_message_dialog(gtk.MESSAGE_ERROR, gtk.BUTTONS_OK, msg)
        
        except Exception, ex:
            msg = "Failed to fetch service status: %s." % (str(ex))
            self.set_status(msg)
            print msg
            traceback.print_exc()
            self.run_message_dialog(gtk.MESSAGE_ERROR, gtk.BUTTONS_OK, msg)
            
        finally:
            self.pipe_manager.lock.release()

        if (pause_resume_service.state == svcctl.SVCCTL_PAUSED):
            self.run_service_control_dialog(pause_resume_service, svcctl.SVCCTL_CONTROL_CONTINUE)
        elif (pause_resume_service.state == svcctl.SVCCTL_RUNNING):
            self.run_service_control_dialog(pause_resume_service, svcctl.SVCCTL_CONTROL_PAUSE)
            
    def on_properties_item_activate(self, widget):
        edit_service = self.get_selected_service()
        self.run_service_edit_dialog(edit_service, self.update_service_callback)
        
        self.set_status("Service \'%s\' updated." % (edit_service.display_name))

    def on_about_item_activate(self, widget):
        dialog = AboutDialog(
            "PyGWSvcCtl", 
            "A tool to remotely manage the services on a computer.\n Based on Jelmer Vernooij's original Samba-GTK",
            self.icon_pixbuf)
        dialog.run()
        dialog.hide()

    def on_services_tree_view_button_press(self, widget, event):
        if (self.get_selected_service() == None):
            return

        if (event.type == gtk.gdk._2BUTTON_PRESS):
            self.on_properties_item_activate(self.properties_item)
            
    def on_update_captions(self, widget):
        self.update_captions()

    def on_update_sensitivity(self, widget):
        self.update_sensitivity()

#************ END OF CLASS ***************

def PrintUseage():
    print "Usage: %s [OPTIONS]" % (str(os.path.split(__file__)[-1]))
    print "All options are optional. The user will be queried for additional information if needed.\n"
    print "  -s  --server\t\tspecify the server to connect to."
    print "  -u  --user\t\tspecify the user."
    print "  -p  --password\tThe password for the user."
    print "  -t  --transport\tTransport type.\n\t\t\t\t0 for RPC, SMB, TCP/IP\n\t\t\t\t1 for RPC, TCP/IP\n\t\t\t\t2 for localhost."
    print "  -c  --connect-now\tSkip the connect dialog." 

def ParseArgs(argv):
    arguments = {}
    
    try: #get arguments into a nicer format
        opts, args = getopt.getopt(argv, "chu:s:p:t:", ["help", "user=", "server=", "password=", "connect-now", "transport="]) 
    except getopt.GetoptError:           
        PrintUseage()
        sys.exit(2)

    for opt, arg in opts:  
        if opt in ("-h", "--help"): 
            PrintUseage()
            sys.exit(0)
        elif opt in ("-s", "--server"):
            arguments.update({"server":arg})
        elif opt in ("-u", "--user"):
            arguments.update({"username":arg})
        elif opt in ("-p", "--password"):
            arguments.update({"password":arg})
        elif opt in ("-t", "--transport"):
            arguments.update({"transport_type":int(arg)})
        elif opt in ("-c", "--connect-now"):
            arguments.update({"connect_now":True})
    return (arguments)

"""
    Info about the thread locks used in this utility:
the pipe lock is <pipe manager instance>.lock.acquire() and .release()
the gdk lock (main thread lock) is simply gtk.gdk.threads_enter() and .threads_leave(), no need to get an instance
the gdk lock is automatically acquired and released with each iteration of the gtk.main() loop.
    So that means every time a callback function is called in the main thread (for example on_connect_item_activate()), 
    it will automatically grab the lock, run the function, and release it afterwards
If you have to, you may acquire both locks at the same time as long as you get the gdk lock first!
"""
if __name__ == "__main__":
    arguments = ParseArgs(sys.argv[1:]) #the [1:] ignores the first argument, which is the path to our utility
    
    gtk.gdk.threads_init()
    main_window = SvcCtlWindow(**arguments)
    main_window.show_all()
    gtk.main()
