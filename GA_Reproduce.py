#!/usr/bin/python

import copy
import optparse
import random
import re
import sys
import xml.dom.minidom



###############################################################################
#### Chromosome class
###############################################################################
class Chromosome:
    def __init__(self, filename, width, height):
        self.width = int(float(width))
        self.height = int(float(height))
        if filename != "":
            dom = xml.dom.minidom.parse(filename)
            chromo = dom.getElementsByTagName("chromosome")
            self.data = list(str(chromo[0].getAttribute("data")).strip())
            self.fitness = float(chromo[0].getAttribute("fitness"))
            self.generation = int(float(chromo[0].getAttribute("generation")))
        else:
            self.data = list()
            for x in range(self.width * self.height):
                self.data.append("0")
            self.fitness = -1
            self.generation = -1
        self.check = None
        return
    
    def set_check(self, chFunc):
        self.check = chFunc
        return
    
    def set_num(self, num):
        (x,y) = self.get_xy(int(float(num)))
        if self.check(x,y):
            self.data[int(float(num))] = "1"
            return True
        return False
    
    def set_xy(self, x, y):
        if self.check(x,y):
            self.data[self.get_num(x, y)] = "1"
            return True
        return False
    
    def invert_num(self, num):
        (x,y) = self.get_xy(num)
        if self.check(x,y):
            if self.data[num] == "0":
                self.data[num] = "1"
            else:
                self.data[num] = "0"
            return True
        return False
    
    def get_xy(self, number):
        y = int(number/self.width)
        x = number - (y * self.width)
        return (x,y)
    
    def get_num(self, x, y):
        num = x + (y * self.width)
        return num
    
    def get_sensor_count(self):
        count = 0
        for x in range(len(self.data)):
            if self.data[x] == "1":
                count += 1
        return count
    
    def __add__(self, other):
        return
    
    def __cmp__(self, other):
        val = 0
        if self.fitness < other.fitness:
            val = -1
        elif self.fitness > other.fitness:
            val = 1
        return val
    
    def mutate(self):
        num = random.randint(0, len(self.data)-1)
        while not self.invert_num(num):
            num = random.randint(0, len(self.data)-1)
        return
    
    def __str__(self):
        mystr = "<chromosome "
        mystr += "data=\"%s\" " % str("".join(self.data))
        mystr += "fitness=\"%s\" " % str(self.fitness)
        mystr += "generation=\"%s\" " % str(self.generation)
        mystr += "/>"
        return mystr



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
        self.chromosomes = list()
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
    
    def build_seed(self, count):
        spots = range(self.max_width * self.max_height)
        if count > len(spots):
            count = len(spots)
        chrom = Chromosome("", self.max_width, self.max_height)
        chrom.set_check(self.valid_sensor_location)
        for x in range(count):
            num = random.randint(0, len(spots) - 1)
            while not chrom.set_num(spots[num]):
                del spots[num]
                num = random.randint(0, len(spots) - 1)
        return chrom
    
    def load_chromosomes(self):
        return
    
    def breed_children(self):
        return
    
    def run(self):
        self.load_site()
        self.load_chromosomes()
        self.chromosomes.sort()
        self.breed_children()
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
    parser.add_option("-r",
                      "--random",
                      dest="random",
                      help="Random numbers seed.")
    (options, args) = parser.parse_args()
    if None in [options.site, options.chromosome]:
        if options.site == None:
            print "ERROR: Missing -s / --site"
        if options.chromosome == None:
            print "ERROR: Missing -c / --chromosome"
        parser.print_help()
        sys.exit()
    
    if options.random == None:
        random.seed()
    else:
        random.seed(float(options.random))
    
    pobj = Pollinator(options)
    pobj.run()

