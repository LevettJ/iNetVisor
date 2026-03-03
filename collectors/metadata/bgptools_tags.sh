#!/bin/bash

# THIS CODE WILL NOT WORK UNTIL THE curl LINES ARE UNCOMMENTED AND --user-agent STRINGS COMPLETED

echo 'Collecting tag data from bgp.tools'
cd ../../data/source
#curl -O https://bgp.tools/tags.txt --user-agent 'NAME ORG - CONTACT@EMAIL'

mkdir bgptools-tags

echo 'Pulling tag files'
while IFS="," read -r tag
do
    sleep 3
    #curl "https://bgp.tools/tags/$tag.csv" -o "bgptools-tags/$tag.csv" --user-agent 'NAME ORG - CONTACT@EMAIL'
done < <(cut -d "," -f1 ../tags.txt)