#!/bin/bash

# Abort if any command fails
set -e

echo "iNetVisor"
echo "---------"
echo "Starting collection"

mkdir data
cd data
mkdir source
mkdir working
mkdir output

echo "  Installing prerequisites"

pip install -U requirements.txt

echo "  Finding data from route collectors"

# Start date X for Y days
python ../collectors/bgp/route_collectors.py -s "01/01/2024 00:00:00" -d "1209600" -o "working/collectors.json"

echo "  Collectors found"

echo "  Collecting BGP MRT files (this will take some time)"

# Start date 10/07/2024 for 10 days
python ../scripts/mrt_to_paths.py -in working/collectors.json -o working/paths.txt

echo "  BGP paths collected as paths.txt"
echo "  Splitting paths.txt into 20GB parts"

cd working

# Split into 20GB files
split -C 20GB --numeric-suffixes paths.txt paths_part_

echo "  Creating compressed backup (paths.tar.gz)"

tar -czvf paths.tar.gz paths_part_*

echo "  Creating list of path files (list_of_path_files.txt)"

ls | grep paths_part_ > list_of_path_files.txt

echo "  Collecting daily paths from PCH"

python ../../collectors/bgp/pch_daily_collector.py "2024" "01" "01"
echo -e "\n2024-01-01-pch_paths.txt" >> list_of_path_files.txt

echo "BGP collection completed at `date`"
echo

echo "Processing BGP data"

echo "  Cleaning BGP paths"

python ../../utils/path_cleaner.py -in "list_of_path_files.txt" -pdb "peeringdb_2_dump_2024_01_14.json" -o "cleaned"

echo "  Cleaned path files"
echo "  Creating list of cleaned path files (clean_path_files.txt)"

cd cleaned
ls | grep clean_paths > clean_path_files.txt

echo "  Exporting list of naive adjacencies"

cd ../../
python ../utils/naive_adjacencies.py -in working/cleaned/clean_path_files.txt -o output/naive_adj.txt

echo "  Exporting 'sanitized_rib.txt' in AS-Rank format"

python ../utils/format_asrank.py -in working/cleaned/clean_path_files.txt -o output/sanitized_rib.txt

echo "Completed"