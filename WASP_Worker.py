import xmpp

import datetime
import optparse
import os
import Queue
import random
import re
import shutil
import subprocess
import sys
import threading
import time
import uuid
import xml.dom.minidom



class Slave(threading.Thread):
    def __init__(self, pypath, directory, tmp_dir, data_queue, msg_queue):
        threading.Thread.__init__(self)
        self.mailbox = data_queue
        self.send_msg = msg_queue
        self.pypath = pypath
        self.directory = directory
        self.tmp_dir = tmp_dir
        self.first_job = True
        return
    
    def run(self):
        print self, "Slave running!"
        while True:
            data = self.mailbox.get()
            if data == "quit":
                return
            if self.first_job:
                self.first_job = False
                time.sleep(int(60.0 * random.random()))
            dom = xml.dom.minidom.parseString(data)
            self.execute_job(dom.firstChild)
        return
    
    def stop(self):
        self.mailbox.put("quit")
        self.join()
        return
    
    def execute_job(self, job):
        job_id = str(job.getAttribute("id"))
        job_run_id = str(job.getAttribute("run_id"))
        job_directory = os.path.join(self.tmp_dir, job_id)
        crfDom = job.getElementsByTagName("chromosome_file")
        job_chromosome = crfDom[0].getAttribute("filename")
        chromosome_xml = str(crfDom[0].firstChild.toxml())
        crfDom = None
        try:
            if not os.path.isdir(job_directory):
                os.mkdir(job_directory)
            
            out = open(os.path.join(job_directory, job_chromosome), 'w')
            out.write(chromosome_xml)
            out.close()
            
            dfDom = job.getElementsByTagName("data_files")
            ofDom = job.getElementsByTagName("orig_files")
            job_files = str(dfDom[0].firstChild.toxml()).split(",")
            job_origs = str(ofDom[0].firstChild.toxml()).split(",")
            #for jf in (job_files + job_origs):
            #    absName = os.path.join(self.directory, self.job_run_id, jf)
            #    if absName not in self.valid_files:
            #        if not os.path.isfile(absName):
            #            self.request_file(jf, job_run_id)
            #            self.waiting_on_files += 1
            #        else:
            #            self.valid_files.append(absName)
            if "site.xml" in job_files:
                job_files.remove("site.xml")
            
            emulated = list()
            p = None
            for df in job_files:
                outFile = os.path.join(job_directory, "%s.xml" % str(uuid.uuid4().hex))
                cmd = "%s CAMS_Emulator.py " % str(self.pypath)
                cmd += "--site=%s " % os.path.join(self.directory,
                                                   job_run_id,
                                                   "site.xml")
                cmd += "--movement=%s " % os.path.join(self.directory,
                                                       job_run_id,
                                                       df)
                cmd += "--chromosome=%s " % os.path.join(job_directory,
                                                         job_chromosome)
                cmd += "--output=%s" % outFile
                
                p = subprocess.Popen(str(cmd).split())
                emulated.append(outFile)
                
                while p.poll() == None:
                    time.sleep(1)
            
            p = None
            
            cmd = "cp %s %s" % (os.path.join(self.directory, "ar"),
                                os.path.join(job_directory, "ar"))
            subprocess.call(str(cmd).split())
            
            cmd = "%s GA_Fitness.py " % str(self.pypath)
            cmd += "--files=%s " % ",".join(emulated)
            cmd += "--chromosome=%s " % os.path.join(job_directory,
                                                     job_chromosome)
            cmd += "--site=%s " % os.path.join(self.directory,
                                               job_run_id,
                                               "site.xml")
            cmd += "--method=CookAr "
            cmd += "--work=%s" % str(job_directory)
            p = subprocess.Popen(str(cmd).split())
            
            while p.poll() == None:
                time.sleep(1)
            
            p = None
            emulated = None
            
            chrom_data = ""
            if os.path.isfile(os.path.join(job_directory, job_chromosome)):
                data = open(os.path.join(job_directory, job_chromosome))
                info = data.readlines()
                chrom_data = "".join(info)
                data.close()
            
            if chrom_data != "":
                chromosome_xml = chrom_data
            
            shutil.rmtree(job_directory)
        except:
            msg = "asdf"
        
        msg = "<job_completed id=\"%s\" >" % str(job_id)
        msg += "<data filename=\"%s\" >" % str(job_chromosome)
        msg += chromosome_xml
        msg += "</data></job_completed>"
        self.send_msg.put(msg)
        job_chromosome = None
        job_directory = None
        job_files = None
        job_origs = None
        job_id = None
        job_run_id = None
        return



class Worker:
    def __init__(self, options):
        self.name = "WASP Worker"
        self.started = datetime.datetime.now()
        self.numjobs = 0
        self.queue_job = Queue.Queue()
        self.queue_msg = Queue.Queue()
        self.workers = list()
        self.username = str(options.jid)
        self.password = str(options.password)
        self.boss = str(options.boss)
        self.directory = str(options.dir)
        self.numThreads = int(float(options.threads))
        self.tmp_dir = os.path.join("/tmp", self.username)
        if not os.path.isdir(self.tmp_dir):
            os.mkdir(self.tmp_dir)
        self.pypath = str(options.pypath)
        self.xmpp = xmpp.Connection(self.name)
        self.xmpp.set_authd_callback(self.has_connected)
        self.xmpp.set_direct_msg_callback(self.message)
        self.xmpp.set_finish_callback(self.finish)
        self.waiting_on_files = 0
        self.p = list()
        self.tasks = list()
        self.emulated = list()
        self.has_job = False
        self.job_id = None
        self.job_run_id = None
        self.job_files = None
        self.job_origs = None
        self.job_directory = None
        self.job_chromosome = None
        self.valid_files = list()
        for x in range(self.numThreads):
            s = Slave(self.pypath, self.directory, self.tmp_dir,
                      self.queue_job, self.queue_msg)
            self.workers.append(s)
            s.start()
        return
    
    def connect(self):
        self.xmpp.connect(self.username, self.password)
        return
    
    def has_connected(self):
        self.xmpp.subscribe_buddy(self.boss)
        if not self.has_job:
            msg = "<worker_ready threads=\"%s\" />" % str(self.numThreads)
            self.xmpp.send(msg, self.boss)
        self.xmpp.callLater(5, self.check_for_messages)
        return
    
    def check_time(self):
        max = datetime.timedelta(hours=6)
        life = datetime.datetime.now() - self.started
        avgTime = life.seconds
        if self.numjobs > 0:
            avgTime = life.seconds / self.numjobs
        #print "average job time in seconds: ", str(avgTime)
        workTime = self.started + life
        workTime += datetime.timedelta(seconds=(avgTime*3))
        maxTime = self.started + max
        #print "lifetime: ", str(life)
        #print "workTime: ", str(workTime)
        #print "maxTime:  ", str(maxTime)
        if maxTime < workTime:
            self.xmpp.callLater(0, self.respawn)
        return
    
    def respawn(self):
        fname = os.path.abspath(os.path.join(self.directory, "run.pbs"))
        subprocess.call(str("qsub %s" % fname).split())
        self.xmpp.callLater(0, self.finish)
        return
    
    def finish(self):
        self.xmpp.disconnect()
        for x in range(len(self.workers)):
            self.queue_job.put("quit")
        for s in self.workers:
            s.stop()
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
    
    def check_for_messages(self):
        if not self.queue_msg.empty():
            try:
                msg = self.queue_msg.get(timeout=1)
                self.xmpp.send(msg, self.boss)
                self.xmpp.callLater(1, self.check_time)
            except:
                msg = ""
        self.xmpp.callLater(1, self.check_for_messages)
        return
    
    def message(self, msg, name):
        print "Msg from:", name
        if msg == "quit":
            self.xmpp.callLater(0, self.finish)
            return
        dom = xml.dom.minidom.parseString(msg)
        type = dom.firstChild.nodeName
        if type == "send_file":
            self.recv_file(dom.firstChild)
            self.waiting_on_files -= 1
        elif type == "job":
            self.queue_job.put(msg)
            self.numjobs += 1
            #self.get_job(dom.firstChild)
        return
    
    def get_job(self, job):
        self.has_job = True
        self.numjobs += 1
        self.waiting_on_files = 0
        self.job_id = str(job.getAttribute("id"))
        self.job_run_id = str(job.getAttribute("run_id"))
        self.job_directory = os.path.join(self.tmp_dir, self.job_id)
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
        ofDom = job.getElementsByTagName("orig_files")
        self.job_files = str(dfDom[0].firstChild.toxml()).split(",")
        self.job_origs = str(ofDom[0].firstChild.toxml()).split(",")
        for jf in (self.job_files + self.job_origs):
            absName = os.path.join(self.directory, self.job_run_id, jf)
            if absName not in self.valid_files:
                if not os.path.isfile(absName):
                    self.request_file(jf, self.job_run_id)
                    self.waiting_on_files += 1
                else:
                    self.valid_files.append(absName)
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
        
        self.emulated = list()
        self.p = list()
        self.tasks = list()
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
            self.tasks.append(str(cmd))
            #self.p.append(subprocess.Popen(str(cmd).split()))
            self.emulated.append(outFile)
        
        t = self.tasks.pop()
        self.p.append(subprocess.Popen(str(t).split()))
        
        self.xmpp.callLater(1, self.wait_emulator)
        return
    
    def wait_emulator(self):
        count = 0
        for x in range(len(self.p)):
            if self.p[x].poll() == None:
                count += 1
        if count == 0:
            if len(self.tasks) > 0:
                count = 1
                t = self.tasks.pop()
                self.p[-1] = subprocess.Popen(str(t).split())
        if count > 0:
            self.xmpp.callLater(1, self.wait_emulator)
            return
        
        self.p = list()
        self.tasks = list()
        
        cmd = "cp %s %s" % (os.path.join(self.directory, "ar"),
                            os.path.join(self.job_directory, "ar"))
        subprocess.call(str(cmd).split())
        
        cmd = "%s GA_Fitness.py " % str(self.pypath)
        cmd += "--files=%s " % ",".join(self.emulated)
        cmd += "--chromosome=%s " % os.path.join(self.job_directory,
                                                 self.job_chromosome)
        cmd += "--site=%s " % os.path.join(self.directory,
                                           self.job_run_id,
                                           "site.xml")
        cmd += "--method=CookAr "
        cmd += "--work=%s" % str(self.job_directory)
        self.p.append(subprocess.Popen(str(cmd).split()))
        
        self.xmpp.callLater(1, self.wait_fitness)
        return
    
    def wait_fitness(self):
        count = 0
        for x in range(len(self.p)):
            if self.p[x].poll() == None:
                count += 1
        if count > 0:
            self.xmpp.callLater(1, self.wait_fitness)
            return
        
        self.emulated = list()
        self.p = list()
        
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
        
        self.has_job = False
        self.xmpp.callLater(0, self.check_time)
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
    parser.add_option("--threads",
                      dest="threads",
                      help="Number of threads to use.",
                      default="1")
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
    if int(float(options.threads)) < 1:
        options.threads = 1
    
    work = Worker(options)
    work.connect()

