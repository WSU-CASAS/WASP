import xmpp

import datetime
import optparse
import os
import random
import re
import shutil
import subprocess
import sys
import uuid
import xml.dom.minidom



class Worker:
    def __init__(self, options):
        self.name = "WASP Worker"
        self.started = datetime.datetime.now()
        self.username = str(options.jid)
        self.password = str(options.password)
        self.boss = str(options.boss)
        self.directory = str(options.dir)
        self.pypath = str(options.pypath)
        self.xmpp = xmpp.Connection(self.name)
        self.xmpp.set_authd_callback(self.has_connected)
        self.xmpp.set_direct_msg_callback(self.message)
        self.xmpp.set_finish_callback(self.finish)
        self.waiting_on_files = 0
        self.job_id = None
        self.job_run_id = None
        self.job_files = None
        self.job_directory = None
        self.job_chromosome = None
        return
    
    def connect(self):
        self.xmpp.connect(self.username, self.password)
        return
    
    def has_connected(self):
        self.xmpp.send("<worker_ready />", self.boss)
        return
    
    def finish(self):
        self.xmpp.disconnect()
        return
    
    def request_file(self, filename, run_id):
        msg = "<request_file "
        msg += "filename=\"%s\" " % str(filename)
        msg += "run_id=\"%s\" />" % str(run_id)
        self.xmpp.send(msg, self.boss)
        return
    
    def recv_file(self, fileDom):
        fname = str(fileDom.getAttribute("filename"))
        rid = str(fileDom.getAttribute("run_id"))
        dir = os.path.join(self.directory, rid)
        if not os.path.isdir(dir):
            os.mkdir(dir)
        out = open(os.path.join(dir, fname), 'w')
        data = fileDom.firstChild
        out.write(data.toxml())
        out.close()
        return
    
    def message(self, msg, name):
        print "Msg from:", name
        dom = xml.dom.minidom.parseString(msg)
        type = dom.firstChild.nodeName
        if type == "send_file":
            self.recv_file(dom.firstChild)
            self.waiting_on_files -= 1
        elif type == "job":
            self.get_job(dom.firstChild)
        return
    
    def get_job(self, job):
        self.waiting_on_files = 0
        self.job_id = str(job.getAttribute("id"))
        self.job_run_id = str(job.getAttribute("run_id"))
        self.job_directory = os.path.join(self.directory, self.job_id)
        if not os.path.isdir(self.job_directory):
            os.mkdir(self.job_directory)
        crfDom = job.getElementsByTagName("chromosome_file")
        self.job_chromosome = crfDom[0].getAttribute("filename")
        out = open(os.path.join(self.job_directory, self.job_chromosome), 'w')
        data = crfDom[0].firstChild
        out.write(data.toxml())
        out.close()
        data = None
        dfDom = job.getElementsByTagName("data_files")
        self.job_files = str(dfDom[0].firstChild.toxml()).split(",")
        for jf in self.job_files:
            absName = os.path.join(self.directory, self.job_run_id, jf)
            if not os.path.isfile(absName):
                self.request_file(jf, self.job_run_id)
                self.waiting_on_files += 1
        if "site.xml" in self.job_files:
            self.job_files.remove("site.xml")
        self.xmpp.callLater(1, self.do_job)
        return
    
    def do_job(self):
        if self.waiting_on_files > 0:
            self.xmpp.callLater(1, self.do_job)
            return
        
        if self.job_chromosome == None:
            return
        
        emulated = list()
        #for df in dfiles.keys():
        for df in self.job_files:
            outFile = os.path.join(self.job_directory, "%s.xml" % str(uuid.uuid4().hex))
            cmd = "%s CAMS_Emulator.py " % str(self.pypath)
            cmd += "--site=%s " % os.path.join(self.directory,
                                               self.job_run_id,
                                               "site.xml")
            cmd += "--movement=%s " % os.path.join(self.directory,
                                                   self.job_run_id,
                                                   df)
            cmd += "--chromosome=%s " % os.path.join(self.job_directory,
                                                     self.job_chromosome)
            cmd += "--output=%s" % outFile
            subprocess.call(str(cmd).split())
            emulated.append(outFile)
        
        cmd = "cp %s %s" % (os.path.join(self.directory, "ar"),
                            os.path.join(self.job_directory, "ar"))
        subprocess.call(str(cmd).split())
        
        cmd = "%s GA_Fitness.py " % str(self.pypath)
        cmd += "--files=%s " % ",".join(emulated)
        cmd += "--chromosome=%s " % os.path.join(self.job_directory,
                                                 self.job_chromosome)
        cmd += "--site=%s " % os.path.join(self.directory,
                                           self.job_run_id,
                                           "site.xml")
        cmd += "--method=CookAr "
        cmd += "--work=%s" % str(self.job_directory)
        subprocess.call(str(cmd).split())
        #print cmd
        #print os.listdir(self.directory)
        
        msg = "<job_completed>"
        msg += "<data filename=\"%s\" >" % str(self.job_chromosome)
        data = open(os.path.join(self.job_directory, self.job_chromosome))
        info = data.readlines()
        msg += "".join(info)
        data.close()
        msg += "</data></job_completed>"
        self.xmpp.send(msg, self.boss)
        
        shutil.rmtree(self.job_directory)
        self.job_chromosome = None
        self.job_directory = None
        self.job_files = None
        self.job_id = None
        self.job_run_id = None
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
    parser.add_option("--boss",
                      dest="boss",
                      help="JID of Boss.",
                      default="boss@node01")
    parser.add_option("--pypath",
                      dest="pypath",
                      help="Python executable path.",
                      default="/usr/bin/python")
    (options, args) = parser.parse_args()
    if None in [options.jid, options.password, options.dir]:
        if options.jid == None:
            print "ERROR: Missing --jid"
        if options.password == None:
            print "ERROR: Missing --password"
        if options.dir == None:
            print "ERROR: Missing --dir"
        parser.print_help()
        sys.exit()
    
    work = Worker(options)
    work.connect()

