import json
import random
import re
import requests
from itertools import islice

import praw
from credentials import *
from datetime import datetime, timedelta
from flask import Flask, request, make_response, render_template
from slackclient import SlackClient

sc = SlackClient(oauth_token)
reddit = praw.Reddit(client_id=reddit_client_id, 
    client_secret=reddit_client_secret,
    user_agent='Slackchop')

# this is an infinite random bit generator. shitty but it works
randbits = iter(lambda: random.getrandbits(1), 2)
def randstream(i):
    return iter(lambda: random.randrange(i), i)

# currently can't get this from an online list because slack doesn't return
# a list of default emoji they support and provide no way of checking if they
# support a particular emoji either
default_emojis = open('emoji_names.txt').read().splitlines()
custom_emojis = []
emojis = []
last_update = datetime.min
update_frequency = timedelta(0, 3600) # update every hour
youtube_url = 'https://www.youtube.com'
youtube_vid_regex = '/watch\?v=[^"]+'
google_search_base = 'https://www.google.com/search'
fake_mobile_agent = '''Mozilla/5.0 (iPhone; U; CPU iPhone OS 4_0 like Mac OS X;
 en-us) AppleWebKit/532.9 (KHTML, like Gecko) Versio  n/4.0.5 Mobile/8A293 Safa
ri/6531.22.7'''

application = Flask(__name__)

def update_emoji_list():
    now = datetime.now()
    global last_update, custom_emojis, default_emojis, emojis
    if now - last_update < update_frequency: return
    custom_emojis = list(sc.api_call('emoji.list')['emoji'].keys())
    emojis = custom_emojis + default_emojis
    last_update = now

update_emoji_list()

def send_message(*args, **kwargs):
    sc.api_call('chat.postMessage', *args, **kwargs)

def handle_message(slack_event, message):
    channel = slack_event['event']['channel']
    match = re.match(r'!youtube\s+(.+)', message)
    if match:
        res = requests.get(youtube_url + '/results',
            params={'search_query':match[1]})
        vids = re.findall(youtube_vid_regex, res.text)
        send_message(channel=channel, text=youtube_url+vids[0])
        return

    match = re.match(r'!(gif|image)\s+(.+)', message)
    if match:
        t, q = match[1], match[2]
        params = {'tbm':'isch', 'q':q, 'safe':''}
        if t == 'gif': params['tbs'] = 'itp:animated'
        response = requests.get(google_search_base,
            params=params, headers={"User-agent": fake_mobile_agent})
        links = re.findall(r'imgurl\\x3d([^\\]+)\\', response.text)
        send_message(channel=channel, text=random.choice(links),
            unfurl_links=True, unfurl_media=True)

    match = re.match(r'!roll\s+(\d*|an?)\s*[dD]\s*(\d+)', message)
    if match:
        n, d = match[1], match[2]
        n = 1 if 'a' in n else int(n)
        d = int(d)
        reply = ', '.join([str(random.randrange(d)+1) for i in range(n)])
        send_message(channel=channel, text=reply);
        return
    if message.rstrip() == '!flip':
        reply = 'heads' if random.getrandbits(1) else 'tails'
        send_message(channel=channel, text=reply);
        return
    match = re.match(r'!(?:shuffle|flip)\s+(.+)', message)
    if match:
        items = list(map(lambda x:x.strip(), match[1].split(',')))
        random.shuffle(items)
        reply = ', '.join(items)
        send_message(channel=channel, text=reply);
        return

    update_emoji_list()

    match = re.match(r'!emoji\s+(\d+)\s*', message)
    if match:
        num = int(match[1])
        if num == 0: return
        reply = ':{}:'.format('::'.join(random.choices(emojis, k=num)))
        send_message(channel=channel, text=reply)
        return
    match = re.match(r'!emoji\s+(:[^:]+:)(?:[\*xX\s])?(\d+)', message)
    if match and int(match[2]) > 0 and match[1][1:-1] in emojis:
        send_message(channel=channel, text=match[1]*int(match[2]))
        return
    match = re.match(r'!emoji\s+(\S+)\s*', message)
    if match:
        es = [x for x in emojis if re.search(match[1], x)][:350]
        if len(es) == 0: return
        reply = ':{}:'.format('::'.join(es))
        send_message(channel=channel, text=reply)
        return

    if message.startswith('!emojify'):
        words = message.split(' ')[1:]
        pattern = ':{}:'
        if words[0].startswith('`') and words[0].endswith('`'):
            pattern = words[0][1:-1]
            words = words[1:]
        if len(words) == 1:
            words = words[0]
        ems = list(map(lambda x: pattern.format(x), words))
        send_message(channel=channel, text=''.join(ems))
        return

    take = lambda x: not x.stickied and not x.is_self
    match = re.match(r'!randfeld\s+(.*)', message)
    if match:
        sub = choose(filter(take,
            reddit.subreddit('seinfeldgifs').search(match[1]+' self:no')), 50)
        send_message(channel=channel, text=sub.url,
            unfurl_links=True, unfurl_media=True, icon_emoji=':jerry:')
        return
    if message.startswith('!randfeld'):
        sub = choose(filter(take,
            reddit.subreddit('seinfeldgifs').hot(limit=50)))
        send_message(channel=channel, text=sub.url,
            unfurl_links=True, unfurl_media=True, icon_emoji=':jerry:')
        return

    if message.startswith('!gridtext '):
        text = message.split(' ', 1)[1]
        if len(text) > 80: text = text[:80]
        res = []
        n = len(text)
        for i in range(n):
            res.append(' '.join(text))
            text = text[-1] + text[:-1]
        reply = '```{}```'.format('\n'.join(res))
        send_message(channel=channel, text=reply)
        return

def choose(seq, limit=None):
    if limit: seq = islice(seq, limit)
    ret = None
    for item, take in zip(seq, randstream(5)):
        if not ret: ret = item
        if not take: return item
    return ret

def event_handler(event_type, slack_event):
    if event_type == 'reaction_added':
        user_id = slack_event['event']['user']
    elif event_type == 'message' and 'text' in slack_event['event']:
        text = slack_event['event']['text']
        handle_message(slack_event, text)
    return make_response("Ok", 200, )

@application.route("/events", methods=["GET", "POST"])
def hears():
    slack_event = json.loads(request.data)
    if "challenge" in slack_event:
        return make_response(slack_event["challenge"],
            200, {"content_type": "application/json"})
    if "event" in slack_event:
        event_type = slack_event["event"]["type"]
        return event_handler(event_type, slack_event)
    return make_response("Ok", 200,)

@application.route("/begin_auth", methods=["GET"])
def pre_install():
    return '''
      <a href="https://slack.com/oauth/authorize?scope={0}&client_id={1}">
          Add to Slack
      </a>
    '''.format(oauth_scope, client_id)

@application.route("/finish_auth", methods=["GET", "POST"])
def post_install():
    auth_code = request.args['code']
    sc = SlackClient("")
    auth_response = sc.api_call(
        "oauth.access",
        client_id=client_id,
        client_secret=client_secret,
        code=auth_code
    )
    user_token = auth_response['access_token']
    bot_token = auth_response['bot']['bot_access_token']
    return "Auth complete"

@application.route("/")
def go_away():
    return 'Go Away'

if __name__ == '__main__':
    application.run(debug=True)
