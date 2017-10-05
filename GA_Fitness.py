#!/usr/bin/python

import copy
import datetime
import optparse
import os
import re
import subprocess
import sys
import time
import uuid
import xml.dom.minidom

from GA_Reproduce import Chromosome


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



class Event:
    def __init__(self, dt, ann, orig):
        self.dt = copy.copy(dt)
        self.ann = copy.copy(ann)
        self.orig = copy.copy(orig)
        return
    
    def __cmp__(self, other):
        val = 0
        if self.dt < other.dt:
            val = -1
        elif self.dt > other.dt:
            val = 1
        elif self.orig and not other.orig:
            val = -1
        elif not self.orig and other.orig:
            val = 1
        return val



class CookAr:
    def __init__(self, options):
        self.file_chromosome = str(options.chromosome)
        self.file_site = str(options.site)
        self.working_dir = str(options.work)
        self.files_rawdata = str(options.files).split(',')
        self.files_orig = dict()
        self.file_ranges = dict()
        self.calc = dict()
        self.all_annotations = list()
        self.all_annotations.append("Other")
        for x in self.files_rawdata:
            self.file_ranges[x] = list()
            dom = xml.dom.minidom.parse(x)
            data = dom.getElementsByTagName("data")
            fname = data[0].getAttribute("filename")
            dir = os.path.dirname(fname)
            nName = os.path.basename(fname)
            nName = re.sub('^m', '', nName)
            origFile = os.path.join(dir, nName)
            self.files_orig[x] = origFile
            info = data[0].firstChild
            self.file_ranges[x].append(get_datetime(info.getAttribute("timestamp")))
            info = data[0].lastChild
            self.file_ranges[x].append(get_datetime(info.getAttribute("timestamp")))
            if data[0].hasAttribute("annotations"):
                this_ann = data[0].getAttribute("annotations")
                this_ann_list = str(this_ann).split(',')
                for one_ann in this_ann_list:
                    if one_ann not in self.all_annotations:
                        self.all_annotations.append(str(one_ann).strip())
            oData = open(origFile)
            lines = oData.readlines()
            oData.close()
            self.file_ranges[origFile] = list()
            stuff = str(lines[0]).split()
            self.file_ranges[origFile].append(get_datetime("%s %s" % (stuff[0],
                                                                      stuff[1])))
            stuff = str(lines[-1]).split()
            self.file_ranges[origFile].append(get_datetime("%s %s" % (stuff[0],
                                                                      stuff[1])))
        
        self.all_annotations.sort()
        dom = xml.dom.minidom.parse(self.file_site)
        site = dom.getElementsByTagName("site")
        self.max_width = int(float(site[0].getAttribute("max_width")))
        self.max_height = int(float(site[0].getAttribute("max_height")))
        self.chromosome = Chromosome(self.file_chromosome,
                                     self.max_width, self.max_height)
        self.annotations = list()
        name = str(uuid.uuid4().hex)
        self.file_config = os.path.join(self.working_dir, "%s.config" % str(name))
        self.file_data = os.path.join(self.working_dir, "%s.data" % str(name))
        self.fitness = -1
        self.events = list()
        return
    
    def write_data(self):
        out = open(self.file_data, 'w')
        for fname in self.files_rawdata:
            dom = xml.dom.minidom.parse(fname)
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
                    if str(line).find("-begin") or str(line).find("-end"):
                        ann = re.sub('-', ' ', line)
                    else:
                        ann = str(line)
                if ann != "":
                    if str(ann).split()[0] not in self.annotations:
                        self.annotations.append(str(ann).split()[0])
                out.write("%s\t%s\t%s\t%s\n" % (dt, serial, message, ann))
        out.close()
        return
    
    def write_config(self):
        out = open(self.file_config, 'w')
        out.write("numactivities\n")
        out.write("  %s\n" % str(len(self.all_annotations)))
        out.write("activitynames\n")
        for x in range(len(self.all_annotations)):
            out.write("  %s\n" % str(self.all_annotations[x]))
        out.write("numfeatures\n")
        out.write("  5\n")
        out.write("numphysicalsensors\n")
        out.write("  %s\n" % str(self.chromosome.get_sensor_count()))
        out.write("numfeaturevalues\n")
        out.write("  %s\n" % str(self.chromosome.get_sensor_count()))
        out.write("  5\n")
        out.write("  7\n")
        out.write("  %s\n" % str(len(self.all_annotations)))
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
                              self.file_data, self.file_config, "-stream"],
                             stdout=subprocess.PIPE)
        
        while p.poll() == None:
            data = p.stdout.readlines()
            for x in data:
                stuff = str(str(x).strip()).split()
                dt = get_datetime("%s %s" % (stuff[0], stuff[1]))
                self.events.append(Event(dt, stuff[2], False))
            time.sleep(1)
        
        for fname in self.files_orig.keys():
            data = open(self.files_orig[fname])
            info = data.readlines()
            data.close()
            activeAnn = "Other"
            nextOther = False
            for line in info:
                stuff = str(str(line).strip()).split()
                dt = get_datetime("%s %s" % (stuff[0], stuff[1]))
                if nextOther:
                    activeAnn = "Other"
                    nextOther = False
                
                if len(stuff) > 4:
                    if re.search('-begin', stuff[4]):
                        activeAnn = re.sub('-begin', '', stuff[4])
                    elif re.search('-end', stuff[4]):
                        nextOther = True
                ann = str(activeAnn)
                self.events.append(Event(dt, ann, True))
        
        self.events.sort()
        hourTD = datetime.timedelta(hours=1)
        blocks = list()
        blocks.append(list())
        chunk = 0
        
        for x in range(len(self.events) - 1):
            blocks[chunk].append(self.events[x])
            diff = abs(self.events[x].dt - self.events[x+1].dt)
            if diff > hourTD:
                chunk += 1
                blocks.append(list())
        blocks[chunk].append(self.events[-1])
        
        for x in self.all_annotations:
            self.calc[x] = {'TP':0, 'FP':0, 'TN':0, 'FN':0}
        
        totalTicks = 0
        for x in range(len(blocks)):
            step = blocks[x][0].dt
            stepper = datetime.timedelta(seconds=0.01)
            t = 0
            activeAnn = "Other"
            while t < len(blocks[x]):
                if activeAnn not in self.calc:
                    self.calc[activeAnn] = {'TP':0, 'FP':0, 'TN':0, 'FN':0}
                totalTicks += 1
                if blocks[x][t].orig:
                    activeAnn = blocks[x][t].ann
                elif blocks[x][t].ann == activeAnn:
                    self.calc[blocks[x][t].ann]['TP'] += 1
                else:
                    self.calc[blocks[x][t].ann]['FP'] += 1
                    self.calc[activeAnn]['FN'] += 1
                
                if t+1 < len(blocks[x]):
                    if blocks[x][t+1].dt < (step + stepper):
                        t += 1
                    else:
                        step += stepper
                else:
                    t += 1
        
        for x in self.all_annotations:
            self.calc[x]['TN'] = totalTicks - self.calc[x]['TP'] - self.calc[x]['FP'] - self.calc[x]['FN']
        testing = 0
        for x in range(len(self.events)):
            if not self.events[x].orig:
                testing += 1
        
        avgAcc = 0.0
        for x in self.all_annotations:
            xPos = float(self.calc[x]['TP'] + self.calc[x]['FN'])
            xNeg = float(self.calc[x]['FP'] + self.calc[x]['TN'])
            tpr = 0.0
            if xPos > 0:
                tpr = float(self.calc[x]['TP']) / float(xPos)
            fpr = 0.0
            if xNeg > 0:
                fpr = float(self.calc[x]['FP']) / float(xNeg)
            acc = (tpr - fpr) * 100.0
            if x != "Other":
                avgAcc += acc
            msg = "%10s  TP =%5d  FP =%5d" % (x, self.calc[x]['TP'], self.calc[x]['FP'])
            msg += "  TN =%5d  FN =%5d" % (self.calc[x]['TN'], self.calc[x]['FN'])
            msg += "\ttpr=%f  fpr=%f" % (tpr*100.0, fpr*100.0)
            msg += "    acc=%f" % (acc)
            #msg += "\t p=%f  f=%f" % (xPos, xNeg)
            #print msg
        self.fitness = avgAcc/(len(self.all_annotations)-1)
        #self.fitness += 2.0 * float(len(self.annotations))
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
        myobj = CookAr(options)
        myobj.run()
        
        fitness = myobj.fitness
        print "Fitness =",fitness
        msg = ""
        for x in myobj.calc.keys():
            msg += "%s:" % str(x)
            msg += "%d:" % myobj.calc[x]['TP']
            msg += "%d:" % myobj.calc[x]['FP']
            msg += "%d:" % myobj.calc[x]['TN']
            msg += "%d," % myobj.calc[x]['FN']
        dom = xml.dom.minidom.parse(options.site)
        site = dom.getElementsByTagName("site")
        max_width = int(float(site[0].getAttribute("max_width")))
        max_height = int(float(site[0].getAttribute("max_height")))
        chrom = Chromosome(options.chromosome, max_width, max_height)
        chrom.fitness = fitness
        chrom.info = msg
        out = open(chrom.filename, 'w')
        out.write(str(chrom))
        out.close()

