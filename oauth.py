import json
import requests
from rauth import OAuth2Service
from flask import current_app, url_for, request, redirect, session


class OAuthSignIn(object):
    providers = None

    def __init__(self, provider_name):
        self.provider_name = provider_name
        credentials = current_app.config['OAUTH_CREDENTIALS'][provider_name]
        self.consumer_id = credentials['id']
        self.consumer_secret = credentials['secret']

    def authorize(self):
        pass

    def callback(self):
        pass

    def get_callback_url(self):
        return url_for('oauth_callback', provider=self.provider_name,
                       _external=True)

    @classmethod
    def get_provider(self, provider_name):
        if self.providers is None:
            self.providers = {}
            for provider_class in self.__subclasses__():
                provider = provider_class()
                self.providers[provider.provider_name] = provider
        return self.providers[provider_name]


class StravaSignIn(OAuthSignIn):
    def __init__(self):
        super(StravaSignIn, self).__init__('strava')
        self.service = OAuth2Service(
            name='strava',
            client_id=self.consumer_id,
            client_secret=self.consumer_secret,
            authorize_url="https://www.strava.com/oauth/authorize",
            base_url="https://www.strava.com/api/v3/",
            access_token_url='https://www.strava.com/oauth/token'
        )

    def authorize(self):
        return redirect(self.service.get_authorize_url(
            scope='profile:read_all,activity:read_all',
            response_type='code',
            #redirect_uri=http://localhost/exchange_token
            approval_prompt = 'force',
            redirect_uri=self.get_callback_url())
        )

    def callback(self):
        def decode_json(payload):
            return json.loads(payload.decode('utf-8'))

        if 'code' not in request.args:
            return None, None, None
        print(request.args)
        
        payload = {'client_id': "63388",
                'client_secret': 'cd53d9a8623c88f85fe7f59ca0c4e9a4e6c2ac5f',
                'code': request.args['code'],
                'grant_type': 'authorization_code'
                }

        response = requests.post(url = 'https://www.strava.com/oauth/token',data = payload)
        print(response.json())
        #check_response(response)
        #Save json response as a variable
        strava_tokens = response.json()

        '''
        oauth_session = self.service.get_auth_session(
            data={
                  'client_id': "63388",
                  'client_secret': 'cd53d9a8623c88f85fe7f59ca0c4e9a4e6c2ac5f',
                  'code': request.args['code'],
                  'grant_type': 'authorization_code',
                  'redirect_uri': self.get_callback_url()},
            decoder=decode_json
        )
        me = oauth_session.get("").json()
        print("ME:",me)
        '''
        return (
            'strava$'
            + str(strava_tokens["athlete"]["id"]),
            strava_tokens["athlete"]["username"],
            strava_tokens["athlete"]["firstname"],
            strava_tokens["athlete"]["lastname"],
            strava_tokens["refresh_token"],
            strava_tokens["access_token"],
            strava_tokens['expires_at']
        )

'''
 + me['id'],
            me.get('email').split('@')[0],  # Facebook does not provide
                                            # username, so the email's user
                                            # is used instead
            me.get('email')
            '''