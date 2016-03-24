#!/usr/bin/env python
import sys
import zipfile
import os
from lxml import html
import requests
import hashlib
from functools import partial
import clapp

# TODO:
#  * Add files to dirs

MANGAREADER = 'http://www.mangareader.net/{}/{}/{}'
MANGATOWN = 'http://www.mangatown.com/manga/{}/c{:0>3}/{}.html'

def md5sum(filename):
    with open(filename, mode='rb') as f:
        d = hashlib.md5()
        for buf in iter(partial(f.read, 128), b''):
            d.update(buf)
    return d.hexdigest()

def parse_cli():
    app = clapp.App()
    app.name = 'MR Crawl'
    app.author = 'Kevin K. <kbknapp@gmail.com>'
    app.version = '0.2.2'
    app.about = 'Command Line utility to download manga into CBR files'
    
    app.new_arg('manga', \
            index=1, \
            required=True, \
            help='The name of the manga, lowercase, hyphens for spaces')
    app.new_arg('page', \
            short='-p', \
            long='--page',\
            args_taken=1, \
            help='Start at page number')
    app.new_arg('chapter', \
            short='-c', \
            long='--chapter',\
            args_taken=1, \
            help='Start at chapter number')
    app.new_arg('src', \
            short='-s', \
            long='--src',\
            args_taken=1, \
            help='Source to download from (all lowercase, nospaces; i.e mangareader [default])')

    return app.start()

def main(cxt, manga_url=MANGAREADER):
    # prefix for CBR and JPG files
    manga = cxt['manga']
    file_name = '{}_{:0>3}_{:0>3}.jpg'
    cbr = '{}_ch{:0>3}.cbr'

    chapter = 0
    if cxt['chapter']:
        chapter = int(cxt['chapter']) - 1
    page = 0
    if cxt['page']:
        chapter = int(cxt['page']) - 1
    curr = ''
    prev = ''
    dups = 0

    while True:
        chapter += 1
        url = manga_url.format(manga, chapter, page)
        if not requests.get(url):
            break
        print(':: Downloading Chapter...{}'.format(chapter))
        imgs = []
        print(' -> Pages', end='', flush=True)
        while True:
            page += 1
            url = manga_url.format(manga, chapter, page)
            req = requests.get(url)
            if req:
                html_txt = requests.get(url).text
                doc = html.fromstring(html_txt)
                img_urls = [i.attrib['src'] for i in doc.cssselect('img')]
                img = img_urls[0]
                print('...{}'.format(page), end='', flush=True)
                img_name = file_name.format(manga, str(chapter).rjust(3, '0'), str(page).rjust(3, '0'))
                with open(img_name, 'wb') as f:
                    f.write(requests.get(img).content)
                curr = md5sum(img_name)
                if curr == prev:
                    dups += 1
                    if dups > 3:
                        print('\n -> Found Multiple Duplicates')
                        print(' -> Cleaning Up...', end='', flush=True)
                        imgs.append(img_name)
                        for img in imgs:
                           os.remove(img)
                        print('Done')
                        return 
                else:
                    prev = curr
                    dups = 0
                imgs.append(img_name)
            else:
                page = 0
                print('\n -> Creating CBR...', end='', flush=True)
                zip = zipfile.ZipFile(cbr.format(manga, chapter), 'w')
                for img in imgs:
                    zip.write(img)
                    os.remove(img)
                zip.close()
                print('Done')
                break

if __name__ == '__main__':
    cxt = parse_cli()
    if cxt['src']:
        src = cxt['src'][0]
        if src == 'mangatown':
            print('Downloading {} from {}'.format(cxt['manga'], 'mangatown'))
            sys.exit(main(cxt, MANGATOWN))
    print('Downloading {} from {}'.format(cxt['manga'], 'mangareader'))
    sys.exit(main(cxt))
