from geopy.geocoders import Nominatim
geolocator = Nominatim(user_agent="Torque")

location = geolocator.reverse('36.634998, -4.493052')
print(location.raw['address'])
address = location.raw['address']
simple_address = ''

try:
    road = address['road']
    simple_address += road
except KeyError:
    road = None
try:
    neighbourhood = address['neighbourhood']
    simple_address += ', ' + neighbourhood
except KeyError:
    neighbourhood = None
try:
    town = address['town']
    simple_address += ', ' + town
except KeyError:
    town = None
try:
    city = address['city']
    simple_address += ', ' + city
except KeyError:
    city = None

# print(road, ' ', neighbourhood, ' ', town, ' ', city)

print(simple_address)

# location = geolocator.geocode("121 N LaSalle St, Chicago")
# Name of streets
# coordenates = (crs[9], crs[10])
# location = rev(coordenates)
# address = location.raw['address']
# print(road)
# print(location.raw['address'])
'''
if address:
    for key in address:
        if 'road' in key:
            road = location.raw['address']['road']
            if road not in track:
                print('added: ', road)
                track.append(road)
        else:
            print('NO HAY NOMBRE DE CALLE --------------------- ')
            print(address)
'''