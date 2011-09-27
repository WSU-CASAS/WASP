#!/usr/bin/python
import matplotlib
matplotlib.use('Agg')
import pylab
import matplotlib.cm as cm
import matplotlib.pyplot as plt
import os
import sys
import xml.dom.minidom
from GA_Reproduce import Chromosome

fig = plt.figure(figsize=(14,9), dpi=128)

class Generation:
    def __init__(self):
        self.ann = dict()
        return
    
    def add_member(self, info):
        stuff = str(info).split(',')
        for ac in stuff:
            if len(ac.strip()) < 1:
                continue
            st = str(ac).strip().split(':')
            ann = str(st[0]).strip()
            pos = float(st[1]) + float(st[4])
            neg = float(st[2]) + float(st[3])
            tpr = 0.0
            if pos > 0:
                tpr = float(st[1]) / float(pos)
            fpr = 0.0
            if neg > 0:
                fpr = float(st[2]) / float(neg)
            acc = (tpr - fpr) * 100.0
            if ann not in self.ann:
                self.ann[ann] = list()
            self.ann[ann].append(acc)
        return
    
    def get_annotations(self):
        return self.ann.keys()
    
    def get_max(self, annotation):
        max = 0.0
        if annotation in self.ann:
            for x in self.ann[annotation]:
                if max < x:
                    max = x
        return max
    
    def get_min(self, annotation):
        min = 100.0
        if annotation in self.ann:
            for x in self.ann[annotation]:
                if min > x:
                    min = x
        return min
    
    def get_avg(self, annotation):
        avg = 0.0
        if annotation in self.ann:
            avg = float(sum(self.ann[annotation])) / float(len(self.ann[annotation]))
        return avg



class GA:
    def __init__(self, sname, cdir):
        self.gen = 0
        self.gens = list()
        self.cdir = cdir
        dom = xml.dom.minidom.parse(sname)
        site = dom.getElementsByTagName("site")
        self.max_width = int(float(site[0].getAttribute("max_width")))
        self.max_height = int(float(site[0].getAttribute("max_height")))
        return
    
    def run(self, fig):
        gen_dir = os.path.join(self.cdir, str(self.gen))
        while os.path.isdir(gen_dir):
            self.gens.append(Generation())
            files = os.listdir(gen_dir)
            for chrom in files:
                #try:
                dom = xml.dom.minidom.parse(os.path.join(gen_dir,chrom))
                chromosome = dom.getElementsByTagName("chromosome")
                info = str(chromosome[0].getAttribute("info"))
                self.gens[-1].add_member(info)
                #except:
                #    print "bad file: ",chrom
            self.gen += 1
            gen_dir = os.path.join(self.cdir, str(self.gen))
        
        x = range(len(self.gens))
        anns = self.gens[0].get_annotations()
        anns.sort()
        yMin = dict()
        yMax = dict()
        yAvg = dict()
        colors = cm.gist_rainbow(pylab.linspace(0, 1, len(anns)))
        count = 0
        for y in anns:
            yMin[y] = list()
            yMax[y] = list()
            yAvg[y] = list()
            for g in range(len(self.gens)):
                yMin[y].append(self.gens[g].get_min(y))
                yMax[y].append(self.gens[g].get_max(y))
                yAvg[y].append(self.gens[g].get_avg(y))
            
            #plt.subplot(len(anns),1,count)
            #plt.plot(x, yMin[y], ':', figure=fig, color=colors[count])
            #plt.figure(1)
            plt.plot(x, yMax[y], ':', figure=fig, color=colors[count])
            plt.plot(x, yAvg[y], '-', figure=fig, color=colors[count])
            #plt.figure(2)
            #plt.plot(x, yAvg[y], 'o', figure=fig, color=colors[count], label=y)
            #plt.errorbar(x, yAvg[y], yerr=[yMin[y],yMax[y]])
            count += 1
        
        return

sname = sys.argv[1]
cname = sys.argv[2]
outName = sys.argv[3]

myGA = GA(sname, cname)
myGA.run(fig)
#plt.figure(1)
plt.subplots_adjust(left=0.025, bottom=0.03, right=1.0, top=1.0)
#plt.figure(2)
#plt.legend(ncol=2)
plt.savefig(outName)
#plt.show()

