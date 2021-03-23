from flask import Flask

import folium

app = Flask(__name__)


@app.route('/')
def index():
    return "Hello"

@app.route('/map/')
def index2():
    start_coords = (46.9540700, 142.7360300)
    folium_map = folium.Map(location=start_coords, zoom_start=14)
   # with open('folium_map.html',"w") as f:
    #        f.write(folium_map._repr_html_())
    return folium_map._repr_html_()


if __name__ == '__main__':
    app.run(debug=True)