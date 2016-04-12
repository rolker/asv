#!/usr/bin/env python

import zmq
import nmea
import sys
import datetime

inconnection = 'tcp://graywhale:7778'
#topic = 'TEST_123'
#topic = 'GPS_01'
topic = 'RVGS_GPS_01'
outfile = '../web/latest.json'
infile = None
lastTime = None

if len(sys.argv) > 1:
    infile = open(sys.argv[1])
else:
    context = zmq.Context()
    subscriber = context.socket(zmq.SUB)
    subscriber.connect(inconnection)
    subscriber.setsockopt(zmq.SUBSCRIBE, topic)

status = nmea.Status()

while True:
    if infile is None:
        message = subscriber.recv()
    else:
        message = infile.readline()
        if len(message) == 0:
            break
    if message.startswith('$'):
        print message.strip()
        s = nmea.Sentence(message)
        status.addSentence(s)
        if s.type == 'GGA' and status.latitude is not None:
            now = datetime.datetime.utcnow()
            if lastTime is None or (now - lastTime).total_seconds() > 1:
                #open(outfile,'w').write(str(status))
                open(outfile,'w').write(status.getGeoJson())
                lastTime = now

