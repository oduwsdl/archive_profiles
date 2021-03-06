# Feedback Needed

We are describing some issues below that we encountered after working on the available dataset. Please let us know your thoughts and suggestions on the following issues and proposed approaches.

## Profile Merging

Generating smaller profiles and merging them to make the master profile is important for many reasons:

- Working on smaller sub-tasks consumes less resources than working on the whole thing together.
- Working on bigger files yields "all or nothing" situation.
- Update does not require re-processing all the previous data along with the new data.
- Parallel processing is possible without sharing data.

On the other hand, merging smaller profiles to make a bigger profile makes it very difficult to keep the record of absolute data and we have to give up several statistical measures.

So far in our profiles we were collecting "URI-R Count", "URI-M Count", "Max Occurrence of URI-M", "Min Occurrence of URI-M" for every Sub-URI. While "Average Occurrence of URI-M" can be derived by dividing "URI-M Count" by "URI-R Count". Our current profiles look like this:

```json
{
  "suburis": {
    "com,cnn)/": {
      "urim": {
        "max": 6,
        "min": 1,
        "total": 61
      },
      "urir": 26
    },
    "uk,co,bbc)/": {
      "urim": {
        "max": 3,
        "min": 1,
        "total": 32
      },
      "urir": 24
    }
  }
}
```

If we generate small profiles from individual (small) CDX files and merge them, we will hardly see any revisits in each individual CDX, which means URI-M related information will not be very effective, hence we can omit the "urim" block from the profile and only focus on the "urir" count.

Currently we have an approach to merge profiles in which we only track URI-R counts and when merge two profiles, we keep record of the sum of URI-R counts of all Sub-URIs and the count of how many profiles those Sub-URIs appeared in. Following example illustrates our current merging implementation.

Profile-1:

```json
{
  "suburis": {
    "com,cnn)/": {
      "urir_sum": 30,
      "sources": 1
    },
    "uk,co,bbc)/": {
      "urir_sum": 20,
      "sources": 1
    }
  }
}
```

Profile-2:

```json
{
  "suburis": {
    "com,cnn)/": {
      "urir_sum": 10,
      "sources": 1
    },
    "com,usatoday)/": {
      "urir_sum": 5,
      "sources": 1
    }
  }
}
```

Merged-Profile:

```json
{
  "suburis": {
    "com,cnn)/": {
      "urir_sum": 40,
      "sources": 2
    },
    "uk,co,bbc)/": {
      "urir_sum": 20,
      "sources": 1
    },
    "com,usatoday)/": {
      "urir_sum": 5,
      "sources": 1
    }
  }
}
```

In the above example, `com,cnn)/` Sub-URI appeared in both the profiles hence there "urim_sum" values are added and "sources" attribute tells that this "urim_sum" value came from two sources/profiles.

This is simple, but not the ideal way of merging profiles because the sum of URI-Rs does not give the absolute number of URI-Rs as if all the CDX files were processed together. Also when a Sub-URI is present in almost all the smaller CDX files with some stable number of URI-Rs and another Sub-URI has big numbers a few times but very small or no URI-R count in rest of the CDX files then inferring probability distribution is not easy. We have merged a few profiles using this approach that were generated from the individual UKWA CDX files.

To simplify this problem if we focus on the usage of the profile, we realize that the biggest reason of having these profiles is to identify the probability of finding certain URI-R in an archive. To achieved this objective without storing URI-R or URI-M counts, we are proposing a derived property "availability" for each Sub-URI that has following characteristics:

- It has a value between 0 to 1.
- It is independent of the values of parent or sibling Sub-URIs. Alternatively the sum of the values of all the siblings is equal to the value of the parent, which can be rolled up and the sum of all the values of TLDs will be 1. I would vote against the later approach as it will cause update propagation.
- The value increases as a function of its current value, URI-R count appeared in the new profile, and the total number of URI-Rs processed so far in the base profile.
- A global scale value is recorded that is modified every time any change happens. This global value will allow decreasing effective probability of all the nodes that did not see any changes without changing their value. Profile consumers read "availability" value of a Sub-URI and multiply it by the global "scale" value to calculate the effective value.
- Initialization of the global scale value and individual scores will require some sort of normalization when the first basic profile is generated. Or it is assumed as if the first profile is being merged into a basic blank profile with a default score for each new node.

With this new derived property "availability" for each URI-R and a global property "scale" the profile may look something like this:

```json
{
  "total_urirs_processed": 1234,
  "scale": 0.93,
  "suburis": {
    "com,cnn)/": {
      "availability": 0.712
    },
    "uk,co,bbc)/": {
      "availability": 0.021
    }
  }
}
```

The two properties will be calculated as functions of various properties described above.

```python
def update_availability(suburi, base_profile, new_profile):
  '''This method is called for every Sub-URI that has to be updated due to the merger of two profiles.'''
  base_profile[suburi]["availability"] = "TODO" # Yet to implement based on the description above.

def update_scale(base_profile, new_profile):
  '''This method is called once every time two profiles are merged together.'''
  base_profile.total_urirs_processed += new_profile.total_urirs_processed
  base_profile.scale = "TODO" # Yet to implement based on the description above.
```

This new proposed method of unifying the profile has complexities that needs to addressed before we can consider it. Some problem with this approach are as follows:

- It relies on information that is scattered at different places in the profile such as "scale" and "total_urirs_processed" in the profile meta.
- It may add computational overhead depending on how we combine various factors to calculate and update the derived values.
- Various profiles will have their own global scale values and it is not clear how they will be merged, especially when two independently evolving base profiles are merged.

If the simple approach currently in practice seems adequate for the purpose then it might be good idea not to invest in any complex approaches.

## Profile Serialization

Earlier we discussed the serialization format and considered XML, JSON, and YAML data formats. Among these formats we chose to serialize profiles in JSON format as it is less verbose than XML, but has similar expressiveness and the availability of tools. JSON is an ideal serialzation format if each node may have varying number of different properties and the data has some nesting. In the first project status update, Andy said, "I don't mind. JSON-LD seems sensible. TBH, most of this could be done with sorted TSV/CSV, which would make binary search much easier. However, that would require separate files for each profile axis, so probably not worth it."

Now that we profiled some big CDX files, we realized that JSON or XML are not ideal for our use case. Here are some reasons behind this conclusion:

- Generating JSON file is not a sequential process, one has to build the data structure in memory (which is generally a nested dictionary) and then serialize the nested structure.
- Programming languages tend to slow down when large number of keys appear in a dictionary. We have observed serious slow down when number of Sub-URIs grows beyond certain number in our profiling.
- JSON/XML files are very sensitive to formatting. Single extra/missed character can damage the semantics of the data or make it completely unusable/unparsable.
- Consuming XML/JSON requires to load entire file, parse it, and build the object data structure in memory. Large files may not be useful for many machines with less than adequate memory and they will take some time to parse and load in the memory.
- Patching/updating/merging such structured data is also not very easy and it will require loading whole file in memory, update specific pieces, and serialize back to disk.

We are now proposing a CDX file style serialization that can be a sorted file stored on the disc with the following benefits:

- Files can be as big as allowed by the files system or can be split into any smaller sizes fit for the needs while individual files are sorted.
- Fast binary searching is possible without loading entire file.
- Merging/updating/paching is easy.
- Standard Unix utilities like grep, comm, awk, sort, uniq, and cut etc. can be used for various tasks.
- CDX style headers can be added (that automatically comes on top after sorting) to describe every field in the file.
- Different types of profiles such as language profile, time profile and sub-URI profile can be stored in separate files with suitable headers to eliminate nesting.
- File format may extend CDX format to allow adding meta data in it.
- This will be even better if we decide to keep only few (one or two) simplified values for each key as described in above section unlike our initial plan where we wanted to store as many statistical measures as we can.

Although sorting is not necessary for profiles and can be optional, but it makes various lookup operations fast by allowing binary search in the file. Sorting will impact the placement of the metadata and header lines. To Keep them on top of the file, we may use comment like syntax and make sure that every line of the metadata section will have complete information, without breaking the lines, although this restriction is not essential. Metadata section can be separated from the data using a marker very much how ARFF (commonly used in Weka) files are organized.

A sample profile in CDX style may look like this:

```cdx
 ARCPROFILE suburi urisum sources
 # name: Test Archive
 # id: http://example.com/archive
 # profile-class: suburis
com,cnn)/ 30 1
uk,co,bbc)/ 20 1
```

Or an ARFF format inspired profile will look like this:

```arff
% name: Test Archive
% id: http://example.com/archive
% profile-class: suburis
@ATTRIBUTE suburi SUBURI
@ATTRIBUTE urisum NUMERIC
@ATTRIBUTE sources NUMERIC
@DATA
com,cnn)/ 30 1
uk,co,bbc)/ 20 1
```

Usually ARFF format uses comma `,` as field separator, but we will be using space instead.

Recently Ilya Kreymer has introduced support for an index file format in [pywb](https://github.com/ikreymer/pywb/issues/76) that is fusion of CDX and JSON. In this file format, keys are kept in the beginning of each line followed by a delimiter (space in this case) and then a block of JSON object containing all the value attributes serialized strictly in a single line. This format allows CDX like sorting and binary search along with the flexibility of adding arbitrary value attributes. Since entire profile is not under a single JSON root node (instead JSON fragments are used as values), scaling updating or merging is easier. We still need to think about how to add metadata in this format. An example of this format will look like this:

```cdxjson
@id: http://example.com/archive
@name: Test Archive
@profile-class: suburis
com,cnn)/ {"urisum": 30, "sources": 1}
uk,co,bbc)/ {"urisum": 20, "sources": 1}
```
