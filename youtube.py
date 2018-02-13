import re
import requests

match_regex  = re.compile(r'!youtube\s+(.+)')
search_regex = re.compile(r'\s+!youtube\s*\(([^\)]+)\)')
video_regex  = re.compile(r'/watch\?v=[^"]+')

youtube_url = 'https://www.youtube.com'

def process_message(message, channel, user, full_event):
    match = match_regex.match(message) or search_regex.search(message)
    if not match: return

    result = requests.get(youtube_url + '/results', params={'search_query':match[1]})
    videos = video_regex.findall(result.text)
    return {'text': youtube_url + videos[0]}

def get_help_messages():
    return [('!youtube QUERY', 'return the first result for QUERY from Youtube')]