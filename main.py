from math import pi, cos, sqrt
import pandas
import geocoder
import folium


def is_insdie(location: str, cities: dict):
    """
    Checks if location is inside the list
    of cities
    """
    location = location.lower()
    location = location.split()

    length = len(location)
    for i in range(length):
        for j in range(i + 1, length + 1):
            city = ' '.join(location[i:j])
            if city in cities:
                return cities[city]

    return False


def dist(my_coord: tuple, city_coord: tuple):
    """
    Returns distance between 2 points 
    with geographical coordinates defined
    """
    radius, mylat, mylon, lat, lon = 6400, my_coord[0], my_coord[1], city_coord[0], city_coord[1]

    rad = radius * cos(mylat * 2 * pi / 360)
    
    delta_lat = radius * (mylat - lat) * 2 * pi / 360
    delta_lon = rad * min(abs(mylon - lon), 180 - abs(mylon - lon)) * 2 * pi / 360

    dist = sqrt(delta_lat**2 + delta_lon**2)

    return dist


def get_cities(path, loc, rad):
    """
    Returns all cities closer to loc than rad
    from database worldcities.csv
    """
    data = pandas.read_csv(path, error_bad_lines=False)

    cities = dict(zip(data['City'], zip(map(lambda x: round(x, 3) , data['Latitude']), map(lambda x: round(x, 3), data['Longitude']))))
    
    new_keys = list(filter(lambda x: dist(loc, cities[x]) < rad, cities))
    cities = {key: cities[key] for key in new_keys}

    return cities


def get_films(path, year, cities: dict):
    """
    Returns all films of certain year that 
    where shooted in certain cities
    """
    data = pandas.read_csv(path, error_bad_lines=False)

    films = dict(zip(data['movie'], zip(data['year'], data['location'])))
    new_keys = list(filter(lambda x: films[x][0] == year, films))

    films = {key: films[key] for key in new_keys}

    new_keys = list(filter(lambda x: is_insdie(films[x][1], cities), films))
    films = {key: (films[key][1], is_insdie(films[key][1], cities)) for key in new_keys}

    return films


def true_locs(films: dict, myloc: list, rad: int):
    """
    Checks coordinates from file location.csv to be
    close to coordiantes gained from geocoder with
    accuracy rad kilometers
    """
    keys = list(films.keys())[:100]
    films = {key: films[key] for key in keys}

    ans = {}

    for film in films:
        location = geocoder.osm(films[film][0]).osm

        if not location:
            continue

        point = (location['y'], location['x'])

        true_dist = dist(myloc, point)
        
        if true_dist < rad:
            films[film] = ((point, dist(myloc, point)), films[film][1])

            ans[film] = films[film]
    
    keyz = list(ans.keys())
    keyz.sort(key=lambda x: ans[x][0][1])

    ans = {key: ans[key] for key in keyz[:10]}

    return ans


def layer_near(myloc, rad, year):
    """
    Creates and returns layer for folium map
    that contains 10 nearest year's film for
    laction myloc with radius rad
    """
    films = true_locs(get_films('locations.csv', str(year), get_cities('worldcities.csv', myloc, rad)), myloc, 300)

    fg_filmz = folium.FeatureGroup(name='Filmz')

    for film in films:
        info = f"""
                Name: {film.strip()}
                Year: {year}
                Location: {films[film][0]}
        """
        fg_filmz.add_child(folium.Marker(location=films[film][0][0], popup=info))

    return fg_filmz


def country_info(city, year, path):
    """
    Reades database and returns all
    films in location city and of year
    year
    """
    data = pandas.read_csv(path, error_bad_lines=False)

    films = dict(zip(data['movie'], zip(data['year'], data['location'])))

    films = {key: films[key] for key in films if films[key][0] == str(year) and city.lower() in films[key][1].lower()}

    return films


def layer_loc(films, year):
    """
    Creates and returns a layer for
    folium map that contains all films
    of year year in certin location
    """
    fg_films = folium.FeatureGroup(name='bycity')

    for index, film in enumerate(films):
        if index == 100:
            break

        location = geocoder.osm(films[film][1]).osm
        if not location:
            continue
        
        loc = (location['y'], location['x'])
        info = f"""
                Name: {film.strip()}
                Year: {year}
                Location: {films[film][1]}
        """

        fg_films.add_child(folium.Marker(location=loc, popup=info))

    return fg_films


def create_map(layers, loc, year):
    """
    Creates and saves a folium TheOpenStreet
    map with layers from layers centered at loc 
    and with layers control
    """
    map_filmz = folium.Map(location=loc, zoom_start=5)

    for el in layers:
        map_filmz.add_child(el)

    map_filmz.add_child(folium.LayerControl())

    map_filmz.save(f'MAP_{loc}_{year}.html')


def opioid_deaths(year, path):
    """
    Creates and returns a layer for 
    folium map that contains statistic
    of opioids deaths in different states
    of USA
    """
    data = pandas.read_csv(path, error_bad_lines=False)

    states = sorted(set(data['State']))
    coords = {}

    for stat in states:
        g = geocoder.osm(stat).osm
        point = [g['y'], g['x']]
        coords[stat] = point

    stuff = list(zip(data['State'], data['Population'], data['Year'], data['Deaths']))

    stuff = list(filter(lambda x: str(x[2]) == year, stuff))

    fg_opioids = folium.FeatureGroup(name='opioids')

    for el in stuff:
        fg_opioids.add_child(folium.CircleMarker(coords[el[0]], radius=int(el[3]) * 100000 / el[1], fill_color='red'))

    return fg_opioids


if __name__ == "__main__":
    country = input("Enter a place for research please: ")
    year = input("Enter a year for films please: ")
    year1 = input("Enter a year for drigs please: ")
    myloc = list(map(float, input("Enter your coordinates please in format lat lon:").split()))
    rad = int(input("Enter a radius"))

    layers = [
        layer_loc(country_info('Russia', 2017, 'locations.csv'), 2017), 
        layer_near(myloc, 100, 2017),
        opioid_deaths(year1, 'Multiple Cause of Death, 1999-2014 v1.1.csv')
        ]

    create_map(layers, myloc, year)
