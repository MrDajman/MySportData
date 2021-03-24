import requests
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
import json
import os
import time
import polyline
import cv2
from operator import itemgetter
import numpy as np
from flask import Flask
#from flask_sqlalchemy import SQLAlchemy
import folium


app = Flask(__name__)
#app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///data.db'
#db = SQLAlchemy(app)

activites_url = "https://www.strava.com/api/v3/athlete/activities"


def startupCheck(tokens_path):
    if os.path.isfile(tokens_path) and os.access(tokens_path, os.R_OK):
        # checks if file exists
        print ("INFO:\tFile strava_tokens.json exists and is readable")
        return True
    else:
        print ("INFO:\tFile strava_tokens.json doesn't exist")
        return False

# Make Strava auth API call with your 
# client_code, client_secret and code
# https://www.strava.com/oauth/authorize?client_id=63388&response_type=code&redirect_uri=http://localhost/exchange_token&approval_prompt=force&scope=profile:read_all,activity:read_all
def first_auth(code):

    payload = {'client_id': "63388",
                'client_secret': 'cd53d9a8623c88f85fe7f59ca0c4e9a4e6c2ac5f',
                'code': code,
                'grant_type': 'authorization_code'
                }

    print("INFO:\tRequesting first tokens with authorization code")
    response = requests.post(url = 'https://www.strava.com/oauth/token',data = payload)
    #print(response.json())
    check_response(response)
    #Save json response as a variable
    strava_tokens = response.json()
    # Save tokens to file
    with open('strava_tokens.json', 'w') as outfile:
        json.dump(strava_tokens, outfile)
    # Open JSON file and print the file contents 
    # to check it's worked properly
    with open('strava_tokens.json') as check:
        data = json.load(check)
    #print(data)
    return strava_tokens


def refresh_auth(strava_tokens):
    # Make Strava auth API call with current refresh token
    print("INFO:\tTokens expired. Retreiving refreshed tokens")
    payload = {
                'client_id': "63388",
                'client_secret': 'cd53d9a8623c88f85fe7f59ca0c4e9a4e6c2ac5f',
                'grant_type': 'refresh_token',
                'refresh_token': strava_tokens['refresh_token']
                }
    response = requests.post(url = 'https://www.strava.com/oauth/token',data = payload)
    
    check_response(response)

    # Save response as json in new variable
    new_strava_tokens = response.json()
    # Save new tokens to file
    with open('strava_tokens.json', 'w') as outfile:
        json.dump(new_strava_tokens, outfile)
    # Use new Strava tokens from now
    strava_tokens = new_strava_tokens

    # Open the new JSON file and print the file contents 
    # to check it's worked properly
    with open('strava_tokens.json') as check:
        data = json.load(check)
    return(response.json()["access_token"])

def get_my_data(access_token):
    print("INFO:\tRetrieving athlete information")
    url = "https://www.strava.com/api/v3/athlete"
    r = requests.get(url, data = {"access_token":access_token})

    check_response(r)
    return r.json()

def get_my_activities(access_token,before = False, after = False, page = False, per_page = False):
    print("INFO:\tRetrieving athlete activities")
    url = "https://www.strava.com/api/v3/activities?"
    if per_page:
        url += "per_page={}?".format(per_page)
    r = requests.get(url, data = {"access_token":access_token})
    check_response(r)
    with open('my_activities.json', 'w') as outfile:
        json.dump(r.json(), outfile, sort_keys=True,)
    
    #print(len(r.json()))
    return r.json()

def check_response(response):
    if response.ok:
        print("INFO:\tSuccessfully retrieved request")
    else:
        errors = response.json()["errors"]
        print("INFO:\tRequest isn't retrieved succesfully. Nb of errors: {}. Exiting...".format(len(errors)))
        for error in errors:
            print("ERROR:\t{}: {}".format(error["resource"],error["code"]))
        exit()

#class Activity(db.Model):
class Activity():
    #constructor
    #id = db.Column(db.Integer, primary_key=True, unique = True)
    #activity_id = db.Column(db.String(80))
    #name = db.Column(db.String(80), unique = False, nullable = False)
    #polyline = 

    #def __repr__(self):
    #    return f"Activity {self.id} - {self.name}"

    def __init__(self, id):
        print("INFO:\tRetrieving activity ID: {}".format(id))
        url = "https://www.strava.com/api/v3/activities/{}?".format(id)
        r = requests.get(url, data = {"access_token":access_token})
        check_response(r)

        self.data = r.json()
        self.polyline = r.json()["map"]["polyline"]

    def get_polyline(self):
        return self.polyline

    def print_activity_map_cv(self, show = False):
        print("INFO:\tRetrieving activity ID: {}".format(id))
        activity_points = np.array(polyline.decode(self.polyline))
        activity_points = activity_points * 10**5
        activity_points = np.array(activity_points, dtype = int)
        
        #activity_points[:,1] = activity_points[:,1] * -1
        #activity_points[:,0] = activity_points[:,0] * -1
        #print (activity_points)
        activity_points[:,[0, 1]] = activity_points[:,[1, 0]]
        activity_points[:,1] = activity_points[:,1] * -1
        # X,Y notation
        max_Y_point = (max(activity_points,key=itemgetter(0)))
        max_X_point = (max(activity_points,key=itemgetter(1)))
        min_Y_point = (min(activity_points,key=itemgetter(0)))
        min_X_point = (min(activity_points,key=itemgetter(1)))

        #print(max_X_point, max_Y_point, min_X_point, min_Y_point)

        img_height = int((max_X_point[1] - min_X_point[1]))
        img_width = int((max_Y_point[0] - min_Y_point[0]))

        subtract_matrix_Y = np.zeros((activity_points.shape),dtype= int)
        subtract_matrix_Y[:,0] = 1

        subtract_matrix_X = np.zeros((activity_points.shape),dtype= int)
        subtract_matrix_X[:,1] = 1

        activity_points = activity_points - subtract_matrix_Y * min_Y_point[0] - subtract_matrix_X * min_X_point[1]

        print(img_height, img_width)

        map_image = np.zeros((img_height,img_width,3), np.uint8)

        cv2.drawContours(map_image, [activity_points], 0, (120,120,120),15)

        #print(map_image)

        cv2.imwrite("img.jpg", map_image) 
        if show:
            cv2.imshow("map", map_image)
            cv2.waitKey(0)
            cv2.destroyAllWindows()


def create_db():
    db.create_all()

def add_activity_db():
    activity = Activity(id = 12, name = "Activity 1")
    activity2 = Activity(id = 12, name = "Activity 2")
    print(activity)
    print(activity2)
    db.session.add(activity)
    db.session.add(activity2)
    db.session.commit()
    print(activity2)
    print(activity)


@app.route('/')
def index():
    start_coords = (48.855, 2.3433)
    #line = [(46.9540700, 142.7360300), (46.5940700, 142.3760300)]
    folium_map = folium.Map(location=start_coords, zoom_start=13)
    #for activity in activities:
    #    a = Activity(activity["id"])
    #    line = polyline.decode(a.get_polyline())
    #    folium.PolyLine(line).add_to(folium_map)
    #yield("BLABLABLA")
    return ("BLABLABLA\n\n\n")+folium_map._repr_html_()
    
if __name__ == "__main__":
    if startupCheck("strava_tokens.json"):
        with open('strava_tokens.json') as json_file:
            strava_tokens = json.load(json_file)
        access_token = strava_tokens["access_token"]
        if strava_tokens['expires_at'] < time.time():
            access_token = refresh_auth(strava_tokens)
        else:
            print("INFO:\tTokens are up to date. Next refresh in {} minutes".format(round((strava_tokens['expires_at'] - time.time())/60.0,2)))
        print("INFO:\tAccess token: {}".format(access_token))

        activities = get_my_activities(access_token,per_page=200)
        
        #print(len(activities))
        #exit()
        #a1 = Activity(activities[0]["id"])
        #a1.print_activity_map_cv()

        #db.drop_all(bind=None)
        #create_db()
        #add_activity_db()
        #Activity.query.all()

        app.run(debug=True)

        #one_activity = get_activity_by_id(activities[0]["id"])
        #print_activity_map(one_activity)

    else:
        # retrieve code from the link
        # https://www.strava.com/oauth/authorize?client_id=63388&response_type=code&redirect_uri=http://localhost/exchange_token&approval_prompt=force&scope=profile:read_all,activity:read_all
        code = '81152c10599d233cf7d92f050991dafbdbdb010b'
        first_auth(code)
