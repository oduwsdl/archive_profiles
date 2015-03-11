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
```

If we generate small profiles from individual (small) CDX files and merge them, we will hardly see any revisits in each individual CDX, which means URI-M related information will not be very effective, hence we can omit the "urim" block from the profile and only focus on the "urir" count.

Currently we have an approach to merge profiles in which we only track URI-R counts and when merge two profiles, we keep record of the sum of URI-R counts of all Sub-URIs and the count of how many profiles those Sub-URIs appeared in. Following example illustrates our current merging implementation.

Profile-1:

```json
{
  "com,cnn)/": {
    "urir_sum": 30,
    "sources": 1
  },
  "uk,co,bbc)/": {
    "urir_sum": 20,
    "sources": 1
  }
}
```

Profile-2:

```json
{
  "com,cnn)/": {
    "urir_sum": 10,
    "sources": 1
  },
  "com,usatoday)/": {
    "urir_sum": 5,
    "sources": 1
  }
}
```

Merged-Profile:

```json
{
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
```

In the above example, "com,cnn)/" Sub-URI appeared in both the profiles hence there "urim_sum" values are added and "sources" attribute tells that this "urim_sum" value came from two sources/profiles.

This is not the ideal way of merging profiles because the sum of URI-Rs does not give the absolute number of URI-Rs as if all the CDX files were processed together. Also when a Sub-URI is present in almost all the smaller CDX files with some stable number of URI-Rs and another Sub-URI has big numbers a few times but very small or no URI-R count in rest of the CDX files then inferring probability distribution is not easy. We have merged a few profiles using this approach that were generated from the individual UKWA CDX files.

To simplify this problem if we focus on the usage of the profile, we realize that the biggest reason of having these profiles is to identify the probability of finding certain URI-R in an archive. To achieved this objective without storing URI-R or URI-M counts, we are proposing a derived property "availability" for each Sub-URI that has following characteristics:

- It has a value between 0 to 1.
- It is independent of the values of parent or sibling Sub-URIs. Alternatively the sum of the values of all the siblings is equal to the value of the parent, which can be rolled up and the sum of all the values of TLDs will be 1. I would vote against the later approach as it will cause update propagation.
- The value increases as a function of its current value, URI-R count appeared in the new CDX, and the proportion of the size of new CDX with respect to the total size of CDXes processed so far.
- A global scale value is recorded that is modified every time any change happens. This global value will allow decreasing effective probability of all the nodes that did not see any changes without changing their value. Profile consumers read "availability" value of a Sub-URI and multiply it by the global "scale" value to calculate the effective value.
- Initialization of the global scale value and individual scores will require some sort of normalization when the first basic profile is generated. Or it is assumed as if the first profile is being merged into a basic blank profile with a default score for each new node.

## Profile Serialization

Earlier we discussed the serialization format and considered XML, JSON, and YAML data formats. Among these formats we chose to serialize profiles in JSON format as it is less verbose than XML, but has similar expressiveness and the availability of tools. JSON is an ideal serialzation format if each node may have varying number of different properties and the data has some nesting. In the first project status update, Andy said, "I don't mind. JSON-LD seems sensible. TBH, most of this could be done with sorted TSV/CSV, which would make binary search much easier. However, that would require separate files for each profile axis, so probably not worth it."

Now that we profiled some big CDX files, we realized that JSON or XML are not ideal for our use case. Here are some reasons behind this conclusion:

- Generating JSON file is not a sequential process, one has to build the data structure in memory (which is generally a nested dictionary) and then serialize the nested structure.
- Programming languages tend to slow down when large number of keys appear in a dictionary. We have observed serious slow down when number of Sub-URIs grows beyond certain number in our profiling.
- JSON/XML files are very sensitive to formatting. Single extra/missed character can damage the semantics of the data or make it completely unusable/unparsable.
- Consuming XML/JSON requires to load entire file, parse it, and build the object data structure in memory. Large files may not be useful for many machines with less than adequate memory and they will take some time to parse and load in the memory.
- Patching/updating/merging such structured data is also not very easy and it will require loading whole file in memory, update specific pieces, and serialize back to disk.

We are now proposing a CDX file style serialization that can be a sorted file stored on the disc with the following benefits:

- Files can be as big as allowed by the files ystem or can be split into any smaller sizes fit for the needs while individual files are sorted.
- Fast binary searching is possible without loading entire file.
- Merging/updating/paching is easy.
- Standard Unix utilities like grep, comm, awk, sort, uniq, and cut etc. can be used for various tasks.
- CDX style headers can be added (that automatically comes on top after sorting) to describe every field in the file.
- Different types of profiles such as language profile, time profile and sub-URI profile can be stored in separate files with suitable headers to eliminate nesting.
- File format may extend CDX format to allow adding meta data in it.
- This will be even better if we decide to keep only few (one or two) simplified values for each key as described in above section unlike our initial plan where we wanted to store as many statistical measures as we can.
