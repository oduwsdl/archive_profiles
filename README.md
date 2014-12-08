# Archive Profiles

A repository for collecting profiles of various web archiving services and updating as they evolve.

This repository currently has directory structure for both profile storage and profile generator script. Later the profiler script will be splitted into a separate repository.

## Running Profiler Script

To setup and run the Profiler script, please follow these steps:

Clone the repository.

```bash
$ git clone git@github.com:oduwsdl/archive_profiles.git
```

Change working directory to the `src` folder.

```bash
$ cd archive_profiles/src
```

Install dependencies from the requirement file (add `sudo` before `pip` command if necessary.)

```bash
$ pip install -r requirements.txt
```

Run the script on the shipped example `cdx` files.

```bash
$ python ./profiler.py cdx/*.cdx
```

If it works please update the `config.ini` file to reflect your collection. Then try to run profiler against your own (preferably small set of) `cdx` file(s).

Warning: This operation will push the generated profile into a [public gist](https://gist.github.com/ibnesayeed). Please be sure about the privacy concerns you may have.

```bash
$ python ./profiler.py path/to/cdx/files/*.cdx
```
