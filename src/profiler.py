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

class Profile(object):
    """Basic archive profile to be evolved by the profiler."""

    def __init__(self, name="", description="", homepage="", accesspoint="", memento_compliance="", timegate="", timemap="", established="", profile_updated="", **kwargs):
        """Initialize a basic archive profile object."""
        self.name = name
        self.description = description
        self.homepage = homepage
        self.accesspoint = accesspoint
        self.memento_compliance = memento_compliance
        self.timegate = timegate
        self.timemap = timemap
        self.established = established
        self.profile_updated = profile_updated
        self.__dict__.update(kwargs)

class Profiler(object):
    """Profiling an archive using CDX files."""

    def __init__(self, debug_level=3):
        """Initialize with a basic empty profile and cache PrettyPrinter object for debugging."""
        self.debug_level = debug_level
        self.profile = {"tld": {}}
        self.pp = pprint.PrettyPrinter(indent=2)
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
                    try:
                        profile["tld"][entry.tld]["domain"][entry.domain]["surt"][entry.surt] += 1
                    except KeyError, e:
                        if e.message == entry.tld:
                            profile["tld"][entry.tld] = {"domain": {}}
                            e.message = entry.domain
                        if e.message == entry.domain:
                            profile["tld"][entry.tld]["domain"][entry.domain] = {"surt": {}}
                            e.message = entry.surt
                        if e.message == entry.surt:
                            profile["tld"][entry.tld]["domain"][entry.domain]["surt"][entry.surt] = 1

    def parse_line(self, line=""):
        """Parses single line of a CDX file and returns selected and derived attributes in a namedtuple."""
        segs = line.strip().split(" ")
        if len(segs) == 10:
            url = urlparse(segs[2])
            dom = tldextract.extract(segs[2])
            Segments = namedtuple("Segments", "scheme, host, domain, tld, surt, mime")
            return Segments(url.scheme, url.netloc, surt(dom.registered_domain), surt(dom.suffix), surt(segs[2]), segs[3])

    def calculate_stats(self, flat=False):
        """Calculates statistics from the raw profile data structure and prepares the profile object for serialization."""
        self.debug("Calculating statistics...", 1)
        profile = self.profile
        if flat:
            profile["domain"] = {}
        psum = purir = 0
        pmin = pmax = 1
        for t in profile["tld"].itervalues():
            tsum = turir = 0
            tmin = tmax = 1
            for d in t["domain"].itervalues():
                s = d["surt"].values()
                count = len(s)
                total = sum(s)
                minm = min(s)
                maxm = max(s)
                d["urir"] = count
                d["urim"] = {"total": total, "min": minm, "max": maxm}
                del d["surt"]
                turir += count
                tsum += total
                tmin = min(minm, tmin)
                tmax = max(maxm, tmax)
            t["urir"] = turir
            t["urim"] = {"total": tsum, "min": tmin, "max": tmax}
            purir += turir
            psum += tsum
            pmin = min(tmin, pmin)
            pmax = max(tmax, pmax)
            if flat:
                profile["domain"].update(t["domain"])
                del t["domain"]
        profile["urir"] = purir
        profile["urim"] = {"total": psum, "min": pmin, "max": pmax}

    def to_json(self, outfile=None):
        """Serializes processed profile object in JSON format."""
        self.debug("Converting to JSNON...", 1)
        if outfile:
            self.debug("Writing output to " + outfile, 1)
            f = open(outfile, 'w')
            json.dump(self.profile, f, sort_keys=True, indent=4, separators=(',', ': '))
        self.debug(self.profile, 3)

    def debug(self, msg, level=0):
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
    p = Profiler()
    p.build_profile(sys.argv[1:])
    p.calculate_stats(flat=True)
    opf = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'json', "profile-"+time.strftime("%Y%m%d-%H%M%S")+".json")
    p.to_json(opf)
