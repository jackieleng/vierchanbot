## Telegram bot for 4chan imageboard

This bot will fetch a random image from 4chan using the `/4chan` command. Currently only
supports a select few boards. Memcache is run to cache 4chan API data, and a cronjob is
run periodically to update this cache. `/help` displays a list of other commands (when
implemented).

This app was made using the [Google App Engine Flask skeleton](https://github.com/GoogleCloudPlatform/appengine-python-flask-skeleton)

Dependencies should be installed in the `./lib` dir, i.e.:

    pip install -r requirements.txt -t <your_app_directory/lib>
