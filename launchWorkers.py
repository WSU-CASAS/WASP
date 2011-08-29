import optparse
import os
import subprocess
import sys


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
    
    mydir = os.getcwd() + "/" + tmp_dir
    if not os.path.isdir(mydir):
        os.mkdir(mydir)
    
    for x in range(workers):
        num = str(x + start)
        if (x + start) < 10:
            num = "00%s" % str(x + start)
        elif (x + start) < 100:
            num = "0%s" % str(x + start)
        
        wkrDir = mydir + "/worker" + num
        if not os.path.isdir(wkrDir):
            os.mkdir(wkrDir)
        
        fname = wkrDir + "/run.pbs"
        out = open(fname, 'w')
        out.write("#PBS -l nodes=1:ppn=1,walltime=24:00:00\n")
        out.write("#PBS -N wkr%s\n" % str(num))
        out.write("cd ~/wasp\n")
        out.write("~/python/bin/python WASP_Worker.py ")
        out.write("--jid=aeolus-worker%s@node01 " % str(num))
        out.write("--password=WASPaeolus-worker%s " % str(num))
        out.write("--dir=%s " % str(wkrDir))
        out.write("--boss=%s " % str(options.boss))
        out.write("\n")
        out.close()


