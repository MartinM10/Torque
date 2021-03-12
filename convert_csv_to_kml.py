import csv
# Input the file name.
from pip._vendor.distlib.compat import raw_input

fname = raw_input("Enter file name WITHOUT extension: ")
data = csv.reader(open(fname + '.csv'), delimiter=',')
# Skip the 1st header row.
data.next()
# Open the file to be written.
f = open('csv2kml.kml', 'w')

# Writing the kml file.
f.write("<?xml version='1.0' encoding='UTF-8'?>\n")
f.write("<kml xmlns='http://earth.google.com/kml/2.1'>\n")
f.write("<Document>\n")
f.write("<name>" + fname + '.kml' + "</name>\n")

for row in data:
    f.write("   <Placemark>\n")
    f.write("       <name>" + str(row[1]) + "</name>\n")
    f.write("       <Style><IconStyle>")
    f.write("       <Icon>http://maps.google.com/mapfiles/kml/shapes/arrow.png</Icon><color>cc00ff00</color><heading>1"
            "</heading""></IconStyle></Style>")
    f.write("       <description>" + '  <![CDATA[<b>' + str(row[3]) + '</b>:&nbsp;' + str(row[4]) + '<br />'
            + ']]>' + "</description>\n")
    f.write("       <Point>\n")
    f.write("           <coordinates>" + str(row[7]) + "," + str(row[6]) + "</coordinates>\n")
    f.write("       </Point>\n")
    f.write("   </Placemark>\n")
f.write("</Document>\n")
f.write("</kml>\n")
f.close()
print("File Created. ")
print("Press ENTER to exit. ")
raw_input()
