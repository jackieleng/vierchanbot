import json
import logging
import urllib
import urllib2
# import requests  # some weird shit with SSL when using requests, strangely
                   # enough urllib and urllib2 seem to work fine...

from google.appengine.ext import ndb

logger = logging.getLogger(__name__)

# Telegram bot api
TOKEN = "113582136:AAF2WHjR7BvoTE_jhP50x05hTp94B5MerwE"
BASE_URL = "https://api.telegram.org/bot" + TOKEN
SENDMESSAGE_URL = BASE_URL + '/sendMessage'

# 4chan api
_threads_url = "https://a.4cdn.org/{board}/threads.json"
_posts_url = "https://a.4cdn.org/{board}/thread/{thread_no}.json"
_images_url = "https://i.4cdn.org/{board}/{imgname}"
threads_url = lambda board: _threads_url.format(board=board)
posts_url = lambda board, thread_no: _posts_url.format(board=board,
                                                       thread_no=thread_no)
img_url = lambda board, imgname: _images_url.format(board=board,
                                                    imgname=imgname)


class PickledThing(ndb.Model):
    """Just store one Python thing with pickle"""
    name = ndb.StringProperty()
    thing = ndb.PickleProperty(compressed=False)


def get_updates(form):
    ok = form.get('ok')

    if ok:
        result = json.loads(form.get('result'))
    else:
        logger.error("Unsuccesful request, description: %s, error_code: %s",
                     (form.get('description'), form.get('error_code')))
        result = {}
    return result


def get_latest_update(updates):
    latest_update = updates[-1]
    update_id = latest_update.get('update_id')
    message = latest_update.get('message')  # optional
    return update_id, message


def get_update(data):
    """The Webhook returns single updates"""
    update_id = data.get('update_id')
    message = data.get('message')  # optional
    return update_id, message


def send_message(chat_id, text, url=SENDMESSAGE_URL, *args, **kwargs):
    # do a post request
    values = {'chat_id': chat_id, 'text': text}
    data = urllib.urlencode(values)
    req = urllib2.Request(url, data)
    response = urllib2.urlopen(req)
    the_page = response.read()
    return the_page


def is_command(msg):
    """Return the command if msg is command, else None"""
    if msg.startswith('/'):
        subs = msg[1:].split(' ')
        return subs
    else:
        return []
