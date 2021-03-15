import csv
# Input the file name.
from pip._vendor.distlib.compat import raw_input

fname = raw_input("Enter file name WITHOUT extension: ")
# fname = "consumo_medio"
data = csv.reader(open(fname + '.csv'), delimiter=',')

# Skip the 1st header row.
next(data)

# Open the file to be written.
f = open(fname + '_lines.kml', 'w')

# Writing the kml file.
f.write("<?xml version='1.0' encoding='UTF-8'?>\n")
f.write("<kml xmlns='http://earth.google.com/kml/2.1'>\n")
f.write("<Document>\n")
f.write("<name>" + fname + '_line.kml' + "</name>\n")
f.write("   <Style id=\"style1\">  <LineStyle> <color>990000ff</color>"
        "   <width>4</width>    </LineStyle>   </Style>")
f.write("   <Placemark> <name>" + "Logging session 1" + "</name>   <description></description>"
                                                        " <styleUrl>#style1</styleUrl>"
        "<LineString>   <altitudeMode>relative</altitudeMode>   <coordinates>")

for row in data:
    f.write(str(row[5]) + "," + str(row[4]) + "\n")

f.write("</coordinates> </LineString>   </Placemark>    </Document>\n")
f.write("</kml>\n")
f.close()
print("File Created. ")
print("Press ENTER to exit. ")
raw_input()
