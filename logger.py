#!/usr/bin/env python3

import logging
import logging.config
import logging.handlers
import sys
import os


LOGGING_CONFIG = {
    'version': 1,
    'disable_existing_loggers': True,
    'formatters': {
        'standard': {
            'format': '%(asctime)s - %(name)s - %(levelname)-8s: %(message)s'
        },
    },
    'handlers': {
        'stream': {
            'level': 'INFO',
            'formatter': 'standard',
            'class': 'logging.StreamHandler',
        },
        'qrplayer_file': {
            'level': 'DEBUG',
            'formatter': 'standard',
            'class': 'logging.FileHandler',
            'filename': '/home/gijs/logs/qrplayer.log',
        },
        'controler_file': {
            'level': 'DEBUG',
            'formatter': 'standard',
            'class': 'logging.FileHandler',
            'filename': '/home/gijs/logs/controler.log',
        },
        'socket': {
            'level': 'DEBUG',
            'class': 'logging.handlers.SocketHandler',
            'host': 'pinas.local',
            'port': logging.handlers.DEFAULT_TCP_LOGGING_PORT,
        },
    },
    'loggers': {
        '': {
            'handlers': ['stream'],
            'level': 'DEBUG',
            'propagate': False,
        },
        'qrplayer': {
            'handlers': ['qrplayer_file', 'socket'],
            'level': 'DEBUG',
            'propagate': False,
        },
        'controler': {
            'handlers': ['stream', 'controler_file', 'socket'],
            'level': 'DEBUG',
            'propagate': False,
        },
    }
}

logging.config.dictConfig(LOGGING_CONFIG)

qrplayer_logger = logging.getLogger('qrplayer')
controler_logger = logging.getLogger('controler')


# class Logger(logging.Logger):
#
#     def __init__(self, name):
#         super().__init__(name, level=logging.DEBUG)
#         handler = logging.StreamHandler(sys.stdout)
#         handler.setLevel(logging.DEBUG)
#         self.formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)-8s: %(message)s')
#         handler.setFormatter(self.formatter)
#         self.addHandler(handler)
#
#     def set_level(self, level):
#         level = level.lower()
#         if level == 'debug':
#             super(Logger, self).setLevel(logging.DEBUG)
#         elif level == 'error':
#             super(Logger, self).setLevel(logging.ERROR)
#         elif level == 'info':
#             super(Logger, self).setLevel(logging.INFO)
#         elif level == 'warning':
#             super(Logger, self).setLevel(logging.WARNING)
#
#     def set_file(self, filename='test.log'):
#         logfile = os.path.join('home', 'gijs', 'logs', filename)
#         fh = logging.FileHandler(logfile)
#         fh.setLevel(logging.DEBUG)
#         fh.setFormatter(self.formatter)
#         self.addHandler(fh)
#
#     def set_remote(self, host='pinas.local'):
#         sh = logging.handlers.SocketHandler(host,
#                     logging.handlers.DEFAULT_TCP_LOGGING_PORT)
#         sh.setLevel(logging.DEBUG)
#         self.addHandler(sh)
