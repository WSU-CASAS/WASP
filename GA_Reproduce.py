#!/usr/bin/python

import copy
import optparse
import os
import random
import re
import shutil
import pgdb
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
            if self.ann[x]['acc'] > 0 and self.ann[x]['avg'] >= 0 and x != "Other":
                if self.ann[x]['acc'] > self.ann[x]['avg']:
                    self.fitness += self.ann[x]['acc'] - self.ann[x]['avg']
                #mul = self.ann[x]['acc'] / self.ann[x]['avg']
                #self.fitness = self.fitness * mul
        self.fitness = self.fitness - (float(str("".join(self.data)).count("1"))/20.0)
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
        self.manager_id = options.manager_id
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
        if options.grid_size != None:
            self.config["grid_size"] = int(float(options.grid_size))
        else:
            self.config["grid_size"] = None
        self.greedy_search = options.greedy_search
        self.space = None
        self.max_width = 0
        self.max_height = 0
        self.chromosomes = list()
        self.children = list()
        self.annotations = list()
        self.mydb = pgdb.connect("", "", "", "", "wasp")
        self.cr = self.mydb.cursor()
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
        if x < len(self.space):
            if y < len(self.space[x]):
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
    
    def build_grid(self, xOff, yOff):
        chrom = Chromosome("", self.max_width, self.max_height)
        chrom.set_check(self.valid_sensor_location)
        for x in range(self.max_width):
            if (x % self.config["grid_size"]) == 0:
                for y in range(self.max_height):
                    if (y % self.config["grid_size"]) == 0:
                        chrom.set_xy(x + xOff, y + yOff)
        #self.print_layout(chrom)
        return chrom
    
    def print_layout(self, chrom):
        for y in range(self.max_height):
            out = ""
            for x in range(self.max_width):
                num = chrom.get_num(x,y)
                if chrom.data[num] == "1":
                    out += "%2s" % chrom.data[num]
                else:
                    out += "%2s" % self.space[x][y]
            print out
        print "\n"
        return
    
    def load_chromosomes(self):
        ann = dict()
        annIds = self.get_annotation_ids()
        query = "SELECT c.genome, "
        if self.greedy_search:
            query += "cg.final_fitness, "
        else:
            query += "c.accuracy, "
        query += "c.cid "
        query += "FROM (chromosome c INNER JOIN chrom_gen cg ON c.cid=cg.cid) "
        query += "INNER JOIN generation g ON cg.gid=g.gid "
        if self.greedy_search:
            query += "WHERE cg.final_fitness IS NOT NULL AND "
        else:
            query += "WHERE c.accuracy<>-1 AND "
        query += "g.gid=%s AND " % str(self.nextgen - 1)
        query += "cg.mid=%s" % self.manager_id
        self.cr.execute(query)
        row = self.cr.fetchone()
        while row != None:
            self.chromosomes.append(Chromosome("", self.max_width,
                                               self.max_height, self.config))
            if not self.greedy_search:
                self.chromosomes[-1].data = list(str(row[0]).strip())
            self.chromosomes[-1].accuracy = float(row[1])
            self.chromosomes[-1].cid = str(row[2]).strip()
            self.chromosomes[-1].generation = self.nextgen - 1
            row = self.cr.fetchone()
        print "chromosomes:",len(self.chromosomes)
        for x in range(len(self.chromosomes)):
            self.chromosomes[x].set_check(self.valid_sensor_location)
            query = "SELECT a.name, ca.tp, ca.fp, ca.tn, ca.fn "
            query += "FROM (chromosome c INNER JOIN chrom_ann ca ON c.cid=ca.cid) "
            query += "INNER JOIN annotation a ON ca.aid=a.aid "
            query += "WHERE c.cid='%s' AND ca.mid='%s'" % (self.chromosomes[x].cid, self.manager_id)
            self.cr.execute(query)
            row = self.cr.fetchone()
            while row != None:
                name = str(row[0]).strip()
                if name not in self.annotations:
                    self.annotations.append(name)
                if name not in ann:
                    ann[name] = 0.0
                self.chromosomes[x].ann[name] = dict()
                self.chromosomes[x].ann[name]['TP'] = float(row[1])
                self.chromosomes[x].ann[name]['FP'] = float(row[2])
                self.chromosomes[x].ann[name]['TN'] = float(row[3])
                self.chromosomes[x].ann[name]['FN'] = float(row[4])
                row = self.cr.fetchone()
            self.chromosomes[x].calculate_accuracies()
            for y in self.chromosomes[x].ann.keys():
                ann[y] += self.chromosomes[x].ann[name]['acc']
        
        gid = str(self.nextgen - 1)
        avg = dict()
        for y in ann.keys():
            avg[y] = ann[y] / float(len(self.chromosomes))
        if not self.greedy_search:
            for x in range(len(self.chromosomes)):
                for y in avg.keys():
                    if y in self.chromosomes[x].ann:
                        self.chromosomes[x].ann[y]['avg'] = avg[y]
                self.chromosomes[x].update_fitness()
                query = "UPDATE chrom_gen SET final_fitness=%f " % self.chromosomes[x].fitness
                query += "WHERE cid=%s AND gid=%s AND mid=%s" % (self.chromosomes[x].cid,
                                                                 gid, self.manager_id)
                self.cr.execute(query)
        self.mydb.commit()
        return
    
    def get_annotation_ids(self):
        anid = dict()
        query = "SELECT aid, name FROM annotation"
        self.cr.execute(query)
        row = self.cr.fetchone()
        while row != None:
            anid[str(row[1]).strip()] = str(row[0]).strip()
            row = self.cr.fetchone()
        return anid
    
    def get_top_annotation_performers(self):
        top = dict()
        top_val = dict()
        for x in self.annotations:
            top[x] = list()
            top_val[x] = 0
        
        for x in range(len(self.chromosomes)):
            for aName in self.annotations:
                val = -1
                if aName in self.chromosomes[x].ann:
                    val = self.chromosomes[x].ann[aName]['acc']
                    if val > top_val[aName]:
                        top[aName] = list()
                        top[aName].append(x)
                        top_val[aName] = val
                    elif val == top_val[aName] and val > 0:
                        top[aName].append(x)
        return top
    
    def breed_children(self):
        r = None
        while r == None:
            query = "SELECT gid FROM generation WHERE gid=%s" % str(self.nextgen)
            self.cr.execute(query)
            r = self.cr.fetchone()
            if r == None:
                query = "INSERT INTO generation (gid) VALUES (nextval('generation_gid_seq'::regclass));"
                self.cr.execute(query)
                self.mydb.commit()
        gid = str(r[0]).strip()
        
        if self.greedy_search:
            bestAnn = self.get_top_annotation_performers()
            myCount = 0
            for ann in self.annotations:
                mylog = open("repo.log",'a')
                mylog.write("%3s\t%6s  %3s\t" % (str(self.nextgen-1),ann,str(len(bestAnn[ann]))))
                for z in bestAnn[ann][:1]:
                    mylog.write("%s " % str(self.chromosomes[z].ann[ann]['acc']))
                mylog.write("\n")
                mylog.close()
                for z in bestAnn[ann][:1]:
                    query = "SELECT genome FROM chromosome WHERE cid='%s'" % self.chromosomes[z].cid
                    self.cr.execute(query)
                    row = self.cr.fetchone()
                    if row != None:
                        self.chromosomes[z].data = list(str(row[0]).strip())
                        myCount += 1
            print "  Children multiplier:",myCount
            myCount = 0
            myTotal = 0
            for x in range(self.max_width):
                myTotal += myCount
                print "x=%3s\tchildren=%6s \ttotal=%s" % (str(x),str(myCount),str(myTotal))
                myCount = 0
                for y in range(self.max_height):
                    if not self.valid_sensor_location(x, y):
                        continue
                    for ann in self.annotations:
                        for z in bestAnn[ann][:1]:
                            num = self.chromosomes[z].get_num(x, y)
                            if self.chromosomes[z].data[num] == "0":
                                myCount += 1
                                chrom = Chromosome("", self.max_width, self.max_height)
                                chrom.set_check(self.valid_sensor_location)
                                chrom.data = copy.deepcopy(self.chromosomes[z].data)
                                chrom.set_xy(x, y)
                                query = "SELECT cid FROM chromosome WHERE "
                                query += "genome='%s'" % str("".join(chrom.data))
                                self.cr.execute(query)
                                r = self.cr.fetchone()
                                if r == None:
                                    try:
                                        query = "INSERT INTO chromosome (genome) VALUES "
                                        query += "('%s')" % ("".join(chrom.data))
                                        self.cr.execute(query)
                                    except pgdb.DatabaseError:
                                        r = None
                                        self.cr = self.mydb.cursor()
                                    query = "SELECT cid FROM chromosome "
                                    query += "WHERE genome='%s'" % "".join(chrom.data)
                                    self.cr.execute(query)
                                    r = self.cr.fetchone()
                                chrom.cid = str(r[0]).strip()
                                query = "SELECT cid FROM chrom_gen WHERE "
                                query += "cid=%s AND gid=%s AND mid=%s" % (chrom.cid, gid, self.manager_id)
                                self.cr.execute(query)
                                if self.cr.rowcount < 1:
                                    query = "INSERT INTO chrom_gen (cid, gid, mid) VALUES "
                                    query += "(%s, %s, %s)" % (str(chrom.cid), gid, self.manager_id)
                                    self.cr.execute(query)
                self.mydb.commit()
        else:
            self.chromosomes.sort(reverse=True)
            survivers = int(len(self.chromosomes) * self.config["survival"])
            for x in range(survivers):
                self.children.append(self.chromosomes[x])
            breeders = int(len(self.chromosomes) * self.config["reproduction"])
            mates = int((len(self.chromosomes) - len(self.children)) / breeders)
            spares = len(self.chromosomes) - (mates * breeders)
            for x in range(breeders):
                turns = mates
                if x > breeders/2:
                    turns = int(mates + (x - breeders/2))
                elif x < breeders/2:
                    turns = int(mates - (breeders/2 - x))
                if x < spares:
                    turns += 1
                for y in range(turns):
                    is_valid = False
                    while not is_valid:
                        nchild = self.chromosomes[x] + self.chromosomes[random.randint(0,breeders)]
                        query = "SELECT count(*) FROM chromosome WHERE "
                        query += "genome='%s'" % str("".join(nchild.data))
                        self.cr.execute(query)
                        r = self.cr.fetchone()
                        if str(r[0]) == "0":
                            is_valid = True
                            query = "INSERT INTO chromosome (genome) VALUES "
                            query += "('%s')" % ("".join(nchild.data))
                            self.cr.execute(query)
                            query = "SELECT cid FROM chromosome "
                            query += "WHERE genome='%s'" % "".join(nchild.data)
                            self.cr.execute(query)
                            r = self.cr.fetchone()
                            nchild.cid = str(r[0]).strip()
                            self.children.append(nchild)
            self.mydb.commit()
            
            if self.population != None:
                while len(self.children) > float(self.population):
                    self.children.pop()
            else:
                while len(self.children) > len(self.chromosomes):
                    self.children.pop()
            
            for x in range(len(self.children)):
                query = "INSERT INTO chrom_gen (cid, gid, mid) VALUES "
                query += "(%s, %s, %s)" % (str(self.children[x].cid), gid, self.manager_id)
                self.cr.execute(query)
        self.mydb.commit()
        return
    
    def insert_chromosome(self, chromo, gid):
        query = "SELECT cid FROM chromosome WHERE genome='%s'" % "".join(chromo.data)
        self.cr.execute(query)
        if self.cr.rowcount < 1:
            query = "INSERT INTO chromosome (genome) VALUES "
            query += "('%s')" % ("".join(chromo.data))
            self.cr.execute(query)
            self.mydb.commit()
            query = "SELECT cid FROM chromosome WHERE genome='%s'" % "".join(chromo.data)
            self.cr.execute(query)
        row = self.cr.fetchone()
        cid = str(row[0]).strip()
        query = "SELECT cid FROM chrom_gen WHERE "
        query += "cid=%s AND gid=%s AND mid=%s" % (cid, str(gid), self.manager_id)
        self.cr.execute(query)
        if self.cr.rowcount < 1:
            query = "INSERT INTO chrom_gen (cid, gid, mid) VALUES "
            query += "(%s, %s, %s)" % (str(cid), str(gid), self.manager_id)
            self.cr.execute(query)
            self.mydb.commit()
        return
    
    def run(self):
        self.load_site()
        if self.seed == None:
            self.load_chromosomes()
            self.breed_children()
        else:
            query = "SELECT gid FROM generation WHERE gid=1"
            self.cr.execute(query)
            r = self.cr.fetchone()
            if r == None:
                query = "INSERT INTO generation (gid) VALUES (nextval('generation_gid_seq'::regclass))"
                self.cr.execute(query)
                self.mydb.commit()
                query = "SELECT gid FROM generation WHERE gid=1"
                self.cr.execute(query)
                r = self.cr.fetchone()
            gid = str(r[0]).strip()
            
            if self.greedy_search:
                for x in range(self.max_width):
                    for y in range(self.max_height):
                        if self.valid_sensor_location(x, y):
                            chromo = Chromosome("", self.max_width, self.max_height)
                            chromo.set_check(self.valid_sensor_location)
                            chromo.set_xy(x, y)
                            self.insert_chromosome(chromo, gid)
            elif self.config["grid_size"] != None:
                for xOff in range(self.config["grid_size"]):
                    for yOff in range(self.config["grid_size"]):
                        chromo = self.build_grid(xOff, yOff)
                        self.insert_chromosome(chromo, gid)
                self.mydb.commit()
            else:
                for x in range(int(float(self.seed))):
                    chromo = self.build_seed(self.config["seed_size"])
                    self.insert_chromosome(chromo, gid)
                self.mydb.commit()
        return



if __name__ == "__main__":
    print "GA Reproduction"
    parser = optparse.OptionParser(usage="usage: %prog [options]")
    parser.add_option("-s",
                      "--site",
                      dest="site",
                      help="Site configuration file.")
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
    parser.add_option("-m",
                      "--manager_id",
                      dest="manager_id",
                      help="Manager id from the DB.")
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
    parser.add_option("--grid_size",
                      dest="grid_size",
                      help="Size of grid of sensors to test on layout.")
    parser.add_option("--greedy_search",
                      dest="greedy_search",
                      help="Perform greedy search over layout.",
                      action="store_true",
                      default=False)
    (options, args) = parser.parse_args()
    if None in [options.site, options.generation]:
        if options.site == None:
            print "ERROR: Missing -s / --site"
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

