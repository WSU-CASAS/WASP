#!/usr/bin/python
#*****************************************************************************#
#**
#**  WASP CAMS Generator
#**
#**    Brian L Thomas, 2011
#**
#** Tools by the Center for Advanced Studies in Adaptive Systems at
#**  the School of Electrical Engineering and Computer Science at
#**  Washington State University
#** 
#** Copyright Washington State University, 2017
#** Copyright Brian L. Thomas, 2017
#** 
#** All rights reserved
#** Modification, distribution, and sale of this work is prohibited without
#**  permission from Washington State University
#**
#** If this code is used for public research, any resulting publications need
#** to cite work done by Brian L. Thomas at the Center for Advanced Study of 
#** Adaptive Systems (CASAS) at Washington State University.
#**  
#** Contact: Brian L. Thomas (bthomas1@wsu.edu)
#** Contact: Diane J. Cook (cook@eecs.wsu.edu)
#*****************************************************************************#
import ConfigParser
import copy
import datetime
import math
import optparse
import os
import pprint
import re
import sys
import time
import xml.dom.minidom
sys.path.append('/usr/lib/pyshared/python2.6')
import gv

from pygraph.classes.graph import graph
from pygraph.algorithms.heuristics import euclidean
from pygraph.algorithms.minmax import heuristic_search
from pygraph.algorithms.minmax import shortest_path
from pygraph.classes.exceptions import NodeUnreachable
from pygraph.readwrite import dot



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
    try:
        if re.search('\.', time[2]) == None:
            sec.append(time[2])
            sec.append("0")
        else:
            sec = re.split('\.', time[2])
    except:
        print newVal
        z = int("45.2")
    dt = datetime.datetime(int(date[0]),
                           int(date[1]),
                           int(date[2]),
                           int(time[0]),
                           int(time[1]),
                           int(sec[0]),
                           int(sec[1]))
    return dt


###############################################################################
#### PersonEvent class
###############################################################################
class PersonEvent:
    def __init__(self, dt, x, y, speed):
        self.dt = dt
        self.res = "1"
        self.x = x
        self.y = y
        self.speed = speed
        self.annotation = ""
        return
    
    def set_ann(self, annotation):
        self.annotation = annotation
        return
    
    def __str__(self):
        mystr = "%s\t%s\t%s\t%s\t%s\t%s" % (str(self.dt), self.res, self.x,
                                            self.y, self.speed, self.annotation)
        return mystr


###############################################################################
#### Event class
###############################################################################
class Event:
    def __init__(self, line):
        stuff = re.split('\s+', str(line).strip())
        date = str(stuff[0]).strip()
        time = str(stuff[1]).strip()
        self.dt = get_datetime("%s %s" % (date, time))
        self.serial = str(stuff[2]).strip()
        self.message = str(stuff[3]).strip()
        self.annotation = None
        if len(stuff) > 4:
            self.annotation = str(stuff[4]).strip()
        self.x = None
        self.y = None
        self.skip = 0
        return
    
    def set_xy(self, x, y):
        self.x = x
        self.y = y
        return
    
    def __cmp__(self, other):
        val = 0
        if self.dt < other.dt:
            val = -1
        elif self.dt > other.dt:
            val = 1
        return val


###############################################################################
#### Annotation class
###############################################################################
class Annotation:
    def __init__(self, dt, annotation):
        self.dt = dt
        self.annotation = annotation
        return
    
    def __cmp__(self, other):
        val = 0
        if self.dt < other.dt:
            val = -1
        elif self.dt > other.dt:
            val = 1
        return val


###############################################################################
#### Space class
###############################################################################
class Space:
    def __init__(self, name):
        self.name = name
        self.area = list()
        return
    
    def add_area(self, x, y, width, height, maxW, maxH):
        for ax in range(int(float(width))):
            for ay in range(int(float(height))):
                nx = int(float(x)) + ax
                ny = int(float(y)) + ay
                if nx < maxW and ny < maxH:
                    spot = "%sx%s" % (str(nx), str(ny))
                    if spot not in self.area:
                        self.area.append(spot)
        return
    
    def in_area(self, x, y):
        spot = "%sx%s" % (str(x), str(y))
        if spot in self.area:
            return True
        return False


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


###############################################################################
#### Generator class
###############################################################################
class Generator:
    def __init__(self, options):
        self.file_site = str(options.site)
        self.file_data = str(options.data)
        self.file_output = str(options.output)
        self.max_width = 0
        self.max_height = 0
        self.space = None
        self.areas = None
        self.sensors = dict()
        self.sensor_view = None
        self.events = list()
        self.gr = graph()
        self.paths = None
        self.events = list()
        self.human = list()
        self.annotations = list()
        self.max_speed = 10.0
        return
    
    def load_site(self):
        dom = xml.dom.minidom.parse(self.file_site)
        site = dom.getElementsByTagName("site")
        self.max_width = int(float(site[0].getAttribute("max_width")))
        self.max_height = int(float(site[0].getAttribute("max_height")))
        
        self.space = list()
        self.paths = list()
        for x in range(self.max_width):
            self.space.append(list())
            self.paths.append(list())
            for y in range(self.max_height):
                self.space[x].append(' ')
                self.paths[x].append(dict())
        
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
        
        furniture = dom.getElementsByTagName("furniture")
        children = furniture[0].childNodes
        for f in children:
            if f.nodeName == "rectangle":
                x = int(float(f.getAttribute("x")))
                y = int(float(f.getAttribute("y")))
                width = int(float(f.getAttribute("width")))
                height = int(float(f.getAttribute("height")))
                px = x
                for ix in range(width):
                    py = y
                    for iy in range(height):
                        if self.space[px][py] == ' ':
                            self.space[px][py] = 'f'
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
        
        self.areas = list()
        spaces = dom.getElementsByTagName("space")
        for space in spaces:
            sName = str(space.getAttribute("name")).strip()
            self.areas.append(Space(sName))
            children = space.childNodes
            for c in children:
                if c.nodeName == "rectangle":
                    x = str(c.getAttribute("x")).strip()
                    y = str(c.getAttribute("y")).strip()
                    width = str(c.getAttribute("width")).strip()
                    height = str(c.getAttribute("height")).strip()
                    self.areas[-1].add_area(x, y, width, height,
                                            self.max_width, self.max_height)
        #self.print_obj(self.space)
        
        self.sensors = dict()
        sens = dom.getElementsByTagName("sensors")
        children = sens[0].childNodes
        for s in children:
            if s.nodeName in ["motion", "door", "item"]:
                id = str(s.getAttribute("id")).strip()
                x = int(float(s.getAttribute("x")))
                y = int(float(s.getAttribute("y")))
                self.sensors[id] = (x,y)
        
        for x in range(self.max_width):
            for y in range(self.max_height):
                if self.space[x][y] not in ['w', 'f']:
                    self.gr.add_node("%dx%d" % (x,y), [('position', (x,y))])
        
        for x in range(self.max_width):
            for y in range(self.max_height):
                if not self.gr.has_node("%dx%d" % (x,y)):
                    continue
                #print x,y
                coords = self.get_coords_around(x, y)
                for cx,cy,cd in coords:
                    if self.gr.has_node("%dx%d" % (cx,cy)):
                        if not self.gr.has_edge(("%dx%d" % (x,y),"%dx%d" % (cx,cy))):
                            self.gr.add_edge(("%dx%d" % (x,y),"%dx%d" % (cx,cy)),
                                             wt=cd)
        
        
        self.handle_path(5, 5, 30, 10)
        #gdot = dot.write(self.gr)
        #gvv = gv.readstring(gdot)
        #gv.layout(gvv, "neato")
        #gv.render(gvv, "png", "sample_out.png")
        return
    
    def handle_path(self, x1, y1, x2, y2):
        if (x2,y2) in self.paths[x1][y1]:
            return
        start = "%dx%d" % (x1,y1)
        dest = "%dx%d" % (x2,y2)
        if "tree" not in self.paths[x1][y1]:
            (st, sd) = shortest_path(self.gr, start)
            self.paths[x1][y1]["tree"] = st
            self.paths[x1][y1]["dist"] = sd
            #print sd[dest]
            #print st[dest]
        
        path = [dest]
        while path[-1] != start:
            nnode = self.paths[x1][y1]["tree"][path[-1]]
            path.append(nnode)
        
        #self.paths[x2][y2][(x1,y1)] = copy.copy(path)
        path.reverse()
        self.paths[x1][y1][(x2,y2)] = copy.copy(path)
        return
    
    def get_coords_around(self, x, y):
        lst = list()
        #  x -->
        # y 8 1 2
        # | 7 x 3
        # V 6 5 4
        dist_strt = 0.25
        dist_diag = math.sqrt(0.25*0.25 + 0.25*0.25)
        if self.is_valid_coord(x, y-1):     # 1
            lst.append((x, y-1, dist_strt))
        if self.is_valid_coord(x+1, y-1):   # 2
            lst.append((x+1, y-1, dist_diag))
        if self.is_valid_coord(x+1, y):     # 3
            lst.append((x+1, y, dist_strt))
        if self.is_valid_coord(x+1, y+1):   # 4
            lst.append((x+1, y+1, dist_diag))
        if self.is_valid_coord(x, y+1):     # 5
            lst.append((x, y+1, dist_strt))
        if self.is_valid_coord(x-1, y+1):   # 6
            lst.append((x-1, y+1, dist_diag))
        if self.is_valid_coord(x-1, y):     # 7
            lst.append((x-1, y, dist_strt))
        if self.is_valid_coord(x-1, y-1):   # 8
            lst.append((x-1, y-1, dist_diag))
        return lst
    
    def is_valid_coord(self, x, y):
        valid = True
        if x < 0:
            valid = False
        if x >= self.max_width:
            valid = False
        if y < 0:
            valid = False
        if y >= self.max_height:
            valid = False
        return valid
    
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
    
    def generate(self):
        print "Generating environment"
        files = os.listdir(self.file_data)
        total_fast = 0
        for fname in files:
            print fname
            
            self.events = list()
            self.human = list()
            self.annotations = list()
            
            data = open(os.path.join(self.file_data, fname))
            info = data.readlines()
            data.close()
            for line in info:
                self.events.append(Event(line))
            
            torm = []
            for i in range(len(self.events)):
                if self.events[i].annotation != None:
                    self.annotations.append(Annotation(self.events[i].dt, self.events[i].annotation))
                if self.events[i].serial in self.sensors and self.events[i].message in ["ON","ABSENT","PRESENT","OPEN","CLOSE"]:
                    (x,y) = self.sensors[self.events[i].serial]
                    self.events[i].set_xy(x,y)
                else:
                    torm.append(i)
            torm.reverse()
            for i in torm:
                del self.events[i]
            
            self.events.sort()
            self.annotations.sort()
            
            for i in range(len(self.events) - 1):
                skip = 0
                while skip < 3 and (i+1+skip) < len(self.events):
                    if not self.check_events(i, i+1+skip):
                        skip += 1
                    else:
                        break
                while (i+1+skip) >= len(self.events):
                    skip -= 1
                self.events[i].skip = skip
            
            i = 0
            while i < (len(self.events) - 1):
                skip = self.events[i].skip
                d = self.get_event_data(i, i+1+skip)
                if d["speed"] >= self.max_speed:
                    #print d["dt"], d["speed"]
                    #else:
                    print d["dt"], d["speed"], "****"
                    total_fast += 1
                sPerSqr = float(d["delta"])/float(len(d["path"]))
                sqrTd = datetime.timedelta(seconds=sPerSqr)
                self.human.append(PersonEvent(d["dt"],d["x1"],d["y1"],d["speed"]))
                timeNow = copy.copy(d["dt"])
                for spot in d["path"][1:]:
                    xy = str(spot).split("x")
                    px = int(float(xy[0]))
                    py = int(float(xy[1]))
                    timeNow += sqrTd
                    pdt = copy.copy(timeNow)
                    self.human.append(PersonEvent(pdt, px, py, d["speed"]))
                i += 1 + skip
            
#            for i in range(len(self.events) - 1):
#                dt = self.events[i].dt
#                x1 = self.events[i].x
#                y1 = self.events[i].y
#                dt_delta = self.events[i+1].dt - dt
#                delta = float(dt_delta.seconds)
#                delta += float(dt_delta.microseconds) / 1000000.0
#                x2 = self.events[i+1].x
#                y2 = self.events[i+1].y
#                self.handle_path(x1, y1, x2, y2)
#                start = "%dx%d" % (x1,y1)
#                dest = "%dx%d" % (x2,y2)
#                path = self.paths[x1][y1][(x2,y2)]
#                dist = self.paths[x1][y1]["dist"][dest]
#                speed = float(dist)/float(delta)
#                sPerSqr = delta/float(len(path))
#                sqrTd = datetime.timedelta(seconds=sPerSqr)
#                mystr = "%s   " % str(dt)
#                mystr += "%s->%s   " % (self.events[i].serial, self.events[i+1].serial)
#                mystr += "%5s->" % str(start)
#                mystr += "%5s  " % str(dest)
#                mystr += "%f m\t" % dist
#                mystr += "%f s\t" % delta
#                mystr += "%f m/s\t" % speed
#                mystr += "%s\t" % str(len(path))
#                mystr += "%fs/square" % float(sPerSqr)
#                mystr += "  %s" % str(datetime.timedelta(seconds=sPerSqr))
#                if speed > 10.0:
#                    total_fast += 1
#                    mystr += "\t****"
#                print mystr
#                #print "\t",path
#                self.human.append(PersonEvent(dt, x1, y1, speed))
#                timeNow = copy.copy(dt)
#                for spot in path[1:]:
#                    xy = str(spot).split("x")
#                    px = int(float(xy[0]))
#                    py = int(float(xy[1]))
#                    timeNow += sqrTd
#                    pdt = copy.copy(timeNow)
#                    self.human.append(PersonEvent(pdt, px, py, speed))
            
            ai = 0
            for i in range(len(self.human)):
                if ai >= len(self.annotations):
                    continue
                if self.human[i].dt > self.annotations[ai].dt:
                    self.human[i].set_ann(self.annotations[ai].annotation)
                    ai += 1
                elif self.human[i].dt == self.annotations[ai].dt:
                    self.human[i].set_ann(self.annotations[ai].annotation)
                    ai += 1
                elif (i+1) < len(self.human):
                    if self.human[i+1].dt > self.annotations[ai].dt:
                        d1 = abs(self.human[i].dt - self.annotations[ai].dt)
                        d2 = abs(self.human[i+1].dt - self.annotations[ai].dt)
                        if d1 < d2:
                            self.human[i].set_ann(self.annotations[ai].annotation)
                            ai += 1
                else:
                    self.human[i].set_ann(self.annotations[ai].annotation)
                    ai += 1
            
            out = open(os.path.join(self.file_output, "m%s" % fname), 'w')
            for i in range(len(self.human)):
                out.write("%s\n" % str(self.human[i]))
            out.close()
        print "total_fast =",total_fast
        return
    
    def get_event_data(self, i, j):
        data = dict()
        data["dt"] = self.events[i].dt
        data["x1"] = self.events[i].x
        data["y1"] = self.events[i].y
        dt_delta = self.events[j].dt - data["dt"]
        data["delta"] = float(dt_delta.seconds)
        data["delta"] += float(dt_delta.microseconds) / 1000000.0
        data["x2"] = self.events[j].x
        data["y2"] = self.events[j].y
        self.handle_path(data["x1"], data["y1"], data["x2"], data["y2"])
        data["path"] = self.paths[data["x1"]][data["y1"]][(data["x2"],data["y2"])]
        data["dist"] = self.paths[data["x1"]][data["y1"]]["dist"]["%dx%d" % (data["x2"], data["y2"])]
        data["speed"] = float(data["dist"])/float(data["delta"])
        return data
    
    def check_events(self, i, j):
        data = self.get_event_data(i, j)
        if data["speed"] < self.max_speed:
            return True
        return False
    
    def output_results(self):
        outFile = open(self.file_output, 'w')
        outFile.write("<data ")
        outFile.write("filename=\"%s\" >" % self.file_movement)
        for r in self.events:
            outFile.write("%s" % str(r))
        outFile.write("</data>")
        outFile.close()
        return
    
    def run(self):
        self.load_site()
        self.generate()
        #self.output_results()
        return


if __name__ == "__main__":
    print "CAMS Generator"
    parser = optparse.OptionParser(usage="usage: %prog [options]")
    parser.add_option("-s",
                      "--site",
                      dest="site",
                      help="Site configuration file.")
    parser.add_option("-d",
                      "--data",
                      dest="data",
                      help="Directory of files with sensor events.")
    parser.add_option("-o",
                      "--output",
                      dest="output",
                      help="Directory to output resulting movement datasets to.")
    (options, args) = parser.parse_args()
    if None in [options.site, options.data, options.output]:
        if options.site == None:
            print "ERROR: Missing -s / --site"
        if options.data == None:
            print "ERROR: Missing -d / --data"
        if options.output == None:
            print "ERROR: Missing -o / --output"
        parser.print_help()
        sys.exit()
    cams_gn = Generator(options)
    cams_gn.run()

