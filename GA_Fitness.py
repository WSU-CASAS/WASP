#!/usr/bin/python

import optparse
import os
import re
import subprocess
import sys
import time
import uuid
import xml.dom.minidom

from GA_Reproduce import Chromosome


class CookAr:
    def __init__(self, options, data_file):
        self.file_chromosome = str(options.chromosome)
        self.file_site = str(options.site)
        self.working_dir = str(options.work)
        self.file_rawdata = os.path.join(self.working_dir, str(data_file))
        dom = xml.dom.minidom.parse(os.path.join(self.working_dir, self.file_site))
        site = dom.getElementsByTagName("site")
        self.max_width = int(float(site[0].getAttribute("max_width")))
        self.max_height = int(float(site[0].getAttribute("max_height")))
        self.chromosome = Chromosome(os.path.join(self.working_dir, self.file_chromosome),
                                     self.max_width, self.max_height)
        self.annotations = list()
        name = str(uuid.uuid4().hex)
        self.file_config = os.path.join(self.working_dir, "%s.config" % str(name))
        self.file_data = os.path.join(self.working_dir, "%s.data" % str(name))
        self.fitness = -1
        return
    
    def write_data(self):
        out = open(self.file_data, 'w')
        dom = xml.dom.minidom.parse(self.file_rawdata)
        data = dom.getElementsByTagName("data")
        children = data[0].childNodes
        for event in children:
            dt = event.getAttribute("timestamp")
            serial = event.getAttribute("serial")
            message = event.getAttribute("message")
            annotation = event.getAttribute("annotation")
            stuff = str(annotation).split(",")
            ann = ""
            for line in stuff:
                if str(line).find("-start") or str(line).find("-end"):
                    ann = line
                    ann = re.sub('-', ' ', ann)
                    ann = re.sub("start", "begin", ann)
            if ann != "":
                if str(ann).split()[0] not in self.annotations:
                    self.annotations.append(str(ann).split()[0])
            out.write("%s\t%s\t%s\t%s\n" % (dt, serial, message, ann))
        out.close()
        return
    
    def write_config(self):
        out = open(self.file_config, 'w')
        out.write("numactivities\n")
        out.write("  %s\n" % str(len(self.annotations)))
        out.write("activitynames\n")
        for x in range(len(self.annotations)):
            out.write("  %s\n" % str(self.annotations[x]))
        out.write("numfeatures\n")
        out.write("  5\n")
        out.write("numphysicalsensors\n")
        out.write("  %s\n" % str(self.chromosome.get_sensor_count()))
        out.write("numfeaturevalues\n")
        out.write("  %s\n" % str(self.chromosome.get_sensor_count()))
        out.write("  5\n")
        out.write("  7\n")
        out.write("  %s\n" % str(len(self.annotations)))
        out.write("  3\n")
        out.write("selectfeatures\n")
        out.write("  0\n")
        out.write("  0\n")
        out.write("  0\n")
        out.write("  0\n")
        out.write("  1\n")
        out.write("mapsensors\n")
        for x in range(self.chromosome.get_sensor_count()):
            out.write("  %s %s\n" % (str(x), str(x)))
        out.write("model\n")
        out.write("  naivebayes")
        out.close()
        return
    
    def run(self):
        self.write_data()
        self.write_config()
        p = subprocess.Popen([os.path.join(self.working_dir, "ar"),
                              self.file_data, self.file_config],
                             stdout=subprocess.PIPE)
        
        while p.poll() == None:
            print "not done, sleeping..."
            time.sleep(1)
        data = p.stdout.readlines()
        for line in data:
            accObj = re.search(".*Average accuracy is (0\.\d+)", line)
            if accObj != None:
                print accObj.group(1)
                self.fitness = float(accObj.group(1)) * 100.0
        
        os.remove(self.file_data)
        os.remove(self.file_config)
        return


if __name__ == "__main__":
    print "GA Fitness Calculator"
    parser = optparse.OptionParser(usage="usage: %prog [options]")
    parser.add_option("-f",
                      "--files",
                      dest="files",
                      help="Files with sensor event data.")
    parser.add_option("-c",
                      "--chromosome",
                      dest="chromosome",
                      help="File with the sensor chromosome definition.")
    parser.add_option("-s",
                      "--site",
                      dest="site",
                      help="Site config file.")
    parser.add_option("-m",
                      "--method",
                      dest="method",
                      help="Fitness generation method.")
    parser.add_option("-w",
                      "--work",
                      dest="work",
                      help="Working directory for data.")
    (options, args) = parser.parse_args()
    if None in [options.files, options.chromosome, options.site, options.method, options.work]:
        if options.files == None:
            print "ERROR: Missing -f / --files"
        if options.chromosome == None:
            print "ERROR: Missing -c / --chromosome"
        if options.site == None:
            print "ERROR: Missing -s / --site"
        if options.method == None:
            print "ERROR: Missing -m / --method"
        if options.work == None:
            print "ERROR: Missing -w / --work"
        parser.print_help()
        sys.exit()
    
    if str(options.method) == "CookAr":
        values = list()
        files = str(options.files).split(",")
        for dfile in files:
            myobj = CookAr(options, dfile)
            myobj.run()
            if myobj.fitness != -1:
                values.append(myobj.fitness)
        
        fitness = float(sum(values)) / float(len(values))
        print "Fitness =",fitness
        
        

