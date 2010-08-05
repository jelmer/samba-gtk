#!/usr/bin/python

import sys
import os.path
import traceback
import getopt
import gobject
import gtk

from samba import credentials
from samba.dcerpc import samr
from samba.dcerpc import security
from samba.dcerpc import lsa

from objects import User
from objects import Group

from dialogs import SAMConnectDialog
from dialogs import UserEditDialog
from dialogs import GroupEditDialog
from dialogs import AboutDialog


class SAMPipeManager:
    
    def __init__(self, server_address, transport_type, username, password):
        self.user_list = []
        self.group_list = []
        
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
        
        self.pipe = samr.samr(binding % (server_address), credentials = creds)
        connection_info = samr.ConnectInfo1()
        self.connect_handle = self.pipe.Connect5(None, 
                                                 0x00000030, #SAMR_SERVER_ACCESS_ENUM_DOMAINS | SAMR_SERVER_ACCESS_OPEN_DOMAIN. Copied from a Windows Vista machine. I couldn't find the correct constants in samr or security
                                                 1, 
                                                 connection_info)[2] #Note the [2]!!
        pass
        
    def close(self):
        if (self.pipe != None):
            self.pipe.Close(self.connect_handle)
            
    def fetch_and_get_domain_names(self):
        if (self.pipe == None): # not connected
            return None
        
        domain_name_list = []
        
        self.sam_domains = self.toArray(self.pipe.EnumDomains(self.connect_handle, 0, -1))
        for (rid, domain_name) in self.sam_domains:
            domain_name_list.append(self.get_lsa_string(domain_name))
        
        return domain_name_list
    
    def set_current_domain(self, domain_index):
        self.domain = self.sam_domains[domain_index]
        
        self.domain_sid = self.pipe.LookupDomain(self.connect_handle, self.domain[1])
        self.domain_handle = self.pipe.OpenDomain(self.connect_handle, security.SEC_FLAG_MAXIMUM_ALLOWED, self.domain_sid)
        
    def fetch_users_and_groups(self):
        del self.user_list[:]
        del self.group_list[:]
        
        # fetch groups
        #TODO: this is a test
        result = self.pipe.QueryDisplayInfo(self.domain_handle, 5, 0, 1024, 2147483647)
        (total_size, returned_size, DispInfo) = result
        
        
        #TODO: this section doesn't work
        self.sam_groups = self.toArray(self.pipe.EnumDomainGroups(self.domain_handle, 0, -1))
        
        for (rid, groupname) in self.sam_groups:
            group = self.fetch_group(rid)
            self.group_list.append(group)
            
        # fetch users
        self.sam_users = self.toArray(self.pipe.EnumDomainUsers(self.domain_handle, 0, 0, -1))
        
        for (rid, username) in self.sam_users:
            user = self.fetch_user(rid)
            self.user_list.append(user)

        
    def add_user(self, user):
        """Creates 'user' on the remote computer. This function will update user's RID.
        
        Returns 'user' with updated RID"""
        
        #Creates the new user on the server using default values for everything. Only the username is taken into account here.
        (user_handle, rid) = self.pipe.CreateUser(self.domain_handle, self.set_lsa_string(user.username), security.SEC_FLAG_MAXIMUM_ALLOWED)        
        new_user = self.fetch_user(rid)
        
        user.rid = rid #update the user's RID
        if user.group_list == []: #The user must be part of a group. If the user is not part of any groups, the user is actually part of the "None" group! 
            user.group_list = new_user.group_list #use the default values assigned to the user when it was created on the server, which is probably "None"
        
        self.update_user(user) #send the other user information to the server.
        user = self.fetch_user(rid, user) # just to make sure we have the updated user properties
        self.user_list.append(user)
        
        return user

    def add_group(self, group):
        (group_handle, rid) = self.pipe.CreateDomainGroup(self.domain_handle, self.set_lsa_string(group.name), security.SEC_FLAG_MAXIMUM_ALLOWED)        
        group.rid = rid
        group = self.fetch_group(rid, group)
        
        self.update_group(group)
        group = self.fetch_group(rid, group) # just to make sure we have the updated group properties
        
        
        self.group_list.append(group)

    def update_user(self, user):
        """Submit any changes to 'user' to the server. The User's RID must be correct for this to work.
        This function will call update_user_security() to update user security options.
        
        returns nothing"""
        user_handle = self.pipe.OpenUser(self.domain_handle, security.SEC_FLAG_MAXIMUM_ALLOWED, user.rid)

        info = self.pipe.QueryUserInfo(user_handle, samr.UserNameInformation)
        #info.account_name = self.set_lsa_string(user.username) #Account name should never be changed.
        info.full_name = self.set_lsa_string(user.fullname)
        self.pipe.SetUserInfo(user_handle, samr.UserNameInformation, info)
        
        info = self.pipe.QueryUserInfo(user_handle, samr.UserAdminCommentInformation)
        info.description = self.set_lsa_string(user.description)
        self.pipe.SetUserInfo(user_handle, samr.UserAdminCommentInformation, info)
        
        info = self.pipe.QueryUserInfo(user_handle, samr.UserControlInformation)
        if (user.must_change_password):
            info.acct_flags |= samr.ACB_PW_EXPIRED
        else:
            info.acct_flags &= ~samr.ACB_PW_EXPIRED

        if (user.password_never_expires):
            info.acct_flags |= samr.ACB_PWNOEXP
        else:
            info.acct_flags &= ~samr.ACB_PWNOEXP
            
        if (user.account_disabled):
            info.acct_flags |= samr.ACB_DISABLED
        else:
            info.acct_flags &= ~samr.ACB_DISABLED

        if (user.account_locked_out):
            info.acct_flags |= samr.ACB_AUTOLOCK
        else:
            info.acct_flags &= ~samr.ACB_AUTOLOCK
        self.pipe.SetUserInfo(user_handle, samr.UserControlInformation, info)
        
        #User cannot change password is updated in the security function
        self.update_user_security(user_handle, user)
        
        
        #TODO: this is a test fix for the must_change_password bug
        if user.rid == 1035:
            info = self.pipe.QueryUserInfo(user_handle, samr.UserAllInformation)
            if (user.must_change_password):
                info.workstations = self.set_lsa_string("0x00020018")
                info.fields_present = samr.SAMR_FIELD_WORKSTATIONS
                #info.acct_flags |= samr.ACB_PW_EXPIRED
            else:
                info.workstations = self.set_lsa_string("0x0000ca4e0")
                info.fields_present = samr.SAMR_FIELD_WORKSTATIONS
                #info.acct_flags &= ~samr.ACB_PW_EXPIRED
            #info.fields_present = samr.SAMR_FIELD_ACCT_FLAGS
            
            new_user_handle = self.pipe.OpenUser(self.domain_handle, security.SEC_STD_WRITE_DAC | security.SEC_STD_READ_CONTROL | samr.SAMR_USER_ACCESS_GET_GROUPS | samr.SAMR_USER_ACCESS_SET_PASSWORD | samr.SAMR_USER_ACCESS_GET_ATTRIBUTES | samr.SAMR_USER_ACCESS_SET_ATTRIBUTES | samr.SAMR_USER_ACCESS_SET_LOC_COM, user.rid)
            self.pipe.SetUserInfo(new_user_handle, samr.UserAllInformation, info)
            #self.pipe.SetUserInfo(user_handle, samr.UserAllInformation, info)
            
            info = self.pipe.QueryUserInfo(user_handle, samr.UserAllInformation)
            pass
        

        info = self.pipe.QueryUserInfo(user_handle, samr.UserProfileInformation)
        info.profile_path = self.set_lsa_string(user.profile_path)
        self.pipe.SetUserInfo(user_handle, samr.UserProfileInformation, info)
        
        info = self.pipe.QueryUserInfo(user_handle, samr.UserScriptInformation)
        info.logon_script = self.set_lsa_string(user.logon_script)
        self.pipe.SetUserInfo(user_handle, samr.UserScriptInformation, info)

        info = self.pipe.QueryUserInfo(user_handle, samr.UserHomeInformation)
        info.home_directory = self.set_lsa_string(user.homedir_path)
        
        if (user.map_homedir_drive == -1):
            info.home_drive = self.set_lsa_string("")
        else:
            info.home_drive = self.set_lsa_string(chr(user.map_homedir_drive + ord('A')) + ":")
        self.pipe.SetUserInfo(user_handle, samr.UserHomeInformation, info)
        
        
        # get the user's old groups list
        group_list = self.rwa_list_to_group_list(self.pipe.GetGroupsForUser(user_handle).rids)
 
        # remove the user from groups
        for group in group_list:
            if (user.group_list.count(group) == 0):
                group_handle = self.pipe.OpenGroup(self.domain_handle, security.SEC_FLAG_MAXIMUM_ALLOWED, group.rid)
                self.pipe.DeleteGroupMember(group_handle, user.rid)

        # add the user to groups
        for group in user.group_list:
            if (group_list.count(group) == 0):
                group_handle = self.pipe.OpenGroup(self.domain_handle, security.SEC_FLAG_MAXIMUM_ALLOWED, group.rid)
                self.pipe.AddGroupMember(group_handle, user.rid, samr.SE_GROUP_ENABLED)

    def update_user_security(self, user_handle, user):
        """Updates the access mask for 'user'.
        
        returns nothing"""
        secinfo = self.pipe.QuerySecurity(user_handle, security.SECINFO_DACL)
        sid = str(self.pipe.RidToSid(self.domain_handle, user.rid))
        
        #this is for readability, we could just do secinfo.sd.dacl.aces[i].trustee if we wanted
        security_descriptor = secinfo.sd
        DACL = security_descriptor.dacl
        ace_list = DACL.aces
        ace = None
            
        for item in ace_list:
            if str(item.trustee) == sid:
                ace = item
                break
            
        if ace == None:
            print "unable to fetch security info for", user.username, "because none exists."
            return user
        
        if user.cannot_change_password:
            ace_list[0].access_mask &= ~samr.SAMR_USER_ACCESS_CHANGE_PASSWORD
            ace.access_mask &= ~samr.SAMR_USER_ACCESS_CHANGE_PASSWORD
        else:
            ace_list[0].access_mask |= samr.SAMR_USER_ACCESS_CHANGE_PASSWORD
            ace.access_mask |= samr.SAMR_USER_ACCESS_CHANGE_PASSWORD
            
        self.pipe.SetSecurity(user_handle, security.SECINFO_DACL, secinfo)
        return

    def update_group(self, group):
        group_handle = self.pipe.OpenGroup(self.domain_handle, security.SEC_FLAG_MAXIMUM_ALLOWED, group.rid)

        info = self.set_lsa_string(group.name)
        self.pipe.SetGroupInfo(group_handle, 2, info)
        
        info = self.set_lsa_string(group.description)
        self.pipe.SetGroupInfo(group_handle, 4, info)
        
    def delete_user(self, user):
        user_handle = self.pipe.OpenUser(self.domain_handle, security.SEC_FLAG_MAXIMUM_ALLOWED, user.rid)
        self.pipe.DeleteUser(user_handle)

    def delete_group(self, group):
        group_handle = self.pipe.OpenGroup(self.domain_handle, security.SEC_FLAG_MAXIMUM_ALLOWED, group.rid)
        self.pipe.DeleteDomainGroup(group_handle)
    
    def fetch_user(self, rid, user = None):
        """Fetch the User whose RID is 'rid'. A new User structure is created if the 'user' argument is left out. 
        
        Returns a User"""
        user_handle = self.pipe.OpenUser(self.domain_handle, security.SEC_FLAG_MAXIMUM_ALLOWED, rid)
        
        #this handles most of the information we need
        info = self.pipe.QueryUserInfo(user_handle, samr.UserAllInformation)
        user = self.info_to_user(info, user)
        
        #some settings, such as "user cannot change password", are actually part of an access list (ACL)
        secinfo = self.pipe.QuerySecurity(user_handle, security.SECINFO_DACL)
        user = self.secinfo_to_user(secinfo, user)
        
        
        group_rwa_list = self.pipe.GetGroupsForUser(user_handle).rids
        user.group_list = self.rwa_list_to_group_list(group_rwa_list)
        
        return user
    
    def fetch_group(self, rid, group = None):
        group_handle = self.pipe.OpenGroup(self.domain_handle, security.SEC_FLAG_MAXIMUM_ALLOWED, rid)
        info = self.pipe.QueryGroupInfo(group_handle, 1)
        group = self.info_to_group(info, group)
        group.rid = rid
        
        return group
    
    def info_to_user(self, query_info, user = None):
        """Converts 'query_info' information into a user type. Values in 'user' will be overwriten by this function. If called with 'None' then a new User structure will be created
        
        returns 'user'"""
        if (user == None):
            user = User(self.get_lsa_string(query_info.account_name), 
                        self.get_lsa_string(query_info.full_name), 
                        self.get_lsa_string(query_info.description), 
                        query_info.rid)
        else:
            user.username = self.get_lsa_string(query_info.account_name)
            user.full_name = self.get_lsa_string(query_info.full_name)
            user.description = self.get_lsa_string(query_info.description)
            user.rid = query_info.rid
        
        user.must_change_password = (query_info.acct_flags & samr.ACB_PW_EXPIRED) != 0
        user.password_never_expires = (query_info.acct_flags & samr.ACB_PWNOEXP) != 0
        user.account_disabled = (query_info.acct_flags & samr.ACB_DISABLED) != 0
        user.account_locked_out = (query_info.acct_flags & samr.ACB_AUTOLOCK) != 0
        #cannot_change_password doesn't get set in a flag, it's a little different
        user.profile_path = self.get_lsa_string(query_info.profile_path)
        user.logon_script = self.get_lsa_string(query_info.logon_script)
        user.homedir_path = self.get_lsa_string(query_info.home_directory)
        
        
        
        drive = self.get_lsa_string(query_info.home_drive)
        if (len(drive) == 2):
            user.map_homedir_drive = ord(drive[0]) - ord('A')
        else:
            user.map_homedir_drive = -1
            
        return user
    
    def secinfo_to_user(self, secinfo, user):
        """Takes 'secinfo' and updates the related fields in 'user'
        
        returns updated 'user'"""
        #this is for readability, we could just do secinfo.sd.dacl.aces[0] if we wanted
        security_descriptor = secinfo.sd
        DACL = security_descriptor.dacl
        ace_list = DACL.aces
        
        #we don't really need to find the user in ace_list because the first entry (S-1-1-0) should have the same flags anyways
        ace =  ace_list[0]
        user.cannot_change_password = (samr.SAMR_USER_ACCESS_CHANGE_PASSWORD & ace.access_mask) == 0
        
        return user
    
    def rwa_list_to_group_list(self, rwa_list):
        group_list = []
        
        for rwa in rwa_list:
            group_rid = rwa.rid
            group_to_add = None
            
            for group in self.group_list:
                if (group.rid == group_rid):
                    group_to_add = group
                    break
                
            if (group_to_add != None):
                group_list.append(group_to_add)
            else:
                raise Exception("group not found for rid = %d" % group_rid)
            
        return group_list

    def info_to_group(self, query_info, group = None):
        if (group == None):
            group = Group(self.get_lsa_string(query_info.name), 
                          self.get_lsa_string(query_info.description),  
                          0)
        else:
            group.name = self.get_lsa_string(query_info.name)
            group.description = self.get_lsa_string(query_info.description)
        
        return group

    @staticmethod
    def toArray((handle, array, num_entries)):
        ret = []
        for x in range(num_entries):
            ret.append((array.entries[x].idx, array.entries[x].name))
        return ret

    @staticmethod
    def get_lsa_string(str):
        return str.string
    
    @staticmethod
    def set_lsa_string(str):
        lsa_string = lsa.String()
        lsa_string.string = unicode(str)
        lsa_string.length = len(str)
        lsa_string.size = len(str)
        
        return lsa_string
    

class SAMWindow(gtk.Window):

    def __init__(self, info_callback = None, server = "", username = "", password = "", transport_type = 0, domain_index = 0, connect_now = False):
        super(SAMWindow, self).__init__()
        #Note: Any change to these arguments should probably also be changed in on_connect_item_activate()

        self.create()
        self.pipe_manager = None
        self.users_groups_notebook_page_num = 0
        self.update_captions()
        self.update_sensitivity()
        
        #It's nice to have this info saved when a user wants to reconnect
        self.server_address = server
        self.username = username
        self.transport_type = transport_type
        
        self.set_status("Disconnected.")
        self.on_connect_item_activate(None, server, transport_type, username, password, connect_now, domain_index)
        
        #This is used so the parent program can grab the server info after we've connected.
        if info_callback != None:
            info_callback(server = self.server_address, username = self.username, transport_type = self.transport_type)
        
    def create(self):
        
        # main window        

        accel_group = gtk.AccelGroup()
        
        self.set_title("User/Group Management")
        self.set_default_size(800, 600)
        self.icon_filename = os.path.join(sys.path[0], "images", "group.png")
        self.user_icon_filename = os.path.join(sys.path[0], "images", "user.png")
        self.group_icon_filename = os.path.join(sys.path[0], "images", "group.png")
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
        self.disconnect_item.set_sensitive(False)
        file_menu.add(self.disconnect_item)
        
        self.sel_domain_item = gtk.MenuItem("_Select Domain", accel_group)
        self.sel_domain_item.set_sensitive(False)
        file_menu.add(self.sel_domain_item)
        
        menu_separator_item = gtk.SeparatorMenuItem()
        menu_separator_item.set_sensitive(False)
        file_menu.add(menu_separator_item)
        
        self.quit_item = gtk.ImageMenuItem(gtk.STOCK_QUIT, accel_group)
        file_menu.add(self.quit_item)
        
        
        self.view_item = gtk.MenuItem("_View")
        self.menubar.add(self.view_item)
        
        view_menu = gtk.Menu()
        self.view_item.set_submenu(view_menu)
        
        self.refresh_item = gtk.ImageMenuItem(gtk.STOCK_REFRESH, accel_group)
        self.refresh_item.set_sensitive(False)
        view_menu.add(self.refresh_item)
        
        
        self.user_group_item = gtk.MenuItem("_User")
        self.menubar.add(self.user_group_item)
        
        user_group_menu = gtk.Menu()
        self.user_group_item.set_submenu(user_group_menu)

        self.new_item = gtk.ImageMenuItem(gtk.STOCK_NEW, accel_group)
        self.new_item.set_sensitive(False)
        user_group_menu.add(self.new_item)

        self.delete_item = gtk.ImageMenuItem(gtk.STOCK_DELETE, accel_group)
        self.delete_item.set_sensitive(False)
        user_group_menu.add(self.delete_item)

        self.edit_item = gtk.ImageMenuItem(gtk.STOCK_EDIT, accel_group)
        self.edit_item.set_sensitive(False)
        user_group_menu.add(self.edit_item)

        
        self.policies_item = gtk.MenuItem("_Policies")
        # self.menubar.add(self.policies_item) TODO: implement policies functionality

        policies_menu = gtk.Menu()
        self.policies_item.set_submenu(policies_menu)
        
        self.user_rights_item = gtk.MenuItem("_User Rights...", accel_group)
        self.user_rights_item.set_sensitive(False)
        policies_menu.add(self.user_rights_item)

        self.audit_item = gtk.MenuItem("A_udit...", accel_group)
        self.audit_item.set_sensitive(False)
        policies_menu.add(self.audit_item)

        menu_separator_item = gtk.SeparatorMenuItem()
        menu_separator_item.set_sensitive(False)
        policies_menu.add(menu_separator_item)
        
        self.trust_relations_item = gtk.MenuItem("_Trust relations", accel_group)
        self.trust_relations_item.set_sensitive(False)
        policies_menu.add(self.trust_relations_item)
        
        
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
        
        self.new_button = gtk.ToolButton(gtk.STOCK_NEW)
        self.new_button.set_is_important(True)
        self.toolbar.insert(self.new_button, 3)
                
        self.edit_button = gtk.ToolButton(gtk.STOCK_EDIT)
        self.edit_button.set_is_important(True)
        self.toolbar.insert(self.edit_button, 4)
                
        self.delete_button = gtk.ToolButton(gtk.STOCK_DELETE)
        self.delete_button.set_is_important(True)
        self.toolbar.insert(self.delete_button, 5)
                
        
        # user list
        
        self.users_groups_notebook = gtk.Notebook()
        vbox.pack_start(self.users_groups_notebook, True, True, 0)
        
        scrolledwindow = gtk.ScrolledWindow(None, None)
        scrolledwindow.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        scrolledwindow.set_shadow_type(gtk.SHADOW_IN)
        self.users_groups_notebook.append_page(scrolledwindow, gtk.Label("Users"))
        
        self.users_tree_view = gtk.TreeView()        
        scrolledwindow.add(self.users_tree_view)
        
        column = gtk.TreeViewColumn()
        column.set_title("")
        renderer = gtk.CellRendererPixbuf()
        renderer.set_property("pixbuf", gtk.gdk.pixbuf_new_from_file_at_size(self.user_icon_filename, 22, 22))
        column.pack_start(renderer, True)
        self.users_tree_view.append_column(column)
                
        column = gtk.TreeViewColumn()
        column.set_title("Name")
        column.set_resizable(True)
        column.set_sort_column_id(0)
        renderer = gtk.CellRendererText()
        column.pack_start(renderer, True)
        self.users_tree_view.append_column(column)
        column.add_attribute(renderer, "text", 0)
                
        column = gtk.TreeViewColumn()
        column.set_title("Full Name")
        column.set_resizable(True)
        column.set_expand(True)
        column.set_sort_column_id(1)
        renderer = gtk.CellRendererText()
        column.pack_start(renderer, True)
        self.users_tree_view.append_column(column)
        column.add_attribute(renderer, "text", 1)
        
        column = gtk.TreeViewColumn()
        column.set_title("Description")
        column.set_resizable(True)
        column.set_expand(True)
        column.set_sort_column_id(2)
        renderer = gtk.CellRendererText()
        column.pack_start(renderer, True)
        self.users_tree_view.append_column(column)
        column.add_attribute(renderer, "text", 2)
        
        column = gtk.TreeViewColumn()
        column.set_title("RID")
        column.set_resizable(True)
        column.set_sort_column_id(3)
        renderer = gtk.CellRendererText()
        column.pack_start(renderer, True)
        self.users_tree_view.append_column(column)
        column.add_attribute(renderer, "text", 3)
        
        self.users_store = gtk.ListStore(gobject.TYPE_STRING, gobject.TYPE_STRING, gobject.TYPE_STRING, gobject.TYPE_INT)
        self.users_store.set_sort_column_id(0, gtk.SORT_ASCENDING)
        self.users_tree_view.set_model(self.users_store)


        # group list

        scrolledwindow = gtk.ScrolledWindow(None, None)
        scrolledwindow.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        scrolledwindow.set_shadow_type(gtk.SHADOW_IN)
        self.users_groups_notebook.append_page(scrolledwindow, gtk.Label("Groups"))
        
        self.groups_tree_view = gtk.TreeView()
        scrolledwindow.add(self.groups_tree_view)
        
        column = gtk.TreeViewColumn()
        column.set_title("Icon")
        renderer = gtk.CellRendererPixbuf()
        renderer.set_property("pixbuf", gtk.gdk.pixbuf_new_from_file_at_size(self.group_icon_filename, 22, 22))
        column.pack_start(renderer, True)
        self.groups_tree_view.append_column(column)

        column = gtk.TreeViewColumn()
        column.set_title("Name")
        column.set_resizable(True)
        column.set_sort_column_id(0)
        renderer = gtk.CellRendererText()
        column.pack_start(renderer, True)
        self.groups_tree_view.append_column(column)
        column.add_attribute(renderer, "text", 0)
                
        column = gtk.TreeViewColumn()
        column.set_title("Description")
        column.set_resizable(True)
        column.set_sort_column_id(1)
        column.set_expand(True)
        renderer = gtk.CellRendererText()
        column.pack_start(renderer, True)
        self.groups_tree_view.append_column(column)
        column.add_attribute(renderer, "text", 1)
        
        column = gtk.TreeViewColumn()
        column.set_title("RID")
        column.set_resizable(True)
        column.set_sort_column_id(2)
        renderer = gtk.CellRendererText()
        column.pack_start(renderer, True)
        self.groups_tree_view.append_column(column)
        column.add_attribute(renderer, "text", 2)

        self.groups_store = gtk.ListStore(gobject.TYPE_STRING, gobject.TYPE_STRING, gobject.TYPE_INT)
        self.groups_store.set_sort_column_id(0, gtk.SORT_ASCENDING)
        self.groups_tree_view.set_model(self.groups_store)


        # status bar

        self.statusbar = gtk.Statusbar()
        self.statusbar.set_has_resize_grip(True)
        vbox.pack_start(self.statusbar, False, False, 0)
        
        
        # signals/events
        
        self.connect("delete_event", self.on_self_delete)
        self.connect("key-press-event", self.on_key_press)
        
        self.connect_item.connect("activate", self.on_connect_item_activate)
        self.disconnect_item.connect("activate", self.on_disconnect_item_activate)
        self.sel_domain_item.connect("activate", self.on_sel_domain_item_activate)
        self.quit_item.connect("activate", self.on_quit_item_activate)
        self.refresh_item.connect("activate", self.on_refresh_item_activate)
        self.new_item.connect("activate", self.on_new_item_activate)
        self.delete_item.connect("activate", self.on_delete_item_activate)
        self.edit_item.connect("activate", self.on_edit_item_activate)
        self.user_rights_item.connect("activate", self.on_user_rights_item_activate)
        self.audit_item.connect("activate", self.on_audit_item_activate)
        self.trust_relations_item.connect("activate", self.on_trust_relations_item_activate)        
        self.about_item.connect("activate", self.on_about_item_activate)
        
        self.connect_button.connect("clicked", self.on_connect_item_activate)
        self.disconnect_button.connect("clicked", self.on_disconnect_item_activate)
        self.new_button.connect("clicked", self.on_new_item_activate)
        self.delete_button.connect("clicked", self.on_delete_item_activate)
        self.edit_button.connect("clicked", self.on_edit_item_activate)
        
        self.users_tree_view.get_selection().connect("changed", self.on_update_sensitivity)
        self.users_tree_view.connect("button_press_event", self.on_users_tree_view_button_press)
        self.groups_tree_view.get_selection().connect("changed", self.on_update_sensitivity)
        self.groups_tree_view.connect("button_press_event", self.on_groups_tree_view_button_press)
        self.users_groups_notebook.connect("switch-page", self.on_users_groups_notebook_switch_page)
        
        self.add_accel_group(accel_group)
        

    def refresh_user_list_view(self):
        if not self.connected():
            return None
        
        (model, paths) = self.users_tree_view.get_selection().get_selected_rows()
        
        self.users_store.clear()
        for user in self.pipe_manager.user_list:
            self.users_store.append(user.list_view_representation())

        if (len(paths) > 0):
            self.users_tree_view.get_selection().select_path(paths[0])

    def refresh_group_list_view(self):
        if not self.connected():
            return None
        
        (model, paths) = self.groups_tree_view.get_selection().get_selected_rows()

        self.groups_store.clear()
        for group in self.pipe_manager.group_list:
            self.groups_store.append(group.list_view_representation())
            
        if (len(paths) > 0):
            self.groups_tree_view.get_selection().select_path(paths[0])

    def get_selected_user(self):
        if not self.connected():
            return None
        
        (model, iter) = self.users_tree_view.get_selection().get_selected()
        if (iter == None): # no selection
            return None
        else:            
            username = model.get_value(iter, 0)
            user_list = [user for user in self.pipe_manager.user_list if user.username == username]
            if (len(user_list) > 0):
                return user_list[0]
            else:
                return None

    def get_selected_group(self):
        if not self.connected():
            return None
        
        (model, iter) = self.groups_tree_view.get_selection().get_selected()
        if (iter == None): # no selection
            return None
        else:            
            name = model.get_value(iter, 0)
            group_list = [group for group in self.pipe_manager.group_list if group.name == name]
            if (len(group_list) > 0):
                return group_list[0]
            else:
                return None

    def set_status(self, message):
        self.statusbar.pop(0)
        self.statusbar.push(0, message)
        
    def update_sensitivity(self):
        connected = (self.pipe_manager != None)
        user_selected = (self.get_selected_user() != None)
        group_selected = (self.get_selected_group() != None)
        selected = [user_selected, group_selected][self.users_groups_notebook_page_num]
        
        self.connect_item.set_sensitive(not connected)
        self.disconnect_item.set_sensitive(connected)
        self.sel_domain_item.set_sensitive(connected)
        self.refresh_item.set_sensitive(connected)
        self.new_item.set_sensitive(connected)
        self.delete_item.set_sensitive(connected and selected)
        self.edit_item.set_sensitive(connected and selected)
        self.user_rights_item.set_sensitive(connected)
        self.audit_item.set_sensitive(connected)
        self.trust_relations_item.set_sensitive(connected)

        self.connect_button.set_sensitive(not connected)
        self.disconnect_button.set_sensitive(connected)
        self.new_button.set_sensitive(connected)
        self.delete_button.set_sensitive(connected and selected)
        self.edit_button.set_sensitive(connected and selected)

    def update_captions(self):
        self.user_group_item.get_child().set_text(["Users", "Groups"][self.users_groups_notebook_page_num > 0])
        self.new_button.set_tooltip_text(["Create a new user", "Create a new group"][self.users_groups_notebook_page_num > 0])
        self.edit_button.set_tooltip_text(["Edit user's properties", "Edit group's properties"][self.users_groups_notebook_page_num > 0])
        self.delete_button.set_tooltip_text(["Delete the user", "Delete the group"][self.users_groups_notebook_page_num > 0])

    def run_message_dialog(self, type, buttons, message, parent = None):
        if (parent == None):
            parent = self
        
        message_box = gtk.MessageDialog(parent, gtk.DIALOG_MODAL, type, buttons, message)
        response = message_box.run()
        message_box.hide()
        
        return response

    def run_user_edit_dialog(self, user = None, apply_callback = None):
        dialog = UserEditDialog(self.pipe_manager, user)
        dialog.show_all()
        
        # loop to handle the applies
        while True:
            response_id = dialog.run()
            
            if (response_id in [gtk.RESPONSE_OK, gtk.RESPONSE_APPLY]):
                problem_msg = dialog.check_for_problems()
                
                if (problem_msg != None):
                    self.run_message_dialog(gtk.MESSAGE_ERROR, gtk.BUTTONS_OK, problem_msg, dialog)
                else:
                    dialog.values_to_user()
                    
                    if (apply_callback != None): #seems like there's only a callback when a user is modified, never when creating a new user.
                        apply_callback(dialog.user)
                        dialog.user_to_values()
                        
                    if (response_id == gtk.RESPONSE_OK):
                        dialog.hide()
                        break
                        
            else:
                dialog.hide()
                return None
        
        return dialog.user

    def run_group_edit_dialog(self, group = None, apply_callback = None):
        dialog = GroupEditDialog(self.pipe_manager, group)
        dialog.show_all()
        
        # loop to handle the applies
        while True:
            response_id = dialog.run()
            
            if (response_id in [gtk.RESPONSE_OK, gtk.RESPONSE_APPLY]):
                problem_msg = dialog.check_for_problems()
                
                if (problem_msg != None):
                    self.run_message_dialog(gtk.MESSAGE_ERROR, gtk.BUTTONS_OK, problem_msg, dialog)
                else:
                    dialog.values_to_group()
                    
                    if (apply_callback != None):
                        apply_callback(dialog.thegroup)
                        dialog.group_to_values()
                                         
                    if (response_id == gtk.RESPONSE_OK):
                        dialog.hide()
                        break
            
            else:
                dialog.hide()
                return None
        
        return dialog.thegroup

    def run_connect_dialog(self, pipe_manager, server_address, transport_type, username, password = "", connect_now = False, domain_index = 0, domains = None):
        connect_now2 = connect_now #this other value is used later on to skip domain selection. 
        #We need a second variable for this or else we would freeze if we had an error while connecting
        
        dialog = SAMConnectDialog(server_address, transport_type, username, password)
        dialog.show_all()
        
        if (domains == None):
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
                        domain_index = 0
                        self.domain_index = domain_index
                        password = dialog.get_password()
                        
                        pipe_manager = SAMPipeManager(server_address, transport_type, username, password)
                        domains = pipe_manager.fetch_and_get_domain_names()
                        break
                    
                    except RuntimeError, re:
                        if re.args[1] == 'Logon failure': #user got the password wrong
                            self.run_message_dialog(gtk.MESSAGE_ERROR, gtk.BUTTONS_OK, "Failed to connect: Invalid username or password.", dialog)
                            dialog.password_entry.grab_focus()
                            dialog.password_entry.select_region(0, -1) #select all the text in the password box
                        elif re.args[1] == 'Access denied':
                            self.run_message_dialog(gtk.MESSAGE_ERROR, gtk.BUTTONS_OK, "Failed to connect: Access denied.", dialog)
                            dialog.password_entry.grab_focus()
                            dialog.password_entry.select_region(0, -1)
                        elif re.args[1] == 'NT_STATUS_HOST_UNREACHABLE':
                            self.run_message_dialog(gtk.MESSAGE_ERROR, gtk.BUTTONS_OK, "Failed to connect: Could not contact the server", dialog)
                            dialog.server_address_entry.grab_focus()
                            dialog.server_address_entry.select_region(0, -1)
                        elif re.args[1] == 'NT_STATUS_NETWORK_UNREACHABLE':
                            self.run_message_dialog(gtk.MESSAGE_ERROR, gtk.BUTTONS_OK, "Failed to connect: The network is unreachable.\n\nPlease check your network connection.", dialog)
                        else:
                            msg = "Failed to connect: " + re.args[1] + "."
                            print msg
                            traceback.print_exc()                        
                            self.run_message_dialog(gtk.MESSAGE_ERROR, gtk.BUTTONS_OK, msg, dialog)
                        
                    except Exception, ex:
                        msg = "Failed to connect: " + str(ex) + "."
                        print msg
                        traceback.print_exc()
                        self.run_message_dialog(gtk.MESSAGE_ERROR, gtk.BUTTONS_OK, msg, dialog)
        
        dialog.set_domains(domains, self.domain_index)
        #return RESPONSE_OK if we were told to auto-connect. Otherwise run the dialog
        response_id = connect_now2 and gtk.RESPONSE_OK or dialog.run()
        dialog.hide()
        
        if (response_id != gtk.RESPONSE_OK):
            return None
        else:
            self.domain_index = dialog.get_domain_index()
            pipe_manager.set_current_domain(self.domain_index)
        
        return pipe_manager
    
    def connected(self):
        return self.pipe_manager != None
    
    def update_user_callback(self, user):
        try:
            self.pipe_manager.update_user(user)

            self.set_status("User '" + user.username + "' updated.")

        except RuntimeError, re:
            msg = "Failed to update user: " + re.args[1] + "."
            print msg
            self.set_status(msg)
            traceback.print_exc()
            self.run_message_dialog(gtk.MESSAGE_ERROR, gtk.BUTTONS_OK, msg)
        
        except Exception, ex:
            msg = "Failed to update user: " + str(ex) + "."
            print msg
            self.set_status(msg)
            traceback.print_exc()
            self.run_message_dialog(gtk.MESSAGE_ERROR, gtk.BUTTONS_OK, msg)
        
        finally:
            self.pipe_manager.fetch_user(user.rid, user) # to make sure we have the updated user properties. This has caught bugs already!
            self.refresh_user_list_view()

    def update_group_callback(self, group):
        try:
            self.pipe_manager.update_group(group)

            self.set_status("Group '" + group.name + "' updated.")

        except RuntimeError, re:
            msg = "Failed to update group: " + re.args[1] + "."
            print msg
            self.set_status(msg)
            traceback.print_exc()
            self.run_message_dialog(gtk.MESSAGE_ERROR, gtk.BUTTONS_OK, msg)
        
        except Exception, ex:
            msg = "Failed to update group: " + str(ex) + "."
            print msg
            self.set_status(msg)
            traceback.print_exc()
            self.run_message_dialog(gtk.MESSAGE_ERROR, gtk.BUTTONS_OK, msg)
        
        finally:
            self.pipe_manager.fetch_group(group.rid, group) # just to make sure we have the updated group properties
            self.refresh_group_list_view()
            
    def on_key_press(self, widget, event):
        if event.keyval == gtk.keysyms.F5: 
            self.on_refresh_item_activate(None)
        elif event.keyval == gtk.keysyms.Delete:
            self.on_delete_item_activate(None)
        elif event.keyval == gtk.keysyms.Return:
            myev = gtk.gdk.Event(gtk.gdk._2BUTTON_PRESS) #emulate a double-click
            if self.users_groups_notebook_page_num == 0:
                self.on_users_tree_view_button_press(None, myev)
            else:
                self.on_groups_tree_view_button_press(None, myev)
            
    def on_self_delete(self, widget, event):
        if (self.pipe_manager != None):
            self.on_disconnect_item_activate(self.disconnect_item)
        
        gtk.main_quit()
        return False

    def on_connect_item_activate(self, widget, server = "", transport_type = 0, username = "", password = "", connect_now = False, domain_index = 0):
        server = server or self.server_address
        transport_type = transport_type or self.transport_type
        username = username or self.username
        
        try:
            self.pipe_manager = self.run_connect_dialog(None, server, transport_type, username, password, connect_now, domain_index)
            if (self.pipe_manager != None):
                self.pipe_manager.fetch_users_and_groups()
                
                self.set_status("Connected to " + server + "/" + SAMPipeManager.get_lsa_string(self.pipe_manager.domain[1]) + ".")
            
        except RuntimeError, re:
            msg = "Failed to open the selected domain: " + re.args[1] + "."
            self.set_status(msg)
            print msg
            traceback.print_exc()
            self.run_message_dialog(gtk.MESSAGE_ERROR, gtk.BUTTONS_OK, msg)
        
        except Exception, ex:
            msg = "Failed to open the selected domain: " + str(ex) + "."
            self.set_status(msg)
            print msg
            traceback.print_exc()
            self.run_message_dialog(gtk.MESSAGE_ERROR, gtk.BUTTONS_OK, msg)
        
        self.refresh_user_list_view()
        self.refresh_group_list_view()
        self.update_sensitivity()
        
    def on_disconnect_item_activate(self, widget):
        if (self.pipe_manager != None):
            self.pipe_manager.close()
            self.pipe_manager = None
            
        self.users_store.clear()
        self.groups_store.clear()       
        self.update_sensitivity()

        self.set_status("Disconnected.")
    
    def on_sel_domain_item_activate(self, widget):
        try:
            self.pipe_manager = self.run_connect_dialog(self.pipe_manager, self.server_address, self.transport_type, self.username, domains = self.pipe_manager.fetch_and_get_domain_names())
            if (self.pipe_manager != None):
                self.pipe_manager.fetch_users_and_groups()
                
                self.set_status("Connected to " + self.server_address + "/" + SAMPipeManager.get_lsa_string(self.pipe_manager.domain[1]) + ".")
        
        except RuntimeError, re:
            msg = "Failed to open the selected domain: " + re.args[1] + "."
            self.set_status(msg)
            print msg
            traceback.print_exc()
            self.run_message_dialog(gtk.MESSAGE_ERROR, gtk.BUTTONS_OK, msg)
        
        except Exception, ex:
            msg = "Failed to open the selected domain: " + str(ex) + "."
            self.set_status(msg)
            print msg
            traceback.print_exc()
            self.run_message_dialog(gtk.MESSAGE_ERROR, gtk.BUTTONS_OK, msg)
        
        self.refresh_user_list_view()
        self.refresh_group_list_view()
        self.update_sensitivity()

    def on_quit_item_activate(self, widget):
        self.on_self_delete(None, None)
    
    def on_refresh_item_activate(self, widget):
        try:
            self.pipe_manager.fetch_users_and_groups()
            
        except RuntimeError, re:
            msg = "Failed to refresh SAM info: " + re.args[1] + "."
            self.set_status(msg)
            print msg
            traceback.print_exc()
            self.run_message_dialog(gtk.MESSAGE_ERROR, gtk.BUTTONS_OK, msg)
        
        except Exception, ex:
            msg = "Failed to refresh SAM info: " + str(ex) + "."
            self.set_status(msg)
            print msg
            traceback.print_exc()
            self.run_message_dialog(gtk.MESSAGE_ERROR, gtk.BUTTONS_OK, msg)
            
        self.refresh_user_list_view()
        self.refresh_group_list_view()
        
        self.set_status("Successfully refreshed Users and Groups")
        
        #deselect any selected groups and users
        (model, iter) = self.users_tree_view.get_selection().get_selected()
        if iter == None: 
            return
        selector = self.users_tree_view.get_selection()
        selector.unselect_iter(iter)
        
        (model, iter) = self.groups_tree_view.get_selection().get_selected()
        if iter == None: 
            return
        selector = self.groups_tree_view.get_selection()
        selector.unselect_iter(iter)


        
    def on_new_item_activate(self, widget):
        if (self.users_groups_notebook_page_num == 0): # users tab
            new_user = self.run_user_edit_dialog()
            if (new_user == None):
                self.set_status("User creation canceled")
                return
            
            try:
                self.pipe_manager.add_user(new_user)
                self.pipe_manager.fetch_users_and_groups()
                
                self.set_status("Successfully created user '" + new_user.username + "'.")
            
            except RuntimeError, re:
                msg = "Failed to create user: " + re.args[1] + "."
                self.set_status(msg)
                print msg
                traceback.print_exc()
                self.run_message_dialog(gtk.MESSAGE_ERROR, gtk.BUTTONS_OK, msg)
            
            except Exception, ex:
                msg = "Failed to create user: " + str(ex) + "."
                self.set_status(msg)
                print msg
                traceback.print_exc()
                self.run_message_dialog(gtk.MESSAGE_ERROR, gtk.BUTTONS_OK, msg)
            
            self.refresh_user_list_view()

        else: # groups tab
            new_group = self.run_group_edit_dialog()
            if (new_group == None):
                return
            
            try:
                self.pipe_manager.add_group(new_group)
                self.pipe_manager.fetch_users_and_groups()
                
                self.set_status("Successfully created group '" + new_group.name + "'.")
                
            except RuntimeError, re:
                msg = "Failed to create group: " + re.args[1] + "."
                self.set_status(msg)
                print msg
                traceback.print_exc()
                self.run_message_dialog(gtk.MESSAGE_ERROR, gtk.BUTTONS_OK, msg)
            
            except Exception, ex:
                msg = "Failed to create group: " + str(ex) + "."
                self.set_status(msg)
                print msg
                traceback.print_exc()
                self.run_message_dialog(gtk.MESSAGE_ERROR, gtk.BUTTONS_OK, msg)
                
            self.refresh_group_list_view()
            
    def on_delete_item_activate(self, widget):
        if (self.users_groups_notebook_page_num == 0): # users tab
            del_user = self.get_selected_user()
    
            if (self.run_message_dialog(gtk.MESSAGE_QUESTION, gtk.BUTTONS_YES_NO, "Do you want to delete user '%s'?" % del_user.username) != gtk.RESPONSE_YES):
                return 
            
            try:
                self.pipe_manager.delete_user(del_user)
                self.pipe_manager.fetch_users_and_groups()
                
                self.set_status("Successfully deleted user '" + del_user.username + "'.")
            
            except RuntimeError, re:
                msg = "Failed to delete user: " + re.args[1] + "."
                self.set_status(msg)
                print msg
                traceback.print_exc()
                self.run_message_dialog(gtk.MESSAGE_ERROR, gtk.BUTTONS_OK, msg)
            
            except Exception, ex:
                msg = "Failed to delete user: " + str(ex) + "."
                self.set_status(msg)
                print msg
                traceback.print_exc()
                self.run_message_dialog(gtk.MESSAGE_ERROR, gtk.BUTTONS_OK, msg)
            
            self.refresh_user_list_view()

        else: # groups tab
            del_group = self.get_selected_group()
    
            if (self.run_message_dialog(gtk.MESSAGE_QUESTION, gtk.BUTTONS_YES_NO, "Do you want to delete group '%s'?" % del_group.name) != gtk.RESPONSE_YES):
                return 
            
            try:
                self.pipe_manager.delete_group(del_group)
                self.pipe_manager.fetch_users_and_groups()
                
                self.set_status("Successfully deleted group '" + del_group.name + "'.")

            except RuntimeError, re:
                msg = "Failed to delete group: " + re.args[1] + "."
                self.set_status(msg)
                print msg
                traceback.print_exc()
                self.run_message_dialog(gtk.MESSAGE_ERROR, gtk.BUTTONS_OK, msg)
            
            except Exception, ex:
                msg = "Failed to delete group: " + str(ex) + "."
                self.set_status(msg)
                print msg
                traceback.print_exc()
                self.run_message_dialog(gtk.MESSAGE_ERROR, gtk.BUTTONS_OK, msg)
                
            self.refresh_group_list_view()             
            
        
    def on_edit_item_activate(self, widget):
        if (self.users_groups_notebook_page_num == 0): # users tab
            edit_user = self.get_selected_user()
            self.run_user_edit_dialog(edit_user, self.update_user_callback)
            
        else: # groups tab
            edit_group = self.get_selected_group()
            self.run_group_edit_dialog(edit_group, self.update_group_callback)

    def on_user_rights_item_activate(self, widget):
        pass
    
    def on_audit_item_activate(self, widget):
        pass
    
    def on_trust_relations_item_activate(self, widget):
        pass
    
    def on_about_item_activate(self, widget):
        dialog = AboutDialog(
                             "PyGWSAM", 
                             "A tool to manage accounts on a SAM server.\n Based on Jelmer Vernooij's original Samba-GTK",
                             self.icon_pixbuf
                             )
        dialog.run()
        dialog.hide()

    def on_users_tree_view_button_press(self, widget, event):
        if (self.get_selected_user() == None):
            return
        
        if (event.type == gtk.gdk._2BUTTON_PRESS):
            self.on_edit_item_activate(self.edit_item)

    def on_groups_tree_view_button_press(self, widget, event):
        if (self.get_selected_group() == None):
            return

        if (event.type == gtk.gdk._2BUTTON_PRESS):
            self.on_edit_item_activate(self.edit_item)

    def on_users_groups_notebook_switch_page(self, widget, page, page_num):
        self.users_groups_notebook_page_num = page_num # workaround - the signal is emitted before the actual change
        self.update_captions()
        self.update_sensitivity()
        
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
    #TODO: mention domain index. And maybe come up with a better way of handling it?

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
    arguments = ParseArgs(sys.argv[1:]) #the [1:] ignores the first argument, which is the path to our utility
    
    main_window = SAMWindow(**arguments)
    main_window.show_all()
    gtk.main()