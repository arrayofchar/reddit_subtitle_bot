import praw, os, sys, httplib2, urlparse, urllib2, re

from Pastebin import PastebinAPI
pastebin_api = PastebinAPI()

import xml.etree.ElementTree as ET
from prawoauth2 import PrawOAuth2Mini

from apiclient.discovery import build_from_document

from oauth2client.client import flow_from_clientsecrets
from oauth2client.file import Storage
from oauth2client.tools import argparser, run_flow

 
user_agent = 'Auto Closed Captioning Post:v0.1 (by /u/SubtitlePythonScript)'
scopes = ['identity', 'read', 'edit', 'history', 'submit']

CLIENT_SECRETS_FILE = 'client_secrets.json'
YOUTUBE_PARTNER_SCOPE = 'https://www.googleapis.com/auth/youtubepartner'

YOUTUBE_URL = 'https://www.youtube.com/api/timedtext?v=%s&lang=en'

BATCH_SIZE = 50
CHAR_LIMIT = 10000

HEADER = 'Hey, looks like there is closed captioning in this video. Let me get that for ya.\n\n'

subreddits = ['educativevideos', ] #'educativevideos', 'lectures', 'science', 'documentaries'

args = argparser.parse_args()


def convert_to_seconds(duration):
    match = re.match('(\d+H)?(\d+M)?(\d+S)?', duration).groups()
    hours = _js_parseInt(match[0]) if match[0] else 0
    minutes = _js_parseInt(match[1]) if match[1] else 0
    seconds = _js_parseInt(match[2]) if match[2] else 0
    return hours * 3600 + minutes * 60 + seconds

def _js_parseInt(string):
    return int(''.join([x for x in string if x.isdigit()]))



class SubtitleBot(object):
        
    request_limit = 10
    
    r = praw.Reddit(user_agent=user_agent)
    youtube = None
    
    r_oauth = None
    g_oauth = None
    pastebin_key = None
    old_id_set = set()
    
    
    def __init__(self):
        temp_list = []
        with open('subbot.db', 'r') as f:
            for line in f:
                self.old_id_set.add(line.strip())
        
        app_key = os.getenv('SUBTITLE_BOT_APP_KEY')
        app_secret = os.getenv('SUBTITLE_BOT_APP_SECRET')
        access_token = os.getenv('SUBTITLE_BOT_ACCESS_TOKEN')
        refresh_token = os.getenv('SUBTITLE_BOT_REFRESH_TOKEN')
        self.r_oauth = PrawOAuth2Mini(self.r, app_key=app_key,
                              app_secret=app_secret, access_token=access_token,
                              scopes=scopes, refresh_token=refresh_token)
        
        self.pastebin_key = os.getenv('PASTEBIN_API_KEY')
#         pastebin_username = os.getenv('PASTEBIN_USERNAME')
#         pastebin_password = os.getenv('PASTEBIN_PASSWORD')
#         self.pastebin_key = pastebin_api.generate_user_key(pastebin_api_key,
#                                                          pastebin_username,
#                                                          pastebin_password)
        
        self.youtube = self.get_youtube_service()
    
    
    def get_youtube_service(self):
        flow = flow_from_clientsecrets(CLIENT_SECRETS_FILE, scope=YOUTUBE_PARTNER_SCOPE,
        message='need client_secrets.json')
    
        storage = Storage("%s-oauth2.json" % sys.argv[0])
        credentials = storage.get()
    
        if credentials is None or credentials.invalid:
            credentials = run_flow(flow, storage, args)
    
        with open("youtube-v3-api-captions.json", "r") as f:
            doc = f.read()
            return build_from_document(doc, http=credentials.authorize(httplib2.Http()))


    def run_bot(self):
        self.r_oauth.refresh()
        self.run_subreddit()
        
        
    def youtube_transcriber(self, video_id, start_point=None):
        url = YOUTUBE_URL % (video_id)
        response = urllib2.urlopen(url)
        data = response.read()
        
        if data:
            root = ET.fromstring(data)
            time_diffs = []
            texts = []
            sum_squared = 0
            
            prev_start = 0
            for child in root:
                cur_start = float(child.attrib['start'])
                if cur_start >= start_point:
                    if prev_start is not 0:
                        diff = cur_start - prev_start
                        time_diffs.append(diff)
                        sum_squared += diff ** (2)
                    prev_start = cur_start
                    
                    tmp_str = child.text.replace('\n', ' ')
                    tmp_str = tmp_str.replace('&#39;', "'")
                    tmp_str = tmp_str.replace('&quot;', '"')
                    texts.append(tmp_str)
                    
            sigma = (sum_squared / len(time_diffs)) ** (0.5)
            
            # construct subtitle paragraphs
            
            final_text = texts[0]
            for i, time_diff in enumerate(time_diffs):
                if time_diff < (sigma*1.3):
                    final_text += ' '+texts[i+1]
                else:
                    final_text += '\n\n'+texts[i+1]
                    
            return final_text
        
        
    def run_subreddit(self):
        # get batch_size amount of videos
        batch, submissions = self.get_videos()
        print batch
        
        self.r.login(disable_warning=True)
        
        for i, query in enumerate(batch):
            if 'v' in query:
                video_id = query['v'][0]
                if 't' in query:
                    start_point = query['t'][0]
                    total_sec = convert_to_seconds(start_point.upper())
                    subtitle = self.youtube_transcriber(video_id, total_sec)
                else:
                    subtitle = self.youtube_transcriber(video_id)
                
                if subtitle:
                    final_text = HEADER+subtitle
                    submission = submissions[i]
                    if len(final_text) < CHAR_LIMIT:
                        # post comment as is
                        submission.add_comment(final_text)
                    else:
                        # post comment in pastebin
                        pastebin_url = pastebin_api.paste(self.pastebin_key, subtitle.encode('utf8'),
                                                         paste_name=submission.id, paste_private='public')
                        pastebin_message = '[Here is the Pastebin link to the closed captioned text](%s)' % (pastebin_url)
                        submission.add_comment(HEADER+pastebin_message)
                    print len(final_text)
                    self.old_id_set.add(submission.id)
                    with open('subbot.db', 'a') as f:
                        f.write(submission.id)
                        f.write('\n')
                    
            
    def get_videos(self):
        batch = []
        submissions = []
        for subreddit_name in subreddits:
            subreddit = self.r.get_subreddit(subreddit_name)
            for submission in subreddit.get_hot(limit=self.request_limit):
                url = submission.url
                if submission.id not in self.old_id_set and 'youtube.com' in url:
                    url_data = urlparse.urlparse(url)
                    query = urlparse.parse_qs(url_data.query)
                    batch.append(query)
                    submissions.append(submission)
                    if len(batch) >= BATCH_SIZE:
                        return batch, submissions
        return batch, submissions
                    

    @DeprecationWarning
    def helloworldyoutube(self):
        video_id = 'JhHMJCUmq28'
        results = self.youtube.captions().list(part="snippet", videoId=video_id).execute()
        # find english subtitle
        en_id = None
        for item in results["items"]:
            print item
            tmp_id = item["id"]
            language = item["snippet"]["language"]
            if language == 'en':
                en_id = tmp_id
                break
        # get english subtitle
         
        # well apparently you can't use captions().download to get subtitle
        subtitle = self.youtube.captions().download(id=en_id, tfmt='srt').execute()        


if __name__ == '__main__':
    bot = SubtitleBot()
    
    bot.run_bot()
    
    while False:
        try:
            bot.run_bot()
        except praw.errors.OAuthInvalidToken:
            bot.r_oauth.refresh()



