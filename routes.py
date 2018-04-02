from urllib2 import urlopen
import sys
import os
import django
sys.path.append('./munis')
os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'
django.setup()
from xml.dom import minidom
import formatter
import psycopg2
import time
import math
import re
import os
import munis
from con.models import Vehicle
from con.models import Route
from con.models import RouteStop
from con.models import Run
from con.models import Path
from con.models import Point
from con.models import Stop
from con.models import Direction
from con.models import DirectionStop
from con.models import DirectionPath
from con.models import Speed
import django.contrib.gis
from django.db import connection, transaction
from django.contrib.gis.gdal import SpatialReference, CoordTransform,OGRGeometry
#from py2neo import neo4j
#graph_db = neo4j.GraphDatabaseService("http://cybre.net:7474/db/data/")
#graph_db.clear();

proj4 = '+proj=lcc +lat_1=37.06666666666667 +lat_2=38.43333333333333 +lat_0=36.5 +lon_0=-120.5 +x_0=2000000 +y_0=500000.0000000001 +ellps=GRS80 +towgs84=0,0,0,0,0,0,0 +units=us-ft +no_defs'
srid='100000'
ccsf = SpatialReference(proj4)
wgs84 = SpatialReference('WGS84')
ct = CoordTransform(wgs84,ccsf)

url = "http://webservices.nextbus.com/service/publicXMLFeed?command=routeConfig&a=sf-muni"
print(url)
#r = open('r.config','r')
#routes = r.read()
routes = ''
if(len(routes)):
  dom = minidom.parse('r.config')
else:
  dom = minidom.parse(urlopen(url))

def fixlat(n):
    return float(n)
    lat = float(n)- 37.0
    lat = lat * (pow(10,(len(str(lat)) - 2)))
    return int(lat)

def fixlon(n):
    return float(n)
    lon = float(n) + 122.0
    lon = -1.0 * lon * (pow(10,(len(str(lon)) - 3)))
    return int(lon)
   

def latlon2city(lon,lat):
  lat = float(lat)
  lon = float(lon)

  west = -122.515003
  east = -122.355684
  north = 37.832365
  south = 37.706032
  
  
  west_coord_1 = 5973058
  east_coord_1 = 6022571
  north_coord_1 = 2132800
  south_coord_1 = 2085080

  west_coord = 5979762.107179
  east_coord = 6024890.063509
  north_coord = 2130875.573550
  south_coord = 2085798.824452

  west_delta = west_coord - west_coord_1 
  east_delta = east_coord - east_coord_1
  north_delta = north_coord - north_coord_1
  south_delta = south_coord - south_coord_1
  
  lon_range = abs(abs(west) - abs(east)) 
  lat_range = north - south 

  ew_range = (east_coord - west_coord) 
  ns_range = (north_coord - south_coord) 
  
  lat_pct = (north - lat)/lat_range
  lon_pct = (abs(west) - abs(lon))/lon_range
  
  #x = west_coord + (lon_pct * ew_range)
  #y = south_coord + (lat_pct * ns_range)
  x = west_coord + (lon_pct * ew_range) 
  y = north_coord - (lat_pct * ns_range) 

  point = "POINT("+str(lon)+" "+str(lat)+")"
  geom = OGRGeometry(point)
  geom.transform(ct)
  res = geom.ewkt
  r = re.compile('([0-9\.]+)')
  (x,y) = r.findall(res)
  return((x,y))
  return((float(x),float(y)))

routes = {}
Route.objects.all().delete();
Stop.objects.all().delete();
Direction.objects.all().delete();
DirectionStop.objects.all().delete();
Path.objects.all().delete();
Point.objects.all().delete();
Speed.objects.all().delete();

for route in dom.getElementsByTagName("route"):
    print(route.getAttribute('tag')," ",route.getAttribute('title'))
    tag = route.getAttribute('tag')

    numtag = tag
    m = re.match(r"^([0-9]+)([A-Z]*)",numtag)
    if(m != None):
      numtag = m.group(1)
      suffix = m.group(2)
      if(int(numtag) < 10):
        numtag = "00"+numtag
      elif(int(numtag) < 100):
        numtag = "0"+numtag
      numtag = numtag + suffix

    r = Route(tag=tag,numtag=numtag,
    title=route.getAttribute('title'),
    color=route.getAttribute('color'),
    oppositecolor=route.getAttribute('oppositecolor'),
    latmin=route.getAttribute('latMin'),
    latmax=route.getAttribute('latMax'),
    lonmin=route.getAttribute('lonMin'),
    lonmax=route.getAttribute('lonMax')) 
    #routes[tag] = graph_db.create({"type" : "route" , "tag" : tag, "title" : r.title, "latmin" : r.latmin, "latmax" : r.latmax, "lonmin" : r.lonmin , "lonmax" : r.lonmax });
    r.save()
    #continue

    route_stop_seq = 1
    stops = {}
    for node in route.getElementsByTagName('stop'):
        if node.nodeName == 'stop' and node.getAttribute('title'):
            (x,y) = latlon2city(node.getAttribute('lon'),node.getAttribute('lat'))
            tag=node.getAttribute('tag')
            s = Stop.objects.filter(tag=tag)
            if(len(s) == 0):
              s = Stop(x=x,y=y,
              loc='SRID=100000;POINT('+ str(x) + ' ' + str(y)  + ')',
              title=node.getAttribute('title'),
              lat=node.getAttribute('lat'),
              lon=node.getAttribute('lon'),
              tag=node.getAttribute('tag'))
              s.save()
              #stops[tag] = graph_db.create({"type" : "node" : "loc" : loc , "lat" : lat , "lon" : lon , "title" : title , "route" : routes[tag] });
            else:
              s = s[0]

            #n = RouteStop(seq=route_stop_seq, route=r, stop=s)
            s.save()
            route_stop_seq += 1


    for node in route.getElementsByTagName('direction'):
        tag=node.getAttribute('tag')
        tag=unicode(re.sub(u'(OB|IB).*$',u'\\1',tag)),
        useforui = 1 if node.getAttribute('useForUI') == 'true' else 0
        sql = "insert into direction (route_id,tag,title,name,useforui) values (%s,%s,%s,%s,%s) returning id";
        d = Direction(tag=tag[0],
        title= node.getAttribute('title'),
        name=node.getAttribute('name'),
        route=r,
        useforui=useforui)
        #graph_db.create({"type" : "direction" , "title" : title , "name" : name , "route" : routes[tag] });
        d.save()
        #cur.execute(sql,(route_id,tag,title,name,useforui))
        #direction_id = cur.fetchone()[0]
        #db.commit()
        stop_seq = 1
        for stop in node.getElementsByTagName('stop'):
            tag = stop.getAttribute('tag')
            s = Stop.objects.filter(tag=tag)[0]
            ds = DirectionStop(direction=d,seq=stop_seq,stop=s)
            #graph_db.create({"type" : "directionstop" , "title" : title , "name" : name , "route" : routes[route.tag] : "tag" : tag });
            ds.save()
            stop_seq += 1

    path_seq = 1
    for path in route.getElementsByTagName('path'):
        pa = Path(route=r,seq=path_seq,loc='POINT(1. 1.)')
        pa.save()
        path_seq += 1
        point_seq = 0
        points = []
        for point in path.getElementsByTagName('point'):
            lat = point.getAttribute('lat')
            lon = point.getAttribute('lon')
            (x,y) = latlon2city(lon,lat)
            #sql = "insert into point (seq,path_id,lat,lon) values (%s,%s,%s,%s)"
            #cur.execute(sql,(point_seq,path_id,lat,lon))
            po = Point(seq=point_seq,path=pa,lat=lat,lon=lon)   
            po.save()
            (x,y) = latlon2city(lon,lat)
            points.insert(point_seq,str(x) + " " +str(y))
            #points.insert(point_seq,str(lon) + " " +str(lat))
            point_seq += 1
        loc = "SRID="+srid+";LINESTRING("+",".join(points)+")"
        #print loc
        #sql = "update path set loc = %s where id = %s"
        pa.loc=loc;
        pa.save()
        #cur.execute(sql,(loc,path_id))




"""
route_stop
 id       | integer               | not null default nextval('route_stop_id_seq'::regclass)
 seq      | integer               | not null
 route_id | integer               | not null
 tag      | character varying(24) | not null
 title    | character varying(64) | not null
 lat      | double precision      | not null
 lon      | double precision      | not null
 stopid   | integer               | not null
 loc      | geometry              | not null

direction_stop
 id           | integer               | not null default nextval('direction_stop_id_seq'::regclass)
 direction_id | integer               | not null
 seq          | integer               | not null
 tag          | character varying(24) | not null

"""

for route in Route.objects.all():
  for direction in Direction.objects.filter(route=route):
    paths = {}

      #sql = "select distinct(pa.id),ST_Distance(s.loc,pa.loc) from con_directionpath dp, con_directionstop ds, con_stop s, con_path pa where dp.direction_id={0} and s.id={1} and ds.stop_id = s.id and dp.path_id=pa.id order by ST_Distance(s.loc,pa.loc) asc limit 1".format(direction.id,direction_stop.stop_id)
    for direction_stop in DirectionStop.objects.filter(direction=direction).order_by('seq'):
      sql = "select distinct(pa.id),ST_Distance(s.loc,pa.loc) from con_directionstop ds, con_stop s, con_path pa where s.id={1} and ds.stop_id = s.id order by ST_Distance(s.loc,pa.loc) asc limit 1".format(direction.id,direction_stop.stop_id)
      cursor = connection.cursor()
      cursor.execute(sql)
      row = cursor.fetchone()
      if(row == None):
          print route.tag+" "+direction.tag+" "+str(direction_stop.id)+" no row"
          continue

      path = Path.objects.filter(id=row[0])

      paths[row[0]] = path
      #print "path: "+str(row[0])+" dist: "+str(row[1])

      
    seq = 0
     
    for path in paths:
        p = Path.objects.filter(id=path)
        dp = DirectionPath(direction=direction,path_id=path,seq=seq)
        dp.save()
        seq = seq + 1

    print direction.tag + " " + str(seq)


for route in Route.objects.all():
  for direction in Direction.objects.filter(route=route):
    n = 0
    for datype in range(0,3):
      n = n + 1
      for hour in range(0,24):
        n = n + 1
        for dpath in DirectionPath.objects.filter(direction=direction):
          n = n + 1
          s = Speed(route=route,direction=direction,path=dpath.path,hour=hour,datype=datype,speed=0,max=-666,min=666,navg=0)
          s.save()

    print route.tag+ " "+direction.tag+" "+str(n)
