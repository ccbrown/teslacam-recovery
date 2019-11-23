#!/bin/bash
diskutil list /dev/disk2s1
diskutil unmount /dev/disk2s1
sudo ./run.py /dev/disk2s1 ~/Downloads/footage/ 480821 
#> ~/Downloads/footage/log.txt
