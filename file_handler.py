import os
import time
import glob
from datetime import timedelta as td
from datetime import datetime as dt

sourcePath = '/var/www/html/sierpinski/'
maxage_days = 14


def get_mp4s():
    minage = dt.now() - td(hours=1)
    files = [
        f for f in set(glob.glob(sourcePath + '*/*.mp4'))
        if dt.fromtimestamp(os.path.getmtime(f)) < minage
    ]
    return set(files)


def filterT(filelist, minhr, maxhr):
    """Returns entries from filterlist which were taken between
    minhr and maxhr (e.g. 6, 22 will return files between 06:00
    and 21:59:59)
    """
    # format: xx-YYYYMMDDHHMMSS.mp4
    intime = []
    totalsize = 0
    for f in filelist:
        filedate = dt.fromtimestamp(os.path.getmtime(f))
        if minhr <= filedate.hour < maxhr:
            intime.append(f)
            totalsize += os.path.getsize(f)
    return set(intime), totalsize / 1024


def filterS(filelist, maxsize):
    """ Returns entries which are smaller than maxsize in bytes.
    """
    insize = []
    totalsize = 0
    for f in filelist:
        size = os.path.getsize(f)
        if size < maxsize:
            insize.append(f)
            totalsize += os.path.getsize(f)
    return set(insize), totalsize / 1024


def filterA(filelist, agelimit):
    """Returns entries which are older than the agelimit from now.
    """
    oldfiles = []
    totalsize = 0
    for f in filelist:
        filedate = dt.fromtimestamp(os.path.getmtime(f))
        if filedate < (dt.now() - agelimit):
            oldfiles.append(f)
            totalsize += os.path.getsize(f)
    return set(oldfiles), totalsize / 1024


def get_total_size(startdate, enddate):
    """ Takes datetime start and end, returns size of all files between
    those times. Uses file modified date."""
    filelist = get_mp4s()
    totalsize = 0
    for f in filelist:
        filedate = dt.fromtimestamp(os.path.getmtime(f))
        if (filedate > startdate) and (filedate < enddate):
            totalsize += os.path.getsize(f)
    return totalsize


def removeFiles(filelist):
    n = 0
    for f in filelist:
        try:
            os.remove(f)
            n += 1
        except FileNotFoundError:
            print(str(time.ctime()) + '        Could not remove file ' + f)
        except OSError:
            print(str(time.ctime()) + '        Permission denied ' + f)
    print(str(time.ctime()) + '    Removed {} files'.format(n))


def cleanVideos(minhr, maxhr, maxsize):
    remaining_files = get_mp4s()
    totalfilecount = len(remaining_files)

    filterfuncs = [{
        'function': filterT,
        'condition': (minhr, maxhr),
        'desc': 'Removing {} during day, {:.0f} KB'
    }, {
        'function': filterS,
        'condition': (maxsize, ),
        'desc': 'Removing {} below size limit, {:.0f} KB'
    }, {
        'function': filterA,
        'condition': (td(days=maxage_days), ),
        'desc': 'Removing {} old files, {:.0f} KB'
    }]

    log = ''
    filecount = 0
    removals = []
    for func_obj in filterfuncs:
        f, s = func_obj['function'](remaining_files, *func_obj['condition'])
        if len(f) > 0:
            log += '\n' + str(time.ctime()) + '        '
            log += func_obj['desc'].format(len(f), s)
            filecount += len(f)
            removals += f
            remaining_files -= f

    if len(removals) > 0:
        status = str(time.ctime()) + '    '
        status += 'Checked {} videos'.format(totalfilecount)
        print(status + log)
        removeFiles(removals)
