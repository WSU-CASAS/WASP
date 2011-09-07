import xmpp

import optparse
import os
import random
import re
import shutil
import subprocess
import sys
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
        self.boss = str(options.boss)
        self.pypath = str(options.pypath)
        self.generation = int(float(options.generation))
        self.generation_dir = None
        self.population = int(float(options.population))
        self.mutation_rate = float(options.mutation_rate)
        self.crossover = int(float(options.crossover))
        self.survival_rate = float(options.survival_rate)
        self.reproduction_rate = float(options.reproduction_rate)
        self.seed_size = options.seed_size
        self.size_limit = options.size_limit
        self.max_generations = options.max_generations
        self.quit_on_generation = False
        self.xmpp = xmpp.Connection(self.name)
        self.xmpp.set_authd_callback(self.has_connected)
        self.xmpp.set_direct_msg_callback(self.message)
        self.xmpp.set_finish_callback(self.finish)
        self.run_id = str(uuid.uuid4().hex)
        self.running_jobs = 0
        dom = xml.dom.minidom.parse(os.path.join(self.directory, "site.xml"))
        site = dom.getElementsByTagName("site")
        self.max_width = int(float(site[0].getAttribute("max_width")))
        self.max_height = int(float(site[0].getAttribute("max_height")))
        
        self.dna = os.path.join(self.directory, "dna")
        if not os.path.isdir(self.dna):
            os.mkdir(self.dna)
        
        found = False
        if self.generation > 0:
            while self.generation >= 0 and not found:
                if os.path.isdir(os.path.join(self.dna, str(self.generation))):
                    found = True
                else:
                    self.generation -= 1
        if not found:
            self.generation = 0
            self.generation_dir = os.path.join(self.dna, str(self.generation))
            if os.path.isdir(self.generation_dir):
                shutil.rmtree(self.generation_dir)
            os.mkdir(self.generation_dir)
            cmd = "%s GA_Reproduce.py " % self.pypath
            cmd += "-s %s " % os.path.join(self.directory, "site.xml")
            cmd += "-c %s " % self.generation_dir
            cmd += "-d %s " % self.generation_dir
            cmd += "-r %f " % random.random()
            cmd += "-g %s " % str(self.generation)
            cmd += "--seed=%s " % str(self.population)
            if self.seed_size != None:
                cmd += "--seed_size=%s " % str(self.seed_size)
            if self.size_limit != None:
                cmd += "--size_limit=%s " % str(self.size_limit)
            cmd = str(cmd).strip()
            subprocess.call(str(cmd).split())
        return
    
    def connect(self):
        self.xmpp.connect(self.username, self.password)
        return
    
    def has_connected(self):
        self.xmpp.callLater(1, self.send_files)
        return
    
    def finish(self):
        self.xmpp.disconnect()
        return
    
    def send_files(self):
        msg = "<send_file "
        msg += "filename=\"site.xml\" " 
        msg += "run_id=\"%s\" >" % self.run_id
        data = open(os.path.join(self.directory, "site.xml"))
        info = data.readlines()
        msg += "".join(info)
        data.close()
        msg += "</send_file>"
        self.xmpp.send(msg, self.boss)
        
        dFiles = os.listdir(self.data_dir)
        for dfile in dFiles:
            msg = "<send_file "
            msg += "filename=\"%s\" " % dfile
            msg += "run_id=\"%s\" >" % self.run_id
            data = open(os.path.join(self.data_dir, dfile))
            info = data.readlines()
            msg += "".join(info)
            data.close()
            msg += "</send_file>"
            self.xmpp.send(msg, self.boss)
        self.xmpp.callLater(1, self.do_work)
        return
    
    def do_work(self):
        chroms = list()
        cFiles = os.listdir(self.generation_dir)
        for cFile in cFiles:
            chroms.append(Chromosome(os.path.join(self.generation_dir, cFile),
                                     self.max_width, self.max_height))
        data_files = os.listdir(self.data_dir)
        for c in chroms:
            if c.fitness == -1:
                msg = "<job "
                msg += "manager=\"%s\" " % str(self.username)
                msg += "run_id=\"%s\" " % self.run_id
                msg += "id=\"%s\" >" % str(uuid.uuid4().hex)
                msg += "<chromosome_file "
                msg += "filename=\"%s\" >" % os.path.basename(str(c.filename))
                msg += str(c)
                msg += "</chromosome_file>"
                msg += "<data_files>"
                msg += ",".join(data_files)
                msg += ",site.xml"
                msg += "</data_files>"
                msg += "</job>"
                print len(msg)
                self.xmpp.send(msg, self.boss)
                self.running_jobs += 1
        return
    
    def message(self, msg, name):
        print "Msg from:", name
        print msg
        if name == self.boss:
            if msg == "quit-now":
                self.xmpp.callLater(0, self.finish)
                return
            elif msg == "quit-generation":
                self.quit_on_generation = True
                return
        dom = xml.dom.minidom.parseString(msg)
        if dom.firstChild.nodeName == "job_completed":
            children = dom.firstChild.childNodes
            for child in children:
                fname = child.getAttribute("filename")
                out = open(os.path.join(self.generation_dir, fname), 'w')
                data = child.firstChild
                out.write(data.toxml())
                out.close()
            self.running_jobs -= 1
            print "running jobs:",self.running_jobs
            if self.running_jobs == 0:
                self.xmpp.callLater(1, self.next_generation)
        return
    
    def next_generation(self):
        if self.quit_on_generation:
            self.xmpp.callLater(0, self.finish)
            return
        self.generation += 1
        if self.max_generations != None:
            if int(float(self.max_generations)) <= self.generation:
                self.xmpp.callLater(0, self.finish)
                return
        last_gen_dir = str(self.generation_dir)
        self.generation_dir = os.path.join(self.dna, str(self.generation))
        if os.path.isdir(self.generation_dir):
            shutil.rmtree(self.generation_dir)
        os.mkdir(self.generation_dir)
        cmd = "%s GA_Reproduce.py " % str(self.pypath)
        cmd += "--site=%s " % str(os.path.join(self.directory, "site.xml"))
        cmd += "--chromosome=%s " % str(last_gen_dir)
        cmd += "--directory=%s " % str(self.generation_dir)
        cmd += "--generation=%s " % str(self.generation)
        cmd += "--random=%f " % random.random()
        cmd += "--mutation_rate=%f " % self.mutation_rate
        cmd += "--crossover=%s " % str(self.crossover)
        cmd += "--survival_rate=%f " % self.survival_rate
        cmd += "--reproduction_rate=%f " % self.reproduction_rate
        if self.seed_size != None:
            cmd += "--seed_size=%s " % str(self.seed_size)
        if self.size_limit != None:
            cmd += "--size_limit=%s " % str(self.size_limit)
        cmd = str(cmd).strip()
        print cmd
        subprocess.call(str(cmd).split())
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
    (options, args) = parser.parse_args()
    if None in [options.jid, options.password, options.dir, options.data]:
        if options.jid == None:
            print "ERROR: Missing --jid"
        if options.password == None:
            print "ERROR: Missing --password"
        if options.dir == None:
            print "ERROR: Missing --dir"
        if options.data == None:
            print "ERROR: Missing --data"
        parser.print_help()
        sys.exit()
    
    if options.random == None:
        random.seed()
    else:
        random.seed(float(options.random))
    
    theMan = Manager(options)
    theMan.connect()

