#!/usr/bin/python
#*****************************************************************************#
#**
#**  WASP Annotation Accuracy Viewer
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
#matplotlib.use('Agg')
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

from CAMS_Emulator import PersonEvent



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
class AnnViewer:
    def __init__(self, options):
        self.file_site = str(options.site)
        self.dir_out = str(options.output)
        self.data_dir = str(options.data)
        self.max_width = 0
        self.max_height = 0
        self.annotations = ["Other"]
        self.moves = list()
        self.space = None
        self.map_weight = None
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
        self.init_map()
        return
    
    def init_map(self):
        self.map_weight = list()
        for x in range(self.max_width):
            self.map_weight.append(list())
            for y in range(self.max_height):
                self.map_weight[x].append(0)
        return
    
    def print_obj(self, obj):
        for y in range(self.max_height):
            out = ""
            for x in range(self.max_width):
                out += "%2s" % obj[x][y]
            print out
        return
    
    def load_movement(self):
        print "Loading Data Files"
        files = os.listdir(self.data_dir)
        for f in files:
            print f
            self.moves.append(list())
            dFile = open(os.path.join(self.data_dir, f))
            mData = dFile.readlines()
            dFile.close()
            
            activeAnn = ""
            prevAnn = ""
            for line in mData:
                if str(line).strip() != "":
                    self.moves[-1].append(PersonEvent(line))
                    if self.moves[-1][-1].annotation != "":
                        tmpAnn = re.sub('-begin|-end', '',
                                        self.moves[-1][-1].annotation)
                        if tmpAnn not in self.annotations:
                            self.annotations.append(tmpAnn)
            activeAnn = ""
            for x in range(len(self.moves[-1]) - 1):
                if self.moves[-1][x].annotation == "":
                    if activeAnn == "":
                        if self.moves[-1][x+1].annotation == "":
                            self.moves[-1][x].annotation = "Other-begin"
                            activeAnn = "Other-begin"
                        else:
                            self.moves[-1][x].annotation = "Other"
                    elif activeAnn == "Other-begin":
                        if self.moves[-1][x+1].annotation != "":
                            self.moves[-1][x].annotation = "Other-end"
                else:
                    if re.search('-begin', self.moves[-1][x].annotation):
                        activeAnn = self.moves[-1][x].annotation
                    elif re.search('-end', self.moves[-1][x].annotation):
                        activeAnn = ""
            
            if self.moves[-1][-1].annotation == "":
                if activeAnn == "":
                    self.moves[-1][-1].annotation = "Other"
                elif activeAnn == "Other-begin":
                    self.moves[-1][-1].annotation = "Other-end"
        
        print "Annotations:",self.annotations
        return
    
    def measure_annotation(self, ann):
        self.init_map()
        annTicks = 0
        totalTicks = 0
        for mf in range(len(self.moves)):
            activeAnn = re.sub('-begin|-end', '', self.moves[mf][0].annotation)
            step = copy.deepcopy(self.moves[mf][0].dt)
            stepper = datetime.timedelta(seconds=0.1)
            t = 0
            while t < len(self.moves[mf]):
                if self.moves[mf][t].annotation != "":
                    activeAnn = re.sub('-begin|-end', '',
                                       self.moves[mf][t].annotation)
                if activeAnn == ann:
                    x = int(float(self.moves[mf][t].x))
                    y = int(float(self.moves[mf][t].y))
                    if x >= self.max_width:
                        x = self.max_width - 1
                    if y >= self.max_height:
                        y = self.max_height - 1
                    self.map_weight[x][y] += 1
                    annTicks += 1
                totalTicks += 1
                
                if t+1 < len(self.moves[mf]):
                    if self.moves[mf][t+1].dt < (step + stepper):
                        t += 1
                    else:
                        step += stepper
                else:
                    t += 1
        print ann, annTicks, totalTicks
        print "\t",float(annTicks)/float(totalTicks)*100.0
        print "\t",self.get_map_max()
        return
    
    def get_map_max(self):
        max = 0
        for x in range(self.max_width):
            for y in range(self.max_height):
                if self.map_weight[x][y] > max:
                    max = self.map_weight[x][y]
        return max
    
    def plot_map(self, filename):
        fig = plt.figure(figsize=(5,7), dpi=128)
        fig.text(0.05, 0.95, str(filename).split('.')[0], 
                 horizontalalignment='left', verticalalignment='top')
        mapMax = self.get_map_max()
        colors = cm.jet(pylab.linspace(0, 1, mapMax))
        for x in range(self.max_width):
            for y in range(self.max_height):
                if self.map_weight[x][y] > 0:
                    plt.plot(x + 1, self.max_height - y, 'o',
                             alpha=float(self.map_weight[x][y] + mapMax/3)/float(mapMax * 1.33),
                             color=colors[self.map_weight[x][y] - 1])
                if self.space[x][y] != ' ':
                    plt.plot(x + 1, self.max_height - y, '.',
                             color='black')
        plt.subplots_adjust(left=0.0, bottom=0.0, right=1.0, top=1.0)
        plt.savefig(os.path.join(self.dir_out, filename))
        plt.close('all')
        return
    
    def run(self):
        self.load_site()
        self.load_movement()
        for ann in self.annotations:
            self.measure_annotation(ann)
            self.plot_map("%s.png" % ann)
            for x in range(self.max_width):
                for y in range(self.max_height):
                    if self.map_weight[x][y] > 2:
                        self.map_weight[x][y] = int(math.log(self.map_weight[x][y]))
                    elif self.map_weight[x][y] > 0:
                        self.map_weight[x][y] = 1
            self.plot_map("%s_log.png" % ann)
        return


if __name__ == "__main__":
    print "Annotation Viewer"
    parser = optparse.OptionParser(usage="usage: %prog [options]")
    parser.add_option("-s",
                      "--site",
                      dest="site",
                      help="Site configuration file.")
    parser.add_option("-d",
                      "--data",
                      dest="data",
                      help="Directory with the movement data files.")
    parser.add_option("-o",
                      "--output",
                      dest="output",
                      help="Directory to output chromosome pictures.")
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
    
    annView = AnnViewer(options)
    annView.run()

