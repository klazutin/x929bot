#!/usr/bin/env python3

import requests, json, random, datetime
from functools import lru_cache
from collections import OrderedDict
import config

cat_facts = ['Cats user their tails for balance and have nearly 30 individual bones in them!',
             'In ancient Egypt killing a cat was a crime punishable by death.',
             'Did you know that the first cat show was held in 1871 at the Crystal Palace in London?',
             'Did you know there are about 100 distinct breeds of domestic cat?',
             'Cats bury their feces to cover their trails from predators.',
             'Did you know that the Pilgrims were the first to introduce cats to North America?',
             'Some notable people who disliked cats include Napoleon Bonaparte, Dwight D. Eisenhower, and Hitler!',
             'Did you know that it has been scientifically proven that stroking a cat can lower a person\'s blood pressure?',
             'Did you know that when cats piss or vomit on your shoes it\'s a sign of undying devotion?',
             'Did you know that cats were domesticated from the African wildcat 10,000 years ago?',
             'Did you know that the first true cats came into existence about 12 million years ago and were the Proailurus?',
             'Did you know that a domestic cat can sprint at about 31 miles per hour?',
             'What is a cat\'s favorite color? It\'s purrrple.'
            ]

class Bot():
    """
    Main bot class for all interactions with the Telegram API.
    """

    telegram_url = config.telegram_url
    telegram_token = config.telegram_token
    offset = 0

    def prepare_time(self):
        now = datetime.datetime.now()
        delta = datetime.timedelta(minutes=30)
        start = now - delta
        start = start.isoformat().split('.')[0]
        start = start.replace('T', '+')
        start = start.replace(':', '%3A')
        end = now + delta
        end = end.isoformat().split('.')[0]
        end = end.replace('T', '+')
        end = end.replace(':', '%3A')
        return start, end

    def send_request(self, method, **kwargs):
        req = Bot.telegram_url+Bot.telegram_token+"/"+method
        result = requests.get(req, params=kwargs)
        return result

    def process_message(self, message):
        chat_id = message['chat']['id']
        text = message['text']
        if text == '/start':
            self.send_request('sendMessage', chat_id=chat_id, text='Welcome to the X92.9 song bot!', reply_markup='{"keyboard": [["🐱","🎵","🎶"]],"one_time_keyboard": false,"resize_keyboard": true}')
        elif text == '/help':
            self.send_request('sendMessage', chat_id=chat_id, text='Use keyboard buttons to get recently played songs or a random cat fact.', reply_markup='{"keyboard": [["🐱","🎵","🎶"]],"one_time_keyboard": false,"resize_keyboard": true}')
        elif text == '🐱' or text == '/cat' or text == 'cat':
            self.send_cat_fact(chat_id)
        elif text == '🎵' or text == '/song' or text == 'song':
            self.send_song(chat_id, 1)
        elif text == '🎶' or text == '/songs' or text == 'songs':
            self.send_song(chat_id, 5)
        else:
            self.send_request('sendMessage', chat_id=chat_id, text='Invalid request, sorry mate!')

    def process_callback(self, callback):
        query_id = callback['id']
        chat_id = callback['message']['chat']['id']
        artist, title = callback['data'].split(' ### ')
        try:
            pleer = Pleer()
            _, _, url = pleer.get_song_download_url(artist, title)
            self.send_request('answerCallbackQuery', callback_query_id=query_id)
            self.send_request('sendAudio', chat_id=chat_id, audio=url)
        except:
            self.send_request('answerCallbackQuery', callback_query_id=query_id)
            self.send_request('sendMessage', chat_id=chat_id, text='Sorry, song not found: %s - %s' % (artist, title))

    def send_cat_fact(self, user):
        cat_fact = random.choice(cat_facts)
        self.send_request('sendMessage', chat_id=user, text=cat_fact)

    def send_song(self, user, num_songs):
        start, end = self.prepare_time()
        req = 'http://cfexfm.s.widget.ldrhub.com/api/?start_date=%s&end_date=%s&key=cfexfm&method=now_playing_range' % (start, end)
        try:
            request = requests.get(req)
            re = json.loads(request.text)['now_playing_range']
        except:
            result = 'Something went wrong connecting to the radio API.'
        i = 0
        while i <= num_songs-1:
            try:
                r = re[i]
                timestamp = r['timestamp'].split(' ')[1][:-3]
                result = '%s: <b>%s</b> - %s' % (timestamp, r['artist'], r['title'])
                song = '%s ### %s' % (r['artist'], r['title'])
                self.send_request('sendMessage', parse_mode='HTML', chat_id=user, text=result, reply_markup='{"inline_keyboard": [[{"text": "Download", "callback_data": "' + song + '"}]]}')
            except IndexError:
                pass
            i += 1

    def get_updates(self):
        result = self.send_request('getUpdates?timeout=100', offset=Bot.offset+1).json()
        if result['ok']:
            for res in result['result']:
                Bot.offset = res['update_id']
                if 'message' in res and 'text' in res['message']:
                    self.process_message(res['message'])
                elif 'callback_query' in res:
                    self.process_callback(res['callback_query'])
                else:
                    print('Don\'t know how to handle message ', res)
                    break

    def update_loop(self):
        print('Bot update loop started')
        while True:
            self.get_updates()


class Pleer():
    """
    Class for interaction with the www.pleer.net api.
    """

    pleer_app_id = config.pleer_app_id
    pleer_app_key = config.pleer_app_key
    pleer_auth_token = ""
    pleer_auth_token_expires = ""

    @classmethod
    def _get_pleer_token(cls):
        if not Pleer.pleer_auth_token or datetime.datetime.now() > Pleer.pleer_auth_token_expires:
            try:
                payload = {'grant_type': 'client_credentials'}
                req = requests.post('http://api.pleer.com/token.php', auth=(Pleer.pleer_app_id, Pleer.pleer_app_key), data=payload)
                req_text = json.loads(req.text)
                Pleer.pleer_auth_token = req_text['access_token']
                Pleer.pleer_auth_token_expires = datetime.datetime.now() + datetime.timedelta(minutes=50)
            except:
                print('Something went wrong getting a Pleer API token')
                return None
        return Pleer.pleer_auth_token

    @lru_cache(maxsize=128, typed=False)
    def get_song_download_url(self, artist, title):
        auth_token = Pleer._get_pleer_token()
        try:
            payload = {'access_token': auth_token,
                       'method': 'tracks_search',
                       'query': artist + ' - ' + title}
            req = requests.post('http://api.pleer.com/index.php', data=payload)
            req_text = json.loads(req.text, object_pairs_hook=OrderedDict)  # force OrderedDict to ensure the order of tracks remains the same
            if not req_text['success'] or 'tracks' not in req_text: return None
            tracks = req_text['tracks']
            track = list(tracks.values())[0]
            track_id = track['id']
            track_artist = track['artist']
            track_title = track['track']
        except:
            print('Something went wrong searching the track %s on Pleer' % artist + ' - ' + title)
            return None
        try:
            payload = {'access_token': auth_token,
                       'method': 'tracks_get_download_link',
                       'track_id': track_id}
            req = requests.post('http://api.pleer.com/index.php', data=payload)
            req_text = json.loads(req.text)
            if not req_text['success'] or 'url' not in req_text: return None
            track_url = req_text['url']
        except:
            print('Something went wrong getting the download URL for %s from Pleer' % track_id)
            return None
        return track_artist, track_title, track_url


if __name__ == '__main__':
    bot = Bot()
    bot.update_loop()
