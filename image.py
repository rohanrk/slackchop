import re
import requests

match_regex  = re.compile(r'!(gif|image)\s+(.+)')
search_regex = re.compile(r'\s+!(gif|image)\s*\(([^\)]+)\)')
video_regex  = re.compile(r'/watch\?v=[^"]+')

youtube_url = 'https://www.youtube.com'

def process_message(message, channel, user):
    match = re.match(r'!(gif|image)\s+(.+)', message)
    if match:
        t, q = match[1], match[2]
        #TODO: Normalize messages before passing them to modules
        q = re.sub(r'<[^\|]*\|([^>]+)>', r'\1', q)
        params = {'tbm':'isch', 'q':q, 'safe':''}
        if t == 'gif': params['tbs'] = 'itp:animated'
        response = requests.get(google_search_base,
            params=params, headers={"User-agent": fake_mobile_agent})
        links = re.findall(r'imgurl\\x3d([^\\]+)\\', response.text)
        send_message(channel=channel, text=random.choice(links),
            unfurl_links=True, unfurl_media=True)

def get_help_messages():
    return [('!youtube QUERY', 'return the first result for QUERY from Youtube')]