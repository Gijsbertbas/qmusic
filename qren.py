#!/usr/lib/python3
import argparse
import glob
import logging
import os
from slugify import slugify
import subprocess, shutil

from bs4 import BeautifulSoup
from mutagen.mp3 import MP3
from mutagen.flac import FLAC
import pdfkit
import spotipy
import spotipy.util as sputil

# Initiate logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
fmt = logging.Formatter('%(asctime)s - %(name)s - %(levelname)-8s: %(message)s')

# always log to stream
sh = logging.StreamHandler()
sh.setFormatter(fmt)
sh.setLevel(logging.DEBUG)
logger.addHandler(sh)

class Music:
    '''
    A class containing all relevant information about a track or album
    It should contain all data for on the merge_cards
    If no track_title present it will be assumed an album
    '''
    def __init__(self):
        self.track_title = None
        self.album_title = None
        self.artist = None
        self.filetype = None

    @property
    def name(self):
        if self.track_title:
            return slugify(self.track_title)
        elif self.album_title:
            return slugify(self.album_title)
        else:
            None

    @property
    def art_uri(self):
        if self.name:
            # capture all img formats (e.g. png, jpg)
            art_uri = 'img/{}.*'.format(self.name)
            files = glob.glob(art_uri)
            return files[0] if files else None
        else:
            return None


class Uri:

    def __init__(self, uri_in=None):
        self.uri_in = uri_in
        self.path = os.getcwd()
        self.path_out = os.path.join(os.getcwd(), 'out')
        self.path_img = os.path.join(os.getcwd(), 'img')
        self.music = None
        self.spotify_access = None
        self.is_processed = False

        if not os.path.exists(self.path_out):
            os.mkdir(self.path_out)
            os.mkdir(os.path.join(self.path_out, 'img'))
            shutil.copyfile('cards.css', os.path.join(self.path_out, 'cards.css'))

        if not uri_in:
            logger.error("no input uri received, can't do much!")
        else:
            logger.info('initiated Uri instance with input {} as type {}'.format(self.uri_in, self.type))

    @property
    def type(self):
        if self.uri_in:
            if 'spotify' in self.uri_in:
                return 'spotify'
            elif 'cmd' in self.uri_in:
                return 'command'
            else:
                return 'library'
        else:
            return 'unknown'

    def process(self, title=None):
        if self.is_processed:
            logger.info('Reprocessing...')

        if self.type == 'library':
            self.uri_out = 'lib:'
            self.is_processed = self._process_library_uri()
        elif self.type == 'spotify':
            self.uri_out = ''
            self.is_processed = self._process_spotify_uri()
        elif self.type == 'command':
            self.uri_out = ''
            self.is_processed = self._process_cmd(title)
        else:
            logger.error('Cannot process uri {}, type unknown!'.format(self.uri_in))

    def generate_card(self):

        if not self.is_processed:
            logger.error('Uri is not (properly) processed yet! first run Uri.process()')
            return

        self._generate_card_imgs()

        html = ''
        html += '<html>\n'
        html += '<head>\n'
        html += ' <link rel="stylesheet" href="cards.css">\n'
        html += '</head>\n'
        html += '<body>\n'
        html += '<div class="card">\n'
        html += self._card_content_html()
        html += '</div>\n'
        html += '</body>\n'
        html += '</html>\n'

        html_filename = '{0}.html'.format(self.music.name)
        html_file = os.path.join(self.path_out, html_filename)

        with open(html_file, 'w') as f:
            f.write(html)

        logger.info('Generated card: {}'.format(html_file))

    def _process_library_uri(self):
        # first check if we deal with a track or an album
        if os.path.isfile(self.uri_in):
            logger.info('Processing {} as a library track.'.format(self.uri_in))
            self.uri_out += 'track:'
            track = Music()
            # process mp3 and flac separately using the mutagen library
            if os.path.splitext(self.uri_in)[-1].lower() == '.mp3':
                track.filetype = 'mp3'
                self.uri_out += '/MP3{}'.format(self.uri_in.split('/MP3')[1])
                mp = MP3(self.uri_in)
                track.track_title = mp.get('TIT2').text[0]
                track.album_title = mp.get('TALB').text[0]
                track.artist = mp.get('TPE1').text[0]

                self.music = track

                art = self._find_artwork(mp)
                if not art:
                    logger.error('Could not find art for {}'.format(self.uri_in))
                    return False
                return True
            elif os.path.splitext(self.uri_in)[-1].lower() == '.flac':
                track.filetype = 'flac'
                self.uri_out += '/FLAC{}'.format(self.uri_in.split('/FLAC')[1])
                fl = FLAC(self.uri_in)
                track.track_title = fl.get('title')[0]
                track.album_title = fl.get('album')[0]
                track.artist = fl.get('artist')[0]

                self.music = track

                art = self._find_artwork(fl)
                if not art:
                    logger.error('Could not find art for {}'.format(self.uri_in))
                    return False
                return True
            else:
                logger.error('File type {} not implemented'.format(os.path.splitext(self.uri_in)[-1]))
                return False
        elif os.path.isdir(self.uri_in):
            # if a folder is given: assume it is an album folder containing tracks
            logger.info('Processing {} as a library album.'.format(self.uri_in))
            self.uri_out += 'album:'
            album = Music()
            if 'MP3' in self.uri_in:
                self.uri_out += '/MP3{}'.format(self.uri_in.split('/MP3')[1])
                tracks = self._list_files(self.uri_in, 'mp3')
                if tracks:
                    album.filetype = 'mp3'
                    mp = MP3(tracks[0])
                    album.album_title = mp.get('TALB').text[0]
                    album.artist = mp.get('TPE1').text[0]
                    self.music = album

                    found_art = self._find_artwork(mp)
                    if not found_art:
                        logger.error('Could not find art for {}'.format(self.uri_in))
                        return False
                    return True
            elif 'FLAC' in self.uri_in:
                self.uri_out += '/FLAC{}'.format(self.uri_in.split('/FLAC')[1])
                tracks = self._list_files(self.uri_in, 'flac')
                if tracks:
                    album.filetype = 'flac'
                    fl = FLAC(tracks[0])
                    album.album_title = fl.get('album')[0]
                    album.artist = fl.get('artist')[0]
                    self.music = album

                    found_art = self._find_artwork(fl)
                    if not found_art:
                        logger.error('Could not find art for {}'.format(self.uri_in))
                        return False
                    return True
                else:
                    logger.error('No files found in album folder {}.'.format(self.uri_in))
                    return False
        else:
            logger.error('no valid library uri presented: {}'.format(self.uri_in))
            return False

    def _process_spotify_uri(self):
        '''
        process a uri which appears to be a spotify uri
        if this process has been ran before during the session,
        sp should already exist
        '''
        if not self.spotify_access:
            sp = self._get_spotify_access()

        if 'track' in self.uri_in:
            logger.info('Processing {} as a spotify track.'.format(self.uri_in))
            track = Music()
            track.filetype = 'spotify'

            sp_track = sp.track(self.uri_in)
            track.track_title = sp_track['name']
            track.artist = sp_track['artists'][0]['name']
            track.album_title = sp_track['album']['name']
            self.music = track
            self.uri_out += sp_track['uri']

            arturl = sp_track['album']['images'][0]['url']
        elif 'album' in self.uri_in:
            logger.info('Processing {} as a spotify album.'.format(self.uri_in))
            album = Music()
            album.filetype = 'spotify'

            sp_album = sp.album(self.uri_in)
            album.album_title = sp_album['name']
            album.artist = sp_album['artists'][0]['name']
            self.music = album
            self.uri_out += sp_album['uri']

            arturl = sp_album['images'][0]['url']
        else:
            logger.error('Could not recognise the type of Spotify uri')

        artimg = os.path.join(self.path_img,'{}.jpg'.format(self.music.name))
        if not os.path.exists(artimg):
            logger.debug('fetching artwork for {} from spotify'.format(self.music.name))
            subprocess.check_output(['curl', arturl, '-o', artimg])

        return True

    def _process_cmd(self, title):
        logger.info('Processing command {}.'.format(self.uri_in))
        self.uri_out += self.uri_in
        self.music = Music()
        self.music.track_title = title
        return True

    def _find_artwork(self, loaded_file):

        artimg = os.path.join(self.path_img,'{0}.jpg'.format(self.music.name))

        if os.path.exists(artimg):
            logger.info('artwork already present')
            return True
        else:
            # check if the mp3/flac file contains an image
            # haven't found files where this occurs, is therefore not tested
            if self.is_track:
                if self.music.filetype == 'mp3':
                    img = loaded_file.get('APIC:')
                elif self.music.filetype == 'flac':
                    img = loaded_file.get('images')
                else:
                    pass
            else:
                img = None

            if img:
                logger.info('found artwork in track file')
                with open(artimg,'wb') as f:
                    f.write(img.data)
                return True
            else:
                logger.debug('no artwork present in track file')
                logger.info('looking in folder for album art')
                # see if the folder contains artwork
                path = os.path.split(loaded_file.filename)[0]
                jpgs = self._list_files(path, with_ext='.jpg')
                if jpgs:
                    for jpg in jpgs:
                        if 'folder.jpg' in jpg.lower():
                            logger.info('using {} as artwork'.format(jpg))
                            shutil.copyfile(jpg, artimg)
                            return True
                    logger.info('using {} as artwork'.format(jpgs[0]))
                    shutil.copyfile(jpgs[0], artimg)
                    return True
                else:
                    # no artwork present in folder either
                    logger.error('using dummy art for {}'.format(self.music.name))
                    shutil.copyfile('img/dummy.png', 'img/{0}.png'.format(self.music.name))
                    return True

    def _generate_card_imgs(self):
        qrout = os.path.join(self.path_out, 'img', '{}_qr.png'.format(self.music.name))
        artin = self.music.art_uri
        try:
            shutil.copyfile(artin, os.path.join(self.path_out,'{}'.format(artin)))
        except Exception as e:
            logger.error('could not find art image {} (error {})'.format(artin, e))

        subprocess.check_output(['qrencode', '-o', qrout, '-s', '8', self.uri_out])
        return True

    def _card_content_html(self):
        qrimg = 'img/{}_qr.png'.format(self.music.name)

        html = ''
        html += '  <img src="{0}" class="art"/>\n'.format(self.music.art_uri)
        html += '  <img src="{0}" class="qrcode"/>\n'.format(qrimg)
        html += '  <div class="labels">\n'
        if self.is_track:
            html += '    <p class="song">{0}</p>\n'.format(self.music.track_title)
            if self.music.artist:
                html += '    <p class="artist"><span class="small">door</span> {0}</p>\n'.format(self.music.artist)
            if self.music.album_title:
                html += '    <p class="album"><span class="small">van album</span> {0}</p>\n'.format(self.music.album_title)
        else:
            html += '    <p class="albumfull">{0}</p>\n'.format(self.music.album_title)
            html += '    <p class="artist"><span class="small">door</span> {0}</p>\n'.format(self.music.artist)
        html += '  </div>\n'
        return html

    def _get_spotify_access(self):
        username = 'gbstraathof'
        scope = 'user-library-read'
        client_id = 'c8e8b5b730014b4ab0fca9241d1b0bd3'
        client_secret = 'bcae2033a1fa42c7ab2867a188e64604'
        token = sputil.prompt_for_user_token(username, scope,
                                             client_id=client_id,
                                             client_secret=client_secret,
                                             redirect_uri='http://localhost/')
        if token:
            spotify_access = True
            self.spotify_access = spotipy.Spotify(auth=token)
            return self.spotify_access
        else:
            raise ValueError('Can\'t get Spotify token for ' + username)
            return


    def _list_files(self, path, with_ext=None):
        ''' return a list of all files with extension 'with_ext' '''
        return [os.path.join(path, file) for file in os.listdir(path) if file.lower().endswith(with_ext)]

    @property
    def is_track(self):
        return True if self.music.track_title else False

def list_files(path, with_ext=None):
    ''' return a list of all files with extension 'with_ext' '''
    return [os.path.join(path, file) for file in os.listdir(path) if file.lower().endswith(with_ext)]

def generate_pdf(filename='print'):
    # Create the output directory

    path_out = os.path.join(os.getcwd(), 'out')
    html_file = os.path.join(path_out,'print.html')

    os.remove(html_file) if os.path.exists(html_file) else None

    index = 0
    html = '''
<html>
<head>
  <link rel="stylesheet" href="cards.css">
</head>
<body>

'''

    cards = list_files(path_out, 'html')
    # for file in os.listdir(path):
    #     if file.endswith(".html"):
    #         cards.append(os.path.join(path, file))

    logger.info('found {} individual cards to merge'.format(len(cards)))

    for card in cards:
        with open(card, 'r') as f:
            soup = BeautifulSoup(f, 'html.parser')

        div = soup.find('div', {'class':'card'})

        if div:
            html += div.prettify()
            html += '\n'

            if index % 2 == 1:
                html += '<br style="clear: both;"/>\n'
                html += '\n'

            index += 1

    html += '\n'
    html += '</body>\n'
    html += '</html>\n'

    with open(html_file, 'w') as f:
        f.write(html)

    pdf_file = os.path.join(os.getcwd(), filename+'.pdf')
    if pdfkit.from_file(html_file, pdf_file, options={'quiet':''}):
        logger.info('created {}'.format(pdf_file))

tests = {
    'library_mp3_track' : '/mnt/gijstereo/MP3/Ane Brun/Rarities/Ane Brun - 01. All My Tears.mp3',
    'library_flac_track': '/mnt/gijstereo/FLAC/Queen/A Night At The Opera/09 Love Of My Life.flac',
    'library_flac_album': '/mnt/gijstereo/FLAC/Queen/A Night At The Opera/',
    'library_mp3_album' : '/mnt/gijstereo/MP3/Ane Brun/Rarities/',
    'spotify_track'     : 'spotify:track:0RQOZ6q9OTvfQX8HCGzmIB',
    'spotify_link'      : 'https://open.spotify.com/track/0RQOZ6q9OTvfQX8HCGzmIB',
    'spotify_album'     : 'spotify:album:5fMVDfMZhrfT8oiUWR1Rz0'
}

cmds = {
  'cmd:toggle': 'Play / Pause',
  'cmd:next': 'Volgende Nummer',
  'cmd:previous': 'Vorige Nummer',
  'cmd:volume:+': 'Harder',
  'cmd:volume:-': 'Zachter'
}


def run_tests():
    logger.info('Running tests, ignoring all other parameters...')
    logger.info('Testing workflow for various input types')
    for test in tests:
        logger.info('Testing an URI for: {}'.format(test))
        u = Uri(tests[test])
        u.process()
        u.generate_card()
    logger.info('Tests finished')

def main(): #using argparser, the recommended module
    parser = argparse.ArgumentParser(description="Generate 'Playing cards' for the volumio qr player")
    parser.add_argument('-c','--commands', action='store_true', help='(re)process standard commands, hardwired here in the code')
    parser.add_argument('-u','--uri', type=str, help='process uri')
    parser.add_argument('-p','--print', type=str, help='generate pdf with all html cards present in the output folder, provide output filename')
    parser.add_argument('-t','--tests', action='store_true', help='run tests (will ignore all other parameters)')
    parser.add_argument('-m','--move', action='store_true', help='move output folder')
    args = parser.parse_args()

    if args.tests:
        path_out = os.path.join(os.getcwd(), 'out')
        if os.path.exists(path_out):
            os.rename(path_out, path_out+'.temp')
            run_tests()
            os.rename(path_out, path_out+'.test')
            os.rename(path_out+'.temp', path_out)
        else:
            run_tests()
            os.rename(path_out, path_out+'.test')
        logger.info('test results are in {}'.format(path_out+'.test'))

    if args.move:
        path_out = os.path.join(os.getcwd(), 'out')
        if os.path.exists(path_out):
            if os.path.exists(path_out+'.old'):
                shutil.rmtree(path_out+'.old')
            os.rename(path_out, path_out+'.old')
            logger.info('moved output filder to out.old')
        else:
            logger.info('no output present, nothing to move')

    if args.commands:
        logger.info('processing commands...')
        for cmd in cmds:
            u = Uri(cmd)
            u.process(title=cmds[cmd])
            u.generate_card()

    if args.uri:
        logger.info('processing uri: {}'.format(args.uri))
        u = Uri(args.uri)
        u.process()
        u.generate_card()

    if args.print:
        generate_pdf(filename=args.print)

if __name__ == '__main__':
    main()
