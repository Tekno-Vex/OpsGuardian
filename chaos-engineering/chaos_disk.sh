#!/bin/bash
echo "Starting Disk Chaos — filling root partition..."
df -h /

echo "Creating large files in ~/diskfill/ ..."
mkdir -p ~/diskfill

i=1
while true; do
    USAGE=$(df / | tail -1 | awk '{print $5}' | tr -d '%')
    echo "Current disk usage: ${USAGE}%"
    if [ "$USAGE" -ge 75 ]; then
        echo "Target reached at ${USAGE}%! Holding for 6 minutes..."
        sleep 360
        break
    fi
    echo "Creating file $i (1GB)..."
    dd if=/dev/zero of=~/diskfill/fill_$i.dat bs=1M count=1000 status=none
    i=$((i+1))
done

echo "Cleaning up..."
rm -rf ~/diskfill/
echo "Disk Chaos complete. Space freed."
df -h /