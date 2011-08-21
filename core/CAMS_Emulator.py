#!/usr/bin/python

import ConfigParser
import datetime
import math
import optparse
import pprint
import re
import sys
import xml.dom.minidom



def get_datetime(newVal):
    """
    Takes the given string in format of YYYY-MM-DD HH:MM:SS.ms and converts it
    to a datetime.datetime() object.  The ms field is optional.
    
    newVal - string to convert to a datetime.datetime() object.
    """
    stuff = re.split('\s+', newVal)
    date = re.split('-', stuff[0])
    time = re.split(':', stuff[1])
    sec = []
    if re.search('\.', time[2]) == None:
        sec.append(time[2])
        sec.append("0")
    else:
        sec = re.split('\.', time[2])
    dt = datetime.datetime(int(date[0]),
                           int(date[1]),
                           int(date[2]),
                           int(time[0]),
                           int(time[1]),
                           int(sec[0]),
                           int(sec[1]))
    return dt


def compare_events(one, two):
    if one.dt <= two.dt:
        if one.dt == two.dt:
            return 0
        else:
            return -1
    return 1


###############################################################################
#### PersonEvent class
###############################################################################
class PersonEvent:
    def __init__(self, line):
        stuff = re.split('\s+', line)
        date = str(stuff[0]).strip()
        time = str(stuff[1]).strip()
        self.dt = get_datetime("%s %s" % (date, time))
        self.res = str(stuff[2]).strip()
        self.x = str(stuff[3]).strip()
        self.y = str(stuff[4]).strip()
        self.speed = float(str(stuff[5]).strip())
        return
    
    def __str__(self):
        mystr = "%s\t%s\t%s\t%s\t%s" % (str(self.dt), self.res, self.x, self.y, self.speed)
        return mystr


###############################################################################
#### Event class
###############################################################################
class Event:
    def __init__(self, dt, serial, message):
        self.dt = dt
        self.serial = serial
        self.message = message
        return
    
    def __str__(self):
        mystr = "%s\t%s\t%s" % (str(self.dt), self.serial, self.message)
        return mystr


###############################################################################
#### Sensor class
###############################################################################
class Sensor:
    def __init__(self, id, x, y):
        self.id = id
        self.x = int(x)
        self.y = int(y)
        self.state = "OFF"
        self.state_trip = None
        self.last_motion = None
        self.view = dict()
        self.add_event = None
        spot = "%sx%s" % (str(x), str(y))
        self.view[spot] = 0
        return
    
    def set_event_func(self, eventFunc):
        self.add_event = eventFunc
        return


###############################################################################
#### MotionSensor class
###############################################################################
class MotionSensor(Sensor):
    def add_view(self, x, y, radius):
        spot = "%sx%s" % (str(x), str(y))
        if spot not in self.view:
            self.view[spot] = int(float(radius))
        return
    
    def in_range(self, x, y):
        spot = "%sx%s" % (str(x), str(y))
        if spot in self.view:
            return True
        return False
    
    def get_range(self, x, y):
        spot = "%sx%s" % (str(x), str(y))
        if spot in self.view:
            return int(self.view[spot])
        return None
    
    def apply_person_event(self, pevent):
        if self.last_motion == None:
            self.last_motion = pevent.dt
        if self.in_range(pevent.x, pevent.y):
            #print "\t",self.id, self.last_motion, self.state
            if self.state == "OFF":
                self.state = "ON"
                #print "***",pevent.dt, self.id, self.state
                self.add_event(pevent.dt, self.id, self.state)
            self.last_motion = pevent.dt
        else:
            #print "\t",self.id, self.last_motion, self.state
            if self.state == "ON":
                #print "***",(self.last_motion - pevent.dt)
                if (pevent.dt - self.last_motion) >= datetime.timedelta(0,2.5):
                    self.state = "OFF"
                    #print "***",pevent.dt, self.id, self.state
                    self.add_event(pevent.dt, self.id, self.state)
        return


###############################################################################
#### Emulator class
###############################################################################
class Emulator:
    def __init__(self, options):
        self.file_site = str(options.site)
        self.file_movement = str(options.movement)
        self.file_chromosome = str(options.chromosome)
        self.file_output = str(options.output)
        self.max_width = 0
        self.max_height = 0
        self.space = None
        self.sensors = None
        self.sensor_view = None
        self.events = list()
        self.movement = list()
        return
    
    def load_site(self):
        dom = xml.dom.minidom.parse(self.file_site)
        site = dom.getElementsByTagName("site")
        self.max_width = int(float(site[0].getAttribute("max_width")))
        self.max_height = int(float(site[0].getAttribute("max_height")))
        
        self.space = list()
        for x in range(self.max_width):
            self.space.append(list())
            for y in range(self.max_height):
                self.space[x].append(' ')
        
        walls = dom.getElementsByTagName("wall")
        for w in walls:
            x = int(float(w.getAttribute("x")))
            y = int(float(w.getAttribute("y")))
            width = int(float(w.getAttribute("width")))
            height = int(float(w.getAttribute("height")))
            px = x
            for ix in range(width):
                py = y
                for iy in range(height):
                    self.space[px][py] = 'w'
                    py += 1
                px += 1
        lintels = dom.getElementsByTagName("lintel")
        for l in lintels:
            x = int(float(l.getAttribute("x")))
            y = int(float(l.getAttribute("y")))
            width = int(float(l.getAttribute("width")))
            height = int(float(l.getAttribute("height")))
            px = x
            for ix in range(width):
                py = y
                for iy in range(height):
                    self.space[px][py] = 'l'
                    py += 1
                px += 1
        offLimits = dom.getElementsByTagName("off_limits")
        children = offLimits[0].childNodes
        for c in children:
            if c.nodeName == "rectangle":
                x = int(float(c.getAttribute("x")))
                y = int(float(c.getAttribute("y")))
                width = int(float(c.getAttribute("width")))
                height = int(float(c.getAttribute("height")))
                px = x
                for ix in range(width):
                    py = y
                    for iy in range(height):
                        if self.space[px][py] == ' ':
                            self.space[px][py] = 'x'
                        py += 1
                    px += 1
        #self.print_obj(self.space)
        return
    
    def load_movement(self):
        print "Loading movement file."
        fileIn = open(self.file_movement)
        mData = fileIn.readlines()
        fileIn.close()
        
        self.movement = list()
        for line in mData:
            if str(line).strip() != "":
                self.movement.append(PersonEvent(line))
        
        print "Adding extra buffers."
        startDT = self.movement[0].dt
        endDT = self.movement[-1].dt
        window = datetime.timedelta(0, 0.25)
        extra = startDT + window
        self.movement.append(PersonEvent("%s\t0\t-1\t-1\t0.0" % str(extra)))
        while extra < endDT:
            self.movement.append(PersonEvent("%s\t0\t-1\t-1\t0.0" % str(extra)))
            extra += window
        
        print "Sorting movement events."
        self.movement.sort(cmp=compare_events)
        return
    
    def load_chromosome(self):
        fileIn = open(self.file_chromosome)
        cData = fileIn.readlines()
        fileIn.close()
        senId = 0
        
        self.sensors = list()
        self.sensor_view = list()
        for x in range(self.max_width):
            self.sensor_view.append(list())
            for y in range(self.max_height):
                self.sensor_view[x].append(list())
        
        for x in range(self.max_width):
            for y in range(self.max_height):
                if cData[y][x] == '1':
                    self.sensors.append(MotionSensor(senId, x, y))
                    self.space[x][y] = str(senId)
                    self.sensor_view[x][y].append(str(senId))
                    self.spread_sensor(senId, x, y)
                    senId += 1
        
        for x in range(len(self.sensors)):
            self.sensors[x].set_event_func(self.add_sensor_event)
        
        self.print_obj(self.space)
        self.print_view()
        #for x in range(len(self.sensors)):
        #    print self.sensors[x].id
        #    print self.sensors[x].view
        return
    
    def spread_sensor(self, id, sX, sY, radius=7):
        for angle in range(360):
            for r in range(radius):
                dx = float(r+1) * float(math.cos(math.radians(angle)))
                dy = float(r+1) * float(math.sin(math.radians(angle)))
                saX = int(sX + dx)
                saY = int(sY + dy)
                if saX < 0:
                    saX = 0
                if saY < 0:
                    saY = 0
                #print saX,saY,self.space[saX][saY]
                if self.space[saX][saY] not in ['w', 'l']:
                    self.sensors[id].add_view(saX, saY, r+1)
                    if self.space[saX][saY] == ' ':
                        self.space[saX][saY] = str(id)
                    if str(id) not in self.sensor_view[saX][saY]:
                        self.sensor_view[saX][saY].append(str(id))
                else:
                    break
        return
    
    def add_sensor_event(self, dt, serial, message):
        self.events.append(Event(dt, serial, message))
        return
    
    def print_obj(self, obj):
        for y in range(self.max_height):
            out = ""
            for x in range(self.max_width):
                out += "%2s" % obj[x][y]
            print out
        return
    
    def print_view(self):
        for y in range(self.max_height):
            out = ""
            for x in range(self.max_width):
                tmp = ""
                for sen in self.sensor_view[x][y]:
                    tmp += "%s" % sen[-1]
                out += "%4s" % tmp
            print out
    
    def emulate(self):
        print "Emulating environment."
        for m in range(len(self.movement)):
            #print self.movement[m]
            for s in range(len(self.sensors)):
                self.sensors[s].apply_person_event(self.movement[m])
        return
    
    def output_results(self):
        for r in self.events:
            print r
        return
    
    def run(self):
        self.load_site()
        self.load_movement()
        self.load_chromosome()
        self.emulate()
        self.output_results()
        return


if __name__ == "__main__":
    print "CAMS Emulator"
    parser = optparse.OptionParser(usage="usage: %prog [options]")
    parser.add_option("-s",
                      "--site",
                      dest="site",
                      help="Site configuration file.")
    parser.add_option("-m",
                      "--movement",
                      dest="movement",
                      help="File with person movement data.")
    parser.add_option("-c",
                      "--chromosome",
                      dest="chromosome",
                      help="File with the sensor chromosome definition.")
    parser.add_option("-o",
                      "--output",
                      dest="output",
                      help="Filename to output resulting dataset to.")
    (options, args) = parser.parse_args()
    if None in [options.site, options.movement, options.chromosome, options.output]:
        if options.site == None:
            print "ERROR: Missing -s / --site"
        if options.movement == None:
            print "ERROR: Missing -m / --movement"
        if options.chromosome == None:
            print "ERROR: Missing -c / --chromosome"
        if options.output == None:
            print "ERROR: Missing -o / --output"
        parser.print_help()
        sys.exit()
    cams_em = Emulator(options)
    cams_em.run()

