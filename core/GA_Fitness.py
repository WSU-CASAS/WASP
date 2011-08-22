#!/usr/bin/python

import optparse
import sys
import xml.dom.minidom



if __name__ == "__main__":
    print "GA Fitness Calculator"
    parser = optparse.OptionParser(usage="usage: %prog [options]")
    parser.add_option("-e",
                      "--event",
                      dest="event",
                      help="File with sensor event data.")
    parser.add_option("-c",
                      "--chromosome",
                      dest="chromosome",
                      help="File with the sensor chromosome definition.")
    (options, args) = parser.parse_args()
    if None in [options.event, options.chromosome]:
        if options.event == None:
            print "ERROR: Missing -e / --event"
        if options.chromosome == None:
            print "ERROR: Missing -c / --chromosome"
        parser.print_help()
        sys.exit()

