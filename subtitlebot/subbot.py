import praw, os, sys, httplib2, urlparse

from prawoauth2 import PrawOAuth2Mini

from apiclient.discovery import build_from_document
from apiclient.errors import HttpError

from oauth2client.client import flow_from_clientsecrets
from oauth2client.file import Storage
from oauth2client.tools import run_flow

 
user_agent = 'Auto Closed Captioning Post:v0.1 (by /u/SubtitlePythonScript)'
scopes = ['identity', 'read', 'edit', 'history', 'submit']

CLIENT_SECRETS_FILE = "client_secrets.json"
YOUTUBE_READ_WRITE_SSL_SCOPE = "https://www.googleapis.com/auth/youtube.force-ssl"



class SubtitleBot(object):
    """
    usage:
    1. setup()
    """
    
    request_limit = 10
    
    r = praw.Reddit(user_agent=user_agent)
    
    r_oauth = None
    g_oauth = None
    old_id_set = None
    
    
    def __init__(self):
        temp_list = []
        with open('workfile', 'r') as f:
            for line in f:
                temp_list.append(line)
        self.old_id_set = set(temp_list)
        
        app_key = os.getenv('SUBTITLE_BOT_APP_KEY')
        app_secret = os.getenv('SUBTITLE_BOT_APP_SECRET')
        access_token = os.getenv('SUBTITLE_BOT_ACCESS_TOKEN')
        refresh_token = os.getenv('SUBTITLE_BOT_REFRESH_TOKEN')
        self.r_oauth = PrawOAuth2Mini(self.r, app_key=app_key,
                              app_secret=app_secret, access_token=access_token,
                              scopes=scopes, refresh_token=refresh_token)
        
        app_key = os.getenv('YOUTUBE_CLIENT_ID')
        app_secret = os.getenv('YOUTUBE_CLIENT_SECRET')
        
    
    def get_youtube_service(self, args):
        flow = flow_from_clientsecrets(CLIENT_SECRETS_FILE, scope=YOUTUBE_READ_WRITE_SSL_SCOPE,
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
        self.r_documentaries()
        
        
    def r_documentaries(self):
        subreddit = self.r.get_subreddit('documentaries')
        for submission in subreddit.get_hot(limit=self.request_limit):
            url = submission.url
            url_data = urlparse.urlparse(url)
            query = urlparse.parse_qs(url_data.query)
            video_id =  query["v"][0]
            try:
                with open("youtube-v3-api-captions.json", "r") as f:
                    doc = f.read()
                    
            except HttpError, e:
                print "An HTTP error %d occurred:\n%s" % (e.resp.status, e.content)

    
    def r_science(self):
        pass
        

if __name__ == '__main__':
    bot = SubtitleBot()
    while True:
        try:
            bot.run_bot()
        except praw.errors.OAuthInvalidToken:
            bot.r_oauth.refresh()
