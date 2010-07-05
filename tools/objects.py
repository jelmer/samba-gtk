
import datetime;

import gtk;

from samba.dcerpc import svcctl
from samba.dcerpc import winreg
from samba.dcerpc import misc


class User:
    
    def __init__(self, username, fullname, description, rid):
        self.username = username
        self.fullname = fullname
        self.description = description
        self.rid = rid
        
        self.password = ""
        self.must_change_password = True
        self.cannot_change_password = False
        self.password_never_expires = False
        self.account_disabled = False
        self.account_locked_out = False
        self.group_list = []
        self.profile_path = ""
        self.logon_script = ""
        self.homedir_path = ""
        self.map_homedir_drive = -1
        
        None

    def list_view_representation(self):
        return [self.username, self.fullname, self.description, self.rid]


class Group:
    
    def __init__(self, name, description, rid):
        self.name = name
        self.description = description
        self.rid = rid
        
    def list_view_representation(self):
        return [self.name, self.description, self.rid]


class Service:
    
    def __init__(self):
        self.name = ""
        self.display_name = ""
        self.description = ""
        
        self.state = svcctl.SVCCTL_STOPPED
        self.check_point = 0
        self.wait_hint = 0
        
        self.accepts_pause = False
        self.accepts_stop = False
        
        self.start_type = svcctl.SVCCTL_AUTO_START
        self.path_to_exe = ""        
        self.account = None # local system account
        self.account_password = None # don't change
        self.allow_desktop_interaction = False
        
        self.start_params = ""
        #self.hw_profile_list = [["Profile 1", True], ["Profile 2", False]] TODO: implement hw_profiles functionality
        
        self.handle = -1
    
    @staticmethod
    def get_state_string(state):
        if (state == svcctl.SVCCTL_CONTINUE_PENDING):
            return "Continue pending"
        elif (state == svcctl.SVCCTL_PAUSE_PENDING):
            return "Pause pending"
        elif (state == svcctl.SVCCTL_PAUSED):
            return "Paused"
        elif (state == svcctl.SVCCTL_RUNNING):
            return "Running"
        elif (state == svcctl.SVCCTL_START_PENDING):
            return "Start pending"
        elif (state == svcctl.SVCCTL_STOP_PENDING):
            return "Stop pending"
        elif (state == svcctl.SVCCTL_STOPPED):
            return "Stopped"
        
    @staticmethod
    def get_start_type_string(start_type):
        if (start_type == svcctl.SVCCTL_BOOT_START):
            return "Start at boot"
        elif (start_type == svcctl.SVCCTL_SYSTEM_START):
            return "Start at system startup"
        elif (start_type == svcctl.SVCCTL_AUTO_START):
            return "Start automatically"
        elif (start_type == svcctl.SVCCTL_DEMAND_START):
            return "Start manually"
        elif (start_type == svcctl.SVCCTL_DISABLED):
            return "Disabled"
        else:
            return ""
        
    def list_view_representation(self):
        return [self.name, self.display_name, self.description, Service.get_state_string(self.state), Service.get_start_type_string(self.start_type)]


class RegistryValue:
    
    def __init__(self, name, type, data, parent):
        self.name = name
        self.type = type
        self.data = data
        self.parent = parent
        
    def get_absolute_path(self):
        if (self.parent == None):
            return self.name
        else:
            return self.parent.get_absolute_path() + "\\" + self.name
        
    def get_data_string(self):
        interpreted_data = self.get_interpreted_data()
        
        if (interpreted_data == None or len(self.data) == 0):
            return "(value not set)"

        elif (self.type == misc.REG_SZ or self.type == misc.REG_EXPAND_SZ):
            return interpreted_data

        elif (self.type == misc.REG_BINARY):
            result = ""
            
            for byte in interpreted_data:
                result += "%02X" % (byte)
                
            return result

        elif (self.type == misc.REG_DWORD):
            return "0x%08X" % (interpreted_data)

        elif (self.type == misc.REG_DWORD_BIG_ENDIAN):
            return "0x%08X" % (interpreted_data)

        elif (self.type == misc.REG_MULTI_SZ):
            result = ""
            
            for string in interpreted_data:
                result += string + " "

            return result

        elif (self.type == misc.REG_QWORD):
            return "0x%016X" % (interpreted_data)

        else:
            return str(interpreted_data)

    def get_interpreted_data(self):
        if (self.data == None):
            return None
        
        if (self.type == misc.REG_SZ or self.type == misc.REG_EXPAND_SZ):
            result = ""
            
            index = 0
            while (index + 1 < len(self.data)): #The +1 ensures that the whole char is valid. Corrupt keys can otherwise cause exceptions
                word = ((self.data[index + 1] << 8) + self.data[index])
                if (word != 0):
                    result += unichr(word)
                index += 2

            return result

        elif (self.type == misc.REG_BINARY):
            return self.data
            
        elif (self.type == misc.REG_DWORD):
            result = 0L
            
            if (len(self.data) < 4):
                return 0L
            
            for i in xrange(4):
                result = (result << 8) + self.data[3 - i]
            
            return result

        elif (self.type == misc.REG_DWORD_BIG_ENDIAN):
            result = 0L
            
            if (len(self.data) < 4):
                return 0L

            for i in xrange(4):
                result = (result << 8) + self.data[i]
                
            return result

        elif (self.type == misc.REG_MULTI_SZ):
            result = []
            string = ""
            
            if (len(self.data) == 0):
                return []
            
            index = 0
            while (index < len(self.data)):
                word = ((self.data[index + 1] << 8) + self.data[index])
                if (word == 0):
                    result.append(string)
                    string = ""
                else:
                    string += unichr(word)

                index += 2

            result.pop() # remove last systematic empty string

            return result

        elif (self.type == misc.REG_QWORD):
            result = 0L
            
            if (len(self.data) < 8):
                return 0L

            for i in xrange(8):
                result = (result << 8) + self.data[7 - i]
        
            return result
        
        else:
            return self.data

    def set_interpreted_data(self, data):
        del self.data[:] 

        if (data == None):
            self.data = None
        
        elif (self.type == misc.REG_SZ or self.type == misc.REG_EXPAND_SZ):
            for uch in data:
                word = ord(uch)
                self.data.append(int(word & 0x00FF))
                self.data.append(int((word >> 8) & 0x00FF))

        elif (self.type == misc.REG_BINARY):
            self.data = []
            for elem in data:
                self.data.append(int(elem))
            
        elif (self.type == misc.REG_DWORD):
            for i in xrange(4):
                self.data.append(int(data >> (8 * i) & 0xFF))

        elif (self.type == misc.REG_DWORD_BIG_ENDIAN):
            for i in xrange(3, -1, -1):
                self.data.append(int(data >> (8 * i) & 0xFF))

        elif (self.type == misc.REG_MULTI_SZ):
            index = 0

            for string in data:
                for uch in string:
                    word = ord(uch)
                    self.data.append(int(word & 0x00FF))
                    self.data.append(int((word >> 8) & 0x00FF))

                self.data.append(0)
                self.data.append(0)

            self.data.append(0)
            self.data.append(0)

        elif (self.type == misc.REG_QWORD):
            for i in xrange(8):
                self.data.append(int(data >> (8 * i) & 0xFF))
        
        else:
            self.data = data

    def list_view_representation(self):
        return [self.name, RegistryValue.get_type_string(self.type), self.get_data_string(), self]
    
    @staticmethod
    def get_type_string(type):
        type_strings = {
                        misc.REG_SZ:"String", 
                        misc.REG_BINARY:"Binary Data", 
                        misc.REG_EXPAND_SZ:"Expandable String", 
                        misc.REG_DWORD:"32-bit Number (little endian)",
                        misc.REG_DWORD_BIG_ENDIAN:"32-bit Number (big endian)",
                        misc.REG_MULTI_SZ:"Multi-String",
                        misc.REG_QWORD:"64-bit Number (little endian)"
                        }
        
        return type_strings[type]


class RegistryKey:
    
    def __init__(self, name, parent):
        self.name = name
        self.parent = parent
        
        self.handle = None
        
    def get_absolute_path(self):
        if (self.parent == None):
            return self.name
        else:
            return self.parent.get_absolute_path() + "\\" + self.name
        
    def get_root_key(self):
        if self.parent == None:
            return self
        else:
            return self.parent.get_root_key()
        
    def list_view_representation(self):
        return [self.name, self]


class Task:
    
    def __init__(self, command, id):
        self.command = command
        self.id = id
        self.job_time = 0
        self.days_of_month = 0
        self.days_of_week = 0
        self.run_periodically = False
        self.non_interactive = False
        
    def get_scheduled_index(self):
        if (self.days_of_month == 0x7FFFFFFF): # daily schedule
            return 0
        elif (self.days_of_week > 0): # weekly schedule
            return 1
        else: # monthly schedule
            return 2
 
    def get_time(self):
        time = self.job_time / 1000 # get rid of milliseconds
        seconds = int(time % 60)
        
        time /= 60 # get rid of seconds
        minutes = int(time % 60)
        
        time /= 60 # get rid of minutes
        hour = int(time % 24)
        
        return (hour, minutes, seconds)
    
    def set_time(self, hour, minutes, seconds):
        h_ms = int(hour * 60 * 60 * 1000)
        m_ms = int(minutes * 60 * 1000)
        s_ms = int(seconds * 1000)
        
        self.job_time = h_ms + m_ms + s_ms
 
    def get_scheduled_days_of_week(self):
        dow_list = []
        
        for day_no in xrange(0, 7):
            if (self.days_of_week & (2 ** day_no)):
                dow_list.append(day_no)

        return dow_list 
        
    def get_scheduled_days_of_month(self):
        dom_list = []
        
        for day_no in xrange(0, 31):
            if (self.days_of_month & (2 ** day_no)):
                dom_list.append(day_no)
                
        return dom_list
        
    def set_scheduled_days_of_week(self, dow_list):
        self.days_of_week = 0x00
        
        for day_no in dow_list:
            self.days_of_week |= (2 ** day_no)
        
    def set_scheduled_days_of_month(self, dom_list):
        self.days_of_month = 0x00000000
        
        for day_no in dom_list:
            self.days_of_month |= (2 ** day_no)
        
    def get_scheduled_description(self):
        if (self.days_of_week == 0x00 and self.days_of_month == 0x00000000):
            return "Not scheduled."
        
        (hour, minutes, seconds) = self.get_time()
        index = self.get_scheduled_index()
        
        at_str = "%02d:%02d" % (hour, minutes)
        
        if (self.run_periodically):
            if (index == 0): # daily schedule
                every_str = "every day" 
            elif (index == 1): # weekly schedule
                dow_str = ""
                for day_no in self.get_scheduled_days_of_week():
                    dow_str += Task.get_day_of_week_name(day_no) + ", "
                
                # eliminate the last comma
                dow_str = dow_str.rstrip(", ")
                
                every_str = "every " + dow_str + " of every week"
            else: # monthly schedule
                dom_str = ""
                for day_no in self.get_scheduled_days_of_month():
                    dom_str += Task.get_day_of_month_name(day_no) + ", "
                
                # eliminate the last comma
                dom_str = dom_str.rstrip(", ")
                
                every_str = "every " + dom_str + " of every month"
        else:
            if (index == 0): # daily schedule
                next_str = "once"
            elif (index == 1): # weekly schedule
                next_str = "next " + self.get_day_of_week_name(self.get_scheduled_days_of_week()[0])
            else:
                next_str = "next " + self.get_day_of_month_name(self.get_scheduled_days_of_month()[0]) + " of the month"

        sw_str = "starting with " + str(datetime.date.today())
        
        if (self.run_periodically):
            return "At " + at_str + ", " + every_str + ", " + sw_str + "."
        else:
            return "At " + at_str + ", " + next_str + ", " + sw_str + "."
    
    @staticmethod
    def get_day_of_week_name(day_no):
        DAYS_OF_WEEK = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

        return DAYS_OF_WEEK[day_no]
    
    @staticmethod
    def get_day_of_month_name(day_no):
        if (day_no == 0):
            return "1st"
        elif (day_no == 1):
            return "2nd"
        elif (day_no == 2):
            return "3rd"
        else:
            return str(day_no + 1) + "th"
        
    def list_view_representation(self):
        return [str(self.id), self.command, self.get_scheduled_description()]
