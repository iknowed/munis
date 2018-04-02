# You'll have to do the following manually to clean this up:
#     * Rearrange models' order
#     * Make sure each model has one field with primary_key=True
# Feel free to rename the models, but don't rename db_table values or field names.
#
# Also note: You'll have to insert the output of 'django-admin.py sqlcustom [appname]'
# into your database.

from django.db import models
from django.contrib.gis.db import models

class Line(models.Model):
    route_id  = models.IntegerField(db_index=True,null=True)
    line      = models.CharField(max_length=32)
    line_geom = models.GeometryField(srid=100000,blank=True)
    direction = models.IntegerField(db_index=True,blank=True)
    numtag    = models.CharField(max_length=16)
    tag       = models.CharField(max_length=16)

class Stop(models.Model):
    tag = models.CharField(max_length=32,blank=True)
    stop_id = models.CharField(max_length=32,blank=True)
    lat = models.FloatField(blank=True)
    lon = models.FloatField(blank=True)
    loc = models.GeometryField(srid=100000,blank=True)
    title = models.CharField(max_length=64,db_index=True,blank=True)
    x = models.FloatField(blank=True)
    y = models.FloatField(blank=True)

class Route(models.Model):
    line = models.CharField(max_length=32, blank=True)
    tag = models.CharField(max_length=32, blank=True)
    numtag = models.CharField(max_length=32, blank=True)
    title = models.CharField(max_length=64, blank=True)
    color = models.TextField(blank=True) # This field type is a guess.
    oppositecolor = models.TextField( blank=True) # This field type is a guess.
    latmin = models.FloatField(blank=True)
    latmax = models.FloatField(blank=True)
    lonmin = models.FloatField(blank=True)
    lonmax = models.FloatField(blank=True)

class RouteStop(models.Model):
    route = models.ForeignKey(Route,blank=True)
    seq = models.IntegerField(db_index=True,blank=True)
    stop = models.ForeignKey(Stop,blank=True)

class Direction(models.Model):
    route = models.ForeignKey(Route,blank=True)
    tag = models.CharField(max_length=32,db_index=True,blank=True)
    title = models.CharField(max_length=64,db_index=True,blank=True)
    name = models.CharField(max_length=32,db_index=True,blank=True)
    useforui = models.IntegerField(blank=True)

class DirectionStop(models.Model):
    direction = models.ForeignKey(Direction,blank=True)
    seq = models.IntegerField(db_index=True,blank=True)
    stop = models.ForeignKey(Stop,blank=True)
    stopid = models.CharField(max_length=32,blank=True)

class Path(models.Model):
    seq = models.IntegerField(blank=True)
    route = models.ForeignKey(Route,blank=True)
    loc = models.GeometryField(srid=100000,blank=True) 

class Point(models.Model):
    seq = models.IntegerField(blank=True)
    path = models.ForeignKey(Path,blank=True)
    lat = models.FloatField(blank=True)
    lon = models.FloatField(blank=True)

class Speed(models.Model):
    route = models.ForeignKey(Route,blank=True)
    direction = models.ForeignKey(Direction,blank=True)
    path = models.ForeignKey(Path,blank=True)
    hour = models.IntegerField(db_index=True,blank=True)
    datype = models.IntegerField(db_index=True,blank=True)
    speed = models.FloatField(db_index=True,null=True,blank=True)
    min = models.FloatField(db_index=True,blank=True)
    max = models.FloatField(db_index=True,blank=True)
    navg = models.IntegerField(db_index=True,blank=True)

class Vehicle(models.Model):
    vid = models.TextField(blank=True)
    route = models.ForeignKey(Route,blank=True)
    direction = models.ForeignKey(Direction,blank=True)
    lat = models.FloatField(blank=True)
    lon = models.FloatField(blank=True)
    loc = models.GeometryField(srid=100000,null=True,blank=True) 
    t = models.BigIntegerField(blank=True)
    predictable = models.BooleanField(blank=True)
    heading = models.IntegerField(blank=True)
    speedkmhr = models.FloatField(null=True,blank=True)
    leadingvehicleid = models.TextField(blank=True)
    stop = models.TextField(blank=True)
    stop_seq = models.IntegerField(null=True,blank=True)
    latlon = models.PointField(null=True, blank=True,)

class Run(models.Model):
    vehicle = models.ForeignKey(Vehicle,blank=True)
    route = models.ForeignKey(Route,blank=True)
    direction = models.ForeignKey(Direction,blank=True)
    start_time = models.BigIntegerField(db_index=True,blank=True)
    end_time   = models.BigIntegerField(db_index=True,blank=True)
    start_date = models.DateTimeField(db_index=True,blank=True)
    end_date   = models.DateTimeField(db_index=True,blank=True)
    speed      = models.FloatField(null=True,db_index=True,blank=True)
    distance   = models.FloatField(db_index=True,blank=True)
    log        = models.TextField(blank=True)
    runlets    = models.IntegerField(db_index=True,blank=True)
    freq       = models.IntegerField(db_index=True,blank=True)

class Runlet(models.Model):
    run = models.ForeignKey(Run,blank=True)
    lat0 = models.FloatField(db_index=True,blank=True)
    lon0 = models.FloatField(db_index=True,blank=True)
    loc0 = models.GeometryField(srid=100000,blank=True)
    t0 = models.IntegerField(db_index=True,blank=True)
    latn = models.FloatField(db_index=True,blank=True)
    lonn = models.FloatField(db_index=True,blank=True)
    locn = models.GeometryField(srid=100000,blank=True)
    tn = models.IntegerField(db_index=True,blank=True)
    path = models.ForeignKey(Path,blank=True)
    distance = models.FloatField(db_index=True,blank=True)
    stop = models.TextField(blank=True)
    stop_seq = models.IntegerField(null=True,blank=True)


class DirectionPath(models.Model):
    direction = models.ForeignKey(Direction,blank=True)
    path = models.ForeignKey(Path,blank=True)
    seq = models.IntegerField(db_index=True,blank=True);


class StopId2Tag(models.Model):
    tag = models.CharField(max_length=32,blank=True)
    stop_id = models.CharField(max_length=32,blank=True)

