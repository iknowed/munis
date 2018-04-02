from urllib2 import urlopen
import sys
import os
import django
sys.path.append('./munis')
os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'
django.setup()

from xml.dom import minidom
import time
import math
import re
import psycopg2
from con.models import Vehicle
from con.models import Route
from con.models import Direction
from con.models import Run

import os
import django.contrib.gis
from django.contrib.gis.gdal import SpatialReference, CoordTransform,OGRGeometry
from django.contrib.gis.geos import GEOSGeometry
from django.db import connection

proj4 = '+proj=lcc +lat_1=37.06666666666667 +lat_2=38.43333333333333 +lat_0=36.5 +lon_0=-120.5 +x_0=2000000 +y_0=500000.0000000001 +ellps=GRS80 +towgs84=0,0,0,0,0,0,0 +units=us-ft +no_defs'
ccsf = SpatialReference(proj4)
wgs84 = SpatialReference('WGS84')
ct = CoordTransform(wgs84,ccsf)

srid='100000'

def latlon2city(lon,lat):
  west = -122.515003
  east = -122.355684
  north = 37.832365
  south = 37.706032
  
  lon_range = abs(abs(west) - abs(east))
  lat_range = north - south
  
  west_coord = 5979762.107179
  east_coord = 6024890.063509
  north_coord = 2130875.573550
  south_coord = 2085798.824452
  
  ew_range = east_coord - west_coord
  ns_range = north_coord - south_coord
  
  lat_pct = (north - lat)/lat_range
  lon_pct = (abs(west) - abs(lon))/lon_range
  
  x = west_coord + (lon_pct * ew_range)
  y = (lat_pct * ns_range)

  point = "POINT("+str(lon)+" "+str(lat)+")"
  geom = OGRGeometry(point)
  geom.transform(ct)
  res = geom.ewkt
  r = re.compile('([0-9\.]+)')
  (x,y) = r.findall(res)
  return((x,y))


def tagsHaveChanged(old,new):
  if(len(old.dirTag) == 0  or len(old.routeTag) == 0):
    return False

  if((old.dirTag != new.dirTag) or (old.routeTag != new.routeTag)):
    return True

  return False

def getNearestPath(self):
  #sql = "select pa.id,ST_Distance(ST_GeomFromEWKT('SRID=4326;POINT(%s %s)'), pa.loc) from path pa, route r where r.tag=%s and pa.route_id=r.id order by ST_Distance(ST_GeomFromEWKT('SRID=4326;POINT(%s %s)'),pa.loc) asc"
  #ST_GeomFromEWKT('SRID=4326;POINT(%s %s)')
  (x,y) = latlon2city(self.lon,self.lat)
  sql = "select dp.path_id,ST_Distance( ST_GeomFromEWKT('SRID=100000;POINT("+ str(x) + " " + str(y) + ")'), pa.loc) from con_directionpath dp, con_direction d, con_path pa where d.tag=%s and dp.direction_id=d.id and pa.id=dp.path_id order by ST_Distance( ST_GeomFromEWKT('SRID=100000;POINT("+ str(x) + " " + str(y) + ")'), pa.loc),pa.loc asc"
  #cur = self.db.cursor()
  cur = connection.cursor()
  cur.execute(sql,(self.dirTag,))
  res = cur.fetchone()
  if(res == None):
    return None
  else:
    return res[0]

def getNearestStreet(self):
  (x,y) = latlon2city(self.lon,self.lat)
  min_heading_one = (self.heading * 1.25) % 360
  max_heading_one = (self.heading * 0.75) % 360
  if max_heading_one < min_heading_one:
      min_heading = max_heading_one
      max_heading = min_heading_one
  else:
      min_heading = min_heading_one
      max_heading = max_heading_one
  sql = "select s.street,s.rt_fadd::int,ST_Distance( ST_GeomFromEWKT('SRID=2227;POINT({0} {1})'), s.the_geom), ((180/3.1415926)*ST_Azimuth(ST_StartPoint(s.the_geom),ST_EndPoint(s.the_geom))::int % 360)::int  as degrees from stclines_streets s order by ST_Distance( ST_GeomFromEWKT('SRID=2227;POINT({0} {1})'), s.the_geom) asc limit 10".format(str(x),str(y))
  cur = connection.cursor()
  cur.execute(sql)
  res = cur.fetchone()
  if(res == None):
    return None
  else:
    return { 'street': res[0], 'block': res[1], 'distance': res[2], 'degrees': res[3] }


def hasOpenRun(old):
  if(old.vid == None):
    return None
  sql = "select id,vehicle_id,route_tag,dir_tag,start_time,end_time,speed,distance,runlets from run where vehicle_id = %s and dir_tag = %s and end_time = 0"
  cur = old.db.cursor()
  cur.execute(sql,(old.vid,old.dirTag))    
  r = cur.fetchone()
  if(r == None):
    return r
  run = {}
  run['id'] = r[0]
  run['vehicle_id'] = r[1]
  run['routeTag'] = r[2]
  run['dirTag'] = r[3]
  run['startTime'] = long(r[4])
  run['endTime'] = r[5]
  run['speed'] = r[6]
  run['distance'] = r[7]
  run['runlets'] = r[8]
  return run

def openRun(new,t):
  cur = new.db.cursor()
  sql = "insert into run (vehicle_id,route_tag,dir_tag,start_time,end_time,speed,log,runlets,distance,start_date,end_date) values (%s,%s,%s,%s,0,0.00,'',0,0,to_timestamp(%s),to_timestamp(0)) returning id"
  cur.execute(sql,(new.vid,new.routeTag,new.dirTag,t,t))
  new.db.commit()
  run = {}
  run['id'] = cur.fetchone()[0]
  run['vehicleID'] = new.vid
  run['routeTag'] = new.routeTag
  run['dirTag'] = new.dirTag
  run['startTime'] = long(t) 
  run['endTime'] = 0
  run['speed'] = 0
  run['runlets'] = 0
  return run

def isInYard(v):
  #ST_GeometryFromText('SRID=2163;POINT(%s %s)')
  (x,y) = latlon2city(v.lon,v.lat)
  #sql = "select ST_Within(ST_SetSRID(ST_MakePoint("+ str(v.lon) + "," + str(v.lat) + " ),"+srid+"),y.the_geom) from yards y";
  sql = "select ST_Within(ST_SetSRID(ST_MakePoint("+ str(x) + "," + str(y) + " ),"+srid+"),y.the_geom) from yards y";
  #cur = v.db.cursor()
  cur = connection.cursor()
  #cur.execute(sql,(v.lon,v.lat))
  cur.execute(sql)
  res = cur.fetchone()
  if(res[0] == True):
    print v.vid+" is in yard"
  return(res[0])

def addRunlet(run,old,new):

  if((old.lat == new.lat) and (old.lon == new.lon) and (run['runlets'] == 0)):
    return

  path_id = getNearestPath(old)

  if(path_id == None):
    path_id = -1

  old_lat = old.lat;
  old_lon = old.lon;
  t0 = old.t;

  new_lat = new.lat;
  new_lon = new.lon;
  tn = new.t;

  if(old.dirTag != new.dirTag):
    old_lat = new_lat
    old_lon = new_lon
    t0 = tn

  sql = "insert into runlet (run_id,lat0,lon0,loc0,t0,latn,lonn,locn,tn,path_id,distance) values ("+str(run['id'])+","+str(old_lat)+","+str(old_lon)+", ST_SetSRID(ST_MakePoint("+ str(old_lon) + "," + str(old_lat) + " ),"+srid+"),"+str(t0)+","+str(new_lat)+","+str(new_lon)+",ST_SetSRID(ST_MakePoint("+ str(new_lon) + "," + str(new_lat) + " ),"+srid+") ,"+str(tn)+","+str(path_id)+",0) returning id"

  cur = old.db.cursor()
  cur.execute(sql)
  old.db.commit()
  id = cur.fetchone()[0]

  GEOSGeom0 = GEOSGeometry("POINT("+str(old.lon)+" "+str(old.lat)+")")
  GEOSGeom0.srid=4326
  GEOSGeomn = GEOSGeometry("POINT("+str(new.lon)+" "+str(new.lat)+")")
  GEOSGeomn.srid=4326
  GEOSGeom0.transform(ct)
  GEOSGeomn.transform(ct)
  dist = GEOSGeom0.distance(GEOSGeomn)
  sql = "update runlet set distance=%s where id=%s"
  cur.execute(sql,(dist,id,))
  old.db.commit()

  freq = int((t - run['startTime'])/(run['runlets'] + 1))

  sql = "update run set distance =  distance + %s, runlets = runlets + 1, freq = %s where id = " + str(run['id']) 
  cur.execute(sql,(dist,freq,))
  old.db.commit()

  """
  cur.execute(sql)
  run = cur.fetchone()
  prev_dist = run[6];
  sql = "select id,ST_Distance(ST_Transform(loc0,"+srid+"),ST_Transform(locn,"+srid+")),tn-t0,path_id from runlet where run_id = " + str(run[0]) + "order by id"
  cur.execute(sql)
  res = cur.fetchall()
  speed = 0
  dist = 0;
  if(len(res) > 1):
    a = []
    for n in range(0,len(res)):
      lat = res[n][2]
      lon = res[n][3]
      a.append(str(lon) + " " + str(lat))
  
    line = "LINESTRING("
    line = line + ",".join(a) + ")"
    sql = "select ST_Length(ST_Transform(loc0,"+srid+"),ST_Transform(locn,"+srid+"));"
    cur.execute(sql)
    l = cur.fetchone()
    dist = float(l[0])
    secs = t - run[3] 
    speed = float(dist/1000.)/(float(secs)/3600.0)
  """

def closeRunlets(db,run):
  cur = db.cursor()
  sql = "delete from runlet where run_id="+str(run['id'])
  cur.execute(sql)
  db.commit()

def endRun(db,run,t):
  cur = db.cursor()
  speed = 0.0
  if((run['endTime']-run['startTime'])  > 0 ):
    speed = float((float(run['distance'])/5280.)/(float((run['endTime']-run['startTime']))/60./60.))
  sql = "update run set end_time = "+str(t)+", end_date = to_timestamp(%s), speed = "+str(speed)+" where id="+str(run['id'])
  cur.execute(sql,(t,))
  db.commit()


def closeRun(db,run,t):
  cur = db.cursor()

  endRun(db,run,t)

  sql = "select id,distance,t0,tn,path_id from runlet where run_id="+str(run['id'])+" order by id"
  cur.execute(sql)
  runlets = cur.fetchall()
  run_dist = 0
  run_time = t-run['startTime']
  for runlet in runlets:
    run_dist += runlet[1]
  
  speed = -1
  if(run_dist != 0.0 and run_time != 0L):
    if(run_time != 0):
      speed = float(float(run_dist)/5280.)/(float(run_time)/60./60.)

    print "closeRun: dist = "+str(run_dist)+" time = "+str(run_time)+" speed = "+str(speed)

  processRun(db,run,t)
  closeRunlets(db,run)
  if((run_dist == 0) or (run_time == 0)):
    sql = "delete from run where id="+str(run['id'])
    cur.execute(sql)
    db.commit()

def processRun(db,run,t):
  (datype,hour) = getDaType(db,run)
  runlets = getRunlets(db,run)
  (time,times,distance,distances) = processRunlets(runlets)
  if((time > 600) or (float(distance) > float(5280.*5.))):
    postPathSpeeds(db,run,times,distances,datype,hour)

def postPathSpeeds(db,run,times,distances,datype,hour):
  cur = db.cursor()
  for path_id in distances:
    if(times[path_id] == 0):
      continue
    if(distances[path_id] == 0):
      continue
  
    new_speed = ((float(distances[path_id])/5280.0)/(float(times[path_id])/60./60.))
  
    sql = "select id,speed,min,max,navg from speed where route_tag = %s and dir_tag = %s and  path_id= %s and datype = %s and hour = %s"
    cur.execute(sql,(run['routeTag'],run['dirTag'],path_id,datype,hour))
    Speed = cur.fetchone()
    if(Speed == None):
      print "no speed for "+run['routeTag']+" "+run['dirTag']+" "+str(path_id)+" "+str(datype)+ " " +str(hour)
      return

    id = Speed[0]
    speed = float(Speed[1])
    min = float(Speed[2])
    max = float(Speed[3])
    navg = float(Speed[4])
    navg+=1
    if(speed == 0):
      speed = new_speed
    else:
      speed = speed + ((new_speed - speed) / navg);

    if(speed > max):
      max = speed
    if(speed < min):
      min = speed

    sql = "update speed set navg = %s, speed = %s, min = %s, max = %s where id=%s"
    cur.execute(sql,(navg,speed,min,max,id))
    db.commit() 

def processRunlets(runlets):
  time = 0
  distance = 0
  distances = {}
  times = {}
  for runlet in runlets:
    id = runlet[0]
    run_id = runlet[1]
    lat0 = runlet[2]
    lon0 = runlet[3]
    t0 = long(runlet[4])
    latn = runlet[5]
    lonn = runlet[6]
    tn = long(runlet[7])
    path_id = str(runlet[8])
    dist = runlet[9]
    loc0 = runlet[10]
    locn = runlet[11]
    time += (tn-t0)
    distance += dist
  
    if(distances.has_key(path_id) == False):
      distances[path_id] = 0
  
    if(times.has_key(path_id) == False):
      times[path_id] = 0
  
    distances[str(path_id)] += float(dist)

    times[path_id] += tn-t0

  return(time,times,distance,distances)


def getRunlets(db,run):
  sql = "select id,run_id,lat0,lon0,t0,latn,lonn,tn,path_id,distance,loc0,locn from runlet where run_id = "+str(run['id'])+" order by id asc"
  cur = db.cursor()
  cur.execute(sql)
  runlets = cur.fetchall()
  return runlets


def getDaType(db,run):
  cur = db.cursor()
  sql = "select to_char(to_timestamp(start_time),'Day') from run where id="+str(run['id'])
  cur.execute(sql)
  res = cur.fetchone()[0]
  day = res
  sql = "select to_char(to_timestamp(start_time),'HH24') from run where id="+str(run['id'])
  cur.execute(sql)
  res = cur.fetchone()[0]
  hour = res
  datype = 0
  if(re.match("Saturday",day)):
    datype = 1
  if(re.match("Sunday",day)):
    datype = 2
  return (datype,hour)

def closeOrphanRuns(db,t):
  cur = db.cursor()
  sql = "select id,vehicle_id,route_tag,dir_tag,start_time,end_time,speed,distance from  run where start_date < (now() - interval '3 hour') and end_time = 0"
  cur.execute(sql)
  
  for orphan in cur.fetchall():
    run = {}
    run['id'] = orphan[0]
    run['vehicle_id'] = orphan[1]
    run['routeTag'] = orphan[2]
    run['dirTag'] = orphan[3]
    run['startTime'] = long(orphan[4])
    run['endTime'] = orphan[5]
    run['speed'] = orphan[6]
    run['distance'] = orphan[6]
    closeRun(db,run,t) 
  

url = "http://webservices.nextbus.com/service/publicXMLFeed?command=vehicleLocations&a=sf-muni&r=22&t="
#db = postgresql.open("pq://muni:mta@cybre.net/municon")

t = 0

while(1):
  try:
  #  db = psycopg2.connect("dbname=municon user=muni password=mta host=cybre.net")
    dom = minidom.parse(urlopen(url+str(t)))
  except:
    time.sleep(5)
    continue

  print url + str(t)
  t = int(int(dom.getElementsByTagName("lastTime")[0].getAttribute('time'))/1000)
  print str(t)

  for vehicle in dom.getElementsByTagName("vehicle"):
    new = Vehicle()
    new.vid = vehicle.getAttribute('id')
    try:
        new.route = Route.objects.filter(tag=vehicle.getAttribute('routeTag'))[0]
    except Exception as e:
        print "can't find routeTag: {0}".format(vehicle.getAttribute('routeTag'))
    try:
        new.direction = Direction.objects.filter(tag=vehicle.getAttribute('dirTag'))[0]
    except Exception as e:
        print "can't find dirTag: {0}".format(vehicle.getAttribute('dirTag'))
        continue
    new.routeTag = vehicle.getAttribute('routeTag')
    new.dirTag = vehicle.getAttribute('dirTag')
    new.dirTag = unicode(re.sub(u'(OB|IB).*$',u'\\1',new.dirTag))

    #if(len(new.dirTag) < 1):
    #   print new.vid + " route "+new.routeTag+" has no dirTag"
    #   continue

    new.t = t - int(vehicle.getAttribute('secsSinceReport'))
    if vehicle.getAttribute('predictable') == 'true':
        new.predictable = True
    else:
        new.predictable = False
    new.heading = int(vehicle.getAttribute('heading'))
    new.speedKmHr = float(vehicle.getAttribute('speedKmHr'))
    new.speedkmhr = float(vehicle.getAttribute('speedKmHr'))
    new.lat = float(vehicle.getAttribute('lat'))
    new.lon = float(vehicle.getAttribute('lon'))
    new.latlon = GEOSGeometry("POINT({0} {1})".format(new.lon,new.lat), srid=4326) 
#    if(isInYard(new)):
#      continue
    p = getNearestPath(new)
    s = getNearestStreet(new)
    print new.vid, new.heading, s
    try:
        new.save()
    except Exception as e:
        print e 
    continue 

    if(vehicle.getAttribute('leadingVehicleID')):
      new.leadingVehicleId = int(vehicle.getAttribute('leadingVehicleID'))
    else:
      new.leadingVehicleId = 0

    old = Vehicle()
    old.get(vid=new.vid)

    new.locate()

    run = hasOpenRun(old) 

    if(tagsHaveChanged(old,new)):
      print "tagsHaveChanged " + old.dirTag + " " + new.dirTag + " " + new.vid
      if(run != None):
        closeRun(db,run,t)
      run = openRun(new,t)

    if(old.dirTag != '' and new.dirTag != '' and run != None):
      addRunlet(run,old,new)

    if(new.dirTag == None or new.dirTag == ''):
      new.delete()
    elif(old.vid == None):    
      new.save();
    else:
      old.update(new) 

  #closeOrphanRuns(db,t)
  #db.close()
  time.sleep(10)


