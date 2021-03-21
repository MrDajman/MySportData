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

def print_activity_map(activity):
    activity = activity
    activity_map = activity["map"]
    activity_points = np.array(polyline.decode(activity_map["polyline"]))
    activity_points = activity_points * 10**6
    activity_points = np.array(activity_points, dtype = int)
    #activity_points[:,1] = activity_points[:,1] * -1
    #activity_points[:,0] = activity_points[:,0] * -1
    #print (activity_points)
    activity_points[:,[0, 1]] = activity_points[:,[1, 0]]
    activity_points[:,1] = activity_points[:,1] * -1
    # Y, X notation
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

    #print(activity_points)

    map_image = np.zeros((img_height,img_width,3), np.uint8)

    #activity_points 

    #activity_points = [tuple(pair) for pair in activity_points]
    #print(activity_points)

    cv2.drawContours(map_image, [activity_points], 0, (120,120,120),5 )
    cv2.imwrite("img.jpg", map_image) 
    #cv2.imshow("map", map_image)
    #cv2.waitKey(0)
    #cv2.destroyAllWindows()

    #print(img_height, img_width)



def check_response(response):
    if response.ok:
        print("INFO:\tSuccessfully retrieved request")
    else:
        errors = response.json()["errors"]
        print("INFO:\tRequest isn't retrieved succesfully. Nb of errors: {}. Exiting...".format(len(errors)))
        for error in errors:
            print("ERROR:\t{}: {}".format(error["resource"],error["code"]))
        exit()


def get_activity_by_id(id):
    print("INFO:\tRetrieving activity ID: {}".format(id))
    url = "https://www.strava.com/api/v3/activities/{}?".format(id)
    r = requests.get(url, data = {"access_token":access_token})
    check_response(r)
    #with open('my_activities.json', 'w') as outfile:
    #    json.dump(r.json(), outfile, sort_keys=True,)
    
    #print(len(r.json()))
    return r.json()

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

        activities = get_my_activities(access_token,per_page=10)
        #print(activities[0]["id"])
        one_activity = get_activity_by_id(activities[0]["id"])
        #print(one_activity)
        print_activity_map(one_activity)

    else:
        # retrieve code from the link
        # https://www.strava.com/oauth/authorize?client_id=63388&response_type=code&redirect_uri=http://localhost/exchange_token&approval_prompt=force&scope=profile:read_all,activity:read_all
        code = '81152c10599d233cf7d92f050991dafbdbdb010b'
        first_auth(code)

    




exit()




'''
Run this fuction to receive access token
https://www.strava.com/oauth/authorize?client_id=63388&response_type=code&redirect_uri=http://localhost/exchange_token&approval_prompt=force&scope=profile:read_all,activity:read_all

def request_token(access_token):
    auth_url = "https://www.strava.com/oauth/token"

    payload = {
        'client_id': "63388",
        'client_secret': 'cd53d9a8623c88f85fe7f59ca0c4e9a4e6c2ac5f',
        'code': '9c13046e3a9cfaaf30f9580b79f239f26bdf1038',
        'grant_type': "authorization_code"
    }


                        url = 'https://www.strava.com/oauth/token',
                        data = {
                                'client_id': [INSERT_CLIENT_ID_HERE],
                                'client_secret': '[INSERT_CLIENT_SECRET_KEY]',
                                'grant_type': 'refresh_token',
                                'refresh_token': strava_tokens['refresh_token']
                                }

    print("Requesting Token...\n")
    res = requests.post(auth_url, data=payload, verify=False)
    print(res)
    print(res.json())
    print(res.ok)
    if res.ok:
        print("Successfully requested ")
    else:
        return 0
    print(res.json())
    access_token = res.json()['access_token']
    print("Access Token = {}\n".format(access_token))
    return res.json()

access_token = 0 
access_token_res = request_token(access_token)
access_token= access_token_res["access_token"]
header = {'Authorization': 'Bearer ' + access_token}
param = {'per_page': 200, 'page': 1}
#my_dataset = requests.get(activites_url, headers=header, params=param).json()
#print(my_dataset[0]["name"])
#print(my_dataset[0]["map"]["summary_polyline"])


end_url = "https://www.strava.com/api/v3/activities/4949939963"
my_data = requests.get(end_url, headers=header, params=param).json()
print(my_data)



#code=792f817b9d623ba0319c9b72fa310661a3a4b967
#cod e d48feacb8f1862aa5fa0633ee87d0a08e8d82c47
#{"token_type": "Bearer", "expires_at": 1616295018, "expires_in": 12697,
# "refresh_token": "9ff7242e6a89b7d152c1ce613bcc94a7814f590a",
# "access_token": "8aec62deadc7e07cc47ecd40cd76f9d8a2dd43b7", 

# token b3ae133fadc1794e19812cc94f2a62a4fc4c58e7'''