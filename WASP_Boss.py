import xmpp

import collections
import copy
import datetime
import optparse
import os
import re
import shutil
import sys
import uuid
import xml.dom.minidom



class Job:
    def __init__(self, manager, message, directory):
        self.manager = manager
        self.runId = None
        self.chromosome = None
        self.jobId = None
        self.data_files = None
        dom = xml.dom.minidom.parseString(message)
        job = dom.getElementsByTagName("job")
        self.jobId = str(job[0].getAttribute("id"))
        self.runId = str(job[0].getAttribute("run_id"))
        chrom = dom.getElementsByTagName("chromosome_file")
        self.chromosome = str(chrom[0].toxml())
        df = dom.getElementsByTagName("data_files")
        self.data_files = str(df[0].toxml())
        return
    
    def completed(self):
        self.jobId = None
        self.chromosome = None
        self.runId = None
        self.data_files = None
        return
    
    def __str__(self):
        job = "<job "
        job += "id=\"%s\" " % str(self.jobId)
        job += "run_id=\"%s\" " % str(self.runId)
        job += "manager=\"%s\" " % str(self.manager)
        job += ">"
        job += str(self.chromosome)
        job += str(self.data_files)
        job += "</job>"
        return job



class Boss:
    def __init__(self, options):
        self.name = "WASP Boss"
        self.username = str(options.jid)
        self.password = str(options.password)
        self.directory = str(options.workingDir)
        self.xmpp = xmpp.Connection(self.name)
        self.xmpp.set_authd_callback(self.has_connected)
        self.xmpp.set_buddy_quit_callback(self.buddy_quit)
        self.xmpp.set_direct_msg_callback(self.message)
        self.xmpp.set_finish_callback(self.finish)
        self.workers = list()
        self.readyWorkers = collections.deque()
        self.workerJobs = dict()
        self.managers = list()
        self.jobs = collections.deque()
        return
    
    def connect(self):
        self.xmpp.connect(self.username, self.password)
        return
    
    def has_connected(self):
        self.workers = list()
        self.managers = list()
        self.readyWorkers = collections.deque()
        self.xmpp.callLater(1, self.send_work)
        return
    
    def finish(self):
        self.xmpp.disconnect()
        return
    
    def buddy_quit(self, name):
        if name in self.workers:
            self.workers.remove(name)
        if name in self.workerJobs:
            self.jobs.appendleft(copy.copy(self.workerJobs[name]))
            del self.workerJobs[name]
        if name in self.readyWorkers:
            self.readyWorkers.remove(name)
        if name in self.managers:
            self.managers.remove(name)
            rmJobs = list()
            for x in range(len(self.jobs)):
                if self.jobs[x].manager == name:
                    rmJobs.append(x)
            rmJobs.reverse()
            for x in rmJobs:
                del self.jobs[x]
        return
    
    def send_work(self):
        for x in range(len(self.readyWorkers)):
            if len(self.jobs) > 0:
                w = self.readyWorkers.popleft()
                j = self.jobs.popleft()
                self.workerJobs[w] = j
                self.xmpp.send(str(j), w)
        self.xmpp.callLater(5, self.send_work)
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
    
    def request_file(self, fileDom, name):
        fname = str(fileDom.getAttribute("filename"))
        rid = str(fileDom.getAttribute("run_id"))
        dir = os.path.join(self.directory, rid)
        if os.path.isfile(os.path.join(dir, fname)):
            msg = "<send_file "
            msg += "filename=\"%s\" " % fname
            msg += "run_id=\"%s\" >" % rid
            data = open(os.path.join(dir, fname))
            info = data.readlines()
            msg += "".join(info)
            data.close()
            msg += "</send_file>"
            self.xmpp.send(msg, name)
        return
    
    def message(self, msg, name):
        print "Msg from:", name
        dom = xml.dom.minidom.parseString(msg)
        type = dom.firstChild.nodeName
        #type = "worker_ready|job|job_completed"
        print "    type =",type
        if type == "job":
            self.jobs.append(Job(name, msg, self.directory))
        elif type == "job_completed":
            if name in self.workerJobs:
                j = self.workerJobs[name]
                j.completed()
                self.xmpp.send(str(msg), j.manager)
                j = None
                del self.workerJobs[name]
                self.readyWorkers.append(name)
        elif type == "worker_ready":
            if name not in self.workers:
                self.workers.append(name)
            if name not in self.readyWorkers:
                self.readyWorkers.append(name)
        elif type == "send_file":
            self.recv_file(dom.firstChild)
        elif type == "request_file":
            self.request_file(dom.firstChild, name)
        elif type == "request_info":
            message = "managers"
            message += "\n    ".join(self.managers)
            message += "\n" + "*"*20 
            message += "workers"
            message += "\n    ".join(self.workers)
            message += "\n" + "*"*20
            message += "ready workers"
            message += "\n    ".join(self.readyWorkers)
            message += "\n"
            self.xmpp.send(message, name)
        return


if __name__ == "__main__":
    parser = optparse.OptionParser(usage="usage: %prog [options]")
    parser.add_option("--jid",
                      dest="jid",
                      help="Jabber ID.")
    parser.add_option("--password",
                      dest="password",
                      help="Jabber ID password.")
    parser.add_option("--workingDir",
                      dest="workingDir",
                      help="Working directory for files.")
    (options, args) = parser.parse_args()
    if None in [options.jid, options.password, options.workingDir]:
        if options.jid == None:
            print "ERROR: Missing --jid"
        if options.password == None:
            print "ERROR: Missing --password"
        if options.workingDir == None:
            print "ERROR: Missing --workingDir"
        parser.print_help()
        sys.exit()
    
    theBoss = Boss(options)
    theBoss.connect()

