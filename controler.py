#!/usr/bin/env python3

import time

from socketIO_client import SocketIO
from gpiozero import Button, LED

from logger import controler_logger as logger
import subprocess
from signal import pause


def shut_down(hostname='gijstereo.local', sonoff='sonoff_gijstereo'):

    logger.info('send stop to qrplayer service')
    subprocess.run(['sudo', 'systemctl', 'stop', 'qrplayer.service'])

    try:
        sio = SocketIO(hostname, wait_for_connection=False)
        logger.info('connected to {}'.format(hostname))
        logger.info('send shutdown to Volumio')
        sio.emit('shutdown')
    except:
        logger.error('could not connect to {}'.format(hostname))

    logger.info('send shutdown to {}'.format(sonoff))
    cmnd = 'cmnd/{}/Backlog'.format(sonoff)
    subprocess.run(["mosquitto_pub","-h","192.168.178.13","-t",cmnd,"-m","Delay 1200; Power off"])

    logger.info('shut down myself')
    subprocess.run(['sudo', 'shutdown'])

light = LED(23)
def enlighten(duration=2):
    logger.debug('Light switched on!')
    light.on()
    time.sleep(duration)
    light.off()


if __name__ == '__main__':

    try:
        offswitch = Button(17)
        lightswitch = Button(16)

        lightswitch.when_pressed = enlighten
        offswitch.when_pressed = shut_down
        pause()

    except KeyboardInterrupt:
        logger.info('Stopping controler...')
