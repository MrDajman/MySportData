import requests
import json
import os
import time
import polyline
import numpy as np
from flask import Flask, render_template, request, session, url_for, current_app, redirect, flash, Response
from flask_login import LoginManager, UserMixin, login_user, logout_user, current_user
from flask_sqlalchemy import SQLAlchemy
from rauth import OAuth2Service
import folium
from oauth import OAuthSignIn
import datetime
import geopy.distance
import branca
from branca.element import MacroElement
from jinja2 import Template
import threading
import random
from threading import Thread


app = Flask(__name__)
app.secret_key = "hello"
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///db.sqlite'
app.config['OAUTH_CREDENTIALS'] = {
    'strava': {
        'id': "63388",
        'secret': 'cd53d9a8623c88f85fe7f59ca0c4e9a4e6c2ac5f'
    }
}

db = SQLAlchemy(app)
lm = LoginManager(app)
lm.login_view = 'index'
exporting_threads = {}

list_colors = [
    "#00FF00",
    "#12FF00",
    "#24FF00",
    "#35FF00",
    "#47FF00",
    "#58FF00",
    "#6AFF00",
    "#7CFF00",
    "#8DFF00",
    "#9FFF00",
    "#B0FF00",
    "#C2FF00",
    "#D4FF00",
    "#E5FF00",
    "#F7FF00",
    "#FFF600",
    "#FFE400",
    "#FFD300",
    "#FFC100",
    "#FFAF00",
    "#FF9E00",
    "#FF8C00",
    "#FF7B00",
    "#FF6900",
    "#FF5700",
    "#FF4600",
    "#FF3400",
    "#FF2300",
    "#FF1100",
    "#FF0000",
]

@app.route('/update_activities/')
def progress_test():
    # function ran in background
    acts_count = len(Activity.query.filter_by(user_id = current_user.id).all())
    run_func(current_user.id)
    return render_template('progress_test.html', activity_count = acts_count)

@app.route('/progress')
def progress():
    def generate(id):
        x = 0

        while x <= 100:
            x = User.query.filter_by(id = id).first().progress_counter
            yield "data:" + str(x) + "\n\n"
            time.sleep(0.5)
            
    return Response(generate(current_user.id), mimetype= 'text/event-stream')


def run_func(user_id):
    data = { 'some': 'data', 'any': 'data' }
    thr = Thread(target=update_activities_db3, args=[user_id])
    thr.start()
    return thr

class User(UserMixin, db.Model):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    social_id = db.Column(db.String(64), nullable=False, unique=True)
    nickname = db.Column(db.String(64), nullable=False)
    fullname = db.Column(db.String(64), nullable=True)
    refresh_token = db.Column(db.String(64), nullable=False)
    access_token = db.Column(db.String(64), nullable=False)
    token_expires = db.Column(db.Integer, nullable=False)
    progress_counter = db.Column(db.Integer, nullable = True)

class Activity(db.Model):
    __tablename__ = 'activity'
    id = db.Column(db.Integer, primary_key=True)
    strava_id = db.Column(db.BigInteger, nullable=False, unique=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    name = db.Column(db.String(64), nullable=True)
    distance = db.Column(db.Float, nullable=True)
    sport = db.Column(db.String(64), nullable=False)
    date = db.Column(db.DateTime, nullable=False)
    polyline = db.Column(db.String(12000), nullable=True)

@lm.user_loader
def load_user(id):
    return User.query.get(int(id))
    id = db.Column(db.Integer, primary_key=True)


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('index'))


@app.route('/authorize/<provider>')
def oauth_authorize(provider):
    if not current_user.is_anonymous:
        return redirect(url_for('index'))
    oauth = OAuthSignIn.get_provider(provider)
    return oauth.authorize()


@app.route('/callback/<provider>')
def oauth_callback(provider):
    if not current_user.is_anonymous:
        return redirect(url_for('index'))
    oauth = OAuthSignIn.get_provider(provider)


    social_id, username, firstname, lastname, refresh_token, access_token, token_expires = oauth.callback()
    if social_id is None:
        flash('Authentication failed.')
        return redirect(url_for('index'))
    user = User.query.filter_by(social_id=social_id).first()

    if not user:
        user = User(
            social_id=social_id, 
            nickname=username, 
            fullname=str(firstname + " " + lastname), 
            refresh_token = refresh_token, 
            access_token = access_token, 
            token_expires = token_expires, 
            progress_counter = 0)
        db.session.add(user)
        db.session.commit()
    else:
        user.refresh_token = refresh_token
        user.access_token = access_token
        user.token_expires = token_expires

        db.session.commit()

    login_user(user, True)
    return redirect(url_for('index'))

@app.route('/sigle_activity_speed/', methods = ['POST'])
def single_activity_speed():
    class BindColorMap(MacroElement):
        def __init__(self, layer, colormap):
            super(BindColorMap, self).__init__()
            self.layer = layer
            self.colormap = colormap
            self._template = Template(u"""
            {% macro script(this, kwargs) %}
                {{this.colormap.get_name()}}.svg[0][0].style.display = 'block';
                {{this._parent.get_name()}}.on('overlayadd', function (eventLayer) {
                    if (eventLayer.layer == {{this.layer.get_name()}}) {
                        {{this.colormap.get_name()}}.svg[0][0].style.display = 'block';
                    }});
                {{this._parent.get_name()}}.on('overlayremove', function (eventLayer) {
                    if (eventLayer.layer == {{this.layer.get_name()}}) {
                        {{this.colormap.get_name()}}.svg[0][0].style.display = 'none';
                    }});
            {% endmacro %}
            """)  # noqa
    start_coords = (48.855, 2.3433)
    
    activity_id = int(request.form['nm'])
    
    activity = Activity.query.filter_by(strava_id=activity_id).first()
    line = polyline.decode(activity.polyline)
    

    streams = get_activity_streams(activity_id, ["velocity_smooth", "altitude"])
    speed = streams["velocity_smooth"]["data"]# in m/s
    altitude = streams["altitude"]["data"]# in m/s
    dist_speed = streams["distance"]["data"]

    color_dict = {i: list_colors[i] for i in range(len(list_colors))}
    start_point = line[0]
    total_line_distance = 0
    last_stream_index = 0
    
    lon_max = (max(line,key=lambda item:item[1])[1])
    lat_max = (max(line,key=lambda item:item[0])[0])
    lon_min = (min(line,key=lambda item:item[1])[1])
    lat_min = (min(line,key=lambda item:item[0])[0])
    start_coords = (lat_min+(lat_max - lat_min)/2, lon_min+(lon_max - lon_min)/2)
    streams_map = folium.Map(location=start_coords, zoom_start=13, tiles='cartodbpositron',width='100%', height='75%', control_scale = True)

    speed_map = folium.FeatureGroup("Speed")#.add_to(streams_map)
    altitude_map = folium.FeatureGroup("Altitude", show = False)#.add_to(streams_map)

    speed_median = np.median(speed)*3.6
    color_margin = 5


    altitude_max = max(altitude)
    altitude_min = min(altitude)
    # legend
    colormap = branca.colormap.LinearColormap([(0,255,0),(255,255,0),(255,0,0)])
    colormap = colormap.scale(speed_median-color_margin, speed_median+color_margin)
    colormap = colormap.to_step(10)
    colormap.caption = 'Speed (km/h)'
    #colormap.add_to(streams_map)

    colormap_altitude = branca.colormap.LinearColormap([(0,255,0),(255,255,0),(255,0,0)])
    colormap_altitude = colormap_altitude.scale(altitude_min, altitude_max)
    colormap_altitude = colormap_altitude.to_step(10)
    colormap_altitude.caption = 'Altitude (m)'
    #colormap_altitude.add_to(streams_map)

    for point in line[1:]:

        point_distance = geopy.distance.distance(start_point, point).m
        total_line_distance += point_distance
        
        if total_line_distance > dist_speed[-1]:
            stream_index = len(speed)-1
        else:
            stream_index = next(x[0] for x in enumerate(dist_speed) if x[1] > total_line_distance)

        if last_stream_index == stream_index:
            segment_speed = 0
            segment_altitude = speed[last_stream_index]
        else:
            segment_speed = np.mean(speed[last_stream_index:stream_index])*3.6 # in km/h 
            segment_altitude = np.mean(altitude[last_stream_index:stream_index]) 

        speed_new_range = (segment_speed - speed_median + color_margin) * (29/(2*color_margin))
        altitude_new_range = (segment_altitude - altitude_min)*(29/(altitude_max-altitude_min))
        if speed_new_range > len(list_colors)-1:
            speed_new_range = len(list_colors)-1
            altitude_new_range = len(list_colors)-1
        elif speed_new_range < 0:
            speed_new_range = 0
            altitude_new_range = 0
        folium.PolyLine((start_point, point), color=color_dict[round(speed_new_range)], weight = 5, control = False).add_to(speed_map)
        folium.PolyLine((start_point, point), color=color_dict[round(altitude_new_range)], weight = 5, control = False).add_to(altitude_map)

        last_stream_index = stream_index
        start_point = point
    streams_map.add_child(speed_map).add_child(altitude_map)
    
    streams_map.add_child(colormap).add_child(colormap_altitude)
    streams_map.add_child(BindColorMap(speed_map,colormap)).add_child(BindColorMap(altitude_map,colormap_altitude))
    folium.LayerControl(collapsed=False).add_to(streams_map)

    return streams_map._repr_html_()

def update_tokens(current_user):
    if current_user.token_expires < time.time():

        print("INFO:\tTokens expired. Retreiving refreshed tokens")

        payload = {
                'client_id': "63388",
                'client_secret': 'cd53d9a8623c88f85fe7f59ca0c4e9a4e6c2ac5f',
                'grant_type': 'refresh_token',
                'refresh_token': current_user.refresh_token
                }

        response = requests.post(url = 'https://www.strava.com/oauth/token',data = payload)

        check_response(response)

        current_user.access_token = response.json()["access_token"]
        current_user.refresh_token = response.json()["refresh_token"]
        current_user.token_expires = response.json()["expires_at"]

        db.session.commit()
        print("INFO:\tTokens Updated")
    else:
        print("INFO:\tTokens Up to date")

def get_activity_streams(id, keys):

    update_tokens(current_user)

    print("INFO:\tRetrieving athlete activities")
    url = "https://www.strava.com/api/v3/activities/{}/streams?".format(id)
    url += "keys="
    for key in keys:
        url += "{},".format(key)
    url = url[:-1]
    url += "&key_by_type=1&"
    url = url[:-1]
    print(url)
    r = requests.get(url, data = {"access_token":current_user.access_token})
    res = check_response(r)
    if res != 1:
        return res
    return r.json()

@app.route('/activities_on_map/')
def activities_on_map():
    start_coords = (48.855, 2.3433)
    folium_map = folium.Map(location=start_coords, zoom_start=13, tiles='cartodbpositron')
    
    run_map = folium.FeatureGroup("Runs").add_to(folium_map)
    ride_map = folium.FeatureGroup("Bike rides").add_to(folium_map)
    
    user_activities = Activity.query.filter_by(user_id=current_user.id).all()

    for activity in user_activities:
        if activity.polyline == None:
            continue
        line = polyline.decode(activity.polyline)
        if len(line) == 0:
            continue

        end_point_address = url_for('single_activity_speed')
        popup_html = """<p>Distance: {}</p>
            <p>Date: {}</p>
            <form action = "{}" target="_blank" method = "post">
            <p><input type="hidden" id="postId" name="nm" value={}></p>
            <p><input type = "submit" value = "Show speed map" /></p>
            </form>""".format(activity.distance, activity.date, end_point_address, activity.strava_id)
        
        if activity.sport in ["Run","Walk"]:
            folium.PolyLine(line, color = "#FF0000", opacity = 0.3, control = False, popup = popup_html).add_to(run_map)
            pass
        elif activity.sport in ["Ride"]:
            folium.PolyLine(line, color = "#0000FF", opacity = 0.3, control = False, popup = popup_html).add_to(ride_map)
            pass

    folium.LayerControl(collapsed=False).add_to(folium_map)

    return folium_map._repr_html_()


def get_my_activities(current_user,before = False, after = False, page = False, per_page = False):
    update_tokens(current_user)
    print("INFO:\tRetrieving athlete activities")
    url = "https://www.strava.com/api/v3/activities?"
    if page:
        url += "page={}&".format(page)
    if per_page:
        url += "per_page={}&".format(per_page)
    url = url[:-1]
    print(url)
    r = requests.get(url, data = {"access_token":current_user.access_token})
    res = check_response(r)
    if res != 1:
        return res
    return r.json()

def update_activities_db3(user_id, nb_to_retrieve = 75):
    current_user = User.query.filter_by(id = user_id).first()
    
    current_user.progress_counter = 0
    db.session.commit()

    page = 1
    count_total = 0
    count_new = 0
    error_out = ""
    while(1):
        try:
            activities_list = get_my_activities(current_user,per_page=200, page = page)
        except TypeError:
            break
        try:
            if len(activities_list) == 0:
                break
        except TypeError:
            try:
                if activities_list == 2:
                    error_out += "Wait 15 minutes for the query limit to Reset"
            except:
                pass
            break
        if activities_list == 0:
            return 0

        for act in activities_list:
            activity = Activity.query.filter_by(strava_id = act["id"]).first()
            if not activity:
                try:
                    strava_id, user_id, name, distance, sport, date, polyline = single_activity_callback(current_user,act["id"])
                except TypeError:
                    break
                
                date_date = date.split("T")[0].split("-")
                date_time = date.split("T")[1][:-1].split(":")
                activity = Activity(strava_id=strava_id,
                                    user_id=user_id,
                                    name = name,
                                    distance = distance,
                                    sport = sport,
                                    date = datetime.datetime(int(date_date[0]),int(date_date[1]),int(date_date[2]),int(date_time[0]),int(date_time[1]),int(date_time[2])),
                                    polyline = polyline)
                db.session.add(activity)
                db.session.commit()
                count_new += 1
                print(current_user.id)
                current_user.progress_counter = int((count_new/nb_to_retrieve)*100)
                db.session.commit()
                if count_new > nb_to_retrieve:
                    break
            else:
                print("INFO:\tActivity already in db")
            count_total +=1
            if count_new > nb_to_retrieve:
                break
        page += 1

    return 0


def single_activity_callback(current_user, id):
        update_tokens(current_user)
        print("INFO:\tRetrieving activity ID: {}".format(id))
        url = "https://www.strava.com/api/v3/activities/{}?".format(id)
        r = requests.get(url, data = {"access_token":current_user.access_token})
        res = check_response(r)
        if res == 1:
            return (r.json()["id"],
                current_user.id,
                r.json()["name"],
                r.json()["distance"],
                r.json()["type"],
                r.json()["start_date_local"],
                r.json()["map"]["polyline"])

        else:
            return False


def check_response(response):
    if response.ok:
        print("INFO:\tSuccessfully retrieved request")
        return 1
    else:
        errors = response.json()["errors"]
        print("INFO:\tRequest isn't retrieved succesfully. Nb of errors: {}.".format(len(errors)))
        for error in errors:
            print("ERROR:\t{}: {} {}".format(error["resource"],error["code"],error["field"]))
            if error["resource"] == "Application" and error["code"] == "exceeded":
                print("ERROR:\tWait 15 minutes for the query limit to renew")
                return 2
            else: print(errors)
            if error["resource"] == "Athlete" and error["code"] == "invalid":
                print("ERROR:\Invalid Access token. Logout and Login")
                return 3
            return 0


if __name__ == '__main__':
    db.create_all()
    app.run(debug=True)
