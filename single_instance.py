# single instance for win32
# https://stackoverflow.com/questions/380870/make-sure-only-a-single-instance-of-a-program-is-running


from win32event import CreateMutex
from win32api import CloseHandle, GetLastError
from winerror import ERROR_ALREADY_EXISTS
import sys

class singleinstance:
    """ Limits application to single instance """

    def __init__(self, uuid):
        self.mutexname = f"my_mutex_{uuid}"
        self.mutex = CreateMutex(None, False, self.mutexname)
        self.lasterror = GetLastError()
    
    def alreadyrunning(self):
        return (self.lasterror == ERROR_ALREADY_EXISTS)
        
    def __del__(self):
        if self.mutex:
            CloseHandle(self.mutex)


if __name__ == '__main__':
    # do this at beginnig of your application
    myapp = singleinstance('9a0ccabe-ed68-468c-bc0c-e5e370dd742c')

    # check is another instance of same program running
    if myapp.alreadyrunning():
        print ("Another instance of this program is already running")
        sys.exit(1)
