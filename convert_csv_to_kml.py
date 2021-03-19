import csv
# Input the file name.
import os

from Torque.settings import STATIC_URL
from pip._vendor.distlib.compat import raw_input

fname = raw_input("Enter file name WITHOUT extension: ")
# fname = "consumo_medio"
current_dir = os.path.dirname(os.path.realpath(__file__))
path = os.path.join(current_dir, 'static', 'data/')
data = csv.reader(open(path + fname + '.csv'), delimiter=',')


# Skip the 1st header row.
titles = next(data)
first_row = next(data)
# Open the file to be written.
f = open(path + fname + '.kml', 'w')

# Writing the kml file.
f.write("<?xml version='1.0' encoding='UTF-8'?>\n"
        "<kml xmlns='http://earth.google.com/kml/2.1'>\n"
        "<Document>\n"
        "<name>" + fname + '.kml' + "</name>\n"
        "<Style id=\"style1\">\n"
        "   <LineStyle>\n"
        "       <color>990000ff</color>\n"
        "       <width>4</width>\n"
        "   </LineStyle>\n"
        "</Style>\n"
        "<Placemark>\n"
        "   <name>" + first_row[0] + " " + first_row[1] + "</name>\n"
        "   <description></description>\n"
        "   <styleUrl>#style1</styleUrl>\n"
        "   <LineString>\n"
        "       <altitudeMode>relative</altitudeMode>\n"
        "       <coordinates>\n")

for row_lines in data:
    f.write("           " + str(row_lines[4]) + "," + str(row_lines[3]) + "\n")

f.write("       </coordinates>\n"
        "   </LineString>\n"
        "</Placemark>\n")

data_points = csv.reader(open(path + fname + '.csv'), delimiter=',')
# Skip the 1st header row.
next(data_points)

for row_points in data_points:
    f.write("<Placemark>\n"
            "   <name>" + str(titles[6]) + "</name>\n"
            "   <Style>\n" 
            "       <IconStyle>\n"
            "           <Icon>\n"
            "               http://maps.google.com/mapfiles/kml/shapes/arrow.png\n"
            "           </Icon>\n"
            "           <color>\n"
            "               cc00ff00\n"
            "           </color>\n"
            "           <heading>\n"
            "               1\n"
            "           </heading>\n"
            "       </IconStyle>\n"
            "   </Style>\n"
            "       <description>\n"
            "           <![CDATA[<b>" + str(row_points[6]) + "</b>&nbsp;" + str(row_points[7]) + "<br />]]>\n"
            "       </description>\n"
            "       <Point>\n"
            "           <coordinates>" + str(row_points[4]) + "," + str(row_points[3]) + "</coordinates>\n"
            "       </Point>\n"
            "</Placemark>\n")

f.write("</Document>\n"
        "</kml>\n")
f.close()
print("File Created. ")
print("Press ENTER to exit. ")
raw_input()
