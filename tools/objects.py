
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
        self.map_homedir_drive = None
        
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
