#*****************************************************************************#
#**
#**  WASP Worker Launcher
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

import optparse
import os
import shutil
import subprocess
import sys
import time


tmp_dir = "work"

if __name__ == "__main__":
    print "WASP Launching Workers"
    parser = optparse.OptionParser(usage="usage: %prog [options]")
    parser.add_option("-n",
                      "--number",
                      dest="number",
                      help="Number of workers to launch.")
    parser.add_option("-s",
                      "--startnum",
                      dest="startnum",
                      help="Start number for workers.",
                      default="0")
    parser.add_option("-b",
                      "--boss",
                      dest="boss",
                      help="JID of Boss to connect to.",
                      default="boss@node01")
    (options, args) = parser.parse_args()
    if options.number == None:
        print "ERROR: Missing -n / --number"
        parser.print_help()
        sys.exit()
    
    workers = int(float(options.number))
    start = int(float(options.startnum))
    
    mdir = "/mnt/pvfs2/bthomas"
    if not os.path.isdir(mdir):
        os.mkdir(mdir)
    mydir = os.path.join(mdir, "%s" % tmp_dir)
    if not os.path.isdir(mydir):
        os.mkdir(mydir)
    
    for x in range(workers):
        num = str(x + start)
        if (x + start) < 10:
            num = "00%s" % str(x + start)
        elif (x + start) < 100:
            num = "0%s" % str(x + start)
        
        wkrDir = os.path.join(mydir, "worker%s" % num)
        if not os.path.isdir(wkrDir):
            os.mkdir(wkrDir)
        
        shutil.copy(os.path.join(os.getcwd(), "ar"), wkrDir)
        
        fname = os.path.join(wkrDir, "run.pbs")
        out = open(fname, 'w')
        out.write("#PBS -l nodes=1:ppn=1,mem=150M,walltime=7:00:00\n")
        out.write("#PBS -N wkr%s\n" % str(num))
        out.write("cd ~/wasp\n")
        out.write("sleep 20\n")
        out.write("~/python/bin/python WASP_Worker.py ")
        out.write("--jid=aeolus-worker%s@node01 " % str(num))
        out.write("--password=WASPaeolus-worker%s " % str(num))
        out.write("--dir=%s " % str(wkrDir))
        out.write("--boss=%s " % str(options.boss))
        out.write("--pypath=/home/bthomas/python/bin/python ")
        out.write("\n")
        out.close()
        
        subprocess.call(str("qsub %s" % fname).split())
        time.sleep(5)

