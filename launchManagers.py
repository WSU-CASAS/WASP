#*****************************************************************************#
#**
#**  WASP Manager Launcher
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

import copy
import optparse
import os
import shutil
import subprocess
import sys
import time


if __name__ == "__main__":
    print "WASP Launching Managers"
    parser = optparse.OptionParser(usage="usage: %prog [options]")
    parser.add_option("-s",
                      "--startnum",
                      dest="startnum",
                      help="Start number for manager's ID.",
                      default="0")
    parser.add_option("--startscreen",
                      dest="startscreen",
                      help="Start on this screen session number.",
                      default="0")
    parser.add_option("-b",
                      "--boss",
                      dest="boss",
                      help="JID of Boss to connect to.",
                      default="boss@node01")
    parser.add_option("--pypath",
                      dest="pypath",
                      help="Python executable path.",
                      default="/usr/bin/python")
    parser.add_option("--dir",
                      dest="dir",
                      help="Directory for Manager working dirs.")
    parser.add_option("--sitedata",
                      dest="sitedata",
                      help="List of site config files and data directories. site.xml:/data/dir:/orig/dir,site.xml:/data/dir:/orig/dir")
    parser.add_option("--population",
                      dest="population",
                      help="List of population sizes.",
                      default="50")
    parser.add_option("--random",
                      dest="random",
                      help="Random numbers seed.")
    parser.add_option("--mutation_rate",
                      dest="mutation_rate",
                      help="List of mutation rates.",
                      default="0.005,0.001,0.0005")
    parser.add_option("--crossover",
                      dest="crossover",
                      help="List of crossover values.",
                      default="1,2,3")
    parser.add_option("--survival_rate",
                      dest="survival_rate",
                      help="List of survival rates.",
                      default="0.10,0.20")
    parser.add_option("--reproduction_rate",
                      dest="reproduction_rate",
                      help="List of reproduction rates.",
                      default="0.20,0.30,0.40")
    parser.add_option("--seed_size",
                      dest="seed_size",
                      help="List of number of sensors to seed with.",
                      default="5")
    parser.add_option("--size_limit",
                      dest="size_limit",
                      help="List of limits on number of sensors (X=None).",
                      default="X")
    parser.add_option("--max_generations",
                      dest="max_generations",
                      help="List of generations GA should evolve to (X=None).",
                      default="300")
    parser.add_option("--grid_size",
                      dest="grid_size",
                      help="Size of grid of sensors to test on layout.",
                      default="X")
    parser.add_option("--greedy_search",
                      dest="greedy_search",
                      help="Perform the greedy search on layout.",
                      action="store_true",
                      default=False)
    parser.add_option("--multiply",
                      dest="multiply")
    (options, args) = parser.parse_args()
    if None in [options.dir, options.sitedata]:
        if options.dir == None:
            print "ERROR: Missing --dir"
        if options.sitedata == None:
            print "ERROR: Missing --sitedata"
        parser.print_help()
        sys.exit()
    
    config = list()
    for sd in str(options.sitedata).split(','):
        for p in str(options.population).split(','):
            for mr in str(options.mutation_rate).split(','):
                for co in str(options.crossover).split(','):
                    for sr in str(options.survival_rate).split(','):
                        for rr in str(options.reproduction_rate).split(','):
                            for ss in str(options.seed_size).split(','):
                                for sl in str(options.size_limit).split(','):
                                    for mg in str(options.max_generations).split(','):
                                        for gs in str(options.grid_size).split(','):
                                            config.append(dict())
                                            config[-1]["sitedata"] = sd
                                            config[-1]["population"] = p
                                            config[-1]["mutation_rate"] = mr
                                            config[-1]["crossover"] = co
                                            config[-1]["survival_rate"] = sr
                                            config[-1]["reproduction_rate"] = rr
                                            config[-1]["seed_size"] = ss
                                            config[-1]["size_limit"] = sl
                                            config[-1]["max_generations"] = mg
                                            config[-1]["grid_size"] = gs
    
    if options.multiply != None:
        config = list()
        num = int(float(options.multiply))
        for x in range(num):
            config.append(dict())
            config[-1]["sitedata"] = str(options.sitedata).split(',')[0]
            config[-1]["population"] = str(options.population).split(',')[0]
            config[-1]["mutation_rate"] = str(options.mutation_rate).split(',')[0]
            config[-1]["crossover"] = str(options.crossover).split(',')[0]
            config[-1]["survival_rate"] = str(options.survival_rate).split(',')[0]
            config[-1]["reproduction_rate"] = str(options.reproduction_rate).split(',')[0]
            config[-1]["seed_size"] = str(options.seed_size).split(',')[0]
            config[-1]["size_limit"] = str(options.size_limit).split(',')[0]
            config[-1]["max_generations"] = str(options.max_generations).split(',')[0]
            config[-1]["grid_size"] = str(options.grid_size).split(',')[0]
    
    start = int(float(options.startnum))
    mydir = os.path.abspath(os.path.normpath(options.dir))
    
    if not os.path.isdir(mydir):
        os.makedirs(mydir)
    
    numScreenRCs = 0
    screenOffset = int(float(options.startscreen))
    
    out = open("wasp_screenrc%s" % str(numScreenRCs + screenOffset), 'w')
    out.write("source $HOME/.screenrc\n#\n")
    
    for x in range(len(config)):
        if x%30 == 0 and x > 1:
            out.close()
            numScreenRCs += 1
            out = open("wasp_screenrc%s" % str(numScreenRCs + screenOffset), 'w')
            out.write("source $HOME/.screenrc\n#\n")
        num = str(x + start)
        if (x + start) < 10:
            num = "0%s" % str(x + start)
        
        wkDir = os.path.join(mydir, "Manager%s" % num)
        if not os.path.isdir(wkDir):
            os.mkdir(wkDir)
        
        #dnaDir = os.path.join(wkDir, "dna")
        #if not os.path.isdir(dnaDir):
        #    os.mkdir(dnaDir)
        shutil.copy(os.path.abspath("dna.db"), wkDir)
        
        sd = str(config[x]["sitedata"]).split(':')
        if not os.path.isfile(sd[0]):
            print "ERROR: '%s' in not a valid site file!" % str(sd[0])
            sys.exit()
        if not os.path.isdir(sd[1]):
            print "ERROR: '%s' in not a valid directory!" % str(sd[1])
            sys.exit()
        if not os.path.isdir(sd[2]):
            print "ERROR: '%s' in not a valid directory!" % str(sd[2])
            sys.exit()
        shutil.copy(sd[0], os.path.join(wkDir, "site.xml"))
        
        cmd = str(options.pypath)
        cmd += " WASP_Manager.py "
        cmd += "--jid=manager%s@node01 " % str(num)
        cmd += "--password=WASPmanager%s " % str(num)
        cmd += "--dir=%s " % str(wkDir)
        cmd += "--data=%s " % str(os.path.abspath(sd[1]))
        cmd += "--orig=%s " % str(os.path.abspath(sd[2]))
        cmd += "--boss=%s " % str(options.boss)
        cmd += "--pypath=%s " % str(options.pypath)
        cmd += "--population=%s " % str(config[x]["population"])
        if options.random != None:
            cmd += "--random=%s " % str(options.random)
        cmd += "--mutation_rate=%s " % str(config[x]["mutation_rate"])
        cmd += "--crossover=%s " % str(config[x]["crossover"])
        cmd += "--survival_rate=%s " % str(config[x]["survival_rate"])
        cmd += "--reproduction_rate=%s " % str(config[x]["reproduction_rate"])
        cmd += "--seed_size=%s " % str(config[x]["seed_size"])
        if config[x]["size_limit"] != "X":
            cmd += "--size_limit=%s " % str(config[x]["size_limit"])
        if config[x]["max_generations"] != "X":
            cmd += "--max_generations=%s " % str(config[x]["max_generations"])
            cmd += "--generation=%s " % str(int(float(config[x]["max_generations"])) - 1)
        if config[x]["grid_size"] != "X":
            cmd += "--grid_size=%s " % str(config[x]["grid_size"])
        if options.greedy_search:
            cmd += "--greedy_search "
        cmd = str(cmd).strip()
        fname = os.path.join(wkDir, "run.sh")
        run = open(fname, 'w')
        run.write("#!/bin/sh\n\n")
        run.write("sleep %s\n" % (x*5))
        run.write("%s\n" % cmd)
        #run.write("bash\n")
        run.close()
        subprocess.call(str("chmod +x %s" % fname).split())
        out.write("screen -t Manager%s  %s\n" % (str(num), fname))
        print cmd
    
    out.close()
    for x in range(numScreenRCs + 1):
        cmd = "screen -d -m -S WASP%s -c wasp_screenrc%s" % (str(x + screenOffset),str(x + screenOffset))
        print cmd
        subprocess.call(str(cmd).split())

