#!/usr/bin/env python

# Author: Sawood Alam <ibnesayeed@gmail.com>
#
# This is a simple script to process several CDX files to profile an archive collection.

import os

os.environ["TLDEXTRACT_CACHE"] = "/tmp/.tld_set"

from collections import namedtuple, defaultdict
from urlparse import urlparse
from surt import surt
import sys
import tldextract
import pprint
import json
import time

class Profiler(object):
    """Profiling an archive using CDX files."""

    def __init__(self, debug_level = 3):
        """Initialize with a basic empty profile and cache PrettyPrinter object for debugging."""
        self.debug_level = debug_level
        self.profile = {"urir": 0, "urim": {"total": 0, "min": 0, "max": 0}, "tld": {}}
        self.pp = pprint.PrettyPrinter(indent = 2)
        self.debug("Profiling started...", 1)

    def build_profile(self, *cdxs):
        """Accepts a list of CDX file names/paths and calls CDX processor on them."""
        self.debug("Building profile from CDX files...", 1)
        for cdx in cdxs[0]:
            self.process_cdx(cdx)

    def process_cdx(self, cdx):
        """Accepts a CDX file and processes it to extract neccessary information and builds a raw data structure."""
        self.debug("Processing CDX: " + cdx, 1)
        profile = self.profile
        with open(cdx) as f:
            for line in f:
                entry = self.parse_line(line)
                if entry and entry.scheme.startswith("http"):
                    if entry.tld not in profile["tld"]:
                        profile["tld"][entry.tld] = {"urir": 0, "urim": {"total": 0, "min": 0, "max": 0}, "domain": {}}
                    if entry.domain not in profile["tld"][entry.tld]["domain"]:
                        profile["tld"][entry.tld]["domain"][entry.domain] = {"urir": 0, "urim": {"total": 0, "min": 0, "max": 0}, "surt": {}}
                    if entry.surt not in profile["tld"][entry.tld]["domain"][entry.domain]["surt"]:
                        profile["tld"][entry.tld]["domain"][entry.domain]["surt"][entry.surt] = 1
                    else:
                        profile["tld"][entry.tld]["domain"][entry.domain]["surt"][entry.surt] += 1

    def parse_line(self, line=""):
        """Parses single line of a CDX file and returns selected and derived attributes in a namedtuple."""
        segs = line.strip().split(" ")
        if len(segs) == 10:
            url = urlparse(segs[2])
            dom = tldextract.extract(segs[2])
            Segments = namedtuple("Segments", "scheme, host, domain, tld, surt, mime")
            return Segments(url.scheme, url.netloc, surt(dom.registered_domain)[:-2], surt(dom.suffix)[:-2], surt(segs[2]), segs[3])

    def calculate_stats(self):
        """Calculates statistics from the raw profile data structure and prepares the profile object for serialization."""
        self.debug("Calculating statistics...", 1)
        profile = self.profile
        psum = purir = 0
        pmin = pmax = 1
        for t in profile["tld"].itervalues():
            tsum = turir = 0
            tmin = tmax = 1
            for d in t["domain"].itervalues():
                s = d["surt"].values()
                d["urir"] = len(s)
                d["urim"]["total"] = sum(s)
                d["urim"]["min"] = min(s)
                d["urim"]["max"] = max(s)
                turir += d["urir"]
                tsum += d["urim"]["total"]
                tmin = min(d["urim"]["min"], tmin)
                tmax = max(d["urim"]["max"], tmax)
                del d["surt"]
            t["urir"] = turir
            t["urim"]["total"] = tsum
            t["urim"]["min"] = tmin
            t["urim"]["max"] = tmax
            purir += turir
            psum += tsum
            pmin = min(tmin, pmin)
            pmax = max(tmax, pmax)
        profile["urir"] = purir
        profile["urim"]["total"] = psum
        profile["urim"]["min"] = pmin
        profile["urim"]["max"] = pmax

    def to_json(self, outfile=None):
        """Serializes processed profile object in JSON format."""
        self.debug("Converting to JSNON...", 1)
        if outfile:
            self.debug("Writing output to " + outfile, 1)
            f = open(outfile, 'w')
            json.dump(self.profile, f, sort_keys=True, indent=4, separators=(',', ': '))
        self.debug(self.profile, 3)

    def debug(self, msg, level = 0):
        """Utility method to log debug messages of various levels."""
        if level < self.debug_level:
            self.pp.pprint(msg)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("To profile a CDX archive:")
        print("  Single CDX file    :    profiler.py abc.cdx")
        print("  Multiple CDX files :    profiler.py abc.cdx def.cdx ...")
        print("  Multiple CDX files :    profiler.py *.cdx abc/*.cdx ...")
        sys.exit(0)
    p = Profiler(3)
    p.build_profile(sys.argv[1:])
    p.calculate_stats()
    opf = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'json', "profile-" + time.strftime("%Y%m%d-%H%M%S") + ".json")
    p.to_json(opf)
