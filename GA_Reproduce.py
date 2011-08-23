#!/usr/bin/python

import copy
import optparse
import random
import re
import sys
import xml.dom.minidom

random.seed()


###############################################################################
#### Chromosome class
###############################################################################
class Chromosome:
    def __init__(self, filename, width, height):
        self.width = int(float(width))
        self.height = int(float(height))
        dom = xml.dom.minidom.parse(filename)
        chromo = dom.getElementsByTagName("chromosome")
        self.data = str(chromo[0].getAttribute("data")).strip()
        self.fitness = float(chromo[0].getAttribute("fitness"))
        return
    
    def get_xy(self, number):
        y = int(number/self.width)
        x = number - (y * self.width)
        return (x,y)
    
    def get_num(self, x, y):
        num = x + (y * self.width)
        return num
    
    def __add__(self, other):
        return
    
    def mutate(self):
        found = False
        num = 0
        while not found:
            num = random.randint(0, len(self.data)-1)
        return



###############################################################################
#### Pollinator class
###############################################################################
class Pollinator:
    def __init__(self, options):
        self.file_site = options.site
        self.dir_chromosome = options.chromosome
        self.space = None
        self.max_width = 0
        self.max_height = 0
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
        return
    
    def valid_sensor_location(self, x, y):
        if self.space[x][y] not in ['x','w','l']:
            return True
        return False
    
    def run(self):
        return



if __name__ == "__main__":
    print "GA Reproduction"
    parser = optparse.OptionParser(usage="usage: %prog [options]")
    parser.add_option("-s",
                      "--site",
                      dest="site",
                      help="Site configuration file.")
    parser.add_option("-c",
                      "--chromosome",
                      dest="chromosome",
                      help="Directory with the sensor chromosome definitions.")
    (options, args) = parser.parse_args()
    if None in [options.site, options.chromosome]:
        if options.site == None:
            print "ERROR: Missing -s / --site"
        if options.chromosome == None:
            print "ERROR: Missing -c / --chromosome"
        parser.print_help()
        sys.exit()
    
    pobj = Pollinator(options)
    pobj.run()

