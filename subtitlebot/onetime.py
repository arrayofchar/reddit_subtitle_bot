import praw, os
from prawoauth2 import PrawOAuth2Server


app_key = os.getenv('SUBTITLE_BOT_APP_KEY')
app_secret = os.getenv('SUBTITLE_BOT_APP_SECRET')

user_agent = 'Auto Closed Captioning Post:v0.1 (by /u/SubtitlePythonScript)'
scopes = ['identity', 'read', 'edit', 'history', 'submit']

reddit_client = praw.Reddit(user_agent=user_agent)
oauthserver = PrawOAuth2Server(reddit_client, app_key=app_key,
                               app_secret=app_secret, state=user_agent,
                               scopes=scopes)

# start the server, this will open default web browser
# asking you to authenticate
oauthserver.start()
tokens = oauthserver.get_access_codes()
print(tokens)
