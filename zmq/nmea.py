#!/usr/bin/env python

import datetime
import json
import geojson

class Sentence:
    def __init__(self,data):
        self.valid = False
        if len(data) and data[0] in ('$',):
            data = data.strip()
            if '*' in data:
                data,checksum = data.split('*',2) 
            parts = data.split(',')
            if len(parts[0]) > 4:
                if parts[0][1] == 'P':
                    self.talker = 'P'
                    self.type = parts[0][2:]
                else:
                    self.talker = parts[0][1:3]
                    self.type = parts[0][3:]
                self.fields = parts[1:]
                self.valid = True
                
    def __str__(self):
        if not self.valid:
            return 'invalid'
        return 'talker: '+self.talker+' type: '+self.type+' '+' '.join(self.fields)
    
    def decode(self):
        ret = {}
        if(self.valid):
            ret['talker'] = self.talker
            ret['type'] = self.type
            ret['fields'] = self.fields
            if self.type == 'ZDA':
                ret['time'] = self.decodeTime()
                ret['date'] = datetime.date(int(self.fields[3]),int(self.fields[2]),int(self.fields[1]))
                ret['datetime'] = datetime.datetime.combine(ret['date'],ret['time'])
            if self.type == 'HDT':
                if self.fields[1] == 'T':
                    ret['heading'] = float(self.fields[0])
            if self.type == 'VTG':
                ret['track'] = float(self.fields[0])
                try:
                    ret['track_mag'] = float(self.fields[2])
                except ValueError:
                    ret['track_mag'] = None
                ret['sog'] = float(self.fields[4])
            if self.type == 'GGA':
                ret['time'] = self.decodeTime()
                ret['quality'] = int(self.fields[5])
                ret['valid'] = False
                if ret['quality'] > 0:
                    ret['valid'] = True
                    lat,lon = self.decodeLatLon()
                    ret['latitude'] = lat
                    ret['longitude'] = lon
                    ret['altitude'] = float(self.fields[8])
                    try:
                        ret['geoidal_separation'] = float(self.fields[10])
                    except ValueError:
                        ret['geoidal_separation'] = None
                    
            if self.type == 'RMC':
                ret['time'] = self.decodeTime()
                datestr = self.fields[8]
                y = int(datestr[4:6])
                if y < 80:
                    y += 2000
                else:
                    y += 1900
                ret['date'] = datetime.date(y,int(datestr[2:4]),int(datestr[:2]))
                ret['datetime'] = datetime.datetime.combine(ret['date'],ret['time'])
                ret['status'] = self.fields[1]
                ret['valid'] = False
                if ret['status'] == 'A':
                    ret['valid'] = True
                    lat,lon = self.decodeLatLon(2)
                    ret['latitude'] = lat
                    ret['longitude'] = lon
                    ret['sog'] = float(self.fields[6])
                    ret['track'] = float(self.fields[7])
                    try:
                        ret['magnetic_variation'] = float(self.fields[9])
                        if self.fields[10] == 'W':
                            ret['magnetic_variation'] = -ret['magnetic_variation']
                    except ValueError:
                        ret['magnetic_variation'] = None

        return ret

    def decodeTime(self,index=0):
        tf = self.fields[index]
        if '.' in tf:
            us = int(float(tf[6:])*1000000)
        else:
            us = 0
        h = int(tf[0:2])
        m = int(tf[2:4])
        s = int(tf[4:6])
        return datetime.time(h,m,s,us)
    
    def decodeLatLon(self,index=1):
        lat = int(self.fields[index][:2])+(float(self.fields[index][2:])/60.0)
        if(self.fields[index+1])=='S':
            lat = -lat
        lon = int(self.fields[index+2][:3])+(float(self.fields[index+2][3:])/60.0)
        if(self.fields[index+3])=='W':
            lon = -lon
        return lat,lon

class Status:
    def __init__(self,id='gps'):
        self.id = id
        self.date = None
        self.time = None
        self.latitude = None
        self.longitude = None
        self.sog = None
        self.heading = None
        self.trackHistory = []
        self.startTime = None
        self.lastTime = None

    def addSentence(self,s):
        if s.type in ('ZDA','HDT','GGA','VTG','RMC'):
            sd = s.decode()
            if s.type == 'ZDA':
                self.date = sd['date']
                self.time = sd['time']
            if s.type == 'RMC':
                self.date = sd['date']
            if s.type in ('GGA','RMC'):
                self.time = sd['time']
                if self.date is not None:
                    currentdt = datetime.datetime.combine(self.date,self.time)
                    self.lastTime = currentdt
                    if self.startTime is None:
                        self.startTime = currentdt
                    deltaTime = currentdt-self.startTime
                    sog = self.sog
                    if sog is None:
                        sog = 0
                    if sd['valid']:
                        self.latitude = sd['latitude']
                        self.longitude = sd['longitude']
                        self.trackHistory.append((self.longitude,self.latitude,0,deltaTime.total_seconds(),sog))
            if s.type == 'HDT':
                self.heading = sd['heading']
            if s.type == 'VTG':
                self.sog = sd['sog']
                
    def __str__(self):
        ret = {}
        ret['system_time'] =  datetime.datetime.utcnow().isoformat()
        if self.date is not None and self.time is not None:
            ret['datetime'] = datetime.datetime.combine(self.date,self.time).isoformat()
        ret['latitude'] = self.latitude
        ret['longitude'] =  self.longitude
        ret['sog'] = self.sog
        ret['heading'] = self.heading
        
        return json.dumps(ret)
    
    def getGeoJson(self):
        ls = geojson.LineString(self.trackHistory)
        if self.startTime is not None:
            lsf = geojson.Feature(geometry=ls, properties={"referenceTime":self.startTime.isoformat()})
        else:
            lsf = geojson.Feature(geometry=ls)
        p = geojson.Point((self.longitude,self.latitude))
        pf = geojson.Feature(geometry=p)
        fc = geojson.FeatureCollection([lsf,pf])
        return geojson.dumps(fc)
    
    def getCZML(self):
        ret = {'id':self.id}
        ret['position']={}
        ret['position']['epoch'] = self.startTime.isoformat()
        ret['position']['cartographicDegrees'] = [(self.lastTime-self.startTime).total_seconds(),self.longitude,self.latitude,0.0]
        return json.dumps(ret)