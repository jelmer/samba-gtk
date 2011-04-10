#!/usr/bin/python

import sys
import os.path
import traceback
import threading
import getopt

import gobject
import gtk
import pango

from samba import credentials
from samba.dcerpc import winreg, security
from samba.dcerpc import misc

from objects import RegistryKey
from objects import RegistryValue

from dialogs import WinRegConnectDialog
from dialogs import RegValueEditDialog
from dialogs import RegKeyEditDialog
from dialogs import RegRenameDialog
from dialogs import RegSearchDialog
from dialogs import RegPermissionsDialog
from dialogs import AboutDialog


class WinRegPipeManager(object):

    def __init__(self, server_address, transport_type, username, password):
        self.service_list = []
        self.lock = threading.RLock()

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
        self.pipe = winreg.winreg(binding % (server_address), credentials = creds)

        self.open_well_known_keys()

    def close(self):
        pass # apparently there's no .Close() method for this pipe

    def ls_key(self, key, regedit_window=None, progress_bar=True, confirm=True):
        """this function gets a list of values and subkeys
        NOTE: this function will acquire the pipe manager lock and gdk lock on its own. Do Not Acquire Either Lock Before Calling This Function!
        \tThis means you can NOT call this function from the main thread with the regedit_window argument or you will have a deadlock. Calling without the regedit_window argument is fine.

        returns (subkey_list, value_list)"""
        subkey_list = []
        value_list = []

        update_GUI = (regedit_window != None)

        self.lock.acquire()
        try: #this can cause access denied errors
            path_handles = self.open_path(key)
        except Exception as ex:
            raise ex
        finally:
            self.lock.release()

        key_handle = path_handles[-1]
        blank_buff = WinRegPipeManager.winreg_string_buf("")

        if (update_GUI and progress_bar):
            num_subkeys = 4800.0 #backup value
            self.lock.acquire()
            try:
                num_subkeys = float(self.pipe.QueryInfoKey(key_handle, WinRegPipeManager.winreg_string(""))[1])
            except RuntimeError as re:
                print "Failed to fetch key information for %s: %s." % (key.get_absolute_path(), re.args[1])
            finally:
                self.lock.release()

        index = 0
        while True: #get a list of subkeys
            try:
                self.lock.acquire()
                (subkey_name, subkey_class, subkey_changed_time) = self.pipe.EnumKey(key_handle,
                                                                                     index,
                                                                                     blank_buff,
                                                                                     blank_buff,
                                                                                     None
                                                                                     )
                self.lock.release() #we want to release the pipe lock before grabbing the gdk lock or else we might cause a deadlock!

                subkey = RegistryKey(subkey_name.name, key)
                subkey_list.append(subkey)

                if (update_GUI):
                    gtk.gdk.threads_enter()
                    regedit_window.set_status("Fetching key: %s" % (subkey_name.name))
                    if (progress_bar):
                        if (index < num_subkeys): #the value of total was a guess so this may cause a GtkWarning for setting fraction to a value above 1.0
                            regedit_window.progressbar.set_fraction(index/num_subkeys)
                            regedit_window.progressbar.show() #other threads calling ls_key() may finish and hide the progress bar.
                    gtk.gdk.threads_leave()

                index += 1

            except RuntimeError as re:
                self.lock.release()
                if (re.args[0] == 0x103): #0x103 is WERR_NO_MORE_ITEMS, so we're done
                    if (update_GUI and progress_bar):
                        gtk.gdk.threads_enter()
                        regedit_window.progressbar.hide()
                        gtk.gdk.threads_leave()
                    break
                else:
                    raise re

        index = 0
        while True: #get a list of values for the key
            try:
                self.lock.acquire()
                (value_name, value_type, value_data, value_length) = self.pipe.EnumValue(key_handle,
                                                                                         index,
                                                                                         WinRegPipeManager.winreg_val_name_buf(""),
                                                                                         0,
                                                                                         [],
                                                                                         8192
                                                                                         )
                self.lock.release()

                value = RegistryValue(value_name.name, value_type, value_data, key)
                value_list.append(value)

                #there's no need to update GUI here since there's usually few Values.
                #Additionally, many values are named "" which is later changed to "(Default)".
                #So printing '"fetching: "+value.name' might look like a glitch to the user.

                index += 1

            except RuntimeError as re:
                self.lock.release()
                if (re.args[0] == 0x103): #0x103 is WERR_NO_MORE_ITEMS
                    break
                else:
                    raise re

        self.lock.acquire()
        try:
            self.close_path(path_handles)
        finally:
            self.lock.release()

        default_value_list = [value for value in value_list if value.name == ""]
        if (len(default_value_list) == 0):
            value = RegistryValue("(Default)", misc.REG_SZ, [], key)
            value_list.append(value)
        else:
            default_value_list[0].name = "(Default)"

        if (update_GUI and confirm):
            gtk.gdk.threads_enter()
            regedit_window.set_status("Successfully fetched keys and values of %s." % (key.name))
            gtk.gdk.threads_leave()

#        #The reference count to Py_None is still not right: It climbs to infinity!
#        print "Finish ls_key()", sys.getrefcount(None)
        return (subkey_list, value_list)

    def get_subkeys_for_key(self, key):
        """this function gets a list subkeys for 'key'

        returns subkey_list"""

        subkey_list = []
        path_handles = self.open_path(key)
        key_handle = path_handles[-1]
        blank_buff = WinRegPipeManager.winreg_string_buf("")
        index = 0

        while True: #get a list of subkeys
            try:
                (subkey_name,
                 subkey_class,
                 subkey_changed_time) = self.pipe.EnumKey(key_handle, index, blank_buff, blank_buff, None)

                subkey = RegistryKey(subkey_name.name, key)
                subkey_list.append(subkey)

                index += 1

            except RuntimeError as re:
                if (re.args[0] == 0x103): #0x103 is WERR_NO_MORE_ITEMS, so we're done
                    break
                else:
                    raise re

        self.close_path(path_handles)

        return subkey_list

    def get_values_for_key(self, key):
        """this function gets a list of values for 'key'

        returns a list of values"""

        value_list = []
        path_handles = self.open_path(key)
        key_handle = path_handles[-1]
        index = 0

        while True: #get a list of values for the key
            try:
                (value_name,
                 value_type,
                 value_data,
                 value_length) = self.pipe.EnumValue(key_handle,
                                                     index,
                                                     WinRegPipeManager.winreg_val_name_buf(""),
                                                     0,
                                                     [],
                                                     8192
                                                     )

                value = RegistryValue(value_name.name, value_type, value_data, key)
                value_list.append(value)

                index += 1

            except RuntimeError as re:
                if (re.args[0] == 0x103): #0x103 is WERR_NO_MORE_ITEMS
                    break
                else:
                    raise re

        self.close_path(path_handles)

        #Every key is supposted to have a default value. If this key doesn't have one, we'll display a blank one
        default_value_list = [value for value in value_list if value.name == ""]
        if (len(default_value_list) == 0):
            value = RegistryValue("(Default)", misc.REG_SZ, [], key)
            value_list.append(value)
        else:
            default_value_list[0].name = "(Default)"

        return value_list

    def get_key_security(self, key):
        #TODO: this

        path_handles = self.open_path(key)
        key_handle = path_handles[-1]


        key_sec_data = winreg.KeySecurityData()
        key_sec_data.size = 99999999 #TODO: find a better number.
        #Fetch the DACL
        result = self.pipe.GetKeySecurity(key_handle, security.SECINFO_DACL , key_sec_data)

        #This is what Vista does. I don't know what it means...
        vista_key_sec_data1 = self.pipe.GetKeySecurity(key_handle, 0x0e4fcce7 , key_sec_data)
        #vista_key_sec_data2 = self.pipe.GetKeySecurity(key_handle, 0xb234a886 , key_sec_data) #this crashes, "Expected type int"



        self.close_path(path_handles)

        return key_sec_data


    def create_key(self, key):
        path_handles = self.open_path(key.parent)
        key_handle = path_handles[len(path_handles) - 1]

        (new_handle, action_taken) = self.pipe.CreateKey(
            key_handle,
            WinRegPipeManager.winreg_string(key.name),
            WinRegPipeManager.winreg_string(key.name),
            0,
            winreg.KEY_ENUMERATE_SUB_KEYS | winreg.KEY_CREATE_SUB_KEY | winreg.KEY_QUERY_VALUE | winreg.KEY_SET_VALUE,
            None,
            winreg.REG_ACTION_NONE) #why this value isn't winreg.REG_CREATED_NEW_KEY is beyond me. I'm not even sure why this value is needed, what were the designers thinking?

        path_handles.append(new_handle)

        self.close_path(path_handles)

    def move_key(self, key, old_name):
        #TODO: implement this
        raise NotImplementedError("Not implemented")

    def remove_key(self, key):
        """Deletes 'key' and recursively deletes all subkeys under it.

        """
        subkey_list = self.get_subkeys_for_key(key)

        for subkey in subkey_list:
            self.remove_key(subkey)

        path_handles = self.open_path(key)
        key_handle = path_handles[len(path_handles) - 2]

        self.pipe.DeleteKey(key_handle, WinRegPipeManager.winreg_string(key.name))
        self.close_path(path_handles)

    def set_value(self, value):
        path_handles = self.open_path(value.parent)
        key_handle = path_handles[len(path_handles) - 1]

        if (value.name == "(Default)"):
            name = ""
        else:
            name = value.name

        self.pipe.SetValue(key_handle, WinRegPipeManager.winreg_string(name), value.type, value.data)
        self.close_path(path_handles)

    def unset_value(self, value):
        path_handles = self.open_path(value.parent)
        key_handle = path_handles[len(path_handles) - 1]

        if (value.name == "(Default)"):
            name = ""
        else:
            name = value.name

        self.pipe.DeleteValue(key_handle, WinRegPipeManager.winreg_string(name))
        self.close_path(path_handles)

    def move_value(self, value, old_name):
        path_handles = self.open_path(value.parent)
        key_handle = path_handles[len(path_handles) - 1]

        self.pipe.DeleteValue(key_handle, WinRegPipeManager.winreg_string(old_name))
        self.pipe.SetValue(key_handle, WinRegPipeManager.winreg_string(value.name), value.type, value.data)

        self.close_path(path_handles)

    def open_well_known_keys(self):
        self.well_known_keys = []

        #additional permissions need to be added to properly fetch security information.
        #winreg.REG_KEY_ALL works but it's best to figure out what permission is actually needed

        key_handle = self.pipe.OpenHKCR(None, winreg.KEY_ENUMERATE_SUB_KEYS | winreg.KEY_CREATE_SUB_KEY | winreg.KEY_QUERY_VALUE | winreg.KEY_SET_VALUE)
        key = RegistryKey("HKEY_CLASSES_ROOT", None)
        key.handle = key_handle
        self.well_known_keys.append(key)

        key_handle = self.pipe.OpenHKCU(None, winreg.KEY_ENUMERATE_SUB_KEYS | winreg.KEY_CREATE_SUB_KEY | winreg.KEY_QUERY_VALUE | winreg.KEY_SET_VALUE)
        key = RegistryKey("HKEY_CURRENT_USER", None)
        key.handle = key_handle
        self.well_known_keys.append(key)

        key_handle = self.pipe.OpenHKLM(None, winreg.KEY_ENUMERATE_SUB_KEYS | winreg.KEY_CREATE_SUB_KEY | winreg.KEY_QUERY_VALUE | winreg.KEY_SET_VALUE)
        key = RegistryKey("HKEY_LOCAL_MACHINE", None)
        key.handle = key_handle
        self.well_known_keys.append(key)

        key_handle = self.pipe.OpenHKU(None, winreg.KEY_ENUMERATE_SUB_KEYS | winreg.KEY_CREATE_SUB_KEY | winreg.KEY_QUERY_VALUE | winreg.KEY_SET_VALUE)
        key = RegistryKey("HKEY_USERS", None)
        key.handle = key_handle
        self.well_known_keys.append(key)

        key_handle = self.pipe.OpenHKCC(None, winreg.KEY_ENUMERATE_SUB_KEYS | winreg.KEY_CREATE_SUB_KEY | winreg.KEY_QUERY_VALUE | winreg.KEY_SET_VALUE)
        key = RegistryKey("HKEY_CURRENT_CONFIG", None)
        key.handle = key_handle
        self.well_known_keys.append(key)

    def open_path(self, key):
        if (key.parent == None):
            return [key.handle]
        else:
            path = self.open_path(key.parent)
            parent_handle = path[-1]

            key_handle = self.pipe.OpenKey(
                                      parent_handle,
                                      WinRegPipeManager.winreg_string(key.name),
                                      0,
                                      winreg.KEY_ENUMERATE_SUB_KEYS | winreg.KEY_CREATE_SUB_KEY | winreg.KEY_QUERY_VALUE | winreg.KEY_SET_VALUE
                                      )

            return path + [key_handle]

    def close_path(self, path_handles):
        for handle in path_handles[:0:-1]:
            self.pipe.CloseKey(handle)

    @staticmethod
    def winreg_string(string):
        ws = winreg.String()
        ws.name = unicode(string)
        ws.name_len = len(string)
        ws.name_size = 8192

        return ws

    @staticmethod
    def winreg_string_buf(string):
        wsb = winreg.StringBuf()
        wsb.name = unicode(string)
        wsb.length = len(string)
        wsb.size = 8192

        return wsb

    @staticmethod
    def winreg_val_name_buf(string):
        wvnb = winreg.ValNameBuf()
        wvnb.name = unicode(string)
        wvnb.length = len(string)
        wvnb.size = 8192

        return wvnb

class KeyFetchThread(threading.Thread):
    def __init__(self, pipe_manager, regedit_window, selected_key, iter):
        super(KeyFetchThread, self).__init__()

        self.name = "KeyFetchThread"
        self.pipe_manager = pipe_manager
        self.regedit_window = regedit_window
        self.selected_key = selected_key
        #TODO: this should take a path instead of an iter. It's possible (though not likely) that a node gets deleted
        #      because of a refresh to it's parent key. This would invalididate the iter.
        self.iter = iter

    def run(self):
        msg = None
        try:
            #the ls_key function will grab the pipe lock
            (key_list, value_list) = self.pipe_manager.ls_key(self.selected_key, self.regedit_window)

            gtk.gdk.threads_enter()
            self.regedit_window.refresh_keys_tree_view(self.iter, key_list)
            #self.regedit_window.keys_tree_view.get_selection().select_iter(self.iter) #select the key, in case selection has changed during fetching. This causes problems
            #columns_autosize() already called by refresh_keys_tree_view()

            self.regedit_window.refresh_values_tree_view(value_list)
            self.regedit_window.update_sensitivity()
            #threads_leave in the finally: section
        except RuntimeError as re:
            msg = "Failed to fetch information about %s: %s." % (self.selected_key.get_absolute_path(), re.args[1])
            print msg

        finally:
            gtk.gdk.threads_leave()

            if (msg != None):
                gtk.gdk.threads_enter()
                self.regedit_window.set_status(msg)
                self.regedit_window.run_message_dialog(gtk.MESSAGE_ERROR, gtk.BUTTONS_OK, msg)
                gtk.gdk.threads_leave()


class SearchThread(threading.Thread):
    def __init__(self, pipe_manager, regedit_window, options, starting_key_iter=None):
        """This thread searches the registry using the options specified in 'options'.
        If 'starting_key_iter' is supplied then it will search only from that key onward."""
        super(SearchThread, self).__init__()

        self.explode = False; #so we can kill this thread if we want to

        self.name = "SearchThread"
        self.pipe_manager = pipe_manager
        self.regedit_window = regedit_window
        self.starting_key_iter = starting_key_iter

        #options are passed in a bit of a weird way.
        (self.text,
         self.search_keys,
         self.search_values,
         self.search_data,
         self.match_whole_string) = options

    def run(self):
        if (self.match_whole_string):
            search_items = [self.text]
        else:
            search_items = self.text.split()

        if self.starting_key_iter == None: #Add root keys, start a normal search
            #this will be a depth-first traversal of the key tree
            stack = [] #we'll push keys onto this stack

            self.pipe_manager.lock.acquire()
            well_known_keys = self.pipe_manager.well_known_keys
            self.pipe_manager.lock.release()

            gtk.gdk.threads_enter()
            for key in well_known_keys: #push the root keys onto the stack
                stack.append((key, self.regedit_window.get_iter_for_key(key), ))
            gtk.gdk.threads_leave()
            stack.reverse() #we pop keys from the end of the list. Without this we'd be searching from the last root key first

        else: #The user pressed find next.
            #create the stack with only the keys we haven't searched yet
            gtk.gdk.threads_enter() #the function below requires the GUI gui_lock because it has to get info from the gtk data structures. But i'm not positive this gui_lock is needed
            stack = self.fill_stack()
            gtk.gdk.threads_leave()

        #stuff we need
        model = self.regedit_window.keys_tree_view.get_model()
        i = 999 #This is so we can print every x statements, to save CPU

        #Stuff simply to speed things up
        search_keys = self.search_keys
        search_values = self.search_values
        search_data = self.search_data
        #dot operations addresses are looked up at run time, so this saves us many lookups
        gui_lock = gtk.gdk.threads_enter
        gui_unlock = gtk.gdk.threads_leave
        pipe_lock = self.pipe_manager.lock.acquire
        pipe_unlock = self.pipe_manager.lock.release
        append_to_key_store = self.regedit_window.keys_store.append
        set_status = self.regedit_window.set_status

        while stack != []:
            if self.explode:
                return

            (key, key_iter) = stack.pop()

            #For the sake of about 8% faster search, we only display a message every few values
            if (i >= 5):
                i = 0
                gui_lock()
                set_status("Searching %s." % key.get_absolute_path())
                gui_unlock()
            else:
                i += 1

            #check if this key's name matches any of our search queries
            if (search_keys):
                for text in search_items:
                    if (key.name.find(text) >= 0): #find() returns the index, so anything greater than -1 means found
                        gui_lock()
                        self.regedit_window.highlight_search_result(key_iter)
                        msg = "Found key at: %s." % key.get_absolute_path()
                        self.regedit_window.set_status(msg)
                        self.regedit_window.search_thread = None
                        gui_unlock()
                        return

            #fetch a list of values for this key
            if (search_values or search_data):
                pipe_lock()
                try:
                    value_list = self.pipe_manager.get_values_for_key(key)
                except RuntimeError as ex:
                    #probably a WERR_ACCESS_DENIED exception. We'll just skip over keys that can't be fetched
                    print "Failed to fetch values for %s: %s." % (key.get_absolute_path(), ex.args[1])
                    continue
                finally:
                    pipe_unlock()

            #Search values' names
            if (search_values):
               for value in value_list: #go through every value for this key
                   for text in search_items: #and check those values for each search string
                        if (value.name.find(text) >= 0): #check if it's in the value's name
                            gui_lock()
                            self.regedit_window.refresh_values_tree_view(value_list) #Fill in the values, we'll need this to hightlight the result
                            value_iter = self.regedit_window.get_iter_for_value(value)
                            self.regedit_window.highlight_search_result(key_iter, value_iter)
                            msg = "Found value at: %s." % value.get_absolute_path()
                            self.regedit_window.set_status(msg)
                            self.regedit_window.search_thread = None
                            gui_unlock()
                            return

            #search values' data
            if (search_data):
               for value in value_list: #go through every value for this key
                   for text in search_items: #and check those values for each search string
                        if (value.get_data_string().find(text) >= 0): #check if it's in the value's data
                            gui_lock()
                            self.regedit_window.refresh_values_tree_view(value_list) #Fill in the values, we'll need this to hightlight the result
                            value_iter = self.regedit_window.get_iter_for_value(value)
                            self.regedit_window.highlight_search_result(key_iter, value_iter)
                            msg = "Found data at: %s." % value.get_absolute_path()
                            self.regedit_window.set_status(msg)
                            self.regedit_window.search_thread = None
                            gui_unlock()
                            return


            #fetch a list of subkeys for this key and append to the stack
            append_list = []
            gui_lock()
            subkey_iter = model.iter_children(key_iter)
            if subkey_iter != None: #if the subkeys already exist in the tree view
                while subkey_iter != None:
                    append_list.append((model.get_value(subkey_iter, 1), subkey_iter, ))
                    subkey_iter = model.iter_next(subkey_iter)
                gui_unlock()
            else: #If we don't already have them, we have to get them
                gui_unlock()
                try:
                    pipe_lock()
                    subkey_list = self.pipe_manager.get_subkeys_for_key(key)
                except RuntimeError as re:
                    #probably a WERR_ACCESS_DENIED exception. We'll just skip over keys that can't be fetched
                    print "Failed to fetch subkeys for %s: %s." % (key.get_absolute_path(), re.args[1])
                    continue
                finally:
                    pipe_unlock()

                #Append these keys to the parent in the TreeStore.
                #Since we're fetching them we might as well add them to the TreeStore so that we don't have to fetch them again later
                gui_lock()
                #key_iter = self.regedit_window.get_iter_for_key(key)
                for current_key in subkey_list:
                    child_iter = append_to_key_store(key_iter, current_key.list_view_representation())
                    append_list.append((current_key, child_iter, ))
                gui_unlock()

            append_list.reverse() #again we have to do this or else we'll search the list from bottom to top
            stack.extend(append_list)

        #if we are here then the loop has finished and found nothing
        msg = "Search query not found."
        if self.match_whole_string: msg += "\n\nConsider searching again with 'Match whole string' unchecked"
        gtk.gdk.threads_enter()
        self.regedit_window.search_thread = None
        self.regedit_window.run_message_dialog(gtk.MESSAGE_INFO, gtk.BUTTONS_OK, msg)
        gtk.gdk.threads_leave()

    def fill_stack(self):
        """Fills the stack with the keys we need to search. This only gets called to create the stack when the user presses 'find next'.
        NOTE: This function requires the gdk lock. Make sure you hold the lock before calling this function."""
        model = self.regedit_window.keys_tree_view.get_model()
        key = model.get_value(self.starting_key_iter, 1)
        root_key = key.get_root_key()
        stack = []

        self.pipe_manager.lock.acquire()
        well_known_keys = self.pipe_manager.well_known_keys
        self.pipe_manager.lock.release()

        #we need to add all keys below the current root key into the stack
        for n in range(len(well_known_keys)):
            if well_known_keys[n].name == root_key.name: #so our root key is the nth key.
                break
        n += 1 #we don't want to add the current root key to the stack
        append_list = []
        while n < len(well_known_keys):
            append_list.append((well_known_keys[n], self.regedit_window.get_iter_for_key(well_known_keys[n]) ,))
            n += 1
        append_list.reverse()
        stack.extend(append_list)

        iter_parents = [] #no parents, WOOHOO!
        iter_current_parent = self.starting_key_iter #yes, we consider the current key a parent also

        #Here we add all ancestors of self.starting_key_iter (the selected key) to key_parents and iter_parents
        while iter_current_parent != None:
            #we'll add each child_iter's iter_current_parent to the key_parents list until we get to the root
            iter_parents.append(iter_current_parent)
            iter_current_parent = model.iter_parent(iter_current_parent)

        iter_parents.reverse()
        for parent_iter in iter_parents:
            iter = model.iter_next(parent_iter) #This will point to the key right after the parent key of our last search result
            append_list = []
            while (iter != None):
                append_list.append((model.get_value(iter, 1), iter, ))
                iter = model.iter_next(iter)
            append_list.reverse()
            stack.extend(append_list)

        #Can't forget to add the starting key's children
        key_iter = model.iter_children(self.starting_key_iter)
        append_list = []
        while key_iter != None:
            append_list.append((model.get_value(key_iter, 1), key_iter, ))
            key_iter = model.iter_next(key_iter)
        append_list.reverse()
        stack.extend(append_list)

        return stack

    def self_destruct(self):
        """This function will only stop the thread, it will not clean up anything or display anything to the user.
        This way the calling thread can do it and it's guaranteed to happen right away."""
        #this probably isn't safe. But who cares, we're killing the thread anyways
        self.explode = True


class RegEditWindow(gtk.Window):

    def __init__(self, info_callback = None, server = "", username = "", password = "", transport_type = 0, connect_now = False):
        super(RegEditWindow, self).__init__()
        #Note: Any change to these arguments should probably also be changed in on_connect_item_activate()

        self.create()
        self.pipe_manager = None
        self.search_thread = None
        self.search_last_options = None
        self.ignore_selection_change = False
        self.update_sensitivity()

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

        self.set_title("Registry Editor")
        self.set_default_size(800, 600)
        self.icon_filename = os.path.join(sys.path[0], "images", "registry.png")
        self.icon_registry_number_filename = os.path.join(sys.path[0], "images", "registry-number.png")
        self.icon_registry_string_filename = os.path.join(sys.path[0], "images", "registry-string.png")
        self.icon_registry_binary_filename = os.path.join(sys.path[0], "images", "registry-binary.png")
        self.icon_pixbuf = gtk.gdk.pixbuf_new_from_file(self.icon_filename)
        self.icon_registry_number_pixbuf = gtk.gdk.pixbuf_new_from_file_at_size(self.icon_registry_number_filename, 22, 22)
        self.icon_registry_string_pixbuf = gtk.gdk.pixbuf_new_from_file_at_size(self.icon_registry_string_filename, 22, 22)
        self.icon_registry_binary_pixbuf = gtk.gdk.pixbuf_new_from_file_at_size(self.icon_registry_binary_filename, 22, 22)

        self.set_icon(self.icon_pixbuf)

    	vbox = gtk.VBox(False, 0)
    	self.add(vbox)

        # TODO: assign keyboard shortcuts

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

        self.import_item = gtk.MenuItem("_Import...", accel_group)
        # TODO: implement import & export
        #file_menu.add(self.import_item)

        self.export_item = gtk.MenuItem("_Export...", accel_group)
        #file_menu.add(self.export_item)

#        menu_separator_item = gtk.SeparatorMenuItem()
#        file_menu.add(menu_separator_item)

        self.quit_item = gtk.ImageMenuItem(gtk.STOCK_QUIT, accel_group)
        file_menu.add(self.quit_item)

        self.edit_item = gtk.MenuItem("_Edit")
        self.menubar.add(self.edit_item)

        self.edit_menu = gtk.Menu()
        self.edit_item.set_submenu(self.edit_menu)

        self.modify_item = gtk.ImageMenuItem("_Modify", accel_group)
        self.edit_menu.add(self.modify_item)

        self.modify_binary_item = gtk.MenuItem("Modify _Binary", accel_group)
        self.edit_menu.add(self.modify_binary_item)

        self.edit_menu.add(gtk.SeparatorMenuItem())

        self.new_item = gtk.ImageMenuItem(gtk.STOCK_NEW, accel_group)
        self.edit_menu.add(self.new_item)

        new_menu = gtk.Menu()
        self.new_item.set_submenu(new_menu)

        self.new_key_item = gtk.MenuItem("_Key", accel_group)
        new_menu.add(self.new_key_item)

        new_menu.add(gtk.SeparatorMenuItem())

        self.new_string_item = gtk.MenuItem("_String Value", accel_group)
        new_menu.add(self.new_string_item)

        self.new_binary_item = gtk.MenuItem("_Binary Value", accel_group)
        new_menu.add(self.new_binary_item)

        self.new_dword_item = gtk.MenuItem("_DWORD Value", accel_group)
        new_menu.add(self.new_dword_item)

        self.new_multi_string_item = gtk.MenuItem("_Multi-String Value", accel_group)
        new_menu.add(self.new_multi_string_item)

        self.new_expandable_item = gtk.MenuItem("_Expandable String Value", accel_group)
        new_menu.add(self.new_expandable_item)

        self.edit_menu.add(gtk.SeparatorMenuItem())

        #TODO: Finish implementing permissions (dialogs are mostly done, just need to fetch/update the data)
        #self.permissions_item = gtk.MenuItem("_Permissions", accel_group)
        #self.edit_menu.add(self.permissions_item)

        #self.edit_menu.add(gtk.SeparatorMenuItem())

        self.delete_item = gtk.ImageMenuItem(gtk.STOCK_DELETE, accel_group)
        self.edit_menu.add(self.delete_item)

        self.rename_item = gtk.ImageMenuItem(gtk.STOCK_EDIT, accel_group)
        self.edit_menu.add(self.rename_item)

        self.edit_menu.add(gtk.SeparatorMenuItem())

        self.copy_item = gtk.MenuItem("_Copy Registry Path", accel_group)
        self.edit_menu.add(self.copy_item)

        self.edit_menu.add(gtk.SeparatorMenuItem())

        self.find_item = gtk.ImageMenuItem(gtk.STOCK_FIND, accel_group)
        self.find_item.get_child().set_text("Find...")
        self.edit_menu.add(self.find_item)

        self.find_next_item = gtk.MenuItem("Find _Next", accel_group)
        self.edit_menu.add(self.find_next_item)

        self.view_item = gtk.MenuItem("_View")
        self.menubar.add(self.view_item)

        view_menu = gtk.Menu()
        self.view_item.set_submenu(view_menu)

        self.refresh_item = gtk.ImageMenuItem(gtk.STOCK_REFRESH, accel_group)
        view_menu.add(self.refresh_item)

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

        self.new_key_button = gtk.ToolButton(gtk.STOCK_NEW)
        self.new_key_button.set_label("New Key")
        self.new_key_button.set_tooltip_text("Create a new registry key")
        self.new_key_button.set_is_important(True)
        self.toolbar.insert(self.new_key_button, 3)

        self.new_string_button = gtk.ToolButton(gtk.STOCK_NEW)
        self.new_string_button.set_label("New Value")
        self.new_string_button.set_tooltip_text("Create a new string registry value")
        self.new_string_button.set_is_important(True)
        self.toolbar.insert(self.new_string_button, 4)

        self.rename_button = gtk.ToolButton(gtk.STOCK_EDIT)
        self.rename_button.set_label("Rename")
        self.rename_button.set_tooltip_text("Rename the selected key or value")
        self.rename_button.set_is_important(True)
        self.toolbar.insert(self.rename_button, 5)

        self.delete_button = gtk.ToolButton(gtk.STOCK_DELETE)
        self.delete_button.set_tooltip_text("Delete the selected key or value")
        self.delete_button.set_is_important(True)
        self.toolbar.insert(self.delete_button, 5)


        # registry tree

        # TODO: make the expanders nicely align with the icons

        self.hpaned = gtk.HPaned()
        vbox.pack_start(self.hpaned)

        scrolledwindow = gtk.ScrolledWindow(None, None)
        scrolledwindow.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        scrolledwindow.set_shadow_type(gtk.SHADOW_IN)
        scrolledwindow.set_size_request(250, 0)
        self.hpaned.add1(scrolledwindow)

        self.keys_tree_view = gtk.TreeView()
        self.keys_tree_view.set_headers_visible(False)
        scrolledwindow.add(self.keys_tree_view)

        column = gtk.TreeViewColumn()
        column.set_title("")
        column.set_resizable(False)
        renderer = gtk.CellRendererPixbuf()
        renderer.set_property("stock-id", gtk.STOCK_DIRECTORY)
        column.pack_start(renderer, True)
        self.keys_tree_view.append_column(column)

        column = gtk.TreeViewColumn()
        column.set_title("Name")
        renderer = gtk.CellRendererText()
        column.pack_start(renderer, True)
        self.keys_tree_view.append_column(column)
        column.add_attribute(renderer, "text", 0)

        self.keys_store = gtk.TreeStore(gobject.TYPE_STRING, gobject.TYPE_PYOBJECT)
        self.keys_tree_view.set_model(self.keys_store)


        # value list

        scrolledwindow = gtk.ScrolledWindow(None, None)
        scrolledwindow.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        scrolledwindow.set_shadow_type(gtk.SHADOW_IN)
        self.hpaned.add2(scrolledwindow)

        self.values_tree_view = gtk.TreeView()
        scrolledwindow.add(self.values_tree_view)

        column = gtk.TreeViewColumn()
        column.set_title("")
        column.set_resizable(False)
        renderer = gtk.CellRendererPixbuf()
        column.pack_start(renderer, True)
        self.values_tree_view.append_column(column)
        column.add_attribute(renderer, "pixbuf", 0)

        column = gtk.TreeViewColumn()
        column.set_title("Name")
        column.set_resizable(True)
        column.set_fixed_width(190)
        #column.set_expand(True)
        column.set_sizing(gtk.TREE_VIEW_COLUMN_FIXED)
        column.set_sort_column_id(1)
        renderer = gtk.CellRendererText()
        renderer.set_property("ellipsize", pango.ELLIPSIZE_END)
        column.pack_start(renderer, True)
        self.values_tree_view.append_column(column)
        column.add_attribute(renderer, "text", 1)

        column = gtk.TreeViewColumn()
        column.set_title("Type")
        column.set_resizable(True)
        column.set_fixed_width(160)
        column.set_sizing(gtk.TREE_VIEW_COLUMN_FIXED)
        column.set_sort_column_id(2)
        renderer = gtk.CellRendererText()
        renderer.set_property("ellipsize", pango.ELLIPSIZE_END)
        column.pack_start(renderer, True)
        self.values_tree_view.append_column(column)
        column.add_attribute(renderer, "text", 2)

        column = gtk.TreeViewColumn()
        column.set_title("Data")
        column.set_resizable(True)
        column.set_fixed_width(300)
        column.set_expand(True)
        column.set_sort_column_id(3)
        renderer = gtk.CellRendererText()
        renderer.set_property("ellipsize", pango.ELLIPSIZE_END)
        column.pack_start(renderer, True)
        self.values_tree_view.append_column(column)
        column.add_attribute(renderer, "text", 3)

        self.values_store = gtk.ListStore(gtk.gdk.Pixbuf, gobject.TYPE_STRING, gobject.TYPE_STRING, gobject.TYPE_STRING, gobject.TYPE_PYOBJECT)
        self.values_store.set_sort_column_id(1, gtk.SORT_ASCENDING)
        self.values_tree_view.set_model(self.values_store)


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
        self.import_item.connect("activate", self.on_import_item_activate)
        self.export_item.connect("activate", self.on_export_item_activate)
        self.quit_item.connect("activate", self.on_quit_item_activate)
        self.modify_item.connect("activate", self.on_modify_item_activate)
        self.modify_binary_item.connect("activate", self.on_modify_binary_item_activate)
        self.new_key_item.connect("activate", self.on_new_key_item_activate)
        self.new_string_item.connect("activate", self.on_new_string_item_activate)
        self.new_binary_item.connect("activate", self.on_new_binary_item_activate)
        self.new_dword_item.connect("activate", self.on_new_dword_item_activate)
        self.new_multi_string_item.connect("activate", self.on_new_multi_string_item_activate)
        self.new_expandable_item.connect("activate", self.on_new_expandable_item_activate)
        #self.permissions_item.connect("activate", self.on_permissions_item_activate)
        self.delete_item.connect("activate", self.on_delete_item_activate)
        self.rename_item.connect("activate", self.on_rename_item_activate)
        self.copy_item.connect("activate", self.on_copy_item_activate)
        self.find_item.connect("activate", self.on_find_item_activate)
        self.find_next_item.connect("activate", self.on_find_next_item_activate)
        self.refresh_item.connect("activate", self.on_refresh_item_activate)
        self.about_item.connect("activate", self.on_about_item_activate)

        self.connect_button.connect("clicked", self.on_connect_item_activate)
        self.disconnect_button.connect("clicked", self.on_disconnect_item_activate)
        self.new_key_button.connect("clicked", self.on_new_key_item_activate)
        self.new_string_button.connect("clicked", self.on_new_string_item_activate)
        self.delete_button.connect("clicked", self.on_delete_item_activate)
        self.rename_button.connect("clicked", self.on_rename_item_activate)

        self.keys_tree_view.get_selection().connect("changed", self.on_keys_tree_view_selection_changed)
        self.keys_tree_view.connect("row-collapsed", self.on_keys_tree_view_row_collapsed_expanded)
        self.keys_tree_view.connect("row-expanded", self.on_keys_tree_view_row_collapsed_expanded)
        self.keys_tree_view.connect("button_press_event", self.on_keys_tree_view_button_press)
        self.keys_tree_view.connect("focus-in-event", self.on_tree_views_focus_in)
        self.values_tree_view.get_selection().connect("changed", self.on_values_tree_view_selection_changed)
        self.values_tree_view.connect("button_press_event", self.on_values_tree_view_button_press)
        self.values_tree_view.connect("focus-in-event", self.on_tree_views_focus_in)

        self.add_accel_group(accel_group)

    def refresh_keys_tree_view(self, iter, key_list, select_me_key = None):
        """Refresh the children of 'iter' by recursively deleting all existing children and appending keys from 'key_list' as children.
        Also selects 'select_me_key' in the tree view. 'select_me_key' is a key that is a child of the key referenced by 'iter' ('select_me_key' must be an element of 'key_list').

        Returns nothing."""
        if (not self.connected()):
            return

        (model, selected_paths) = self.keys_tree_view.get_selection().get_selected_rows()

        if (iter == None):
            #If iter is None then the tree is empty.
            self.pipe_manager.lock.acquire()
            well_known_keys = self.pipe_manager.well_known_keys
            self.pipe_manager.lock.release()
            for key in well_known_keys:
                self.keys_store.append(None, key.list_view_representation())

        else:
            #Delete any children the selected key has
            while (self.keys_store.iter_children(iter)):
                self.keys_store.remove(self.keys_store.iter_children(iter))
            #add keys from key_list as children.
            for key in key_list:
                self.keys_store.append(iter, key.list_view_representation())

        if (iter != None):
            #expand the selected row
            self.keys_tree_view.expand_row(self.keys_store.get_path(iter), False)

            #Select the key select_me_key. Select_me_key is a key and not an iter, so this isn't as straight forward as it could be
            #but we know it's a child of the key pointed to by 'iter' and an element of 'key_list.
            if (select_me_key != None):
                child_iter = self.keys_store.iter_children(iter) #get the first (at index 0) child of 'iter'
                while (child_iter != None): #child_iter will equal none if call iter_children() or iter_next() and there is no next child.
                    key = self.keys_store.get_value(child_iter, 1)
                    if (key.name == select_me_key.name):
                        self.keys_tree_view.get_selection().select_iter(child_iter) #select that key
                        break
                    child_iter = self.keys_store.iter_next(child_iter)

            #if 'select_me_key' isn't given, then select whatever was selected before
            elif (len(selected_paths) > 0):
                for path in selected_paths: #there's almost certainly only one, but o well
                    try: #try them until one works.
                        sel_iter = self.keys_store.get_iter(path)
                        self.keys_tree_view.get_selection().select_iter(sel_iter)
                        break
                    except Exception:
                            self.keys_tree_view.get_selection().select_iter(iter) #highlight (select) 'iter'
            else:
                self.keys_tree_view.get_selection().select_iter(iter) #highlight (select) 'iter'

        #self.keys_tree_view.columns_autosize() #This doesn't really help, it just slows down long lists
        self.update_sensitivity()

    def refresh_values_tree_view(self, value_list):
        if (not self.connected()):
            return

        type_pixbufs = { #change misc back to winreg when the constants are in the right place
                        misc.REG_SZ:self.icon_registry_string_pixbuf,
                        misc.REG_EXPAND_SZ:self.icon_registry_string_pixbuf,
                        misc.REG_BINARY:self.icon_registry_binary_pixbuf,
                        misc.REG_DWORD:self.icon_registry_number_pixbuf,
                        misc.REG_DWORD_BIG_ENDIAN:self.icon_registry_number_pixbuf,
                        misc.REG_MULTI_SZ:self.icon_registry_string_pixbuf,
                        misc.REG_QWORD:self.icon_registry_number_pixbuf,
                        }

        (model, selected_paths) = self.values_tree_view.get_selection().get_selected_rows()

        self.values_store.clear()

        for value in value_list:
            try: #This can fail when we get a value of a type that isn't in type_pixbufs (such as REG_NONE)
                self.values_store.append([type_pixbufs[value.type]] + value.list_view_representation())
            except (KeyError, IndexError, ) as er:
                #TODO: handle REG_NONE types better.
                if value.type == misc.REG_NONE:
                    print "Not displaying a hidden value at %s." % (value.get_absolute_path())
                else:
                    print "Failed to display %s in the value tree: values of type %s cannot be handled." % (value.get_absolute_path(), str(value.type))

        if (len(selected_paths) > 0):
            try:
                sel_iter = self.values_store.get_iter(selected_paths[0])
                self.values_tree_view.get_selection().select_iter(sel_iter)

            except Exception:
                if (len(value_list) > 0):
                    last_iter = self.values_store.get_iter_first()
                    while (self.values_store.iter_next(last_iter) != None):
                        last_iter = self.values_store.iter_next(last_iter)
                    self.values_tree_view.get_selection().select_iter(last_iter)

        self.update_sensitivity()

    def get_selected_registry_key(self):
        """Get the registry key that is currently selected in the tree view. Also returns the iter for that key in the tree view

        Returns (iter, RegistryKey)"""
        if not self.connected():
            return (None, None)

        (model, iter) = self.keys_tree_view.get_selection().get_selected()
        if (iter == None): # no selection
            return (None, None)
        else:
            return (iter, model.get_value(iter, 1))

    def get_selected_registry_value(self):
        """Get the registry value that is currently selected in the tree view. Also returns the iter for that value

        Returns (iter, RegistryValue)"""
        if not self.connected(): # not connected
            return (None, None)

        (model, iter) = self.values_tree_view.get_selection().get_selected()
        if (iter == None): # no selection
            return (None, None)
        else:
            return (iter, model.get_value(iter, 4))

    def get_iter_for_value(self, value):
        """This function takes a value and gets the iterator for that value in the gtk.TreeStore.

        Returns an iterator or None"""
        if not self.connected():
            return

        model = self.values_tree_view.get_model()
        iter = model.get_iter_first()
        while iter != None:
            current_value = model.get_value(iter, 4)
            if (current_value.name == value.name):
                return iter
            iter = model.iter_next(iter)
        return None

    def get_iter_for_key(self, key):
        """This function takes a key and gets the iterator for that key in the gtk.TreeStore.
        Note: this function is SLOW. Only call this function if you cannot figure out a better method.

        Returns an iterator or None"""
        if not self.connected():
            return

        model = self.keys_tree_view.get_model()
        path = key.get_absolute_path()

        key_names = path.split("\\")

        model = self.keys_tree_view.get_model()
        current_key_iter = model.get_iter_first() #get iter to the first root node

        step = 0 #currently checking this index in key_names
        while (current_key_iter != None):
            current_key = model.get_value(current_key_iter, 1)
            if current_key.name == key_names[step]:
                if (step >= len(key_names) - 1): #if this is the last step then we've found the key! (cue audio from Zelda)
                    return current_key_iter
                current_key_iter = model.iter_children(current_key_iter) #step to the decendant, start itering their children (that sounds wrong...)
                step += 1
            else:
                current_key_iter = model.iter_next(current_key_iter)

        return None

    def set_status(self, message):
        self.statusbar.pop(0)
        self.statusbar.push(0, message)

    def update_sensitivity(self):
        connected = self.connected()

        key_selected = (self.get_selected_registry_key()[1] != None)
        value_selected = (self.get_selected_registry_value()[1] != None)
        value_set = (value_selected and len(self.get_selected_registry_value()[1].data) > 0)
        value_default = (value_selected and self.get_selected_registry_value()[1].name == "(Default)")
        key_focused = self.keys_tree_view.is_focus()
        if (connected):
            root_key_selected = (key_selected and self.get_selected_registry_key()[1].parent == None)

        # sensitiviy

        self.connect_item.set_sensitive(not connected)
        self.disconnect_item.set_sensitive(connected)
        self.import_item.set_sensitive(connected)
        self.export_item.set_sensitive(connected)
        self.modify_item.set_sensitive(connected and value_selected)
        self.modify_binary_item.set_sensitive(connected and value_selected)
        self.new_key_item.set_sensitive(connected and key_selected)
        self.new_string_item.set_sensitive(connected and key_selected)
        self.new_binary_item.set_sensitive(connected and key_selected)
        self.new_dword_item.set_sensitive(connected and key_selected)
        self.new_multi_string_item.set_sensitive(connected and key_selected)
        self.new_expandable_item.set_sensitive(connected and key_selected)
        #self.permissions_item.set_sensitive(connected and (key_selected or value_selected))
        if (key_focused):
            self.delete_item.set_sensitive(connected and key_selected and not root_key_selected)
            self.rename_item.set_sensitive(connected and key_selected and not root_key_selected)
        else:
            self.delete_item.set_sensitive(connected and value_selected and (value_set or not value_default))
            self.rename_item.set_sensitive(connected and value_selected and not value_default)
        self.copy_item.set_sensitive(connected and key_selected)
        self.find_item.set_sensitive(connected)
        self.find_next_item.set_sensitive(connected)
        self.refresh_item.set_sensitive(connected)

        self.connect_button.set_sensitive(self.connect_item.state != gtk.STATE_INSENSITIVE)
        self.disconnect_button.set_sensitive(self.disconnect_item.state != gtk.STATE_INSENSITIVE)
        self.new_key_button.set_sensitive(self.new_key_item.state != gtk.STATE_INSENSITIVE)
        self.new_string_button.set_sensitive(self.new_string_item.state != gtk.STATE_INSENSITIVE)
        self.rename_button.set_sensitive(self.rename_item.state != gtk.STATE_INSENSITIVE)
        self.delete_button.set_sensitive(self.delete_item.state != gtk.STATE_INSENSITIVE)


        # captions

        self.delete_item.get_child().set_text("Delete " + ["Value", "Key"][key_focused])
        self.delete_button.set_tooltip_text("Delete the selected " + ["value", "key"][key_focused])

        self.rename_item.get_child().set_text("Rename " + ["Value", "Key"][key_focused])
        self.rename_button.set_tooltip_text("Rename the selected " + ["value", "key"][key_focused])

    def run_message_dialog(self, type, buttons, message, parent = None):
        if (parent == None):
            parent = self

        message_box = gtk.MessageDialog(parent, gtk.DIALOG_MODAL, type, buttons, message)
        response = message_box.run()
        message_box.hide()

        return response

    def run_value_edit_dialog(self, value, type, apply_callback = None):
        if (type == None):
            type = value.type

        if (value != None):
            original_type = value.type
            value.type = type
        else:
            original_type = type


        dialog = RegValueEditDialog(value, type)
        dialog.show_all()
        dialog.update_type_page_after_show()

        # loop to handle the applies
        while True:
            response_id = dialog.run()

            if (response_id in [gtk.RESPONSE_OK, gtk.RESPONSE_APPLY]):
                problem_msg = dialog.check_for_problems()

                if (problem_msg != None):
                    self.run_message_dialog(gtk.MESSAGE_ERROR, gtk.BUTTONS_OK, problem_msg)
                else:
                    dialog.values_to_reg_value()
                    if (apply_callback != None):
                        dialog.reg_value.type = original_type
                        if (not apply_callback(dialog.reg_value)):
                            response_id = gtk.RESPONSE_NONE
                        dialog.reg_value.type = type
                    if (response_id == gtk.RESPONSE_OK):
                        dialog.hide()
                        break

            else:
                dialog.hide()
                return None

        dialog.reg_value.type = original_type

        return dialog.reg_value

    def run_key_edit_dialog(self, key, apply_callback = None):
        dialog = RegKeyEditDialog(key)
        dialog.show_all()

        # loop to handle the applies
        while True:
            response_id = dialog.run()

            if (response_id in [gtk.RESPONSE_OK, gtk.RESPONSE_APPLY]):
                problem_msg = dialog.check_for_problems()

                if (problem_msg != None):
                    self.run_message_dialog(gtk.MESSAGE_ERROR, gtk.BUTTONS_OK, problem_msg)
                else:
                    dialog.values_to_reg_key()
                    if (apply_callback != None):
                        if (not apply_callback(dialog.reg_key)):
                            response_id = gtk.RESPONSE_NONE
                    if (response_id == gtk.RESPONSE_OK):
                        dialog.hide()
                        break

            else:
                dialog.hide()
                return None

        return dialog.reg_key

    def run_rename_dialog(self, key, value, apply_callback = None):
        dialog = RegRenameDialog(key, value)
        dialog.show_all()

        # loop to handle the applies
        while True:
            response_id = dialog.run()

            if (response_id in [gtk.RESPONSE_OK, gtk.RESPONSE_APPLY]):
                problem_msg = dialog.check_for_problems()

                if (problem_msg != None):
                    self.run_message_dialog(gtk.MESSAGE_ERROR, gtk.BUTTONS_OK, problem_msg)
                else:
                    dialog.values_to_reg()
                    if (apply_callback != None):
                        if (not apply_callback([dialog.reg_value, dialog.reg_key][dialog.reg_key != None])):
                            response_id = gtk.RESPONSE_NONE
                    if (response_id == gtk.RESPONSE_OK):
                        dialog.hide()
                        break

            else:
                dialog.hide()
                return None

        if (dialog.reg_key == None):
            return dialog.reg_value
        else:
            return dialog.reg_key

    def run_connect_dialog(self, pipe_manager, server_address, transport_type, username, password = "", connect_now = False):
        dialog = WinRegConnectDialog(server_address, transport_type, username, password)
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

                    pipe_manager = WinRegPipeManager(server_address, transport_type, username, password)

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
                    elif re.args[1] == 'NT_STATUS_OBJECT_NAME_NOT_FOUND':
                        self.run_message_dialog(gtk.MESSAGE_ERROR, gtk.BUTTONS_OK, "Failed to connect: NT_STATUS_OBJECT_NAME_NOT_FOUND.\n\nIs the remote registry service running?", dialog)
                    else:
                        msg = "Failed to connect: %s." % (re.args[1])
                        print msg
                        traceback.print_exc()
                        self.run_message_dialog(gtk.MESSAGE_ERROR, gtk.BUTTONS_OK, msg, dialog)

                except Exception as ex:
                    msg = "Failed to connect: %s." % (str(ex))
                    print msg
                    traceback.print_exc()
                    self.run_message_dialog(gtk.MESSAGE_ERROR, gtk.BUTTONS_OK, msg, dialog)

        dialog.hide()
        return pipe_manager

    def run_search_dialog(self):
        dialog = RegSearchDialog()
        dialog.show_all()

        # loop to handle the applies
        while True:
            response_id = dialog.run()

            if (response_id == gtk.RESPONSE_OK): #the search button returns RESPONSE_OK
                problem_msg = dialog.check_for_problems()
                if (problem_msg != None):
                    self.run_message_dialog(problem_msg[1], gtk.BUTTONS_OK, problem_msg[0])
                else:
                    dialog.hide()
                    break
            else:
                dialog.hide()
                return
        #this isn't very elegant, but conforms with the way other dialogs are done here
        return (dialog.search_entry.get_text(),
                dialog.check_match_keys.get_active(),
                dialog.check_match_values.get_active(),
                dialog.check_match_data.get_active(),
                dialog.check_match_whole_string.get_active())

    def connected(self):
        return self.pipe_manager != None

    def update_value_callback(self, value):
        (iter, selected_key) = self.get_selected_registry_key()
        if (selected_key == None):
            return False

        try:
            self.pipe_manager.lock.acquire()
            self.pipe_manager.set_value(value)
            value_list = self.pipe_manager.get_values_for_key(selected_key)

            self.refresh_values_tree_view(value_list)
            self.set_status("Value \'%s\' updated." % (value.get_absolute_path()))
            return True
        except RuntimeError, re:
            msg = "Failed to update value: %s." % (re.args[1])
            print msg
            self.set_status(msg)
            traceback.print_exc()
            self.run_message_dialog(gtk.MESSAGE_ERROR, gtk.BUTTONS_OK, msg)
        except Exception, ex:
            msg = "Failed to update value: %s." % (str(ex))
            print msg
            self.set_status(msg)
            traceback.print_exc()
            self.run_message_dialog(gtk.MESSAGE_ERROR, gtk.BUTTONS_OK, msg)
        finally:
            self.pipe_manager.lock.release()

        return False

    def rename_key_callback(self, key):
        (iter, selected_key) = self.get_selected_registry_key()
        if (selected_key == None):
            return False

        if (key.name == key.old_name):
            return True

        #performance would be better if we released the lock between pipe manager calls, but that would make for very complex code - not worth it
        self.pipe_manager.lock.acquire()
        try:
            key_list = self.pipe_manager.get_subkeys_for_key(selected_key.parent)

            #check if a key with that name already exists
            if (len([k for k in key_list if k.name == key.name]) > 0):
                self.run_message_dialog(gtk.MESSAGE_ERROR, gtk.BUTTONS_OK, "This key already exists. Please choose another name.", self)
                return False

            self.pipe_manager.move_key(key, key.old_name)
            key_list = self.pipe_manager.get_subkeys_for_key(selected_key.parent)

            key.old_name = key.name
            parent_iter = self.keys_store.iter_parent(iter)
            self.refresh_keys_tree_view(parent_iter, key_list, key)

            self.set_status("Key \'%s\' renamed." % (key.get_absolute_path()))
            return True

        except RuntimeError, re:
            msg = "Failed to rename key: %s." % (re.args[1])
            print msg
            self.set_status(msg)
            traceback.print_exc()
            self.run_message_dialog(gtk.MESSAGE_ERROR, gtk.BUTTONS_OK, msg)
        except Exception, ex:
            msg = "Failed to rename key: %s." % (str(ex))
            print msg
            self.set_status(msg)
            traceback.print_exc()
            self.run_message_dialog(gtk.MESSAGE_ERROR, gtk.BUTTONS_OK, msg)
        finally:
            self.pipe_manager.lock.release()

        return False

    def rename_value_callback(self, value):
        (iter_key, selected_key) = self.get_selected_registry_key()
        if (selected_key == None):
            return False

        (iter_value, selected_value) = self.get_selected_registry_value()
        if (selected_value == None):
            return False

        if (value.name == value.old_name):
            return True

        self.pipe_manager.lock.acquire()
        try:
            value_list = self.pipe_manager.get_values_for_key(selected_key)

            if (len([v for v in value_list if v.name == value.name]) > 0):
                self.run_message_dialog(gtk.MESSAGE_ERROR, gtk.BUTTONS_OK, "This value already exists. Please choose another name.", self)
                return False

            self.pipe_manager.move_value(value, value.old_name)
            value_list = self.pipe_manager.get_values_for_key(selected_key)

            value.old_name = value.name
            self.refresh_values_tree_view(value_list)
            self.set_status("Value \'%s\' renamed." % (value.get_absolute_path()))
            return True

        except RuntimeError, re:
            msg = "Failed to rename value: %s." % (re.args[1])
            print msg
            self.set_status(msg)
            traceback.print_exc()
            self.run_message_dialog(gtk.MESSAGE_ERROR, gtk.BUTTONS_OK, msg)
        except Exception, ex:
            msg = "Failed to rename value: %s." % (str(ex))
            print msg
            self.set_status(msg)
            traceback.print_exc()
            self.run_message_dialog(gtk.MESSAGE_ERROR, gtk.BUTTONS_OK, msg)
        finally:
            self.pipe_manager.lock.release()

        return False

    def new_value(self, type):
        (iter, selected_key) = self.get_selected_registry_key()
        if (selected_key == None):
            return

        new_value = self.run_value_edit_dialog(None, type)
        if (new_value == None):
            return

        new_value.parent = selected_key

        self.pipe_manager.lock.acquire()
        try:

            value_list = self.pipe_manager.get_values_for_key(selected_key)

            if (len([v for v in value_list if v.name == new_value.name]) > 0):
                self.run_message_dialog(gtk.MESSAGE_ERROR, gtk.BUTTONS_OK, "This value already exists.", self)
                return False

            self.pipe_manager.set_value(new_value)
            value_list = self.pipe_manager.get_values_for_key(selected_key)
            self.refresh_values_tree_view(value_list)
            self.set_status("Value \'%s\' successfully added." % (new_value.get_absolute_path()))

        except RuntimeError, re:
            msg = "Failed to create value: %s." % (re.args[1])
            self.set_status(msg)
            print msg
            traceback.print_exc()
            self.run_message_dialog(gtk.MESSAGE_ERROR, gtk.BUTTONS_OK, msg)
        except Exception, ex:
            msg = "Failed to create value: %s."  % (str(ex))
            self.set_status(msg)
            print msg
            traceback.print_exc()
            self.run_message_dialog(gtk.MESSAGE_ERROR, gtk.BUTTONS_OK, msg)
        finally:
            self.pipe_manager.lock.release()

    def highlight_search_result(self, key_iter, value_iter=None):
        """Select key_iter in the tree store. If value_iter is not none then value_iter will also be selected.

        returns True if a key was successfully selected"""
        if not self.connected():
            return
        if key_iter == None:
            return

        result = False

        self.ignore_selection_change = True
        model = self.keys_tree_view.get_model()
        try:
            self.keys_tree_view.expand_to_path(model.get_path(key_iter))
            self.keys_tree_view.set_cursor(model.get_path(key_iter))

            result = True
        except RuntimeError as re:
            #this could happen when we try to highlight a value that isn't in the tree
            print "Problem selecting key:", re.args[1]

        if value_iter != None:
            model = self.values_tree_view.get_model()
            try:
                path = model.get_path(value_iter)
                self.values_tree_view.set_cursor(path)
                self.values_tree_view.expand_to_path(path)
            except RuntimeError as re:
                print "Problem selecting value:", re.args[1]

        self.ignore_selection_change = False
        return result

    def on_key_press(self, widget, event):
        if event.keyval == gtk.keysyms.F5:
            self.on_refresh_item_activate(None)
        elif event.keyval == gtk.keysyms.F3:
            self.on_find_next_item_activate(None)
        elif event.keyval == gtk.keysyms.F2:
            self.on_rename_item_activate(None)
        elif event.keyval == gtk.keysyms.Delete:
            self.on_delete_item_activate(None)
        elif event.keyval == gtk.keysyms.Return:
            myev = gtk.gdk.Event(gtk.gdk._2BUTTON_PRESS) #emulate a double-click
            self.on_values_tree_view_button_press(None, myev)
#        else:
#            print "Key pressed:", event.keyval

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
        self.set_status("Connected to %s." % (self.server_address))

        self.refresh_keys_tree_view(None, None)

    def on_disconnect_item_activate(self, widget):
        if self.search_thread != None:
            self.search_thread.self_destruct()
            self.search_thread = None
        if (self.pipe_manager != None):
            self.pipe_manager.close()
            self.pipe_manager = None

        self.keys_store.clear()
        self.values_store.clear()
        self.keys_tree_view.columns_autosize()
        self.update_sensitivity()

        self.set_status("Disconnected.")

    def on_export_item_activate(self, widget):
        pass

    def on_import_item_activate(self, widget):
        pass

    def on_quit_item_activate(self, widget):
        self.on_self_delete(None, None)

    def on_modify_item_activate(self, widget):
        if not self.connected():
            return
        (iter, edit_value) = self.get_selected_registry_value()
        self.run_value_edit_dialog(edit_value, None, self.update_value_callback)

    def on_modify_binary_item_activate(self, widget):
        if not self.connected():
            return
        (iter, edit_value) = self.get_selected_registry_value()
        self.run_value_edit_dialog(edit_value, misc.REG_BINARY, self.update_value_callback)

        self.set_status("Value \'%s\' updated." % (edit_value.get_absolute_path()))

    def on_new_key_item_activate(self, widget):
        (iter, selected_key) = self.get_selected_registry_key()
        if (selected_key == None):
            return

        new_key = self.run_key_edit_dialog(None)
        if (new_key == None):
            return

        new_key.parent = selected_key

        self.pipe_manager.lock.acquire()
        try:
            key_list = self.pipe_manager.get_subkeys_for_key(selected_key)

            if (len([k for k in key_list if k.name == new_key.name]) > 0):
                self.run_message_dialog(gtk.MESSAGE_ERROR, gtk.BUTTONS_OK, "This key already exists.", self)
                return False

            self.pipe_manager.create_key(new_key)
            key_list = self.pipe_manager.get_subkeys_for_key(selected_key)
            self.refresh_keys_tree_view(iter, key_list, new_key)
            self.set_status("Key \'%s\' successfully added." % (new_key.get_absolute_path()))

        except RuntimeError, re:
            msg = "Failed to create key: %s." % (re.args[1])
            self.set_status(msg)
            print msg
            traceback.print_exc()
            self.run_message_dialog(gtk.MESSAGE_ERROR, gtk.BUTTONS_OK, msg)
        except Exception, ex:
            msg = "Failed to create key: %s." % (str(ex))
            self.set_status(msg)
            print msg
            traceback.print_exc()
            self.run_message_dialog(gtk.MESSAGE_ERROR, gtk.BUTTONS_OK, msg)
        finally:
            self.pipe_manager.lock.release()

    def on_new_string_item_activate(self, widget):
        self.new_value(misc.REG_SZ)

    def on_new_binary_item_activate(self, widget):
        self.new_value(misc.REG_BINARY)

    def on_new_dword_item_activate(self, widget):
        self.new_value(misc.REG_DWORD)

    def on_new_multi_string_item_activate(self, widget):
        self.new_value(misc.REG_MULTI_SZ)

    def on_new_expandable_item_activate(self, widget):
        self.new_value(misc.REG_EXPAND_SZ)

    def on_permissions_item_activate(self, widget):
        if not self.connected():
            return

        (iter, selected_key) = self.get_selected_registry_key()
        #fetch permissions
        self.pipe_manager.lock.acquire()
        try:
            key_sec_data = self.pipe_manager.get_key_security(selected_key)
        except RuntimeError as ex:
            msg = "Failed to fetch permissions: %s." % (ex.args[1])
            print msg
#            traceback.print_exc()
#            self.set_status(msg)
        finally:
            self.pipe_manager.lock.release()


        dialog = RegPermissionsDialog(None, None)
        dialog.show_all()
        pass

    def on_delete_item_activate(self, widget):
        key_focused = self.keys_tree_view.is_focus()

        if (key_focused):
            (iter, selected_key) = self.get_selected_registry_key()
            if (selected_key == None):
                return

            if (self.run_message_dialog(gtk.MESSAGE_QUESTION, gtk.BUTTONS_YES_NO, "Do you want to delete key '%s'?" % selected_key.name) != gtk.RESPONSE_YES):
                return
        else:
            (iter, selected_value) = self.get_selected_registry_value()
            if (selected_value == None):
                return

            if (self.run_message_dialog(gtk.MESSAGE_QUESTION, gtk.BUTTONS_YES_NO, "Do you want to delete value '%s'?" % selected_value.name) != gtk.RESPONSE_YES):
                return

        self.pipe_manager.lock.acquire()
        try:
            if (key_focused):

                self.pipe_manager.remove_key(selected_key)
                key_list = self.pipe_manager.get_subkeys_for_key(selected_key.parent)

                parent_iter = self.keys_store.iter_parent(iter)
                self.refresh_keys_tree_view(parent_iter, key_list)

                self.set_status("Key \'%s\' successfully deleted." % (selected_key.get_absolute_path()))
            else:
                self.pipe_manager.unset_value(selected_value)
                value_list = self.pipe_manager.get_values_for_key(selected_value.parent)

                self.refresh_values_tree_view(value_list)
                self.set_status("Value \'%s\' successfully deleted." % (selected_value.get_absolute_path()))

        except RuntimeError, re:
            if re.args[1] == 'WERR_BADFILE':
                msg = "Failed to delete value: it's already gone!"
                self.on_refresh_item_activate(None)
            else:
                msg = "Failed to delete value: %s." % (re.args[1])
                self.set_status(msg)
                print msg
                traceback.print_exc()
            self.run_message_dialog(gtk.MESSAGE_ERROR, gtk.BUTTONS_OK, msg)
        except Exception, ex:
            msg = "Failed to delete value: %s." % (str(ex))
            self.set_status(msg)
            print msg
            traceback.print_exc()
            self.run_message_dialog(gtk.MESSAGE_ERROR, gtk.BUTTONS_OK, msg)
        finally:
            self.pipe_manager.lock.release()

    def on_rename_item_activate(self, widget):
        if not self.connected():
            return
        key_focused = self.keys_tree_view.is_focus()

        if (key_focused):
            (iter, rename_key) = self.get_selected_registry_key()
            rename_key.old_name = rename_key.name
            self.run_rename_dialog(rename_key, None, self.rename_key_callback)

        else:
            (iter, rename_value) = self.get_selected_registry_value()
            rename_value.old_name = rename_value.name
            self.run_rename_dialog(None, rename_value, self.rename_value_callback)

    def on_copy_item_activate(self, widget):
        if not self.connected():
            return

        key_focused = self.keys_tree_view.is_focus()

        if (key_focused):
            (iter, selected_key) = self.get_selected_registry_key()
            if (selected_key == None):
                return

            path = selected_key.get_absolute_path()
        else:
            (iter, selected_value) = self.get_selected_registry_value()
            if (selected_value == None):
                return

            path = selected_value.get_absolute_path()

        clipboard = gtk.clipboard_get(gtk.gdk.SELECTION_CLIPBOARD)
        clipboard.set_text(path)

    def on_find_item_activate(self, widget):
        if not self.connected():
            return

        if self.search_thread == None:
            result = self.run_search_dialog()
            if result == None: #The user pressed cancel
                return

            self.search_last_options = result
            self.search_thread = SearchThread(self.pipe_manager, self, result)
            self.search_thread.start()
        else:
            #this means the search thread is already running!
            msg = "A search is already under way. We can only have one search at a time.\n\nCancel the current search?"
            response = self.run_message_dialog(gtk.MESSAGE_QUESTION, gtk.BUTTONS_YES_NO, msg)
            if response == gtk.RESPONSE_YES:
                #we have to clean up after the thread because self_destruct() only kills the thread without any cleanup
                self.search_thread.self_destruct()
                self.search_thread = None
                self.set_status("Search canceled.") #this may not get shown since the thread may not stop right away
                self.on_find_item_activate(None) #Call this function again to get the new search started

    def on_find_next_item_activate(self, widget):
        if not self.connected():
            return
        if self.search_thread != None:
            self.run_message_dialog(gtk.MESSAGE_INFO, gtk.BUTTONS_OK, "Calm down, we're still searching!")
            return
        if self.search_last_options == None:
            self.run_message_dialog(gtk.MESSAGE_INFO, gtk.BUTTONS_OK, "There is no previous search to continue from.")
            self.on_find_item_activate(None)
            return

        #get selections. Stuff is selected by the search, or the user can select if he/she wants to search elsewhere
        (sel_key_iter, sel_key) = self.get_selected_registry_key()
        (sel_value_iter, sel_value) = self.get_selected_registry_value()
        value_model = self.values_tree_view.get_model()
        #get search options from the last search
        (text,
         search_keys,
         search_values,
         search_data,
         match_whole_string) = self.search_last_options

        if (match_whole_string):
            search_items = [text]
        else:
            search_items = text.split()

        #search the remaining values in this key
        if (search_values):
            if sel_value_iter != None:
                value_iter = value_model.iter_next(sel_value_iter) #point to the value after the one we just found
            else:
                value_iter = value_model.get_iter_first()
            while (value_iter != None): #this will be none when there is no more values
                current_value = value_model.get_value(value_iter, 4)
                for text in search_items:
                    if (current_value.name.find(text) >= 0): #check if it's in the value's name
                        self.highlight_search_result(sel_key_iter, value_iter)
                        msg = "Found value at: %s." % (current_value.get_absolute_path())
                        self.set_status(msg)
                        return
                value_iter = value_model.iter_next(value_iter)

        #search the remaining data too
        if (search_data):
            if sel_value_iter != None:
                value_iter = value_model.iter_next(sel_value_iter) #point to the value after the one we just found
            else:
                value_iter = value_model.get_iter_first()
            while (value_iter != None):
                current_value = value_model.get_value(value_iter, 4)
                for text in search_items: #and check those values for each search string
                    if (current_value.get_data_string().find(text) >= 0): #check if it's in the value's data
                        self.highlight_search_result(sel_key_iter, value_iter)
                        msg = "Found data at: %s." % (current_value.get_absolute_path())
                        self.set_status(msg)
                        return
                value_iter = value_model.iter_next(value_iter)

        #so it's not in this key's values. Lets continue searching the rest of the registry
        self.search_thread = SearchThread(self.pipe_manager, self, self.search_last_options, sel_key_iter)
        self.search_thread.start()

    def on_refresh_item_activate(self, widget):
        (iter, selected_key) = self.get_selected_registry_key()
        if (selected_key == None):
            return

        KeyFetchThread(self.pipe_manager, self, selected_key, iter).start()

        #deselect any selected values
        (iter, value) = self.get_selected_registry_value()
        if iter == None:
            return
        selector = self.values_tree_view.get_selection()
        selector.unselect_iter(iter)

    def on_about_item_activate(self, widget):
        dialog = AboutDialog(
                             "PyGWRegEdit",
                             "A tool to remotely edit a Windows Registry.\n Based on Jelmer Vernooij's original Samba-GTK",
                             self.icon_pixbuf
                             )
        dialog.run()
        dialog.hide()

    def on_keys_tree_view_selection_changed(self, widget):
        if self.ignore_selection_change:
            return
        (iter, selected_key) = self.get_selected_registry_key()
        if (selected_key == None):
            return

        self.set_status("Selected path \'%s\'." % (selected_key.get_absolute_path()))

        #deselect any selected values
        (val_iter, value) = self.get_selected_registry_value()
        if val_iter != None:
            selector = self.values_tree_view.get_selection()
            selector.unselect_iter(val_iter)

        #If this key has children already then we don't need to fetch it again.
        #this means that keys without subkeys will always be fetched when clicked.
        #This is a minor flaw because fetching zero keys is fast
        child_count = self.keys_store.iter_n_children(iter)
        if (child_count == 0):
            #create a thread to fetch the keys.
            KeyFetchThread(self.pipe_manager, self, selected_key, iter).start()
        else:
            self.pipe_manager.lock.acquire()
            try:
                value_list = self.pipe_manager.get_values_for_key(selected_key)
                self.refresh_values_tree_view(value_list)
            except Exception, ex:
                msg = "Failed to get values for %s: %s." % (selected_key.get_absolute_path(), str(ex))
                print msg
                self.set_status(msg)
            finally:
                self.pipe_manager.lock.release()

    def on_keys_tree_view_row_collapsed_expanded(self, widget, iter, path):
        self.keys_tree_view.columns_autosize()

    def on_keys_tree_view_button_press(self, widget, event):
        if (event.type == gtk.gdk._2BUTTON_PRESS): #double click
            (iter, selected_key) = self.get_selected_registry_key()
            if (selected_key == None):
                return

            expanded = self.keys_tree_view.row_expanded(self.keys_store.get_path(iter))

            if (expanded):
                self.keys_tree_view.collapse_row(self.keys_store.get_path(iter))
            else:
                self.keys_tree_view.expand_row(self.keys_store.get_path(iter), False)
        elif (event.button == 3): #right click
            self.values_tree_view.grab_focus()
            self.edit_menu.popup(None, None, None, event.button, int(event.time))

    def on_values_tree_view_selection_changed(self, widget):
        if self.ignore_selection_change:
            return
        (iter, selected_value) = self.get_selected_registry_value()

        if (selected_value != None):
            self.set_status("Selected path \'%s\\%s\'." % (selected_value.get_absolute_path(), selected_value.name))

        self.update_sensitivity()

    def on_values_tree_view_button_press(self, widget, event):
        if (event.type == gtk.gdk._2BUTTON_PRESS): #double click
            (iter, selected_value) = self.get_selected_registry_value()
            if (selected_value == None):
                return

            self.on_modify_item_activate(self.modify_item)
        elif (event.button == 3): #right click
            self.values_tree_view.grab_focus()
            self.edit_menu.popup(None, None, None, event.button, int(event.time))

    def on_tree_views_focus_in(self, widget, event):
        self.update_sensitivity()

#************ END OF CLASS ***************

def PrintUsage():
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
        PrintUsage()
        sys.exit(2)

    for opt, arg in opts:
        if opt in ("-h", "--help"):
            PrintUsage()
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
    window = RegEditWindow(**arguments)
    window.show_all()
    gtk.main()
