#!/usr/bin/python

import copy
import optparse
import re
import sys
import xml.dom.minidom



###############################################################################
#### Chromosome class
###############################################################################
class Chromosome:
    def __init__(self):
        return
    
    def __add__(self, other):
        return



###############################################################################
#### Pollinator class
###############################################################################
class Pollinator:
    def __init__(self, options):
        return



if __name__ == "__main__":
    print "GA Reproduction"
    parser = optparse.OptionParser(usage="usage: %prog [options]")
    parser.add_option("-c",
                      "--chromosome",
                      dest="chromosome",
                      help="Directory with the sensor chromosome definitions.")
    (options, args) = parser.parse_args()
    if None in [options.chromosome]:
        if options.chromosome == None:
            print "ERROR: Missing -c / --chromosome"
        parser.print_help()
        sys.exit()
    
    pobj = Pollinator(options)

