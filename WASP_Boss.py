import xmpp

import collections
import copy
import datetime
import optparse
import os
import re
import sys
import uuid
import xml.dom.minidom



class Job:
    def __init__(self, manager, message, directory):
        self.manager = manager
        self.command = None
        self.directory = directory
        self.files = list()
        self.jobId = None
        dom = xml.dom.minidom.parseString(message)
        job = dom.getElementsByTagName("job")
        self.command = str(job[0].getAttribute("command"))
        self.jobId = str(job[0].getAttribute("id"))
        children = job[0].childNodes
        for child in children:
            fname = child.getAttribute("filename")
            if fname not in self.files:
                self.files.append(fname)
                out = open(os.path.join(self.directory, fname), 'w')
                data = child.firstChild
                out.write(data.toxml())
                out.close()
        return
    
    def completed(self):
        for rmFile in self.files:
            os.remove(os.path.join(self.directory, rmFile))
        self.command = None
        self.directory = None
        self.files = None
        self.jobId = None
        return
    
    def __str__(self):
        job = "<job "
        job += "id=\"%s\" " % str(self.jobId)
        job += "manager=\"%s\" " % str(self.manager)
        job += "command=\"%s\" " % str(self.command)
        job += ">"
        for f in self.files:
            job += "<data "
            job += "filename=\"%s\" >" % str(f)
            data = open(os.path.join(self.directory, f))
            info = data.readlines()
            job += "".join(info)
            data.close()
            job += "</data>"
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
    
    def message(self, msg, name):
        dom = xml.dom.minidom.parseString(msg)
        type = dom.nodeName
        #type = "worker_ready|job|job_completed"
        if type == "job":
            self.jobs.append(Command(name, msg, self.directory))
        elif type == "job_completed:":
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

