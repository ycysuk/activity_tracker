# cyyang
# 2019/12/21

# common: Log, ReadConfig


import datetime
import logging
import configparser



class Log:
    ''' logs '''
    def __init__(self, log_name):
        self.log_name = log_name
        # create logger with '__name__'
        self.logger = logging.getLogger(self.log_name)
        self.logger.setLevel(logging.DEBUG)

        # create file handler which logs even debug messages
        self.fh = logging.FileHandler('./log/{}_{}.log'.format(log_name, datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).strftime('%Y-%m')))
        self.fh.setLevel(logging.DEBUG)

        # create console handler with a higher log level
        self.ch = logging.StreamHandler()
        # self.ch.setLevel(logging.ERROR)
        self.ch.setLevel(logging.DEBUG)

        # create formatter and add it to the handlers
        # formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s')
        self.fh.setFormatter(formatter)
        self.ch.setFormatter(formatter)

        # add the handlers to the logger
        self.logger.addHandler(self.fh)
        self.logger.addHandler(self.ch)


    def __del__(self):
        try:
            self.fh.close()
            self.ch.close()
            self.logger.removeHandler(self.fh)
            self.logger.removeHandler(self.ch)
        except:
            pass



class ReadConfig:
    ''' read config from ini'''
    def __init__(self, logname):
        self.L = Log(logname)
        self.logger = self.L.logger


    def read(self, filename):
        self.logger.info('reading config file {}'.format(filename))
        cfg = configparser.ConfigParser()
        cfg.read(filename)
        return cfg


###########################################################



def run():
    # test

    rc = ReadConfig(logname='test')
    cfg = rc.read('./test.cfg')

    filename = cfg['flights']['file']
    
    del rc

    L = Log('test')
    logger = L.logger
    logger.info('info {}'.format(filename))
    logger.warning('warning')
    logger.error('error')



if __name__ == '__main__':

    run()

###########################################################