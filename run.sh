#!/bin/bash

diskId=disk2
deviceNode=/dev/${diskId}s1

isUsbDrive() {
	diskutil list $diskId
	echo "=== $diskId info"
    info=$(diskutil info $diskId | egrep 'Protocol|Whole|Media Name|Removable')

    local returnStr=$(printf "$info\n" | grep -m1 Protocol | cut -d ':' -f 2)
    echo "Protocol: $returnStr"
    if [[ "$returnStr" != *"USB" ]]; then echo "Not $expectedDeviceName. Exit"; exit; fi

    returnStr=$(printf "$info\n" | grep -m1 Whole | cut -d ':' -f 2)
    echo "Whole: $returnStr"
    if [[ "$returnStr" != *"Yes" ]]; then echo "Not whole $expectedDeviceName. Exit"; exit; fi

    echo "$info"
}

isUsbDrive

echo ""
read -p "Please confirm that $deviceNode is your teslacam usb? (y/n) " answer
if [ "$answer" != "y" ]; then 
    echo "In run.sh file, edit the line diskId=disk2 to your usb drive"
    exit; fi

diskutil unmount $deviceNode
mkdir -p ~/Downloads/teslacam/
sudo ./run.py $deviceNode ~/Downloads/teslacam/ 0 
