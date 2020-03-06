#!/usr/bin/env python3

from logger import qrplayer_logger as logger
import os
from pprint import pprint
import subprocess
from time import sleep

from socketIO_client import SocketIO


def host_available(hostname):
    '''
    Function to verify if a host is available
    Using ping with 5 packages and waiting 3 ms for a response
    The function transforms the return code from ping into a boolean for available (True) or not (False)
    '''
    ret_code = subprocess.call(['ping', '-c', '5', '-W', '3', hostname],
                                stdout=open(os.devnull, 'w'),
                                stderr=open(os.devnull, 'w'))
    return not bool(ret_code)


class VolumioControler:

    def __init__(self, hostname='gijstereo.local', logger=None): #'192.168.178.59'):

        self.playload = None

        if not logger:
            logger = initiatelogger()

        # if the Volumio host is not available, wait 5 seconds and try again
        # current timeout is 30 seconds
        if not host_available(hostname):
            attempts = 0
            sleep(5)
            while (not host_available(hostname)) and (attempts < 6):
                attempts += 1
                logger.info('waiting for host {} to be available'.format(hostname))
                sleep(5)

        if host_available(hostname):
            sio = SocketIO(hostname)

            if sio.connected:
                self.connected = True
                logger.info('connected to {}'.format(hostname))

                sio.on('pushState', self._on_re_state)
                sio.on('pushBrowseLibrary', self._on_re_browse)
                self.sio = sio
                self.state()
            else:
                logger.error('failed to connect to {}'.format(server))
        else:
            logger.error('failed to start, host {} was not found alive'.format(hostname))


    def _on_re_state(self,data):
        self.playload = {k: data[k] for k in data.keys() & {'service', 'title', 'uri'}}

    def _on_re_browse(self, data):
        logger.info('received browsing results')

    def state(self):
        self.sio.emit('getState', '')
        self.sio.wait(seconds=1)

    def playsong(self, uri):
        self.sio.emit('addPlay',{'uri': uri})
        self.sio.wait(seconds=1)
        self.state()
        if self.playload['uri'] == uri:
            logger.debug('successfully started playing {}'.format(uri))
        else:
            logger.error('failed to start playing {}'.format(uri))

    def toggle(self):
        self.sio.emit('toggle','')

    def volume(self, set):
        self.sio.emit('volume', set)

    def next(self):
        self.sio.emit('next', '')

    def previous(self):
        self.sio.emit('prev', '')

    def browsespotify(self):
        self.sio.emit('browseLibrary', {'uri':'spotify/playlists'})
        self.sio.wait(seconds=1)

    def disconnect(self):
        self.sio.disconnect()
        self.connected = self.sio.connected

    def shutdown(self):
        self.sio.emit('shutdown','')
        self.sio.disconnect()
        self.connected = False

class Scanner():

    def __init__(self, hostname='gijstereo.local', logger=None):
        self.scan = None
        if not logger:
            logger = Logger('SCANNER')
        self.stereo = VolumioControler(hostname=hostname, logger=logger)
        self.qrcode = ''


    def _handlecmd(self, cmd):
        if cmd.startswith('cmd:'):
            logger.info('process command')
            task = cmd.split(':')[1]
            if task == 'toggle':
                self.stereo.toggle()
            elif task == 'volume':
                mode, task, set = cmd.split(':')[:3]
                if set in ['+','-']:
                    self.stereo.volume(set)
                else:
                    self.stereo.volume(int(set))
            elif task == 'next':
                self.stereo.next()
            elif task == 'previous':
                self.stereo.previous()
            else:
                logger.error("command '{}' not understood".format(cmd))
        elif cmd.startswith('spotify:'):
            self.stereo.playsong(cmd)
        elif cmd.startswith('lib:'):
            self.stereo.playsong(cmd)
        else:
            logger.error("don't know what to do with command '{}'".format(cmd))

    def _scan(self):

        while True:
            data = self.cam.readline()
            qrcode = str(data)[8:]
            if qrcode:
                self.qrcode = qrcode.rstrip()
                logger.info('scanned {}'.format(self.qrcode))
                self._handlecmd(self.qrcode)

    def startscanner(self):
        self.cam = os.popen('/usr/bin/zbarcam --nodisplay --prescale=300x250', 'r')
        try:
            self._scan()
        except KeyboardInterrupt:
            logger.info('Stopping scanner...')
        finally:
            self.stereo.disconnect()
            if not self.stereo.connected:
                logger.info('disconnected from server')
                logger.info('------------------------')
            self.cam.close()

if __name__ == '__main__':

    logger.info("Start logging...")

    s = Scanner(logger=logger)
    s.startscanner()
