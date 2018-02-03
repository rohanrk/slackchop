import json
import random
import re
import requests

from credentials import client_id, client_secret, oauth_token, oauth_scope
from datetime import datetime, timedelta
from flask import Flask, request, make_response, render_template
from slackclient import SlackClient

sc = SlackClient(oauth_token)

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
        res = requests.get(youtube_url + '/results', params={'search_query':match[1]})
        vids = re.findall(youtube_vid_regex, res.text)
        send_message(channel=channel, text=youtube_url+vids[0])
        return

    update_emoji_list()

    match = re.match(r'!randmoji\s+(\d+)\s*', message)
    if match:
        num = int(match[1])
        if num == 0: return
        reply = ':{}:'.format('::'.join(random.choices(emojis, k=num)))
        send_message(channel=channel, text=reply)
        return
    match = re.match(r'!randmoji\s+(:[^:]+:)(?:[\*xX\s])?(\d+)', message)
    if match and int(match[2]) > 0 and match[1][1:-1] in emojis:
        send_message(channel=channel, text=match[1]*int(match[2]))
        return
    match = re.match(r'!randmoji\s+(\S+)\s*', message)
    if match:
        es = [x for x in emojis if re.search(match[1], x)][:350]
        if len(es) == 0: return
        reply = ':{}:'.format('::'.join(es))
        send_message(channel=channel, text=reply)
        return

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
        return make_response(slack_event["challenge"], 200, {"content_type": "application/json"})
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