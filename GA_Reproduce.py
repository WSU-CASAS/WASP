#!/usr/bin/python

import copy
import optparse
import os
import random
import re
import shutil
import sqlite3
import sys
import uuid
import xml.dom.minidom



###############################################################################
#### Chromosome class
###############################################################################
class Chromosome:
    def __init__(self, filename, width, height, config=dict()):
        self.width = int(float(width))
        self.height = int(float(height))
        self.config = config
        self.filename = filename
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
        child = Chromosome("", self.width, self.height, self.config)
        child.set_check(self.check)
        valid_child = False
        while not valid_child:
            points = list()
            for x in range(self.config["crossover"]):
                r = random.randint(1, len(self.data) - 2)
                while r in points:
                    r = random.randint(1, len(self.data) - 2)
                points.append(r)
            points.append(0)
            points.append(len(self.data))
            points.sort()
            child.data = list()
            for x in range(len(points) - 1):
                if (x % 2) == 0:
                    child.data = list(child.data + self.data[points[x]:points[x+1]])
                else:
                    child.data = list(child.data + other.data[points[x]:points[x+1]])
            child.mutate()
            if self.config["size_limit"] != None:
                if str("".join(self.data)).count("1") <= self.config["size_limit"]:
                    valid_child = True
            else:
                valid_child = True
        return child
    
    def __cmp__(self, other):
        myf = self.fitness - (float(str("".join(self.data)).count("1"))/10.0)
        otf = other.fitness - (float(str("".join(other.data)).count("1"))/10.0)
        val = 0
        if myf < otf:
            val = -1
        elif myf > otf:
            val = 1
        return val
    
    def mutate(self):
        for x in range(len(self.data)):
            num = random.random()
            if num < self.config["mutation"]:
                self.invert_num(x)
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
        self.dir_nextgen = options.directory
        self.nextgen = int(float(options.generation))
        self.seed = options.seed
        self.population = options.population
        self.config = dict()
        self.config["mutation"] = float(options.mutation_rate)
        self.config["crossover"] = int(float(options.crossover))
        self.config["survival"] = float(options.survival_rate)
        self.config["reproduction"] = float(options.reproduction_rate)
        self.config["seed_size"] = int(float(options.seed_size))
        if options.size_limit != None:
            self.config["size_limit"] = int(float(options.size_limit))
        else:
            self.config["size_limit"] = None
        self.space = None
        self.max_width = 0
        self.max_height = 0
        self.chromosomes = list()
        self.children = list()
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
        chromoFiles = os.listdir(self.dir_chromosome)
        for cFile in chromoFiles:
            self.chromosomes.append(Chromosome(os.path.join(self.dir_chromosome, cFile),
                                               self.max_width, self.max_height,
                                               self.config))
        for x in range(len(self.chromosomes)):
            self.chromosomes[x].set_check(self.valid_sensor_location)
        return
    
    def breed_children(self):
        conn = sqlite3.connect(os.path.join(self.dir_chromosome, "../../dna.db"))
        cr = conn.cursor()
        for x in range(len(self.chromosomes)):
            query = "UPDATE dna SET fitness=%f " % self.chromosomes[x].fitness
            query += "WHERE id='%s'" % os.path.basename(self.chromosomes[x].filename)
            cr.execute(query)
        conn.commit()
        self.chromosomes.sort(reverse=True)
        survivers = int(len(self.chromosomes) * self.config["survival"])
        for x in range(survivers):
            self.children.append(self.chromosomes[x])
        breeders = int(len(self.chromosomes) * self.config["reproduction"])
        mates = int((len(self.chromosomes) - len(self.children)) / breeders)
        spares = len(self.chromosomes) - (mates * breeders)
        
        for x in range(breeders):
            turns = mates
            if x < spares:
                turns += 1
            for y in range(turns):
                is_valid = False
                while not is_valid:
                    nchild = self.chromosomes[x] + self.chromosomes[x+y]
                    query = "SELECT count(*) FROM dna WHERE "
                    query += "chromosome='%s'" % str("".join(nchild.data))
                    cr.execute(query)
                    r = cr.fetchone()
                    if str(r[0]) == "0":
                        is_valid = True
                        cname = "%s.xml" % str(uuid.uuid4().hex)
                        fname = os.path.join(self.dir_nextgen, cname)
                        nchild.filename = fname
                        query = "INSERT INTO dna (id, chromosome, generation) VALUES "
                        query += "('%s', '%s', %s)" % (cname, "".join(nchild.data), self.nextgen)
                        cr.execute(query)
                        conn.commit()
                        self.children.append(nchild)
        
        if self.population != None:
            while len(self.children) > float(self.population):
                self.children.pop()
        else:
            while len(self.children) > len(self.chromosomes):
                self.children.pop()
        
        for x in range(len(self.children)):
            if self.children[x].generation == -1:
                self.children[x].generation = self.nextgen
                fname = self.children[x].filename
                out = open(fname, 'w')
                out.write(str(self.children[x]))
                out.close()
            else:
                shutil.copy(self.children[x].filename, self.dir_nextgen)
        conn.commit()
        cr.close()
        conn.close()
        return
    
    def run(self):
        self.load_site()
        if self.seed == None:
            self.load_chromosomes()
            self.chromosomes.sort()
            self.breed_children()
        else:
            conn = sqlite3.connect(os.path.join(self.dir_chromosome, "../../dna.db"))
            cr = conn.cursor()
            for x in range(int(float(self.seed))):
                chromo = self.build_seed(self.config["seed_size"])
                chromo.generation = 0
                cfile = "%s.xml" % str(uuid.uuid4().hex)
                fname = os.path.join(self.dir_nextgen, cfile)
                out = open(fname, 'w')
                out.write(str(chromo))
                out.close()
                query = "INSERT INTO dna (id, chromosome, generation) VALUES "
                query += "('%s', '%s', %s)" % (cfile, "".join(chromo.data), chromo.generation)
                cr.execute(query)
            conn.commit()
            cr.close()
            conn.close()
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
    parser.add_option("-d",
                      "--directory",
                      dest="directory",
                      help="Directory for next generation of chromosomes.")
    parser.add_option("-g",
                      "--generation",
                      dest="generation",
                      help="Value for next generation.")
    parser.add_option("--seed",
                      dest="seed",
                      help="Size of new seed population.")
    parser.add_option("-r",
                      "--random",
                      dest="random",
                      help="Random numbers seed.")
    parser.add_option("--mutation_rate",
                      dest="mutation_rate",
                      help="Rate of mutation in new chromosomes.",
                      default="0.005")
    parser.add_option("--crossover",
                      dest="crossover",
                      help="Number of folds in reproduction.",
                      default="1")
    parser.add_option("--survival_rate",
                      dest="survival_rate",
                      help="Percent of parents that survive into next generation.",
                      default="0.10")
    parser.add_option("--reproduction_rate",
                      dest="reproduction_rate",
                      help="Percent of parents that get to reproduce.",
                      default="0.25")
    parser.add_option("--seed_size",
                      dest="seed_size",
                      help="Number of sensors to seed with.",
                      default="10")
    parser.add_option("--size_limit",
                      dest="size_limit",
                      help="Put a limit on number of sensors.")
    parser.add_option("--population",
                      dest="population",
                      help="Size limit of the population.")
    (options, args) = parser.parse_args()
    if None in [options.site, options.chromosome, options.directory, options.generation]:
        if options.site == None:
            print "ERROR: Missing -s / --site"
        if options.chromosome == None:
            print "ERROR: Missing -c / --chromosome"
        if options.directory == None:
            print "ERROR: Missing -d / --directory"
        if options.generation == None:
            print "ERROR: Missing -g / --generation"
        parser.print_help()
        sys.exit()
    
    if options.random == None:
        random.seed()
    else:
        random.seed(float(options.random))
    
    pobj = Pollinator(options)
    pobj.run()

