cat data/daily_data_files.txt | while read line
do
    echo $line
    bzip2 -dk $line
    echo "   ...extracted"
    extrct=${line::-4}
    python ../utils/process_daily_data.py -in $extrct -r2as data/router2as.json -asndb data/asndb.dat -o ${extrct}.json
    echo "   ...cleaning up"
    rm $extrct
    echo "   ...done"
    echo
done
echo "Done