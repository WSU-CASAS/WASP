#*****************************************************************************#
#**
#**  WASP Boss
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
    def __init__(self, manager, message, id):
        self.manager = manager
        self.message = str(message)
        self.id = str(id)
        return
    
    def completed(self):
        self.message = None
        return
    
    def __str__(self):
        return self.message

class Worker:
    def __init__(self, threads="1"):
        self.threads = int(float(threads))
        self.jobs = dict()
        self.ready = True
        return
    
    def finish_job(self, id):
        manager = ""
        if id in self.jobs:
            manager = str(self.jobs[id].manager)
            del self.jobs[id]
        if len(self.jobs) < self.threads:
            self.ready = True
        else:
            self.ready = False
        return manager
    
    def remove_manager(self, manager):
        to_remove = list()
        for j in self.jobs.keys():
            if manager == self.jobs[j].manager:
                to_remove.append(j)
        for j in to_remove:
            del self.jobs[j]
        if len(self.jobs) < self.threads:
            self.ready = True
        else:
            self.ready = False
        return
    
    def add_job(self, job):
        success = False
        if job.id not in self.jobs:
            self.jobs[job.id] = job
            success = True
        if len(self.jobs) < self.threads:
            self.ready = True
        else:
            self.ready = False
        return success
    
    def reset(self):
        old_jobs = list()
        for x in self.jobs.keys():
            old_jobs.append(copy.deepcopy(self.jobs[x]))
        self.jobs = dict()
        self.ready = True
        return old_jobs



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
        self.workers = dict()
        self.readyWorkers = collections.deque()
        self.workerJobs = dict()
        self.workerThreads = 0
        self.managers = list()
        self.jobs = collections.deque()
        self.job_count = 0
        self.started = False
        return
    
    def connect(self):
        self.xmpp.connect(self.username, self.password)
        return
    
    def has_connected(self):
        if not self.started:
            self.started = True
            self.xmpp.callLater(1, self.send_work)
            self.xmpp.callLater(300, self.check_workers)
            self.xmpp.callLater(300, self.update_status)
        return
    
    def finish(self):
        self.xmpp.disconnect()
        return
    
    def update_status(self):
        self.xmpp.set_status("%s layouts tested!" % str(self.job_count))
        self.xmpp.callLater(600, self.update_status)
        return
    
    def buddy_quit(self, name):
        print "buddy_quit( %s )" % str(name)
        print "workers:      ", len(self.workers)
        print "workerThreads:", str(self.workerThreads)
        print "readyWorkers: ", len(self.readyWorkers)
        print "len(jobs):    ", len(self.jobs)
        if name in self.workers:
            self.workerThreads -= self.workers[name].threads
            jobs = self.workers[name].reset()
            for j in jobs:
                self.jobs.appendleft(copy.copy(j))
            del self.workers[name]
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
                self.jobs.remove(self.jobs[x])
            for x in self.workers.keys():
                self.workers[x].remove_manager(name)
                if self.workers[x].ready and x not in self.readyWorkers:
                    self.readyWorkers.append(x)
        return
    
    def check_workers(self):
        for wkr in self.workerJobs.keys():
            self.xmpp.query_buddy(wkr)
        for mgr in self.managers:
            self.xmpp.query_buddy(mgr)
        self.xmpp.callLater(300, self.check_workers)
        return
    
    def send_work(self):
        if len(self.readyWorkers) > 0 and len(self.jobs) > 0:
            w = self.readyWorkers.popleft()
            j = self.jobs.popleft()
            if self.workers[w].add_job(j):
                self.xmpp.send(str(j), w)
                if self.workers[w].ready:
                    self.readyWorkers.append(w)
            self.xmpp.callLater(0, self.send_work)
        else:
            self.xmpp.callLater(1, self.send_work)
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
        if name == "bthomas@node01":
            if msg == "quit-now":
                for x in self.workers.keys():
                    self.xmpp.send("quit", x)
                for x in range(len(self.managers)):
                    self.xmpp.send("quit-now", self.managers[x])
                return
            elif msg == "quit-workers":
                for x in self.workers.keys():
                    self.xmpp.send("quit", x)
                return
            elif msg == "quit-managers":
                for x in range(len(self.managers)):
                    self.xmpp.send("quit-now", self.managers[x])
                return
            elif msg == "quit-generation":
                for x in range(len(self.managers)):
                    self.xmpp.send("quit-generation", self.managers[x])
                return
            elif msg == "conditional-refresh":
                for x in range(len(self.managers)):
                    self.xmpp.send("conditional-refresh", self.managers[x])
                return
            elif re.search('manager-refresh-', msg):
                stuff = str(msg).split('-')
                if len(stuff) >= 3:
                    self.xmpp.send("refresh", str(stuff[2]).strip())
                return
            elif re.search('manager-refresh', msg):
                for x in range(len(self.managers)):
                    self.xmpp.send("refresh", self.managers[x])
                return
        dom = xml.dom.minidom.parseString(msg)
        type = dom.firstChild.nodeName
        print "Msg from:", name, "    type =", type
        if type == "job":
            id = dom.firstChild.getAttribute("id")
            self.jobs.append(Job(name, msg, id))
        elif type == "job_completed":
            self.job_count += 1
            id = dom.firstChild.getAttribute("id")
            if name in self.workers:
                manager = self.workers[name].finish_job(id)
                if manager != "":
                    self.xmpp.send(str(msg), manager)
                if self.workers[name].ready and name not in self.readyWorkers:
                    self.readyWorkers.append(name)
        elif type == "worker_ready":
            try:
                threads = dom.firstChild.getAttribute("threads")
            except:
                threads = "1"
            if name not in self.workers:
                self.workers[name] = Worker(threads)
                self.workerThreads += int(float(threads))
            if self.workers[name].ready and name not in self.readyWorkers:
                self.readyWorkers.append(name)
            if len(self.workers[name].jobs) > 0:
                old_jobs = self.workers[name].reset()
                for j in old_jobs:
                    self.jobs.appendleft(copy.copy(j))
        elif type == "send_file":
            if name not in self.managers:
                self.managers.append(name)
            self.recv_file(dom.firstChild)
        elif type == "request_file":
            self.request_file(dom.firstChild, name)
        elif type == "info":
            message = "managers: %s\n" % str(len(self.managers))
            message += "workers: %s\n" % str(len(self.workers))
            message += "workerThreads: %s\n" % str(self.workerThreads)
            message += "ready workers: %s\n" % str(len(self.readyWorkers))
            message += "jobs: %s" % str(len(self.jobs))
            self.xmpp.send(message, name)
        elif type == "request_info":
            message = "managers"
            message += "\n    ".join(self.managers)
            message += "\n" + "*"*20 
            message += "workers"
            message += "\n    ".join(self.workers.keys())
            message += "\n" + "*"*20
            message += "ready workers"
            message += "\n    ".join(self.readyWorkers)
            message += "\n"
            self.xmpp.send(message, name)
        elif type == "get_job_counts":
            message = "managers"
            m = dict()
            for x in range(len(self.managers)):
                m[self.managers[x]] = 0
            for n in self.workers.keys():
                for j in self.workers[n].jobs.keys():
                    m[self.workers[n].jobs[j].manager] += 1
            for n in m.keys():
                message += "\n%s: %s" % (n, str(m[n]))
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

