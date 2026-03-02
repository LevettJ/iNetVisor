#!/bin/bash

echo 'Collecting tag data from bgp.tools'
cd ../data/source
#curl -O https://bgp.tools/tags.txt --user-agent 'Josh Levett UoY - joshua.levett@york.ac.uk'

echo 'Pulling tag files'
while IFS="," read -r tag
do
    sleep 3
    curl "https://bgp.tools/tags/$tag.csv" -o "bgptools-tags/$tag.csv" --user-agent 'Josh Levett UoY - joshua.levett@york.ac.uk'
done < <(cut -d "," -f1 tags.txt)