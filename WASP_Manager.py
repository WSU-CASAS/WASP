#*****************************************************************************#
#**
#**  WASP Manager
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

import xmpp

import collections
import datetime
import optparse
import os
import random
import re
import shutil
import pgdb
import subprocess
import sys
import time
import uuid
import xml.dom.minidom

from GA_Reproduce import Chromosome



class Manager:
    def __init__(self, options):
        self.name = "WASP Manager"
        self.username = str(options.jid)
        self.password = str(options.password)
        self.directory = str(options.dir)
        self.data_dir = str(options.data)
        self.orig_dir = str(options.orig)
        self.site = os.path.join(self.directory, "site.xml")
        self.boss = str(options.boss)
        self.pypath = str(options.pypath)
        self.generation = int(float(options.generation))
        self.population = int(float(options.population))
        self.mutation_rate = float(options.mutation_rate)
        self.crossover = int(float(options.crossover))
        self.survival_rate = float(options.survival_rate)
        self.reproduction_rate = float(options.reproduction_rate)
        self.seed_size = options.seed_size
        self.size_limit = options.size_limit
        self.max_generations = options.max_generations
        self.grid_size = options.grid_size
        self.greedy_search = options.greedy_search
        self.manager_id = 0
        self.quit_on_generation = False
        self.xmpp = xmpp.Connection(self.name)
        self.xmpp.set_authd_callback(self.has_connected)
        self.xmpp.set_direct_msg_callback(self.message)
        self.xmpp.set_finish_callback(self.finish)
        self.run_id = "run42" #str(uuid.uuid4().hex)
        self.running_jobs = 0
        self.work_this_gen = 0
        self.max_work_per_gen = 50000
        self.last_gen = datetime.datetime.now()
        self.last_job = datetime.datetime.now()
        dom = xml.dom.minidom.parse(self.site)
        site = dom.getElementsByTagName("site")
        self.max_width = int(float(site[0].getAttribute("max_width")))
        self.max_height = int(float(site[0].getAttribute("max_height")))
        self.ann_cache = dict()
        self.p = None
        self.completed_jobs = collections.deque()
        
        self.mydb = pgdb.connect("", "", "", "", "wasp")
        self.cr = self.mydb.cursor()
        self.get_manager_id()
        
        found = False
        if self.generation > 0:
            query = "SELECT g.gid FROM generation g INNER JOIN chrom_gen cg "
            query += "ON g.gid=cg.gid INNER JOIN chromosome c ON c.cid=cg.cid "
            query += "WHERE cg.mid=%s " % self.manager_id
            if not self.greedy_search:
                #query += "AND cg.final_fitness IS NOT NULL "
                #else:
                query += "AND c.accuracy<>-1 "
            query += "ORDER BY g.gid DESC LIMIT 1"
            self.cr.execute(query)
            r = self.cr.fetchone()
            if r != None:
                found = True
                self.generation = int(float(r[0]))
        if not found:
            self.generation = 1
            cmd = "%s GA_Reproduce.py " % self.pypath
            cmd += "-s %s " % os.path.join(self.directory, "site.xml")
            cmd += "-r %f " % random.random()
            cmd += "-g %s " % str(self.generation)
            cmd += "-m %s " % self.manager_id
            cmd += "--seed=%s " % str(self.population)
            if self.seed_size != None:
                cmd += "--seed_size=%s " % str(self.seed_size)
            if self.size_limit != None:
                cmd += "--size_limit=%s " % str(self.size_limit)
            if self.grid_size != None:
                cmd += "--grid_size=%s " % str(self.grid_size)
            if self.greedy_search:
                cmd += "--greedy_search "
            cmd = str(cmd).strip()
            print cmd
            subprocess.call(str(cmd).split())
        self.has_set_auto = False
        return
    
    def connect(self):
        self.xmpp.connect(self.username, self.password)
        return
    
    def has_connected(self):
        self.xmpp.callLater(1, self.send_files)
        if not self.has_set_auto:
            self.has_set_auto = True
            self.xmpp.callLater(900, self.auto_refresh_jobs)
            self.xmpp.callLater(2, self.load_completed_jobs)
        return
    
    def finish(self):
        self.xmpp.disconnect()
        return
    
    def get_manager_id(self):
        query = "SELECT mid FROM manager WHERE "
        query += "dir_work='%s' AND " % self.directory
        query += "dir_data='%s' AND " % self.data_dir
        query += "dir_orig='%s' AND " % self.orig_dir
        query += "site_config='%s' AND " % self.site
        query += "population='%s' AND " % str(self.population)
        query += "crossover='%s' AND " % str(self.crossover)
        query += "mutation_rate='%s' AND " % str(self.mutation_rate)
        query += "survival_rate='%s' AND " % str(self.survival_rate)
        query += "reproduction_rate='%s' AND " % str(self.reproduction_rate)
        query += "seed_size='%s' AND " % str(self.seed_size)
        query += "max_generation='%s'" % str(self.max_generations)
        print query
        self.cr.execute(query)
        row = self.cr.fetchone()
        if row == None:
            query = "INSERT INTO manager (dir_work, dir_data, dir_orig, site_config, "
            query += "population, crossover, mutation_rate, survival_rate, "
            query += "reproduction_rate, seed_size, max_generation) VALUES "
            query += "('%s', '%s', '%s', '%s', " % (self.directory,
                                                    self.data_dir,
                                                    self.orig_dir,
                                                    self.site)
            query += "%s, %s, %s, %s, %s, %s, %s);" % (str(self.population),
                                                       str(self.crossover),
                                                       str(self.mutation_rate),
                                                       str(self.survival_rate),
                                                       str(self.reproduction_rate),
                                                       str(self.seed_size),
                                                       str(self.max_generations))
            print query
            self.cr.execute(query)
            self.mydb.commit()
            time.sleep(1)
            self.get_manager_id()
        else:
            self.manager_id = str(row[0]).strip()
        return
    
    def send_files(self):
        msg = "<send_file "
        msg += "filename=\"site.xml\" " 
        msg += "run_id=\"%s\" >" % self.run_id
        data = open(self.site)
        info = data.readlines()
        msg += "".join(info)
        data.close()
        msg += "</send_file>"
        self.xmpp.send(msg, self.boss)
        
        dFiles = os.listdir(self.data_dir)
        dFiles.sort()
        oFiles = os.listdir(self.orig_dir)
        oFiles.sort()
        for dfile in dFiles:
            msg = "<send_file "
            msg += "filename=\"%s\" " % dfile
            msg += "run_id=\"%s\" >" % self.run_id
            data = open(os.path.join(self.data_dir, dfile))
            info = data.readlines()
            msg += "".join(info)
            data.close()
            msg += "</send_file>"
            #self.xmpp.send(msg, self.boss)
        
        for dfile in oFiles:
            msg = "<send_file "
            msg += "filename=\"%s\" " % dfile
            msg += "run_id=\"%s\" >" % self.run_id
            data = open(os.path.join(self.orig_dir, dfile))
            info = data.readlines()
            msg += "".join(info)
            data.close()
            msg += "</send_file>"
            #self.xmpp.send(msg, self.boss)
        self.xmpp.callLater(1, self.do_work)
        return
    
    def do_work(self):
        #if 4 <= self.generation:
        #    self.xmpp.callLater(1, self.finish)
        #    return
        self.work_this_gen += 1
        self.last_gen = datetime.datetime.now()
        chroms = list()
        data_files = os.listdir(self.data_dir)
        data_files.sort()
        orig_files = os.listdir(self.orig_dir)
        orig_files.sort()
        
        query = "SELECT c.genome "
        query += "FROM (chromosome c INNER JOIN chrom_gen cg ON c.cid=cg.cid) "
        query += "INNER JOIN generation g ON cg.gid=g.gid "
        if self.greedy_search:
            query += "WHERE cg.final_fitness IS NULL "
        else:
            query += "WHERE c.accuracy=-1 "
        query += "AND g.gid=%s AND cg.mid=%s " % (str(self.generation), self.manager_id)
        query += "LIMIT 10000"
        self.cr.execute(query)
        row = self.cr.fetchone()
        while row != None:
            chroms.append((str(row[0]).strip(),str(uuid.uuid4().hex).strip()))
            row = self.cr.fetchone()
        
        print "sending jobs:",len(chroms)
        for (c,u) in chroms:
            msg = "<job "
            msg += "manager=\"%s\" " % str(self.username)
            msg += "run_id=\"%s\" " % self.run_id
            msg += "id=\"%s\" >" % str(u)
            msg += "<chromosome_file "
            msg += "filename=\"%s.xml\" >" % str(u)
            msg += "<chromosome "
            msg += "data=\"%s\" " % str(c)
            msg += "fitness=\"-1\" "
            msg += "generation=\"%s\" " % str(self.generation)
            msg += "info=\"\" />"
            msg += "</chromosome_file>"
            msg += "<data_files>"
            msg += ",".join(data_files)
            msg += ",site.xml"
            msg += "</data_files>"
            msg += "<orig_files>"
            msg += ",".join(orig_files)
            msg += "</orig_files>"
            msg += "</job>"
            self.xmpp.send(msg, self.boss)
            self.running_jobs += 1
        if self.running_jobs == 0:
            self.xmpp.callLater(1, self.next_generation)
        return
    
    def auto_refresh_jobs(self):
        td_job = datetime.timedelta(minutes=30)
        if (self.last_job - datetime.datetime.now()) > td_job:
            self.running_jobs = 0
            self.xmpp.callLater(0, self.do_work)
        self.xmpp.callLater(900, self.auto_refresh_jobs)
        return
    
    def load_completed_jobs(self):
        if len(self.completed_jobs) > 0:
            (data,fitness,info,generation) = self.completed_jobs.popleft()
            print "\tM=%s\tG=%s\tF=%s" % (self.manager_id, generation, fitness)
            query = "SELECT cid FROM chromosome WHERE genome='%s'" % str(data).strip()
            self.cr.execute(query)
            r = self.cr.fetchone()
            cid = str(r[0]).strip()
            if self.greedy_search:
                #if str(fitness).strip() != "-1":
                query = "UPDATE chrom_gen SET final_fitness=%s " % str(fitness).strip()
                query += "WHERE cid=%s AND mid=%s AND gid=%s " % (cid, self.manager_id, str(self.generation))
                self.cr.execute(query)
            else:
                query = "UPDATE chromosome SET accuracy=%s " % str(fitness).strip()
                query += "WHERE cid='%s'" % str(cid)
                self.cr.execute(query)
            self.mydb.commit()
            
            anns = str(info).split(',')
            for line in anns:
                if line == "":
                    continue
                stuff = str(line).split(':')
                # name:TP:FP:TN:FN
                self.handle_annotation_cache(str(stuff[0]))
                query = "SELECT cid, aid FROM chrom_ann WHERE "
                query += "cid=%s AND aid=%s " % (cid,
                                                 self.ann_cache[stuff[0]])
                query += " AND mid=%s" % self.manager_id
                self.cr.execute(query)
                r = self.cr.fetchone()
                if r == None:
                    query = "INSERT INTO chrom_ann (cid, aid, mid, tp, fp, tn, fn) VALUES "
                    query += "(%s, %s, %s, %s, %s, %s, %s)" % (cid,
                                                           self.ann_cache[stuff[0]],
                                                           self.manager_id,
                                                           stuff[1], stuff[2],
                                                           stuff[3], stuff[4])
                    self.cr.execute(query)
            self.mydb.commit()
            self.running_jobs -= 1
            print "running jobs:",self.running_jobs,"\t\t%d" % len(self.completed_jobs)
            if self.running_jobs == 0:
                self.xmpp.callLater(1, self.next_generation)
            self.xmpp.callLater(0.000001, self.load_completed_jobs)
        else:
            self.xmpp.callLater(1, self.load_completed_jobs)
        return
    
    def message(self, msg, name):
        #print "Msg from:", name
        #print msg
        if name == self.boss:
            if msg == "quit-now":
                print "Boss command:",msg
                self.xmpp.callLater(0, self.finish)
                return
            elif msg == "quit-generation":
                print "Boss command:",msg
                self.quit_on_generation = True
                return
            elif msg == "refresh":
                print "Boss command:",msg
                self.running_jobs = 0
                self.xmpp.callLater(0, self.do_work)
                return
            elif msg == "conditional-refresh":
                print "Boss command:",msg
                td = datetime.timedelta(hours=1)
                if (self.last_gen - datetime.datetime.now()) > td:
                    self.xmpp.callLater(0, self.do_work)
                return
        dom = xml.dom.minidom.parseString(msg)
        if dom.firstChild.nodeName == "job_completed":
            self.last_job = datetime.datetime.now()
            children = dom.getElementsByTagName("chromosome")
            for child in children:
                data = child.getAttribute("data")
                fitness = child.getAttribute("fitness")
                info = child.getAttribute("info")
                generation = child.getAttribute("generation")
                self.completed_jobs.append((data,fitness,info,generation))
                #print "\tM=%s\tG=%s\tF=%s" % (self.manager_id, generation, fitness)
                #query = "SELECT cid FROM chromosome WHERE genome='%s'" % str(data).strip()
                #self.cr.execute(query)
                #r = self.cr.fetchone()
                #cid = str(r[0]).strip()
                #if self.greedy_search:
                #    #if str(fitness).strip() != "-1":
                #    query = "UPDATE chrom_gen SET final_fitness=%s " % str(fitness).strip()
                #    query += "WHERE cid=%s AND mid=%s AND gid=%s " % (cid, self.manager_id, str(self.generation))
                #    self.cr.execute(query)
                #else:
                #    query = "UPDATE chromosome SET accuracy=%s " % str(fitness).strip()
                #    query += "WHERE cid='%s'" % str(cid)
                #    self.cr.execute(query)
                #self.mydb.commit()
                # 
                #anns = str(info).split(',')
                #for line in anns:
                #    if line == "":
                #        continue
                #    stuff = str(line).split(':')
                #    # name:TP:FP:TN:FN
                #    self.handle_annotation_cache(str(stuff[0]))
                #    query = "SELECT cid, aid FROM chrom_ann WHERE "
                #    query += "cid=%s AND aid=%s " % (cid,
                #                                     self.ann_cache[stuff[0]])
                #    query += " AND mid=%s" % self.manager_id
                #    self.cr.execute(query)
                #    r = self.cr.fetchone()
                #    if r == None:
                #        query = "INSERT INTO chrom_ann (cid, aid, mid, tp, fp, tn, fn) VALUES "
                #        query += "(%s, %s, %s, %s, %s, %s, %s)" % (cid,
                #                                               self.ann_cache[stuff[0]],
                #                                               self.manager_id,
                #                                               stuff[1], stuff[2],
                #                                               stuff[3], stuff[4])
                #        self.cr.execute(query)
                #self.mydb.commit()
            #self.running_jobs -= 1
            #print "running jobs:",self.running_jobs
            #if self.running_jobs == 0:
            #    self.xmpp.callLater(1, self.next_generation)
        else:
            print "Msg from:", name
            print msg
        return
    
    def handle_annotation_cache(self, name):
        if name in self.ann_cache:
            return
        query = "SELECT aid FROM annotation WHERE name='%s'" % name
        self.cr.execute(query)
        r = self.cr.fetchone()
        if r == None:
            query = "INSERT INTO annotation (name) VALUES ('%s')" % name
            self.cr.execute(query)
            self.mydb.commit()
            query = "SELECT aid FROM annotation WHERE name='%s'" % name
            self.cr.execute(query)
            r = self.cr.fetchone()
        self.ann_cache[name] = str(r[0]).strip()
        return
    
    def next_generation(self):
        found = 0
        query = "SELECT count(*) "
        query += "FROM (chromosome c INNER JOIN chrom_gen cg ON c.cid=cg.cid) "
        query += "INNER JOIN generation g ON cg.gid=g.gid "
        if self.greedy_search:
            query += "WHERE cg.final_fitness IS NULL AND "
        else:
            query += "WHERE c.accuracy=-1 AND "
        query += "g.gid=%s AND cg.mid=%s" % (str(self.generation), self.manager_id)
        self.cr.execute(query)
        row = self.cr.fetchone()
        found = int(float(str(row[0]).strip()))
        if found > 0 and self.work_this_gen < self.max_work_per_gen:
            self.xmpp.callLater(1, self.do_work)
            return
        
        if self.quit_on_generation:
            self.xmpp.callLater(0, self.finish)
            return
        self.generation += 1
        if self.max_generations != None:
            if int(float(self.max_generations)) <= self.generation:
                #if 4 <= self.generation:
                self.xmpp.callLater(1, self.finish)
                return
        cmd = "%s GA_Reproduce.py " % str(self.pypath)
        cmd += "--manager_id=%s " % str(self.manager_id)
        cmd += "--site=%s " % str(self.site)
        cmd += "--generation=%s " % str(self.generation)
        cmd += "--random=%f " % random.random()
        cmd += "--mutation_rate=%f " % self.mutation_rate
        cmd += "--crossover=%s " % str(self.crossover)
        cmd += "--survival_rate=%f " % self.survival_rate
        cmd += "--reproduction_rate=%f " % self.reproduction_rate
        cmd += "--population=%s " % str(self.population)
        if self.seed_size != None:
            cmd += "--seed_size=%s " % str(self.seed_size)
        if self.size_limit != None:
            cmd += "--size_limit=%s " % str(self.size_limit)
        if self.greedy_search:
            cmd += "--greedy_search "
        cmd = str(cmd).strip()
        print cmd
        self.p = subprocess.Popen(str(cmd).split())
        #subprocess.call(str(cmd).split())
        self.xmpp.callLater(1, self.wait_next_generation)
        return
    
    def wait_next_generation(self):
        if self.p.poll() == None:
            self.xmpp.callLater(1, self.wait_next_generation)
            return
        self.p = None
        self.running_jobs = 0
        self.work_this_gen = 0
        self.xmpp.callLater(1, self.do_work)
        return



if __name__ == "__main__":
    parser = optparse.OptionParser(usage="usage: %prog [options]")
    parser.add_option("--jid",
                      dest="jid",
                      help="Jabber ID.")
    parser.add_option("--password",
                      dest="password",
                      help="Jabber ID password.")
    parser.add_option("--dir",
                      dest="dir",
                      help="Working directory for files.")
    parser.add_option("--data",
                      dest="data",
                      help="Directory of data files.")
    parser.add_option("--orig",
                      dest="orig",
                      help="Original data files for comparison.")
    parser.add_option("--boss",
                      dest="boss",
                      help="JID of Boss.",
                      default="boss@node01")
    parser.add_option("--pypath",
                      dest="pypath",
                      help="Python executable path.",
                      default="/usr/bin/python")
    parser.add_option("--generation",
                      dest="generation",
                      help="Generation to start with.",
                      default="0")
    parser.add_option("--population",
                      dest="population",
                      help="Population size.",
                      default="30")
    parser.add_option("--random",
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
                      help="Number of sensors to seed with.")
    parser.add_option("--size_limit",
                      dest="size_limit",
                      help="Put a limit on number of sensors.")
    parser.add_option("--max_generations",
                      dest="max_generations",
                      help="Number of generations to acheive then quit.")
    parser.add_option("--grid_size",
                      dest="grid_size",
                      help="Size of grid of sensors to test.")
    parser.add_option("--greedy_search",
                      dest="greedy_search",
                      help="Perform greedy search on layout.",
                      action="store_true",
                      default=False)
    (options, args) = parser.parse_args()
    if None in [options.jid, options.password, options.dir, options.data, options.orig]:
        if options.jid == None:
            print "ERROR: Missing --jid"
        if options.password == None:
            print "ERROR: Missing --password"
        if options.dir == None:
            print "ERROR: Missing --dir"
        if options.data == None:
            print "ERROR: Missing --data"
        if options.orig == None:
            print "ERROR: Missing --orig"
        parser.print_help()
        sys.exit()
    
    if options.random == None:
        random.seed()
    else:
        random.seed(float(options.random))
    
    theMan = Manager(options)
    theMan.connect()

