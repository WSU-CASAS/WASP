#!/usr/bin/python
#*****************************************************************************#
#**
#**  WASP Chromosome Viewer
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

import matplotlib
matplotlib.use('Agg')
import pylab
import matplotlib.cm as cm
import matplotlib.pyplot as plt
import ConfigParser
import copy
import datetime
import math
import optparse
import os
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
            if self.state == "OFF":
                self.state = "ON"
                self.add_event(pevent.dt, self.id, self.state, pevent)
            self.last_motion = pevent.dt
        else:
            if self.state == "ON":
                if (pevent.dt - self.last_motion) >= datetime.timedelta(0,2.5):
                    self.state = "OFF"
                    self.add_event(pevent.dt, self.id, self.state, pevent)
        return


###############################################################################
#### ChromViewer class
###############################################################################
class ChromViewer:
    def __init__(self, options, cDir):
        self.file_site = str(options.site)
        self.dir_chromosome = cDir
        self.dir_out = str(options.directory)
        self.max_width = 0
        self.max_height = 0
        self.space = None
        self.areas = None
        self.sensors = None
        self.sensor_view = None
        self.sensor_map = None
        self.map_weight = None
        self.regen_pics = options.regen_all
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
        self.map_weight = list()
        for x in range(self.max_width):
            self.map_weight.append(list())
            for y in range(self.max_height):
                self.map_weight[x].append(0)
        return
    
    def load_chromosome(self, chrom_file):
        dom = xml.dom.minidom.parse(chrom_file)
        chromo = dom.getElementsByTagName("chromosome")
        cData = str(chromo[0].getAttribute("data"))
        senId = 0
        
        self.sensors = list()
        self.sensor_view = list()
        for x in range(self.max_width):
            self.sensor_view.append(list())
            for y in range(self.max_height):
                self.sensor_view[x].append(list())
        
        self.sensor_map = copy.deepcopy(self.space)
        
        #self.print_obj(self.space)
        for x in range(self.max_width):
            for y in range(self.max_height):
                if cData[x + (y*self.max_width)] == '1':
                    self.sensors.append(MotionSensor(senId, x, y))
                    #self.space[x][y] = str(senId)
                    #self.sensor_view[x][y].append(str(senId))
                    self.sensor_map[x][y] = str(senId)
                    self.map_weight[x][y] += 1
                    #self.spread_sensor(senId, x, y)
                    senId += 1
        
        #for x in range(len(self.sensors)):
        #    self.sensors[x].set_event_func(self.add_sensor_event)
        
        #self.print_obj(self.sensor_map)
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
    
    def add_sensor_event(self, dt, serial, message, pevent):
        self.events.append(Event(dt, serial, message, pevent))
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
    
    def run(self, outFile=None):
        if not self.regen_pics:
            if os.path.isfile(os.path.join(self.dir_out, outFile)):
                return
        self.load_site()
        files = os.listdir(self.dir_chromosome)
        for f in files:
            fname = os.path.join(self.dir_chromosome, f)
            self.load_chromosome(fname)
        #self.print_obj(self.map_weight)
        fig = plt.figure(figsize=(5,7), dpi=128)
        fig.text(0.05, 0.95, str(outFile).split('.')[0], horizontalalignment='left', verticalalignment='top')
        colors = cm.jet(pylab.linspace(0, 1, len(files)))
        for x in range(self.max_width):
            for y in range(self.max_height):
                if self.map_weight[x][y] > 0:
                    plt.plot(x + 1, self.max_height - y, 'o',
                             alpha=float(self.map_weight[x][y] + len(files)/3)/float(len(files) * 1.33),
                             color=colors[self.map_weight[x][y] - 1])
                if self.space[x][y] != ' ':
                    plt.plot(x + 1, self.max_height - y, 's',
                             color='black')
        plt.subplots_adjust(left=0.0, bottom=0.0, right=1.0, top=1.0)
        plt.savefig(os.path.join(self.dir_out, outFile))
        #plt.show()
        plt.close('all')
        
        self.map_weight = None
        self.areas = None
        self.sensor_map = None
        self.sensor_view = None
        self.space = None
        return


if __name__ == "__main__":
    print "Chromosome Viewer"
    parser = optparse.OptionParser(usage="usage: %prog [options]")
    parser.add_option("-s",
                      "--site",
                      dest="site",
                      help="Site configuration file.")
    parser.add_option("-c",
                      "--chromosome",
                      dest="chromosome",
                      help="File with the sensor chromosome definition.")
    parser.add_option("-d",
                      "--directory",
                      dest="directory",
                      help="Directory to output chromosome pictures.")
    parser.add_option("-r",
                      "--regen_all",
                      dest="regen_all",
                      action="store_true",
                      help="Force regeneration of all images.",
                      default=False)
    (options, args) = parser.parse_args()
    if None in [options.site, options.chromosome, options.directory]:
        if options.site == None:
            print "ERROR: Missing -s / --site"
        if options.chromosome == None:
            print "ERROR: Missing -c / --chromosome"
        if options.directory == None:
            print "ERROR: Missing -d / --directory"
        parser.print_help()
        sys.exit()
    gen = 0
    while os.path.isdir(os.path.join(options.chromosome, str(gen))):
        print options.chromosome,gen
        cams_em = ChromViewer(options, os.path.join(options.chromosome, str(gen)))
        cams_em.run("%s.png" % str(gen))
        cams_em = None
        gen += 1
    

