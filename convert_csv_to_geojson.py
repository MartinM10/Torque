import csv

# Read in raw data from csv
from pip._vendor.distlib.compat import raw_input

fname = raw_input("Enter file name WITHOUT extension: ")
rawData = csv.reader(open(fname + '.csv'), delimiter=',')

# the template. where data from the csv will be formatted to geojson
template = \
   ''' \
   { "type" : "Feature",
       "geometry" : {
           "type" : "Point",
           "coordinates" : [%s, %s]},
       "properties" : { "userId" : %s, "date" : "%s", "speed" : "%s"}
       },
   '''


# the head of the geojson file
output = \
   ''' \

{ "type" : "Feature Collection",
   "features" : [
   '''


# loop through the csv by row skipping the first
iter = 0
for row in rawData:
   iter += 1
   if iter >= 2:
      userId = row[0]
      session = row[1]
      lat = row[3]
      lon = row[4]
      time = row[2]
      speed = row[6]

      # output += template % (row[0], row[2], row[1], row[3], row[4])
      output += template % (lon, lat,  userId,  time, speed)

# the tail of the geojson file
output += \
   ''' \
   ]

}
   '''


# opens an geoJSON file to write the output
outFileHandle = open(fname + ".geojson", "w")
outFileHandle.write(output)
outFileHandle.close()