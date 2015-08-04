import json
import logging
import random
import traceback
import time
import urllib
import urllib2

from flask import Flask
from flask import request
from google.appengine.api import memcache

import api

app = Flask(__name__)
app.config['DEBUG'] = True

# Note: We don't need to call run() since our application is embedded within
# the App Engine WSGI application server.

logger = logging.getLogger(__name__)
# logger.setLevel(logging.DEBUG)  # this doesn't work, it's still INFO (maybe
                                  # set by Flask?)

WEBHOOK = True
LAST_4CHAN_API_CALL_TIME = 0  # global

# Bot modes settings
ECHO = False  # echo everything, global


@app.route('/')
def index():
    """Return a friendly HTTP greeting."""
    return 'Hello World'


@app.errorhandler(404)
def page_not_found(e):
    """Return a custom 404 error."""
    return 'Sorry, nothing at this URL.', 404


@app.route('/test', methods=['GET', 'POST'])
def test():
    """Test"""
    logger.info("Got these args %s", request.args)
    # add means only add when key doesn't exist
    #memcache.add(key='key', value=str(request.args), time=3600)
    memcache.set(key='key2', value=str(request.args), time=3600)
    return str(memcache.get('a:images'))
    #return str(memcache.get('key2'))


@app.route('/tasks/update_cache', methods=['GET'])
def update_cache():
    """Periodic cache update."""
    timeout = 60

    t0 = time.time()

    # get from https://a.4cdn.org/{board}/threads.json
    board = 'a'
    response = urllib2.urlopen(api.threads_url(board), timeout=timeout)
    threads = json.load(response)  # response is file-like
    time.sleep(2)

    # a nice functional approach (may be faster)
    all_threads = reduce(lambda x, y: x + y['threads'], threads, [])

    # all thread numbers, can be inserted into:
    # http://a.4cdn.org/{board}/thread/{thread_no}.json
    all_thread_nos = [t['no'] for t in all_threads]

    all_img_filenames = []
    for no in all_thread_nos:
        try:
            response = urllib2.urlopen(api.posts_url(board, no),
                                       timeout=timeout)
        except urllib2.HTTPError:
            logger.warning("Could not open: %s", api.posts_url(board, no))
            logger.warning(traceback.format_exc())
            continue
        except Exception:
            logger.error(
                "Exception when opening: %s", api.posts_url(board, no))
            logger.error(traceback.format_exc())
            continue
        posts = json.load(response)['posts']  # a list of post objects

        # Note: not all posts contain images
        img_filenames = [str(p['tim']) + p['ext'] for p in posts if
                         p.get('tim') is not None]
        all_img_filenames.extend(img_filenames)
        time.sleep(2)
    logger.info("Update finished. %s threads, %s img filenames",
                len(all_thread_nos), len(all_img_filenames))
    logger.info("Total time %s", time.time() - t0)

    memcache.set(key='a:images', value=all_img_filenames)

    return "a okay"


@app.route('/listen', methods=['POST'])
def listen():
    """Listening to incoming messages from webhook"""
    logger.info(request.get_json())

    if WEBHOOK:
        update_id, msg = api.get_update(request.get_json())
    else:
        # TODO: updates via long polling; this doesn't work yet (use threads?)
        # updates = api.get_updates(request.args)  # a list of updates
        # update_id, msg = api.get_latest_update(updates)
        pass

    if msg:
        chat_id = msg['chat']['id']
        text = msg.get('text')  # TODO: is optional!!
        cmd = ''
        has_cmd = api.is_command(msg.get('text', ''))

        if len(has_cmd) > 0:
            logger.debug(has_cmd)
            cmd = has_cmd[0]

            if cmd == 'echo':
                try:
                    global ECHO
                    if has_cmd[1] == 'on':
                        ECHO = True
                        api.send_message(chat_id, "Echo turned on")
                    elif has_cmd[1] == 'off':
                        ECHO = False
                        api.send_message(chat_id, "Echo turned off")
                except Exception:
                    logger.warning("/echo has no second arg")
                    # just catch the exceptions for now...
                    logger.warning(traceback.format_exc())

            elif cmd == '4chan':
                global LAST_4CHAN_API_CALL_TIME
                now = time.time()

                imgs = memcache.get('a:images')
                if not imgs:
                    logger.error("Cache empty for a:images")
                    return "No images", 404

                if now - LAST_4CHAN_API_CALL_TIME < 1:
                    api.send_message(chat_id, "pls be gentle on api")
                else:

                    # 10 retries
                    for i in range(10):
                        logger.info("Getting random img, try number: %s", i)
                        board = 'a'
                        img_name = random.choice(imgs)
                        img_url = api.img_url(board, img_name)
                        resp = urllib.urlopen(img_url)
                        if resp.getcode() == 200:
                            api.send_message(chat_id, img_url)
                            break
                        else:
                            logger.info("404 url: %s", img_url)
                            # TODO: remove from cache
                            time.sleep(1)

                    LAST_4CHAN_API_CALL_TIME = now

            elif cmd == 'sakurafish':
                api.send_message(chat_id,
                                 "https://data.archive.moe/board/a/image/1434/"
                                 "39/1434397984867.jpg")

            elif cmd == 'help':
                api.send_message(
                    chat_id, "Commands:\n/4chan: random 4chan image (only /a/"
                             " for now)\n/sakurafish: sakurafish")

        # do not echo commands
        if ECHO and not cmd:
            resp = api.send_message(chat_id, text)
            logger.debug("Echo result: %s", resp)

    return "A response"
