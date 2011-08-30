import xmpp

import datetime
import optparse
import os
import random
import re
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
        self.files = list()
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
    
    def message(self, msg, name):
        print "Msg from:", name
        dom = xml.dom.minidom.parseString(msg)
        job = dom.firstChild
        command = str(job.getAttribute("command"))
        children = job.childNodes
        for child in children:
            fname = child.getAttribute("filename")
            print "    ", fname
            if fname not in self.files:
                self.files.append(fname)
            out = open(os.path.join(self.directory, fname), 'w')
            data = child.firstChild
            out.write(data.toxml())
            out.close()
        dfiles = dict()
        for f in self.files:
            if f != command and f != "site.xml":
                dfiles[f] = "%s.xml" % str(uuid.uuid4().hex)
        
        emulated = list()
        for df in dfiles.keys():
            cmd = "%s CAMS_Emulator.py " % str(self.pypath)
            cmd += "--site=%s " % os.path.join(self.directory, "site.xml")
            cmd += "--movement=%s " % os.path.join(self.directory, df)
            cmd += "--chromosome=%s " % os.path.join(self.directory, command)
            cmd += "--output=%s" % os.path.join(self.directory, dfiles[df])
            subprocess.call(str(cmd).split())
            #print cmd
            #print os.listdir(self.directory)
            emulated.append(str(dfiles[df]))
        
        cmd = "%s GA_Fitness.py " % str(self.pypath)
        cmd += "--files=%s " % ",".join(emulated)
        cmd += "--chromosome=%s " % str(command)
        cmd += "--site=site.xml "
        cmd += "--method=CookAr "
        cmd += "--work=%s" % str(self.directory)
        subprocess.call(str(cmd).split())
        #print cmd
        #print os.listdir(self.directory)
        
        msg = "<job_completed>"
        msg += "<data filename=\"%s\" >" % str(command)
        data = open(os.path.join(self.directory, command))
        info = data.readlines()
        msg += "".join(info)
        data.close()
        msg += "</data></job_completed>"
        self.xmpp.send(msg, self.boss)
        
        for fname in self.files:
            os.remove(os.path.join(self.directory, fname))
        self.files = list()
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

