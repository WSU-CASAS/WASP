import sys

if "pygtk" in sys.modules:
    from twisted.internet import gtk2reactor
    gtk2reactor.install()

from twisted.words.protocols.jabber import client, jid, xmlstream
from twisted.words.xish import domish
from twisted.internet import reactor

import datetime
import re
import signal
import uuid
import xml.dom.minidom
import xml.etree.ElementTree as ETree
import xml.parsers.expat

def getText(nodelist):
    rc = ""
    for node in nodelist:
        if node.nodeType == node.TEXT_NODE:
            rc = rc + node.data
    return str(rc)

def getData(node, message):
    result = ""
    try:
        dom = xml.dom.minidom.parseString(message)
        xmsg = dom.getElementsByTagName(node)
        if xmsg.length > 0:
            result = getText(xmsg[0].childNodes)
    except xml.parsers.expat.ExpatError:
        result = ""
    return result

def dict_to_xml(oDict):
    if len(oDict) != 1:
        print "ERROR: dict_to_xml() needs dict() of len=1"
        return None
    key = oDict.keys()[0]
    root = ETree.Element(key)
    dict_to_xml_children(oDict[key], key, root)
    return root

def dict_to_xml_children(obj, name, xElem):
    if type(obj) == type(list()):
        for dup in obj:
            if type(dup) == type(dict()):
                elem = ETree.SubElement(xElem, name)
                dict_to_xml_children(dup, name, elem)
            else:
                dict_to_xml_children(dup, name, xElem)
    elif type(obj) == type(dict()):
        for key in obj.keys():
            if type(obj[key]) != type(list()):
                elem = ETree.SubElement(xElem, key)
                dict_to_xml_children(obj[key], key, elem)
            else:
                for dup in obj[key]:
                    elem = ETree.SubElement(xElem, key)
                    dict_to_xml_children(dup, key, elem)
    elif type(obj) == type(str()):
        xElem.text = obj
    return

def xmlstr_to_dict(message):
    try:
        xElem = ETree.fromstring(message)
        newDict = xml_to_dict(xElem, dict())
    except xml.parsers.expat.ExpatError:
        newDict = dict()
    return newDict

def xml_to_dict(xElem, newDict=dict()):
    position = None
    if xElem.tag in newDict:
        if type(newDict[xElem.tag]) != type(list()):
            newDict[xElem.tag] = [newDict[xElem.tag]]
        position = len(newDict[xElem.tag])
        if xElem.text:
            newDict[xElem.tag].append(xElem.text)
        else:
            newDict[xElem.tag].append("")
    else:
        if xElem.text:
            newDict[xElem.tag] = xElem.text
        else:
            newDict[xElem.tag] = dict()
    children = xElem.getchildren()
    if children:
        if position == None:
            newDict[xElem.tag] = dict()
        else:
            newDict[xElem.tag][position] = dict()
        for child in children:
            if position == None:
                newDict[xElem.tag] = xml_to_dict(child, newDict[xElem.tag])
            else:
                newDict[xElem.tag][position] = xml_to_dict(child, newDict[xElem.tag][position])
    if newDict[xElem.tag] == dict():
        newDict[xElem.tag] = ""
    return newDict


class Data:
    def clean(self, msg):
        msg = re.sub('_#!#_', '', msg)
        return msg


class Event(Data):
    by = ""
    category = ""
    stamp = ""
    location = ""
    message = ""
    serial = ""
    mtype = ""
    uuid = ""
    def __init__(self, msg):
        data = xmlstr_to_dict(msg)
        if data != dict():
            self.build_event(data)
        return
    
    def build_event(self, data):
        self.by = self.clean(data['publish']['data']['event']['by'])
        self.category = self.clean(data['publish']['data']['event']['category'])
        self.stamp = self.clean(data['publish']['data']['event']['epoch'])
        self.location = self.clean(data['publish']['data']['event']['location'])
        self.message = self.clean(data['publish']['data']['event']['message'])
        self.serial = self.clean(data['publish']['data']['event']['serial'])
        self.mtype = self.clean(data['publish']['data']['event']['type'])
        self.uuid = self.clean(data['publish']['data']['event']['uuid'])
        if self.by == "":
            self.by = "unknown"
        if self.category == "":
            self.category = "unknown"
        if self.stamp == "":
            self.stamp = datetime.datetime.now()
        else:
            self.stamp = datetime.datetime.fromtimestamp(float(self.stamp))
        if self.location == "":
            self.location = "unknown"
        if self.message == "":
            self.message = "unknown"
        if self.serial == "":
            self.serial = "unknown"
        if self.mtype == "":
            self.mtype = "unknown"
        if self.uuid == "":
            self.uuid = str(uuid.uuid4().hex)
        return
    
    def get_scribe_event(self):
        msg = "EVENT"
        msg += "_#!#_%s" % self.uuid
        msg += "_#!#_%s" % str(self.stamp)
        msg += "_#!#_%s" % self.serial
        msg += "_#!#_%s" % self.location
        msg += "_#!#_%s" % self.message
        msg += "_#!#_%s" % self.by
        msg += "_#!#_%s" % self.category
        msg += "_#!#_%s" % self.mtype
        return msg


class Tag(Event):
    createdBy = ""
    labelName = ""
    dsetName = ""
    expirName = ""
    def __init__(self, msg):
        data = xmlstr_to_dict(msg)
        if data != dict():
            self.build_event(data)
            self.build_tag(data)
        return
    
    def build_tag(self, data):
        self.createdBy = self.clean(data['publish']['data']['tag']['created_by'])
        self.labelName = self.clean(data['publish']['data']['tag']['label']['name'])
        self.labelValue = self.clean(data['publish']['data']['tag']['label']['value'])
        self.dsetName = self.clean(data['publish']['data']['tag']['dataset']['name'])
        self.expirName = self.clean(data['publish']['data']['tag']['experiment']['name'])
        if self.createdBy == "":
            self.createdBy = "unknown"
        if self.dsetName == "":
            self.dsetName = "unknown"
        if self.expirName == "":
            self.expirName = "unknown"
        return
    
    def get_scribe_tag(self):
        msg = "TAG"
        msg += "_#!#_%s" % self.createdBy
        msg += "_#!#_%s" % self.labelName
        msg += "_#!#_%s" % self.labelValue
        msg += "_#!#_%s" % self.dsetName
        msg += "_#!#_%s" % self.expirName
        msg += "_#!#_%s" % self.uuid
        msg += "_#!#_%s" % str(self.stamp)
        msg += "_#!#_%s" % self.serial
        msg += "_#!#_%s" % self.location
        msg += "_#!#_%s" % self.message
        msg += "_#!#_%s" % self.by
        msg += "_#!#_%s" % self.category
        msg += "_#!#_%s" % self.mtype
        return msg


class Connection:
    def __init__(self, name):
        self.name = name
        self.isAuthenticated = False
        self.jid = None
        self.server = None
        self.authd_callback = None
        self.buddy_quit_callback = None
        self.direct_msg_callback = None
        self.error_callback = None
        self.finish_callback = None
        self.reactor = reactor
        self.debugging = False
        self.waiting_roster = False
        self.roster = None
        return
    
    def connect(self, jidVal=None, password=None):
        myJid = jid.JID(jidVal)
        self.jid = myJid.userhost()
        self.server = str(myJid.host)
        myJid.resource = "onlyone"
        factory = client.basicClientFactory(myJid, password)
        factory.addBootstrap('//event/stream/authd', self.authd)
        self.reactor.connectTCP(myJid.host, 5222, factory)
        if self.finish_callback != None:
            print "XMPP Lib: setting finish_callback"
            self.reactor.addSystemEventTrigger('before', signal.SIGINT, self.finish_callback)
        self.reactor.run()
        return
    
    def disconnect(self):
        if self.isAuthenticated:
            self.isAuthenticated = False
            if self.reactor.running:
                self.reactor.stop()
        return
    
    def authd(self, xmlstreamobj):
        print "authenticated"
        self.isAuthenticated = True
        
        xmlstreamobj.addObserver('/presence', self.presence)
        xmlstreamobj.addObserver('/message', self.listen)
        xmlstreamobj.addObserver('/iq', self.handle_iq)
        self.connection = xmlstreamobj
        
        self.set_status("%s is up!" % self.name)
        
        self.waiting_roster = True
        iq = domish.Element(('jabber:client', 'iq'))
        iq['type'] = 'get'
        iq.addElement(('jabber:iq:roster', 'query'))
        self.connection.send(iq)
        
        if self.authd_callback != None:
            self.reactor.callLater(1, self.authd_callback)
        return
    
    def clean_jid(self, dirty):
        clean = jid.JID(str(dirty))
        return clean.userhost()
    
    def callLater(self, seconds, function, *args):
        self.reactor.callLater(seconds, function, *args)
        return
    
    def set_authd_callback(self, cb):
        self.authd_callback = cb
        return
    
    def set_direct_msg_callback(self, cb):
        self.direct_msg_callback = cb
        return
    
    def set_error_callback(self, cb):
        self.error_callback = cb
        return
    
    def set_finish_callback(self, cb):
        self.finish_callback = cb
        return
    
    def set_buddy_quit_callback(self, cb):
        self.buddy_quit_callback = cb
        return
    
    def handle_iq(self, elem):
        if self.waiting_roster and elem.query.uri == 'jabber:iq:roster':
            print "got roster!"
            self.waiting_roster = False
            self.handle_roster(elem)
        print "=" * 60
        print elem.toXml()
        return
    
    def handle_roster(self, elem):
        self.roster = dict()
        items = re.findall('<item .*?</item>|<item .*?/>', elem.toXml())
        for x in items:
            jid = re.findall("jid='(.*?)'", x)
            print jid[0]
            if re.search("ask='", x):
                ask = re.findall("ask='(.*?)'", x)
                print "    ask =",ask[0]
            if re.search("subscription='", x):
                subscr = re.findall("subscription='(.*?)'", x)
                print "    subscription =",subscr[0]
        return
    
    def presence(self, elem):
        if elem.hasAttribute('type'):
            presence = domish.Element(('jabber:client', 'presence'))
            presence['to'] = str(elem['from'])
            presence['from'] = str(self.jid)
            if elem['type'] == "subscribe":
                presence['type'] = "subscribed"
                self.connection.send(presence)
            elif elem['type'] == "unsubscribe":
                presence['type'] = "unsubscribed"
                self.connection.send(presence)
            elif elem['type'] == "unavailable":
                print "%s went byby..." % str(elem['from'])
                if self.buddy_quit_callback != None:
                    self.buddy_quit_callback(str(elem['from']))
        else:
            print "presence (online)","="*40
            print elem.toXml()
        return
    
    def listen(self, elem):
        isError = False
        if elem.hasAttribute('type'):
            if elem['type'] == "error":
                isError = True
                if self.error_callback != None:
                    self.error_callback(str(elem.toXml()))
                #if re.search("error code='503'",str(elem.toXml())):
                #    print "ERROR: Couldn't send to %s" % str(elem['from'])
        if not isError:
            if self.debugging:
                print "msg from:",str(elem['from'])
                print str(elem.toXml())
            whofrom = self.clean_jid(elem['from'])
            body = getData("body", str(elem.toXml()))
            if body != "":
                if re.search("<error>.*?</error>", body):
                    if self.error_callback != None:
                        self.error_callback(body)
                    else:
                        print body
                else:
                    if self.direct_msg_callback != None:
                        self.direct_msg_callback(body, self.clean_jid(elem['from']))
        return
    
    def send(self, message, to):
        if self.isAuthenticated:
            msg = domish.Element((None, 'message'))
            msg['to'] = str(to)
            msg['from'] = str(self.jid)
            msg.addElement('body', content=message)
            self.connection.send(msg)
        return
    
    def subscribe_buddy(self, buddy):
        presence = domish.Element(('jabber:client', 'presence'))
        presence['to'] = str(buddy)
        presence['from'] = str(self.jid)
        presence['type'] = "subscribe"
        self.connection.send(presence)
        return
    
    def unsubscribe_buddy(self, buddy):
        presence = domish.Element(('jabber:client', 'presence'))
        presence['to'] = str(buddy)
        presence['from'] = str(self.jid)
        presence['type'] = "unsubscribe"
        self.connection.send(presence)
        return
    
    def log_finish(self, message):
        print self.name,"  msg:",message
        return
    
    def set_status(self, value):
        status = domish.Element(('jabber:client', 'presence'))
        status.addElement('status', content=value)
        self.connection.send(status)
        return

