import librosa
import soundfile as sf
from bs4 import BeautifulSoup
import os
import argparse
import warnings
import re

parser = argparse.ArgumentParser(description='Chunk wav file according to ELAN eaf subdivion of speech')
parser.add_argument('--wavfldr', metavar= 'w', type =str, help = 'wav input file')
parser.add_argument('--elanfldr', metavar='e', type = str, help = 'reference elan file')
parser.add_argument('--outfldr' , metavar='o', type = str, help= 'output folder for chunked wav and json files')
args = parser.parse_args()


def get_participants(markup, maxlen = 25000, exclude = [] ):
    """Extracts annotation tiers from elan eaf file. 
    The default argument 'excllude' takes a list of names of undesired tiers"""
    source = open(markup).read()
    soup = BeautifulSoup(source, 'xml')
    d = {}

    for t in soup.find_all('TIER'):
        try:
            if 'TIER_ID' in t.attrs and t.attrs['TIER_ID'] not in exclude and 'default-lt' in t.attrs.values():
                d[t.attrs['TIER_ID']] = t

        except Exception as e:
            print(e)

    sents = []
    tids = []
    for k,values in d.items():
        for v in values.find_all('ALIGNABLE_ANNOTATION'):
            ts1 = v['TIME_SLOT_REF1']
            ts2 = v['TIME_SLOT_REF2']
            tids.extend([ts1,ts2])
            annid = v['ANNOTATION_ID']
            sents.append([ts1,ts2,v.find('ANNOTATION_VALUE').get_text(), annid, k])

    tslots = {}
    for tslot in soup.find('TIME_ORDER').find_all('TIME_SLOT'):
        if 'TIME_VALUE' in tslot.attrs:
            tslots[tslot['TIME_SLOT_ID']]=  tslot['TIME_VALUE']
    timedsents = []
    for ts1,ts2,text,annid,k in sents:
        time1 = tslots[ts1]
        time2 = tslots[ts2]
        timedsents.append([ts1, int(time1), ts2, int(time2), text, annid,k])
    timedsents = sorted(timedsents, key = lambda x :x[3])
    out = []
    temp = []
    chunkl = maxlen
    for s in timedsents:
        if s[3] > chunkl:
            out.append(sorted(temp, key = lambda x : x[1]))
            temp = []
            temp.append(s)
            chunkl += maxlen

        else:
            temp.append(s)

    return timedsents

def get_time_text(parts, audiof, outfldr):
    d = {}
    audio_file_, sr = librosa.load(audiof)
    for i,sent in enumerate(parts):
        try:
            s_id, s, e_id, e, text, id_, speaker = sent
            if 'hhh' and 'hm' and 'XXX' and 'xxx' not in text:

                s = int(s*sr/1000)
                e = int(e*sr/1000)
                outfname = f'{audiof.split("/")[-1][:-4]}_{speaker}_{id_}.wav'
                sf.write(outfldr + outfname, audio_file_[s:e], sr)
                d[outfname] = re.sub(r'\t', '' ,text)
        except Exception as e:
            print(e)
    return d


files = [(f'{args.wavfldr}{wav}', f'{args.elanfldr}{wav[:-3]}eaf') for wav in os.listdir(args.wavfldr) if f'{wav[:-3]}eaf' in os.listdir(args.elanfldr) ]
data = []
if files == []:
    warnings.warn("There is a problem with your file names: do wav and eaf files have the same name?")
else:
    for wav, eaf in files:
        outeaf = get_participants(eaf) 
        textinfo = get_time_text(outeaf, wav, args.outfldr)
        for k,v in textinfo.items():
           data.append([k[:-4], args.outfldr+k, v])


with open(args.outfldr+'datainfo.csv', 'w') as outf:
    [outf.write(f'{name}\t{pth}\t{text}\n') for name, pth, text in data]
