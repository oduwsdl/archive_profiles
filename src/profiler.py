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
import requests
import ConfigParser

class Profile(object):
    """Basic archive profile to be evolved by the profiler."""

    def __init__(self, name="", description="", homepage="", accesspoint="", memento_compliance="", timegate="", timemap="", established="", profile_updated="", **kwargs):
        """Initialize a basic archive profile object."""
        self.about = {
            "name": name,
            "description": description,
            "homepage": homepage,
            "accesspoint": accesspoint,
            "memento_compliance": memento_compliance,
            "timegate": timegate,
            "timemap": timemap,
            "established": established,
            "profile_updated": profile_updated
        }
        self.__dict__["about"].update(kwargs)
        self.stats = {}
        setattr(self, "@context", "https://oduwsdl.github.io/contexts/archiveprofile.jsonld")
        setattr(self, "@id", homepage)

    def to_json(self):
        """Serializes processed profile object in JSON format."""
        print("Converting to JSNON...")
        return json.dumps(self, default=lambda o: o.__dict__, sort_keys=True, indent=4, separators=(',', ': '))

class Profiler(object):
    """Profiling an archive using CDX files."""

    def __init__(self, debug_level=3):
        """Initialize with a basic empty profile and cache PrettyPrinter object for debugging."""
        self.debug_level = debug_level
        self.suburi = {}
        self.pp = pprint.PrettyPrinter(indent=2)
        self.debug("Profiling started...", 1)

    def build_profile(self, *cdxs):
        """Accepts a list of CDX file names/paths and calls CDX processor on them."""
        self.debug("Building profile from CDX files...", 1)
        self.suburi["tld"] = {}
        self.suburi["suburi"] = {}
        for cdx in cdxs[0]:
            self.process_cdx(cdx)

    def process_cdx(self, cdx):
        """Accepts a CDX file and processes it to extract neccessary information and builds a raw data structure."""
        self.debug("Processing CDX: " + cdx, 1)
        suburi = self.suburi
        with open(cdx) as f:
            for line in f:
                entry = self.parse_line(line)
                if entry and entry.scheme.startswith("http"):
                    self.flat_ds(entry)
                    #self.nested_ds(entry)

    def nested_ds(self, entry):
        suburi = self.suburi
        try:
            suburi["tld"][entry.tld]["domain"][entry.domain]["surt"][entry.surt] += 1
        except KeyError, e:
            if e.message == entry.tld:
                suburi["tld"][entry.tld] = {"domain": {}}
                e.message = entry.domain
            if e.message == entry.domain:
                suburi["tld"][entry.tld]["domain"][entry.domain] = {"surt": {}}
                e.message = entry.surt
            if e.message == entry.surt:
                suburi["tld"][entry.tld]["domain"][entry.domain]["surt"][entry.surt] = 1

    def flat_ds(self, entry):
        suburi = self.suburi
        surtparts = entry.surt.split("?")[0].split("/")
        uniqsurts = set([entry.tld, entry.domain, "/".join(surtparts[0:2]), "/".join(surtparts[0:3])])
        for u in uniqsurts:
            try:
                suburi["suburi"][u] += 1
            except KeyError, e:
                suburi["suburi"][u] = 1

    def parse_line(self, line=""):
        """Parses single line of a CDX file and returns selected and derived attributes in a namedtuple."""
        segs = line.strip().split(" ")
        if len(segs) == 10:
            url = urlparse(segs[2])
            dom = tldextract.extract(segs[2])
            Segments = namedtuple("Segments", "scheme, host, domain, tld, surt, uri, time, mime")
            return Segments(url.scheme, url.netloc, surt(dom.registered_domain), surt(dom.suffix), surt(segs[2]), segs[2], segs[1], segs[3])

    def calculate_stats(self, flat=False):
        """Calculates statistics from the raw profile data structure and prepares the profile object for serialization."""
        self.debug("Calculating statistics...", 1)
        suburi = self.suburi
        if flat:
            suburi["domain"] = {}
        psum = purir = 0
        pmin = pmax = 1
        for t in suburi["tld"].itervalues():
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
                suburi["domain"].update(t["domain"])
                del t["domain"]
        suburi["urir"] = purir
        suburi["urim"] = {"total": psum, "min": pmin, "max": pmax}

    def to_json(self, outfile=None):
        """Serializes processed profile object in JSON format."""
        self.debug("Converting to JSNON...", 1)
        if outfile:
            self.debug("Writing output to " + outfile, 1)
            f = open(outfile, 'w')
            json.dump(self.suburi, f, sort_keys=True, indent=4, separators=(',', ': '))
        self.debug(self.suburi, 3)

    def debug(self, msg, level=0):
        """Utility method to log debug messages of various levels."""
        if level < self.debug_level:
            self.pp.pprint(msg)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("\nTo profile a CDX archive:")
        print("  Single CDX file    :    profiler.py abc.cdx")
        print("  Multiple CDX files :    profiler.py abc.cdx def.cdx ...")
        print("  Multiple CDX files :    profiler.py *.cdx abc/*.cdx ...\n")
        sys.exit(0)
    scriptdir = os.path.dirname(os.path.abspath(__file__))
    config = ConfigParser.ConfigParser()
    config.read(os.path.join(scriptdir, "config.ini"))
    print(config.sections())
    p = Profile(name=config.get("archive", "name"),
                description=config.get("archive", "description"),
                homepage=config.get("archive", "homepage"),
                accesspoint=config.get("archive", "accesspoint"),
                memento_compliance=config.get("archive", "memento_compliance"),
                timegate=config.get("archive", "timegate"),
                timemap=config.get("archive", "timemap"),
                established=config.get("archive", "established"),
                profile_updated=time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                mechanism="https://oduwsdl.github.io/terms/mechanism#cdx")
    pr = Profiler()
    pr.build_profile(sys.argv[1:])
    #pr.calculate_stats(flat=True)
    p.stats = pr.suburi
    jsonstr = p.to_json()
    opf = os.path.join(scriptdir, 'json', "profile-"+time.strftime("%Y%m%d-%H%M%S")+".json")
    print("Writing output to " + opf)
    f = open(opf, 'w')
    f.write(jsonstr)
    f.close()
    gist = {
        "description": "An archive profile created on "+time.strftime("%Y-%m-%d at %H:%M:%S")+".",
        "public": True,
        "files": {
            "profile-"+time.strftime("%Y%m%d-%H%M%S")+".json": {
                "content": jsonstr
            }
        }
    }
    req = requests.post(config.get("github", "endpoint"),
                        data=json.dumps(gist),
                        auth=(config.get("github", "user"), config.get("github", "token")))
    print("Writing to GitHub: " + str(req.status_code))
