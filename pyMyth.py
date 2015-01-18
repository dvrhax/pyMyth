#!/usr/bin/env python3

import sys, re
import datetime as dt
import requests
import subprocess
import stdmod3
import pytz


def sortFunc():
    pass

class pyMyth:
    def __init__(self, host, port=6544):
        self.baseAddr = 'http://{}:{}/'.format(host, port)
        self.headers = {'Accept':'application/json'}
        self.buildChannelMap()
        self.localtz = pytz.timezone('America/Detroit')
        self.utctz = pytz.utc
        
    def buildChannelMap(self):
        guide = self.getGuide('now', 'now')
        self.channelMap = {}
        for chan in guide['ProgramGuide']['Channels']:
            self.channelMap[chan['ChanNum']] = chan['ChanId']

    def getGuide(self, StartTime, EndTime, StartChanId=None, NumChannels=None, Details=None):
        params = {}
        if StartTime == 'now':
            params['StartTime'] = dt.datetime.utcnow().isoformat()
        else:
           params['StartTime'] = StartTime
        if EndTime == 'now':
            params['EndTime'] = dt.datetime.utcnow().isoformat()
        else:
           params['EndTime'] = EndTime
        if StartChanId:
           params['StartChanId'] = self.channelMap[StartChanId]
        if NumChannels:
           params['NumChannels'] = NumChannels
        if Details:
           params['Details'] = Details

        return requests.get('{}Guide/GetProgramGuide'.format(self.baseAddr), params = params, headers = self.headers).json()

    def getProgramDetails(self, ChanId, StartTime):
        params = {'ChanId':self.channelMap[ChanId], 'StartTime':StartTime}
        return requests.get('{}Guide/GetProgramDetails'.format(self.baseAddr), params = params, headers = self.headers).json()

    def getRecorded(self, StartIndex=0, Count=0, Descending=True):
        params = {'StartIndex':StartIndex, 'Count':Count}
        if Descending:
            params['Descending'] = 'true'
        else:
            params['Descending'] = 'false'

        return requests.get('{}Dvr/GetRecordedList'.format(self.baseAddr), params = params, headers = self.headers).json()

    def getUpcomingList(self, StartIndex=None, Count=None, ShowAll=None):
        params = {}
        if StartIndex:
           params['StartIndex'] = StartIndex
        if Count:
           params['Count'] = Count
        if ShowAll:
           params['ShowAll'] = ShowAll

        return requests.get('{}Dvr/GetUpcomingList'.format(self.baseAddr), params = params, headers = self.headers).json()

    def GetRecordSchedule(self, **params):
        #Should not be called directly
        #RecordId=None, Template=None, ChanId=None, StartTime=None, MakeOverride=None
        return requests.get('{}Dvr/GetRecordSchedule'.format(self.baseAddr), params = params, headers = self.headers).json()        

    def AddRecordSchedule(self, params):
        return requests.post('{}Dvr/AddRecordSchedule'.format(self.baseAddr), params = params, headers = self.headers).text

class pyMythHelper(pyMyth):
    #def __init__(self, host, port=6544):
        #parent.__init__(*args, **kargs)
    
    def iso2DT(self, dateTime, tz=None):
        if not tz: tz = self.utctz
        dt1 = dt.datetime(*map(int, re.split('[^\d]', dateTime)[:-1]))
        return dt1.replace(tzinfo=tz)

    def showUpcoming(self):
        upcoming = self.getUpcomingList()['ProgramList']['Programs']
        current = self.getCurrentlyRecording()
        cLen = []
        uLen = []

        for p in current:
            cLen.append(len('{Title}: {SubTitle} -'.format(**p)))

        for p in upcoming:
            uLen.append(len('{Title}: {SubTitle} -'.format(**p)))

        try:
            cMax = max(cLen)
        except ValueError:
            cMax = 0

        try:
            uMax = max(uLen)
        except ValueError:
            uMax = 0

        tsOffset = max(cMax, uMax) + 2
        cOffset = [tsOffset - ts for ts in cLen]
        uOffset = [tsOffset - ts for ts in uLen]

        for prog, header in zip((zip(current, cOffset), zip(upcoming, uOffset)), ('Current:', '\nUpcoming:')):
            print(header)
            for p, o in prog:
                p['startTime'] = self.iso2DT(p['StartTime']).astimezone(self.localtz)
                p['endTime'] = self.iso2DT(p['EndTime']).astimezone(self.localtz)
                print('{Title}: {SubTitle}{0:>{offset}} {startTime:%b %d} {startTime:%H:%M} to {endTime:%H:%M}'.format('-', offset = o, **p))

    def getCurrentlyRecording(self):
        cRecord = []
        now = dt.datetime.utcnow().isoformat()
        rec = self.getRecorded()['ProgramList']['Programs']
        for r in rec:
            if r['EndTime'] > now: #May change this in the future to compare the datetime objects instead of strings
                cRecord.append(r)
        return cRecord

    def recordNow(self, chanNum, debug=False):
        guide = self.getGuide('now', 'now', chanNum, 1)
        chan = guide['ProgramGuide']['Channels'][0]['Programs'][0]
        recRule = self.GetRecordSchedule(ChanId=self.channelMap[chanNum], StartTime=chan['StartTime'])['RecRule']
        recRule['Type'] = 'Single Record'
        recRule['Station'] = recRule['CallSign']
        if debug: return recRule
        print('RecordId: {}'.format(self.AddRecordSchedule(recRule)))
        self.showUpcoming()

    def programDetailsHelper(self, chanNum, Time):
        guide = self.getGuide(Time, Time, chanNum, 1)
        chan = guide['ProgramGuide']['Channels'][0]['Programs'][0]
        return self.getProgramDetails(chanNum, chan['StartTime'])

    def watch(self):
        recorded = self.getRecorded()['ProgramList']['Programs']
        progDict = {}

        for p in recorded:
            if p['SubTitle'] == '':
                p['SubTitle'] = p['Title']
            try:
                progDict[p['Title']][p['SubTitle']]={'ChanId':p['Channel']['ChanId'], 'StartTime':p['Recording']['StartTs']}
            except KeyError:
                progDict[p['Title']] = {p['SubTitle']:{'ChanId':p['Channel']['ChanId'], 'StartTime':p['Recording']['StartTs']}}

        show = stdmod3.select_func('SubTitle',stdmod3.select_func('prompt',progDict))

        subprocess.call(['mplayer', '-autosync', '30',' -cache', '8192', '{ba}Content/GetRecording?ChanId={ChanId}&StartTime={StartTime}'.format(ba=self.baseAddr, **show)])

    def showGuide(self):
        guideRaw = self.getGuide('now', 'now')['ProgramGuide']['Channels']
        #guide = [g['Programs'][0] for g in guideRaw]
        guide = []
        for g in guideRaw:
            g['Programs'][0].update({'ChanNum': g['ChanNum']})
            guide.append(g['Programs'][0])

        gLen = []

        for p in guide:
            gLen.append(len('{Title}: {SubTitle} -'.format(**p)))

        tsOffset = max(gLen) + 2
        gOffset = [tsOffset - ts for ts in gLen]

        for p, o in zip(guide, gOffset):
            p['startTime'] = self.iso2DT(p['StartTime']).astimezone(self.localtz)
            p['endTime'] = self.iso2DT(p['EndTime']).astimezone(self.localtz)
            #print('{Title}: {SubTitle}{0:>{offset}} {ChanNum:>4} {startTime:%H:%M} to {endTime:%H:%M}'.format('-', offset = o, **p))
            print('{ChanNum:>4} - {Title}: {SubTitle}{0:>{offset}} {startTime:%H:%M} to {endTime:%H:%M}'.format('-', offset = o, **p))

if __name__ == '__main__':
    pmh = pyMythHelper('mcu')
    if sys.argv[-1] == '--upcoming':
        pmh.showUpcoming()
    if sys.argv[-1] == '--watch':
        pmh.watch()
    if sys.argv[-1] == '--recordnow':
        pmh.recordNow(input('Channel: '))
    if sys.argv[-1] == '--guide':
        pmh.showGuide()
