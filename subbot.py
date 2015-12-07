import praw, os
from prawoauth2 import PrawOAuth2Mini


class SubtitleBot(object):
    """
    usage:
    1. setup()
    """
    
    user_agent = 'Auto Closed Captioning Post:v0.1 (by /u/SubtitlePythonScript)'
    scopes = ['identity', 'read', 'edit', 'history', 'submit']
    request_limit = 10
    
    r = None
    oauth_helper = None
    
    
    def __init__(self):
        self.r = praw.Reddit(user_agent=self.user_agent)
        
        app_key = os.getenv('SUBTITLE_BOT_APP_KEY')
        app_secret = os.getenv('SUBTITLE_BOT_APP_SECRET')
        access_token = os.getenv('SUBTITLE_BOT_ACCESS_TOKEN')
        refresh_token = os.getenv('SUBTITLE_BOT_REFRESH_TOKEN')
        self.oauth_helper = PrawOAuth2Mini(self.r, app_key=app_key,
                              app_secret=app_secret, access_token=access_token,
                              scopes=self.scopes, refresh_token=refresh_token)

    def run_bot(self):
        self.oauth_helper.refresh()
        self.r_documentaries()
        
    def r_documentaries(self):
        subreddit = self.r.get_subreddit('documentaries')
        for submission in subreddit.get_hot(limit=self.request_limit):
            url = submission.url
            print url
            
    
    def r_science(self):
        pass
        

if __name__ == '__main__':
    bot = SubtitleBot()
    while True:
        try:
            bot.run_bot()
        except praw.errors.OAuthInvalidToken:
            bot.oauth_helper.refresh()
