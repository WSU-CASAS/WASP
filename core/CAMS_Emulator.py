#!/usr/bin/python

import ConfigParser
import datetime
import math
import optparse
import pprint
import re
import sys
import xml.dom.minidom



class Sensor:
    def __init__(self):
        return

class MotionSensor(Sensor):
    def __init__(self):
        return


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
        return
    
    def load_chromosome(self):
        fileIn = open(self.file_chromosome)
        cData = fileIn.readlines()
        fileIn.close()
        senId = 0
        
        self.sensors = list()
        self.sensor_view = list()
        for x in range(self.max_width):
            self.sensors.append(list())
            self.sensor_view.append(list())
            for y in range(self.max_height):
                self.sensors[x].append(' ')
                self.sensor_view[x].append(list())
        
        for x in range(self.max_width):
            for y in range(self.max_height):
                if cData[y][x] == '1':
                    self.sensors[x][y] = str(senId)
                    self.space[x][y] = str(senId)
                    self.sensor_view[x][y].append(str(senId))
                    self.spread_sensor(senId, x, y)
                    senId += 1
        
        self.print_obj(self.space)
        #self.print_obj(self.sensors)
        self.print_view()
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
                    if self.space[saX][saY] == ' ':
                        self.space[saX][saY] = str(id)
                    if str(id) not in self.sensor_view[saX][saY]:
                        self.sensor_view[saX][saY].append(str(id))
                else:
                    break
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
        return
    
    def output_results(self):
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

