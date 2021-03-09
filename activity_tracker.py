# activites tracker
# inspired by ActivityWatch
# scan active windows per 100ms
# Applications, Window Titles, Categories
# write records into sqlite db
# another script (the server) reads db and visualizes in browser

# 2020/8/4
# cyyang

# get active window:
# https://stackoverflow.com/questions/10266281/obtain-active-window-using-python
# https://www.programcreek.com/python/example/81370/win32gui.GetForegroundWindow



import os
import datetime
from time import sleep
import sqlite3
import json

from threading import Thread, Lock, Event

import sys
import getpass
import psutil


if sys.platform in ['Windows', 'win32', 'cygwin']:
    from win32gui import GetForegroundWindow, GetWindowText
    from win32process import GetWindowThreadProcessId
    from win32api import SetConsoleCtrlHandler


NOTIFY = True

if NOTIFY:
    from win10toast import ToastNotifier



from common import Log
from single_instance import singleinstance



SLEEPTIME = 0.01        # accuracy ~10ms
DBSYNCSLEEPTIME = 600    # write db every 10min

class ActivityTracker(Thread):
    ''' activites tracker '''
    def __init__(self):
        Thread.__init__(self, name='fwi')
        self.L = Log('activity_tracker')
        self.logger = self.L.logger

        self.chk_single_instanse()

        self.user = getpass.getuser()

        self.db = f'./data/{self.user}_{datetime.datetime.now():%Y-%m}.db'
        self.create_db()

        self.event = {
            'timestamp': '',
            'duration': 0.0,
            'app' : '',
            'title' : '',
            }
        self.events = []
        self.lock = Lock()
        self.db_lock = Lock()
        self.rec_e = Event()

        self.exit_flag = False

        if sys.platform in ['Windows', 'win32', 'cygwin']:
            self.getForegroundWindowInfo = self.getForegroundWindowInfo_win32
            SetConsoleCtrlHandler(self.on_exit, True)


    def on_exit(self, sig, func=None):
        self.logger.warning(f'exit code:{sig}, flush db')
        self.exit_flag = True
        self.rec_e.set()

        if NOTIFY:
            toaster = ToastNotifier()
            toaster.show_toast("Activity Tracker",
                            "Activity Tracker stops in 3 secs",
                            icon_path=None,
                            duration=3,
                            threaded=True)
            while toaster.notification_active(): sleep(0.1)
        sys.exit()


    def chk_single_instanse(self):
        self.myapp = singleinstance('5ed3212f-bf45-48e6-8f74-af76e890f4e5')  # gen by uuid.uuid4()

        # check is another instance of same program running
        if self.myapp.alreadyrunning():
            self.logger.warning('Another instance is already running, exit')
            sys.exit(1)


    def getForegroundWindowInfo_win32(self):
        hwnd = GetForegroundWindow()
        if hwnd > 0:
            try:
                title = GetWindowText(hwnd)
                tid, pid = GetWindowThreadProcessId(hwnd)
                app = psutil.Process(pid).name()
                # user = psutil.Process(pid).username().rpartition('\\')[2]
                if title == '':
                    title = app[:-4]
            except:
                title = app = ''
        else:
            title = app = ''

        return {'app':app, 'title':title}


    def run(self):
        last_fwi = self.getForegroundWindowInfo()
        last_tm = datetime.datetime.now()
        self.rec_e.wait(SLEEPTIME)
        
        while not self.exit_flag and last_fwi['app'] == '':
            last_fwi = self.getForegroundWindowInfo()
            last_tm = datetime.datetime.now()
            self.rec_e.wait(SLEEPTIME)

        while not self.exit_flag:
            fwi = self.getForegroundWindowInfo()
            tm = datetime.datetime.now()

            with self.lock:
                self.event = {
                'timestamp':f'{last_tm:%Y-%m-%d %H:%M:%S.%f}',
                'duration':round((tm - last_tm).total_seconds(), 2),
                'app' : last_fwi['app'],
                'title' : last_fwi['title'],
                }

                if fwi['app'] != '' and fwi != last_fwi:
                    last_fwi = fwi
                    last_tm = tm

                    self.events.append(self.event)

            self.rec_e.wait(SLEEPTIME)

        # add 'stop' event
        tm = datetime.datetime.now()
        with self.lock:
            self.event = {
            'timestamp':f'{tm:%Y-%m-%d %H:%M:%S.%f}',
            'duration': 1.0,
            'app' : 'activity_tracker.py',
            'title' : 'Activity Tracker Stopped',
            }

            self.events.append(self.event)

        self.flush_db()


    def create_db(self):
        if not os.path.exists(self.db):
            self.logger.info(f'create db {self.db}')
            conn = sqlite3.connect(self.db)
            # create table events
            with conn:
                conn.execute('''
                create table events(
                    id integer primary key autoincrement,
                    timestamp datetime not null,
                    duration decimal(10, 3) not null,
                    app varchar(256) not null,
                    title varchar(1024) not null
                    )
                ''')
            conn.close()


    def insert_events(self, events):
        # insert events
        if len(events) == 0:
            return

        self.logger.info(f'insert [{len(events)}] events')

        if self.db != f"./data/{self.user}_{events[0]['timestamp'][:7]}.db":
            self.db = f"./data/{self.user}_{events[0]['timestamp'][:7]}.db"
            self.create_db()

        with self.db_lock:
            conn = sqlite3.connect(self.db)

            try:
                with conn:
                    conn.executemany('insert into events values (?,?,?,?,?)', [(None, event['timestamp'], event['duration'], event['app'], event['title']) for event in events])
            except Exception as e:
                self.logger.error(f'insert events error, {e}')

            conn.close()


    def update_event(self, event):
        # update event
        timestamp = event['timestamp']
        duration = event['duration']
        app = event['app']
        title = event['title']

        self.logger.info(f'update event {app}')

        if self.db != f"./data/{self.user}_{timestamp[:7]}.db":
            self.db = f"./data/{self.user}_{timestamp[:7]}.db"
            self.create_db()

        with self.db_lock:
            conn = sqlite3.connect(self.db)

            try:
                cur = conn.execute(f"select max(id) from events where timestamp='{timestamp}' and app='{app}' and title='{title}'")
                results = cur.fetchall()
                with conn:
                    if len(results) > 0 and results[0][0] is not None:
                        # update existed
                        id = results[0][0]
                        conn.execute(f"update events set duration={duration} where id={id}")
                    else:
                        # insert new
                        conn.execute(f"insert into events(timestamp, duration, app, title) values('{timestamp}', {duration}, '{app}', '{title}')")

            except Exception as e:
                self.logger.error(f'update event error, {e}')

            conn.close()


    def flush_db(self):
        with self.lock:
            events = self.events.copy()
            self.events.clear()
            event = self.event.copy()

        try:
            if len(events) > 0:
                self.update_event(events[0])
                self.insert_events(events[1:])
            else:
                self.update_event(event)
        except Exception as e:
            self.logger.error(f'recording error, {e}')


    def start_record(self):
        # self.daemon = True
        self.start()

        print('start recording')
        sleep(10)
        while not self.exit_flag:
            self.flush_db()

            self.rec_e.wait(DBSYNCSLEEPTIME)



def run():
    ar = ActivityTracker()
    ar.start_record()


if __name__ == '__main__':

    run()
