<a name="readme-top"></a>

<!-- PROJECT DETAILS -->
<div align="center">

  <h1 align="center">iNetVisor</h1>

  <p align="center">
    A <a href="https://systronlab.github.io"><strong>SYSTRON Lab</strong></a> project
    <br />
    from the <a href="https://www.cs.york.ac.uk/"><strong>Department of Computer Science</strong></a> at the University of York
  </p>
</div>


<!-- TABLE OF CONTENTS -->
<details>
  <summary>Table of Contents</summary>
  <ol>
    <li><a href="#about-the-project">About the project</a></li>
    <li><a href="#getting-started">Getting started</a></li>
    <li><a href="#collecting-bgp-data">Collecting BGP data</a></li>
    <li><a href="#collecting-tracroute-data">Collecting traceroute data</a></li>
    <li><a href="#collecting-metadata">Collecting metadata</a></li>
    <li><a href="#forming-a-topology">Forming a topology</a></li>
    <li><a href="#publications">Publications</a></li>
    <li><a href="#contact">Contact</a></li>
  </ol>
</details>


<!-- ABOUT THE PROJECT -->
## About the project

iNetVisor collects Internet routing and reachability data from BGP and traceroutes, and constructs a topology graph supported by Internet resource metadata from registries, PeeringDB and external sources.

<p align="right">(<a href="#readme-top">back to top</a>)</p>


<!-- GETTING STARTED -->
## Getting started

This repository contains tooling that integrates with [RIPE Atlas](https://atlas.ripe.net/) to collect public traceroute data and instigate new traceroute measurements. You do not need a RIPE Access account or RIPE Atlas credits to collect publicly available data from RIPE Atlas as part of the traceroute collection. However, **you do need an Access account and Atlas credits to instigate new measurements on the Atlas platform.**

There are a few prerequisites before running this tool:

- Install [rust-lang](https://www.rust-lang.org/learn/get-started) (this allows us to use BGPKit)

**Install Python prerequisites**
```sh
$ pip install -r requirements.txt
```

<p align="right">(<a href="#readme-top">back to top</a>)</p>


<!-- USING THE TOOL -->
## Collecting BGP data

You can simply run:

```sh
$ run_inetvisor.sh
```

Alternatively you can follow the steps below to run each step manually, rather than the automated script.

### Find relevant route collectors

To obtain a file containing the relevant route collectors and metadata for the interval of interest, we use `route_collectors.py`, and supply a *start time*, *duration* and optionally, an *output* file destination. This produces a `.json` format.

```sh
# Specifying an output is optional, will print to terminal if -o is not supplied
$ python collectors/bgp/route_collectors.py -s "dd/mm/yyyy HH:MM:SS" -d "86400" -o "collectors.json"
```

### Obtaining a list of paths

For each collector specified in the *input* file, we download and decompress the MRT file and explore the records, outputting a file containing pipe-separated paths followed by accompanying IPv4/IPv6 and timestamp metadata.

```sh
$ python collectors/bgp/mrt_to_paths.py -in collectors.json -o paths.txt
```

This produces a file of the format `P|A|T|H/IPver|timestamp`, for example:

```txt
123|456|789/v4|1704110400.0
```

### Splitting into processable files (optional)

To make the large file size of `paths.txt` easier to manage, you can use the inbuilt Linux command:

```sh
split -C 20GB --numeric-suffixes paths.txt paths_part_
```

### Separating clean and undesirable paths

This step cleans the available paths, removing prepending or route servers from valid paths, and removing paths containing loops or bogons. To do this, you must supply a [PeeringDB dataset file as JSON or SQLite](https://www.caida.org/catalog/datasets/peeringdb/) such that we can extract known route servers. This produces a number of files: `clean_paths.txt` containing paths without prepending or route servers, but otherwise valid; files starting `formerly_` containing valid paths in uncleaned form (for reference); and finally files starting `removed_` which have been identified as invalid. All exported paths continue to have the original metadata (IP version and timestamp).

```sh
python utils/path_cleaner.py -in list_of_path_files.txt -pdb peeringdb.json -o exportdir
```

### Naive adjacencies

Simply extracting the unique adjacencies in the cleaned `as_path`.

```sh
python utils/naive_adjacencies.py -in list_of_files -o naive_adjacencies.txt
```

### Run AS-Rank

Previous work in this area has resulted in the creation of differing versions of `asrank.pl`, including by Gao (Gao, 2001) and [the CAIDA project (Luckie, 2013)](https://catalog.caida.org/paper/2013_asrank). We provide `format_asrank.py` to run on the same list of files to allow for direct comparisons with our data. This also enables support for other work, such as [Problink (Jin, 2019)](https://github.com/YuchenJin/ProbLink/).

```sh
python utils/format_asrank.py -in list_of_files -o path_data.txt
./asrank.pl path_data.txt > asrank_result.txt
```

### Other notes

The files produced and processed by this tool can be quite large, depending on the volume of data collected. We note that using TAR to compress files reduces the size of the text files significantly (~500GB of a `.txt` becomes ~15GB of `.tar.gz`). We use text files as these are simple to process without adding extraction to the execution time of the tool.

<p align="right">(<a href="#readme-top">back to top</a>)</p>

<!-- COLLECTING TRACEROUTE DATA -->
## Collecting traceroute data

### Prepare the mapping of router IP addresses to ASNs

Traditional tools introduce circular dependency into IP to ASN mappings by relying on existing AS relationship models. Some alternative approaches use statistical modelling, which could introduce inaccuracies in the process. We want to attempt a best-possible approach to accuracy, instead relying on operational data from IXPs above existing approaches.

Therefore, the approach taken in this tool is first-match from:
1. **Check [IXPDB](https://ixpdb.euro-ix.net/en/) for the router IP address**. If present, we prefer this ASN as the data source is relatively fresh and in most cases collected directly from the IXP. We collect this data using the 'List all ASNs' option in the IXPDB API.
2. **Check [PeeringDB](https://www.peeringdb.com/) for the router IP address**. If present, we use this ASN, as self-reported operational data is still preferable to prefix matching. We find a discrepancy between IXPDB and PeeringDB data in around 0.24% of cases. Observing the link state using PCH and IXP looking glasses shows many of these discrepancies come from inaccessible peering states - so we prefer the more current IXPDB data, but it is unlikely a traceroute will contain the impacted IPs.

```sh
$ python collectors/traceroute/router_to_as.py -xdb data/ixpdb_asns.json -pdb data/peeringdb_data.json -o data/router2as.json
```

### Supplement with best-guess (pyasn)

We use `pyasn` on the routing table to supplement our assured data, creating an `ipasn.dat` file we use for secondary lookups later. [Read more about pyasn](https://github.com/hadiasghari/pyasn).

### Collect public traceroutes

#### Using the RIPE Atlas API

This collects all publicly available traceroutes from RIPE Atlas in the specified time period, exporting key information (probe id, start time, source, destination, and hops) into a JSON file. Providing the optional `--router2as` argument returns an ASN value for each traceroute IP address, if a mapping exists.

```sh
$ python collectors/traceroute/collect.py -s "DD/MM/YYYY HH:MM:SS" -d 3600 -r2as data/router2as.json -asndb data/asndb.dat -o data/traceroute.json
```

#### Using Atlas Daily Dumps (most recent 30 days)

This collects publicly available traceroute data for the most recent 30-day period based on data available in the [Atlas Daily Dumps](https://data-store.ripe.net/datasets/atlas-daily-dumps/). It comprises of two scripts (one to download the `.bz2` files and another to extract and translate to our format) and a modified version of the collection Python script. Both require minor changes to adjust your data source (for the first, a `.txt` of desired files, and for the second, paths to your `data/router2as.json` and `data/asndb.dat`)

```sh
$ collectors/traceroute/01_daily_collect.sh
$ collectors/traceroute/02_daily_translate.sh
```

### Transfrom traceroutes to AS adjacencies

This part of the tool takes as input the previously exported `traceroute.json` data and generates a new file containing a list of adjacencies as identified in the traceroute data. Notably, the function provided by this tool is *strict*: an AS is only considered adjacent where two ASNs are directly adjacent in the path, and so where an internal IP address, timeout/null response is seen, the ASNs on either side are not considered adjacent (contrary to the assumption used by some other tooling).

```sh
$ python utils/trace_to_adjacency.py -in data/traceroute.json -o data/adjacencies.txt
```

<p align="right">(<a href="#readme-top">back to top</a>)</p>


<!-- COLLECTING METADATA -->
## Collecting metadata

You can manually collect the required files, each of which should be placed in the `data/source` directory.

<p align="right">(<a href="#readme-top">back to top</a>)</p>


<!-- FORMING A TOPOLOGY -->
## Forming a topology

Run the following tool to collate the information as a topology graph. Only `-a` and `-o` are mandatory.

```sh
$ python topology/data_to_graph.py -a 'data/working/AS_ADJACENCIES.txt' -r 'data/working/AS_RELATIONSHIPS.txt' -c 'data/source/countries_with_colours.csv' -h4 'data/working/IPv4_HEGEMONY.csv' -h6 'data/working/IPv6_HEGEMONY.csv' -p 'data/source/peeringdb_2_dump_2025_11_06.json' -b 'data/source/tags.txt' 'data/source/bgptools-tags' -o 'data/output/graph.graphml'
```

<p align="right">(<a href="#readme-top">back to top</a>)</p>


<!-- PUBLICATIONS -->
## Publications

- [(Preprint) Unveiling Internet Censorship: Analysing the Impact of Nation States’ Content Control Efforts on Internet Architecture and Routing Patterns](https://systronlab.github.io/publications/2024-unveiling-internet-censorship)
- [(Abstract) From Internet to Emulator: A Virtual Testbed for Internet Routing Protocols](https://systronlab.github.io/publications/2024-from-internet-to-emulator)

<p align="right">(<a href="#readme-top">back to top</a>)</p>


<!-- CONTACT -->
## Contact

**Josh Levett**: [@Levett_Josh](https://twitter.com/Levett_Josh) / joshua.levett (at) york.ac.uk


<p align="right">(<a href="#readme-top">back to top</a>)</p>