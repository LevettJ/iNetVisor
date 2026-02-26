cat files_to_get.txt | while read line
do
    echo $line
    curl -L -O $line
done
echo "Done"