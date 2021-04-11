# MySportData

App to show interactive heatmap of all the activities using Strava API

### Map of all the activities
![Heatmap](Screenshot.png)

### Speed map of single activity
![Speedmap](Screenshot2.png)

### Altitude map of single activity
![Altitudemap](Screenshot3.png)

## How to use (local server)
1. Copy the repository
```
git clone https://github.com/MrDajman/MySportData.git
```
2. Install the requirements
```
pip install -r requirements.txt
```
3. Run the app
```
python main.py
```
4. Go to http://127.0.0.1:5000/


## Current functionalities
- Loging in via Strava
- User database
- Storing activities in the database
- **Interactive map with all the activities**
- **Interactive map with color trail for the speed of an activity**
- Progress bar for retrieving the activities


## To Do
- Manage the exceptions (api small limit; api big limit?)
- Stop thread when leaving the website
- Last complete update (User table variable)

## Ideas for future development
- Snap activity tracks to the roads

## Resources
- Strava API
- Flask, flask_sqlachemy
- OpenStreetMap
- Folium
