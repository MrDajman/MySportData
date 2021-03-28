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
from flask import Flask, render_template, request
#from flask_sqlalchemy import SQLAlchemy
import folium
from folium import plugins


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
    if page:
        url += "page={}&".format(page)
    if per_page:
        url += "per_page={}&".format(per_page)
    url = url[:-1]
    print(url)
    r = requests.get(url, data = {"access_token":access_token})
    if check_response(r) == False:
        return 0
    
    with open('my_activities.json', 'w') as outfile:
        json.dump(r.json(), outfile, sort_keys=True,)
    
    #print(len(r.json()))
    return r.json()

def check_response(response):
    if response.ok:
        print("INFO:\tSuccessfully retrieved request")
        return True
    else:
        errors = response.json()["errors"]
        print("INFO:\tRequest isn't retrieved succesfully. Nb of errors: {}.".format(len(errors)))
        for error in errors:
            print("ERROR:\t{}: {}".format(error["resource"],error["code"]))
            if error["resource"] == "Application" and error["code"] == "exceeded":
                print("ERROR:\tWait 15 minutes for the query limit to renew")
            return False

        #exit() 

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
        self.id = r.json()["id"]
        self.name = r.json()["name"]
        self.distance = r.json()["distance"]
        self.type = r.json()["type"]
        self.start_date_local = r.json()["start_date_local"]

    def get_activity_id(self):
        return self.id

    def get_activity_dict(self):
        act_dict = {
            self.id: 
            {
                "id": self.id,
                "name": self.name,
                "distance": self.distance,
                "type": self.type,
                "start_date_local": self.start_date_local,
                "polyline": self.polyline
            }
        }
        return act_dict

    def get_polyline(self):
        return (self.polyline)

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


def update_activities_json():
    page = 1
    count_old = 0
    count_new = 0
    while(1):
        activities_list = get_my_activities(access_token,per_page=200, page = page)
        if len(activities_list) == 0:
            break
        if activities_list == 0:
            return 0


        for activity in activities_list:
            with open('activities.json', "r+") as json_file:
                data = json.load(json_file)
                if str(activity["id"]) not in data:
                    a = Activity(activity["id"])
                    data[activity["id"]]=a.get_activity_dict()[activity["id"]]

                    json_file.seek(0)
                    json.dump(data, json_file, indent=4)
                    count_new += 1
                else:
                    print("INFO:\tAvtivity {} is already in the database".format(activity["id"]))
                    count_old += 1
        page += 1
    return count_new, count_old

def create_db():
    db.create_all()

@app.route('/activities_on_map/')
def activities_on_map():
    start_coords = (48.855, 2.3433)
    folium_map = folium.Map(location=start_coords, zoom_start=13, tiles='cartodbpositron')
    
    run_map = folium.FeatureGroup("Runs").add_to(folium_map)
    ride_map = folium.FeatureGroup("Bike rides").add_to(folium_map)
    
    with open('activities.json', "r") as json_file:
        data = json.load(json_file)
        print(len(data))
    for activity_id in data:
        if data[activity_id]["polyline"] == None:
            continue
        line = polyline.decode(data[activity_id]["polyline"])
        if len(line) == 0:
            continue
        if data[activity_id]["type"] in ["Run","Walk"]:
            popup_text = "Distance: {}\n Date: {}".format(data[activity_id]["distance"], data[activity_id]["start_date_local"])
            folium.PolyLine(line, color = "#FF0000", opacity = 0.3, control = False, popup = popup_text).add_to(run_map)
            #run_polylines.add_to(run_map).add_to(folium_map)
            #run_polylines.layer_name = "Runs"
            
            pass
        elif data[activity_id]["type"] in ["Ride"]:
            folium.PolyLine(line, color = "#0000FF", opacity = 0.3, control = False).add_to(ride_map)
            pass
        #folium.ColorLine(line,(255,255,0)).add_to(folium_map)

    folium.LayerControl(collapsed=False).add_to(folium_map)
    return folium_map._repr_html_()

@app.route('/', methods=['GET', 'POST'])
def index():
    print (request.method)
    if request.method == "POST":
        update_activities_json()
    #if request.method == "GET":
    with open('activities.json', "r+") as json_file:
        data = json.load(json_file)
    activity_nb = len(data)
    return render_template('index.html',activity_nb = activity_nb)
    
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

        app.run(debug=True)

    else:
        # retrieve code from the link
        # https://www.strava.com/oauth/authorize?client_id=63388&response_type=code&redirect_uri=http://localhost/exchange_token&approval_prompt=force&scope=profile:read_all,activity:read_all
        code = '81152c10599d233cf7d92f050991dafbdbdb010b'
        first_auth(code)
