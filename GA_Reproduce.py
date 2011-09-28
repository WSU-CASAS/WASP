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
        self.info = ""
        self.cid = ""
        self.accuracy = -1
        self.ann = dict()
        if filename != "":
            dom = xml.dom.minidom.parse(filename)
            chromo = dom.getElementsByTagName("chromosome")
            self.data = list(str(chromo[0].getAttribute("data")).strip())
            self.fitness = float(chromo[0].getAttribute("fitness"))
            self.generation = int(float(chromo[0].getAttribute("generation")))
            if chromo[0].hasAttribute("info"):
                self.info = str(chromo[0].getAttribute("info"))
        else:
            self.data = list()
            for x in range(self.width * self.height):
                self.data.append("0")
            self.fitness = -1
            self.generation = -1
        self.check = None
        return
    
    def calculate_accuracies(self):
        for x in self.ann.keys():
            pos = float(self.ann[x]['TP'] + self.ann[x]['FN'])
            neg = float(self.ann[x]['FP'] + self.ann[x]['TN'])
            tpr = 0.0
            if pos > 0:
                tpr = float(self.ann[x]['TP']) / pos
            fpr = 0.0
            if neg > 0:
                fpr = float(self.ann[x]['FP']) / neg
            acc = (tpr - fpr) * 100.0
            self.ann[x]['acc'] = acc
            self.ann[x]['avg'] = acc
        return
    
    def update_fitness(self):
        self.fitness = float(self.accuracy)
        for x in self.ann.keys():
            if self.ann[x]['acc'] != 0 and self.ann[x]['avg'] != 0 and x != "Other":
                mul = self.ann[x]['acc'] / self.ann[x]['avg']
                self.fitness = self.fitness * mul
        self.fitness = self.fitness - (float(str("".join(self.data)).count("1"))/10.0)
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
        val = 0
        if self.fitness < other.fitness:
            val = -1
        elif self.fitness > other.fitness:
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
        mystr += "info=\"%s\" " % str(self.info)
        mystr += "/>"
        return mystr



###############################################################################
#### Pollinator class
###############################################################################
class Pollinator:
    def __init__(self, options):
        self.file_site = options.site
        self.chromDB = options.chromosome
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
        ann = dict()
        conn = sqlite3.connect(self.chromDB)
        cr = conn.cursor()
        query = "SELECT c.genome, c.accuracy, c.cid "
        query += "FROM (chromosome c INNER JOIN chrom_gens cg ON c.cid=cg.cid) "
        query += "INNER JOIN generations g ON cg.gid=g.gid "
        query += "WHERE g.gen=%s" % str(self.nextgen - 1)
        cr.execute(query)
        row = cr.fetchone()
        while row != None:
            self.chromosomes.append(Chromosome("", self.max_width,
                                               self.max_height, self.config))
            self.chromosomes[-1].data = list(str(row[0]).strip())
            self.chromosomes[-1].accuracy = float(row[1])
            self.chromosomes[-1].cid = str(row[2]).strip()
            self.chromosomes[-1].generation = self.nextgen - 1
            row = cr.fetchone()
        
        for x in range(len(self.chromosomes)):
            self.chromosomes[x].set_check(self.valid_sensor_location)
            query = "SELECT a.name, ca.tp, ca.fp, ca.tn, ca.fn "
            query += "FROM (chromosome c INNER JOIN chrom_anns ca ON c.cid=ca.cid) "
            query += "INNER JOIN annotations a ON ca.aid=a.aid "
            query += "WHERE c.cid='%s'" % self.chromosomes[x].cid
            cr.execute(query)
            row = cr.fetchone()
            while row != None:
                name = str(row[0]).strip()
                if name not in ann:
                    ann[name] = 0.0
                self.chromosomes[x].ann[name] = dict()
                self.chromosomes[x].ann[name]['TP'] = float(row[1])
                self.chromosomes[x].ann[name]['FP'] = float(row[2])
                self.chromosomes[x].ann[name]['TN'] = float(row[3])
                self.chromosomes[x].ann[name]['FN'] = float(row[4])
                row = cr.fetchone()
            self.chromosomes[x].calculate_accuracies()
            for y in ann.keys():
                ann[y] += self.chromosomes[x].ann[name]['acc']
        
        query = "SELECT gid FROM generations WHERE gen=%s" % str(self.nextgen - 1)
        cr.execute(query)
        r = cr.fetchone()
        gid = str(r[0]).strip()
        avg = dict()
        for y in ann.keys():
            avg[y] = ann[y] / float(len(self.chromosomes))
        for x in range(len(self.chromosomes)):
            for y in avg.keys():
                self.chromosomes[x].ann[y]['avg'] = avg[y]
            self.chromosomes[x].update_fitness()
            query = "UPDATE chrom_gens SET final_fitness=%f " % self.chromosomes[x].fitness
            query += "WHERE cid=%s AND gid=%s" % (self.chromosomes[x].cid, gid)
            cr.execute(query)
        conn.commit()
        cr.close()
        conn.close()
        return
    
    def breed_children(self):
        self.chromosomes.sort(reverse=True)
        survivers = int(len(self.chromosomes) * self.config["survival"])
        for x in range(survivers):
            self.children.append(self.chromosomes[x])
        breeders = int(len(self.chromosomes) * self.config["reproduction"])
        mates = int((len(self.chromosomes) - len(self.children)) / breeders)
        spares = len(self.chromosomes) - (mates * breeders)
        
        conn = sqlite3.connect(self.chromDB)
        cr = conn.cursor()
        query = "INSERT INTO generations (gen) VALUES (%s)" % str(self.nextgen)
        cr.execute(query)
        conn.commit()
        query = "SELECT gid FROM generations WHERE gen=%s" % str(self.nextgen)
        cr.execute(query)
        r = cr.fetchone()
        gid = str(r[0]).strip()
        
        for x in range(breeders):
            turns = mates
            if x < spares:
                turns += 1
            for y in range(turns):
                is_valid = False
                while not is_valid:
                    nchild = self.chromosomes[x] + self.chromosomes[x+y]
                    query = "SELECT count(*) FROM chromosome WHERE "
                    query += "genome='%s'" % str("".join(nchild.data))
                    cr.execute(query)
                    r = cr.fetchone()
                    if str(r[0]) == "0":
                        is_valid = True
                        uid = str(uuid.uuid4().hex)
                        query = "INSERT INTO chromosome (genome, uuid) VALUES "
                        query += "('%s', '%s')" % ("".join(nchild.data), uid)
                        cr.execute(query)
                        conn.commit()
                        query = "SELECT cid FROM chromosome "
                        query += "WHERE uuid='%s'" % uid
                        cr.execute(query)
                        r = cr.fetchone()
                        nchild.cid = str(r[0]).strip()
                        self.children.append(nchild)
        
        if self.population != None:
            while len(self.children) > float(self.population):
                self.children.pop()
        else:
            while len(self.children) > len(self.chromosomes):
                self.children.pop()
        
        for x in range(len(self.children)):
            query = "INSERT INTO chrom_gens (cid, gid) VALUES "
            query += "(%s, %s)" % (str(self.children[x].cid), gid)
            cr.execute(query)
        conn.commit()
        cr.close()
        conn.close()
        return
    
    def run(self):
        self.load_site()
        if self.seed == None:
            self.load_chromosomes()
            self.breed_children()
        else:
            conn = sqlite3.connect(self.chromDB)
            cr = conn.cursor()
            query = "INSERT INTO generations (gen) VALUES (0)"
            cr.execute(query)
            query = "SELECT gid FROM generations WHERE gen=0"
            cr.execute(query)
            r = cr.fetchone()
            gid = r[0]
            for x in range(int(float(self.seed))):
                chromo = self.build_seed(self.config["seed_size"])
                cuuid = str(uuid.uuid4().hex)
                query = "INSERT INTO chromosome (genome, uuid) VALUES "
                query += "('%s', '%s')" % ("".join(chromo.data), cuuid)
                cr.execute(query)
                query = "SELECT cid FROM chromosome WHERE uuid='%s'" % cuuid
                cr.execute(query)
                row = cr.fetchone()
                cid = row[0]
                query = "INSERT INTO chrom_gens (cid, gid) VALUES "
                query += "(%s, %s)" % (str(cid), str(gid))
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
                      help="SQLite3 database with the sensor chromosome definitions.")
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
    if None in [options.site, options.chromosome, options.generation]:
        if options.site == None:
            print "ERROR: Missing -s / --site"
        if options.chromosome == None:
            print "ERROR: Missing -c / --chromosome"
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

