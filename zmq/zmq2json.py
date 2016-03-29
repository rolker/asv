#!/usr/bin/env python

import zmq
import nmea
import sys

inconnection = 'tcp://graywhale:7778'
#topic = 'TEST_123'
#topic = 'GPS_01'
topic = 'RVGS_GPS_01'
outfile = '../web/latest.json'
infile = None

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
        if s.type == 'GGA':
            #open(outfile,'w').write(str(status))
            open(outfile,'w').write(status.getGeoJson())

