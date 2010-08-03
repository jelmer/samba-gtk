'''
Created on May 17, 2010

@author: shatterz
'''
import sys
import pygtk
pygtk.require20() #require pygtk version 2.0
import gtk
import gtk.glade
import os.path
import getopt

import pygwsam
import pygwregedit
import pygwcrontab
import pygwsvcctl

class SambaUtilities(object):
    def __init__(self, connection_args = {}):
        
        self.create()
        
        self.sam_menubar = None
        self.sam_toolbar = None
        self.regedit_menubar = None
        self.regedit_toolbar = None
        self.svcctl_menubar = None
        self.svcctl_toolbar = None
        self.crontab_menubar = None
        self.crontab_toolbar = None
        
        
        self.connection_args = connection_args
        self.print_redirect_sring = ""
        
        
        
    def create(self):
        #get a builder and put it to work
        builder = gtk.Builder()
        builder.add_from_file("main.glade")
        
        #dictionary for connections, and then connect
        connections = {"on_window1_destroy": gtk.main_quit,
                       "on_quit_item_activate": self.on_quit_item_activate,
                       "on_connect_all_button_clicked": self.on_connect_all_button_clicked,
                       "on_disconnect_all_button_clicked": self.on_disconnect_all_button_clicked,
                       "on_toolbuttontest1_clicked": self.OnNothing,
                       "on_utility_notebook_switch_page": self.on_utility_notebook_switch_page,
                       "on_clear_log_activate": self.on_clear_log_activate,
                       }
        builder.connect_signals(connections)
        
        
        #Handles
        
        self.window = builder.get_object("main_window")
        self.menubar_viewport = builder.get_object("menubar_viewport")
        self.menubar = builder.get_object("menubar")
        self.toolbar_viewport = builder.get_object("toolbar_viewport")
        self.toolbar = builder.get_object("toolbar")
        
        self.messages_textview = builder.get_object("messages_textview")
        
        self.sam_viewport = builder.get_object("sam_viewport")
        self.svcctl_viewport = builder.get_object("svcctl_viewport")
        self.crontab_viewport = builder.get_object("crontab_viewport")
        self.regedit_viewport = builder.get_object("regedit_viewport")
        
        self.progressbar = builder.get_object("progressbar")
        self.statusbar = builder.get_object("statusbar")
        
        self.window.show()
        
        
    def init_sam_page(self):
        if self.sam_viewport.child != None:
            return
        
        
        sam_window = pygwsam.SAMWindow(**self.connection_args) #start up the utility
        sam_window.users_groups_notebook.reparent(self.sam_viewport) #reparent the main widget into a notebook tab
        self.sam_viewport.show_all() #unhide all widgets
        
        #TODO: handle menubar and toolbar
        self.sam_menubar = sam_window.menubar
        self.sam_menubar.unparent()
        self.sam_toolbar = sam_window.toolbar
        self.sam_toolbar.unparent() #We'll be displaying this later. We need to unparent it before attaching it to another container
        sam_window.statusbar = self.statusbar
        
        self.set_status("User tab initialized.")
        
    def init_regedit_page(self):
        if self.regedit_viewport.child != None:
            return

        regedit_window = pygwregedit.RegEditWindow(**self.connection_args) #start up the utility
        regedit_window.hpaned.reparent(self.regedit_viewport) #reparent the main widget into a notebook tab
        self.regedit_viewport.show_all() #unhide all widgets
        
        #TODO: handle menubar and toolbar
        regedit_window.progressbar = self.progressbar
        regedit_window.statusbar = self.statusbar
        
        self.set_status("Regedit tab initialized.")
        
    def init_svcctl_page(self):
        if self.svcctl_viewport.child != None:
            return
        
        
        svcctl_window = pygwsvcctl.SvcCtlWindow(**self.connection_args) #start up the utility
        svcctl_window.scrolledwindow.reparent(self.svcctl_viewport) #reparent the main widget into a notebook tab
        self.svcctl_viewport.show_all() #unhide all widgets
        
        #TODO: handle menubar and toolbar
        svcctl_window.progressbar = self.progressbar
        svcctl_window.statusbar = self.statusbar
        
        self.set_status("Services tab initialized.")
    
    def init_crontab_page(self):
        if self.crontab_viewport.child != None:
            return
        
        
        crontab_window = pygwcrontab.CronTabWindow(**self.connection_args) #start up the utility
        crontab_window.scrolledwindow.reparent(self.crontab_viewport) #reparent the main widget into a notebook tab
        self.crontab_viewport.show_all() #unhide all widgets
        
        #TODO: handle menubar and toolbar
        crontab_window.statusbar = self.statusbar
        
        self.set_status("Scheduled tasks tab initialized.")
        
    def push_status_message(self, message):
        """Pushes a message to the status textview in the main tab. This function inserts a \"\\n\" for you."""
        buffer = self.messages_textview.get_buffer()
        text = buffer.get_text(buffer.get_start_iter(), buffer.get_end_iter())
        text += message + "\n"
        buffer.set_text(text)
        
        #scroll to the bottom
        self.messages_textview.scroll_to_iter(buffer.get_end_iter(), 0.0)
        
    def set_status(self, message):
        self.statusbar.pop(0)
        self.statusbar.push(0, message)
        self.push_status_message(message)
        
    def write(self, string): #Make this class a writeable object. Used so we can redirect print statements
        if string == '\n':
            self.push_status_message(self.print_redirect_sring)
            print >>sys.__stdout__, self.print_redirect_sring #also print the string normally
            self.print_redirect_sring = ""
        else:
            self.print_redirect_sring += string

        
    def on_utility_notebook_switch_page(self, widget, page, page_num):
        if page_num == 0: #main page
            
            #Menubar
            children = self.menubar_viewport.get_children()
            self.menubar_viewport.remove(children[0])
            self.menubar_viewport.add(self.menubar)
            self.menubar_viewport.show_all()
            #Toolbar
            children = self.toolbar_viewport.get_children()
            self.toolbar_viewport.remove(children[0])
            self.toolbar_viewport.add(self.toolbar)
            self.toolbar_viewport.show_all()
            
        
        elif page_num == 1: #Sam page
            if self.sam_viewport.child == None:
                self.init_sam_page()
            
            #Menubar
            children = self.menubar_viewport.get_children()
            self.menubar_viewport.remove(children[0])
            self.menubar_viewport.add(self.sam_menubar)
            self.menubar_viewport.show_all()
            
            #Toolbar
            children = self.toolbar_viewport.get_children()
            self.toolbar_viewport.remove(children[0])
            self.toolbar_viewport.add(self.sam_toolbar)
            self.toolbar_viewport.show_all()
                
        elif page_num == 2: #Services page
            if self.svcctl_viewport.child == None:
                self.init_svcctl_page()
                
        elif page_num == 3: #Crontab page
            if self.crontab_viewport.child == None:
                self.init_crontab_page()
                
        elif page_num == 4: #Regedit page
            if self.regedit_viewport.child == None:
                self.init_regedit_page()
                    
        
    def OnNothing(self, widget):
        """Called when the user wants to add a little sugar"""
        print "Nothing has been done."
        
    def on_connect_all_button_clicked(self, widget):
        #TODO: display a dialog to get info if connection_arguments does not contain --connect-now
        pass
    
    def on_disconnect_all_button_clicked(self, widget):
        #TODO: this
        pass
        
    def on_clear_log_activate(self, widget):
        self.messages_textview.get_buffer().set_text("")
        
        
    def on_quit_item_activate(self, widget):
        """Called when the user hits the quit button"""
        print "now exiting..."
        gtk.main_quit()

class WritableObject:
    def __init__(self):
        self.content = []
    def write(self, string):
        self.content.append(string)

#************ END OF CLASS ***************

def PrintUseage():
    print "Usage: " + str(os.path.split(__file__)[-1]) + " [OPTIONS]"
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


if __name__ == "__main__":
    arguments = ParseArgs(sys.argv[1:])
    gtk.gdk.threads_init()
    main_window = SambaUtilities(arguments)
    sys.stdout = main_window #This class is writeable. This is so we can redirect print statements from the other utilities
    gtk.main()
