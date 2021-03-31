# activites tracker
# inspired by ActivityWatch
# user interface

# 2020/8/5
# cyyang

import os
import datetime
import time
import sqlite3
import json
import re
from shutil import copy

from threading import Thread, Lock

import getpass

import pandas as pd
import matplotlib.pyplot as plt
from io import BytesIO

# import requests

from bottle import run, static_file
from bottle import get, post, request, response, redirect




from common import Log
from single_instance import singleinstance

HEAD = 20

class ATServer(Thread):
    ''' a simple web app, data statistics and visualization'''
    def __init__(self):
        Thread.__init__(self, name='')
        self.L = Log('at_server')
        self.logger = self.L.logger
        
        self.user = getpass.getuser()
        self.rulefile = './cat_rules.csv'

        self.df_events = pd.DataFrame()
        self.df_grpby = {}


    def read_events(self, from_datetime, to_datetime):
        self.logger.info(f'read events [{from_datetime}, {to_datetime}]')

        # read db of from_datetime
        db_name = f'./data/{self.user}_{from_datetime[:7]}.db'
        conn = sqlite3.connect(db_name)
        self.df_events = pd.read_sql(f"select * from events where timestamp between '{from_datetime}' and '{to_datetime}'", conn, parse_dates={'timestamp':'%Y-%m-%d %H:%M:%S.%f'})
        conn.close()

        if from_datetime[:7] != to_datetime[:7]:
            # contains 2 dbs, read db of to_datetime
            db_name = f'./data/{self.user}_{to_datetime[:7]}.db'
            conn = sqlite3.connect(db_name)
            df = pd.read_sql(f"select * from events where timestamp between '{from_datetime}' and '{to_datetime}'", conn, parse_dates={'timestamp':'%Y-%m-%d %H:%M:%S.%f'})
            conn.close()
            self.df_events = pd.concat([self.df_events, df], ignore_index=True)

        self.df_events['timestamp_end'] = self.df_events.timestamp + pd.to_timedelta(self.df_events.duration, unit='S')

        self.logger.info(f'total {len(self.df_events)} events')


    def refresh_data(self, from_datetime, to_datetime, cats):
        self.read_events(from_datetime, to_datetime)
        self.categorize(cats)
        for by in ['cat', 'app', 'title']:
            df = self.df_events.groupby(by, as_index=False)['duration'].sum().sort_values(by=['duration'], ascending=False).rename(columns={by:'name', 'duration':'value'})

            if len(df) > HEAD:
                self.df_grpby[by] = df.head(HEAD-1).append({'name':'others', 'value':df.tail(len(df)-HEAD+1).value.sum()}, ignore_index=True)
            else:
                self.df_grpby[by] = df

            self.df_grpby[by]['value'] = (self.df_grpby[by]['value'] / 60).round(1)  # convert to minutes

        # uncat
        for by in ['app', 'title']:
            df = self.df_events.loc[self.df_events.cat == 'uncat'].groupby(by, as_index=False)['duration'].sum().sort_values(by=['duration'], ascending=False).rename(columns={by:'name', 'duration':'value'})

            if len(df) > HEAD:
                self.df_grpby[f'uncat_{by}'] = df.head(HEAD-1).append({'name':'others', 'value':df.tail(len(df)-HEAD+1).value.sum()}, ignore_index=True)
            else:
                self.df_grpby[f'uncat_{by}'] = df

            self.df_grpby[f'uncat_{by}']['value'] = (self.df_grpby[f'uncat_{by}']['value'] / 60).round(1)  # convert to minutes

        return self.df_events.timestamp.min(), self.df_events.timestamp_end.max()


    def categorize(self, cats):
        self.df_events['cat'] = 'uncat'
        for cat, rule in cats:
            self.df_events.loc[self.df_events.title.str.match(rule, case=False) | self.df_events.app.str.match(rule, case=False), 'cat'] = cat


    def timeline(self, by='cat'):
        self.df_events['id_g'] = ( ~ self.df_events[by].eq(self.df_events[by].shift())).astype(int).cumsum()
        gb = self.df_events.groupby('id_g', sort=False, as_index=False)

        self.df_timeline = gb.first()[[by, 'timestamp']]
        self.df_timeline['timestamp_end'] = gb.last()['timestamp_end']
        # self.df_timeline['duration'] = gb.duration.sum()['duration']
        self.df_timeline['duration'] = (self.df_timeline.timestamp_end - self.df_timeline.timestamp).dt.total_seconds()

        # record top title in each group
        df2 = self.df_events.groupby(['id_g', 'title'], sort=False, as_index=False).duration.sum()
        self.df_timeline['title'] = df2.loc[df2.index.isin(df2.groupby('id_g', sort=False).duration.idxmax()), 'title'].values  # mention indices mismatch

        self.logger.info(f'combine events by {by}, reduce size from {len(self.df_events)} to {len(self.df_timeline)}')



    def read_catrules(self):
        self.logger.info('read cat rules')
        if os.path.exists(self.rulefile):
            with open(self.rulefile, 'r', encoding='utf-8') as f:
                cats = f.read()
            cats = [l.partition(',')[::2] for l in cats.strip('\n').split('\n')[1:]]
            return cats
        else:
            return []


    def save_catrules(self, cats):
        if os.path.exists(self.rulefile):
            copy(self.rulefile, self.rulefile + '.bak')

        with open(self.rulefile, 'w', encoding='utf-8') as f:
            f.write('cat,rule\n')
            for cat, rule in cats:
                if cat != '' and rule != '':
                    f.write(f'{cat},{rule}\n')

        self.logger.info(f'{len(cats)} cat rules saved')


    def chk_running(self):
        tracker = singleinstance('5ed3212f-bf45-48e6-8f74-af76e890f4e5')  # gen by uuid.uuid4()

        # check is another instance of same program running
        if tracker.alreadyrunning():
            self.logger.info(f'activity tracker status: running')
            return True
        else:
            self.logger.info(f'activity tracker status: stopped')
            return False



    # def pie(self, by):
    #     self.logger.info(f'pie by {by}')
    #     if len(self.df_gb) > 0 and by in ['cat', 'app']:
    #         ax = self.df_gb.plot.pie(y='duration', labels=self.df_gb[by].values, autopct='%.2f', legend=False, figsize=(8, 6))
    #         fig = ax.get_figure()
    #         buf = BytesIO()
    #         fig.savefig(buf, format='png', dpi=120)
    #         return buf.getvalue()
    #     else:
    #         return None




###########################################################

ats = ATServer()



###########################################################
# route lists:
# /                         homepage
# /refresh                  refresh
# /<by>.json
# /<by>_timeline.json

###########################################################



@get('/')
def homepage():
    now = datetime.datetime.now()
    from_datetime = f'{now:%Y-%m-%d} 00:00:00'
    to_datetime = f'{now:%Y-%m-%d %H:%M:%S}'

    cats = ats.read_catrules()
    dt_min, dt_max = ats.refresh_data(from_datetime, to_datetime, cats)

    with open('./pages/home.html', 'r', encoding='utf-8') as f:
        html = f.read()

    return re.sub(r'REPLACE_TEXT', f'today {dt_min:%Y-%m-%d %H:%M:%S} - {dt_max:%Y-%m-%d %H:%M:%S} {round((dt_max - dt_min).total_seconds() / 60)}m', html)


@get('/refresh')
def refresh():
    range_ = request.query.get('range', 'today')

    now = datetime.datetime.now()
    if range_ == 'today':
        from_datetime = f'{now:%Y-%m-%d} 00:00:00'
        to_datetime = f'{now:%Y-%m-%d %H:%M:%S}'
    elif range_ == 'yesterday':
        newday = now + datetime.timedelta(days=-1)
        from_datetime = f'{newday:%Y-%m-%d} 00:00:00'
        to_datetime = f'{newday:%Y-%m-%d} 24:00:00'
    elif range_ == 'last3days':
        newday = now + datetime.timedelta(days=-2)
        from_datetime = f'{newday:%Y-%m-%d} 00:00:00'
        to_datetime = f'{now:%Y-%m-%d %H:%M:%S}'
    elif range_ == 'lastweek':
        newday = now + datetime.timedelta(days=-6)
        from_datetime = f'{newday:%Y-%m-%d} 00:00:00'
        to_datetime = f'{now:%Y-%m-%d %H:%M:%S}'

    cats = ats.read_catrules()
    dt_min, dt_max = ats.refresh_data(from_datetime, to_datetime, cats)

    # print('\n', now, len(ats.df_events), range_, dt_min, dt_max, '\n')

    with open('./pages/home.html', 'r', encoding='utf-8') as f:
        html = f.read()

    html = re.sub(r'REPLACE_TEXT', f'{range_} {dt_min:%Y-%m-%d %H:%M:%S} - {dt_max:%Y-%m-%d %H:%M:%S} {round((dt_max - dt_min).total_seconds() / 60)}m', html)
    html = re.sub(rf'<option value="{range_}">', f'<option value="{range_}" selected="selected">', html)

    return html


@get('/<by:re:(?:cat|app|title)>.json')
def get_json(by):
    return ats.df_grpby[by].to_json(orient='records', force_ascii=False)


@get('/<by:re:(?:cat|app|title)>_timeline.json')
def get_json_timeline(by):
    idx_by = json.dumps(dict(zip(ats.df_grpby[by].name, range(len(ats.df_grpby[by])))))

    ats.timeline(by)

    timelines = ats.df_timeline.rename(columns={by:'name', 'timestamp':'start', 'timestamp_end':'end'}).to_json(orient='records', force_ascii=False, date_format='epoch')

    return f'{{"data_by":{get_json(by)}, "idx_by":{idx_by}, "timeline":{timelines}}}'


@get('/uncat_<by:re:(?:app|title)>.json')
def get_json_uncat(by):
    return ats.df_grpby[f'uncat_{by}'].to_json(orient='records', force_ascii=False)


@get('/status.png')
def get_status_png():
    if ats.chk_running():
        return static_file('green.png', root='./pages/pngs/', mimetype='image/png')
    else:
        return static_file('red.png', root='./pages/pngs/', mimetype='image/png')


@get('/catrules.json')
def get_catrules():
    cats = ats.read_catrules()
    return json.dumps(cats)


@get('/catrules')
def catrules_page():
    return static_file('catrules.html', root='./pages/', mimetype='text/html')


@post('/save_catrules')
def save_catrules():
    cats = request.forms.decode().getall('cats_list')
    rules = request.forms.decode().getall('rules_list')
    ats.save_catrules(list(zip(cats, rules)))

    redirect("/catrules")



# @get('/pie.png')
# def pie():
#     by = request.query.get('by', 'cat')

#     response.content_type = 'image/png'
#     return ats.pie(by)



@get('/ui.css')
def homepage_css():
    return static_file('ui.css', root='./pages/', mimetype='text/css')

@get('/jquery-3.5.1/jquery.min.js')
def homepage_jquery():
    return static_file('jquery.min.js', root='./pages/jquery-3.5.1/', mimetype='text/javascript')

@get('/d3-6.3.1/d3.min.js')
def homepage_d3():
    return static_file('d3.min.js', root='./pages/d3-6.3.1/', mimetype='text/javascript')


# @get('/<page:re:(?:register|login|change|upload|query|files)>_html')
# def pages(page):
#     return static_file(f'{page}.html', root='./pages/', mimetype='text/html')




###########################################################

if __name__ == '__main__':
    from argparse import ArgumentParser

    parser = ArgumentParser()
    parser.add_argument('-p', '--port', default=5601, type=int, help='port to listen on')
    args = parser.parse_args()
    port = args.port

    run(host='127.0.0.1', port=port, server='paste', debug=False)
    # run(host='127.0.0.1', port=port, debug=True)


###########################################################
