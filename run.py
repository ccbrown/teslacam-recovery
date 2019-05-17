#!/usr/bin/python

import os
import sys
import struct

# Used for debugging.


def dumpBinary(data):
    offset = 0
    for byte in data:
        print '%02X ' % ord(byte),
        offset += 1
        if offset % 16 == 0:
            print
        elif offset % 8 == 0:
            print ' ',
    return


if len(sys.argv) < 3:
    print 'Usage: '+sys.argv[0]+' input outputdir'
    sys.exit()

f = open(sys.argv[1], 'rb')

bootSector = f.read(512)

bytesPerSector,       = struct.unpack("<H", bootSector[0x0B:0x0D])
sectorsPerCluster,    = struct.unpack("<B", bootSector[0x0D])
reservedSectors,      = struct.unpack("<H", bootSector[0x0E:0x10])
numberOfFATs,         = struct.unpack("<B", bootSector[0x10])
maxRootDirEntries,    = struct.unpack("<H", bootSector[0x11:0x13])
totalSectors,         = struct.unpack("<H", bootSector[0x13:0x15])
sectorsPerFAT,        = struct.unpack("<I", bootSector[0x24:0x28])
rootDirectoryCluster, = struct.unpack("<I", bootSector[0x2c:0x30])

if totalSectors == 0:
    totalSectors, = struct.unpack("<I", bootSector[0x20:0x24])

totalClusters = totalSectors/sectorsPerCluster
bytesPerCluster = bytesPerSector*sectorsPerCluster

print 'Bytes per sector: %d' % bytesPerSector
print 'Sectors per cluster: %d' % sectorsPerCluster
print 'Reserved sectors: %d' % reservedSectors
print 'Number of FATs: %d' % numberOfFATs
print 'Maximum root directory entries: %d' % maxRootDirEntries
print 'Total sectors: %d' % totalSectors
print 'Total clusters: %d' % totalClusters
print 'Sectors per FAT: %d' % sectorsPerFAT
print 'Root Directory Cluster: %d' % rootDirectoryCluster


def sect2byte(sect):
    return sect*bytesPerSector


def clust2byte(clust):
    return sect2byte(reservedSectors+numberOfFATs*sectorsPerFAT+maxRootDirEntries*32/bytesPerSector+(clust-2)*sectorsPerCluster)


def isNonzero(data):
    for x in data:
        if ord(x) != 0x00:
            return True
    return False


fatEntries = list()

print 'Reading FATs at offset %d . . .' % sect2byte(reservedSectors)

f.seek(sect2byte(reservedSectors))

for i in range(0, numberOfFATs):
    fat = f.read(sectorsPerFAT*bytesPerSector)
    j = 0
    while j < sectorsPerFAT*bytesPerSector:
        entry, = struct.unpack("<I", fat[j:j+4])
        fatEntries.append(entry & 0x0FFFFFFF)
        j += 4


def readDirectory(directory_cluster, tabs, path='/', root=False):
    pad = list()
    for i in range(0, tabs):
        pad.append('\t')
    pad = ''.join(pad)

    while True:
        f.seek(clust2byte(directory_cluster))
        lfn = ''
        for i in range(bytesPerCluster / 32):
            entry = f.read(32)

            short_filename = entry[0:8]
            extension = entry[8:11]
            attributes = ord(entry[11])
            lastModifiedTime, = struct.unpack("<H", entry[0x16:0x18])
            lastModifiedDate, = struct.unpack("<H", entry[0x18:0x1a])
            clusterLow,       = struct.unpack("<H", entry[0x1a:0x1c])
            clusterHigh,      = struct.unpack("<H", entry[0x14:0x16])
            filesize,         = struct.unpack("<I", entry[28:32])
            cluster = (clusterHigh << 16) | clusterLow

            filename = lfn.replace('\xff', '').replace(
                '\0', '') if lfn != '' else ('%s.%s' % (short_filename, extension))

            if attributes == 0 and cluster == 0:
                continue

            if attributes != 0x0F:
                # Not a long file name.
                print '\n%sFilename:   %s' % (pad, filename)
                print '%sAttributes: 0x%02X' % (pad, attributes)
                print '%sFilesize:   %d' % (pad, filesize)
                print '%sLast Modified: %d-%d-%d %d:%02d:%02d' % (pad,
                                                                  1980 +
                                                                  ((lastModifiedDate & 0xfe00) >> 9), (
                                                                      lastModifiedDate & 0x1e0) >> 5, lastModifiedDate & 0x1f,
                                                                  (lastModifiedTime & 0xf800) >> 11, (
                                                                      lastModifiedTime & 0x7e0) >> 5, lastModifiedTime & 0x1f
                                                                  )
                lfn = ''

                firstCluster = cluster
                curCluster = cluster
                lastCluster = firstCluster - 1
                while curCluster < 0x0FFFFFF0:
                    if curCluster != lastCluster + 1:
                        print '%sClusters: %d - %d' % (pad,
                                                       firstCluster, lastCluster)
                        firstCluster = curCluster
                    lastCluster = curCluster
                    curCluster = fatEntries[curCluster]
                print '%sClusters: %d - %d' % (pad, firstCluster, lastCluster)

            if attributes == 0x0F:
                # Long file name.
                lfn = entry[0x01:0x01+10] + \
                    entry[0x0e:0x0e+12] + entry[0x1c:0x1c+4] + lfn
            elif attributes & 0x08:
                # Volume label.
                pass
            elif attributes & 0x10 and short_filename != '.       ' and short_filename != '..      ':
                print '%sEntering directory . . .' % pad
                # Create the directory structure.
                try:
                    os.mkdir('%s%s%s' % (sys.argv[2], path, filename))
                except OSError:
                    pass
                prev_pos = f.tell()
                readDirectory(cluster, tabs+1, '%s%s/' % (path, filename))
                f.seek(prev_pos)
            elif short_filename != '.       ' and short_filename != '..      ' and filesize != 0xFFFFFFFF:
                # Modify this condition if you want to export some files.
                if True:
                    continue

                # Export the files.
                prev_pos = f.tell()
                fout = open('%s%s%s' % (sys.argv[2], path, filename), 'wb')

                # For recovering files, it may be useful to assume contiguous clusters.
                contiguous = True
                if contiguous:
                    f.seek(clust2byte(cluster))
                    fout.write(f.read(filesize))
                else:
                    curCluster = cluster
                    while curCluster < 0x0FFFFFF0:
                        f.seek(clust2byte(curCluster))
                        fout.write(f.read(bytesPerCluster))
                fout.close()
                f.seek(prev_pos)
        directory_cluster = fatEntries[directory_cluster]
        if (directory_cluster & 0xFFFFFF8) == 0xFFFFFF8:
            break


def find_mp4s(start_cluster, end_cluster, assumed_size):
    try:
        os.mkdir('%s/mp4s' % (sys.argv[2]))
    except OSError:
        pass
    cluster = start_cluster
    while cluster < end_cluster:
        if cluster % 1000 == 0:
            print 'Currently on cluster %d' % (cluster)
        f.seek(clust2byte(cluster))
        header = f.read(12)
        if header == '\0\0\0 ftypmp42':
            print 'Found mp4 at cluster %d' % (cluster)
            f.seek(clust2byte(cluster))
            fout = open('%s/mp4s/%d.mp4' % (sys.argv[2], cluster), 'wb')
            f.seek(clust2byte(cluster))
            fout.write(f.read(assumed_size))
            fout.close()
        cluster += 1


# If you want to do a faster, more targeted search, you can uncomment these lines and use the output
# to specify a cluster range to find_mp4s below:

#print 'Reading directories...'
#readDirectory(rootDirectoryCluster, 1)

print 'Finding mp4s...'
find_mp4s(0, totalClusters, 40000000)

print

f.close()
