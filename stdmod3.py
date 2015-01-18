#!/usr/bin/python
import binascii, os

def pyconfig(pyname,configlist):
    pyname=os.path.split(pyname)[1]
    configpath=os.path.expanduser('~/.pyconfig')
    if not os.path.isdir(configpath):
        os.mkdir(configpath)
    configfile='pyconfig'
    configfp=os.path.join(configpath,configfile)
    if not os.path.isfile(configfp):
        pyconfig_write(configfp,pyname,'',configlist)
    return pyconfig_read(configfp,pyname,configlist)

def pyconfig_write(fpath,sname,contents,ilist):
    dict={}
    print('Setup %s' % sname)
    for item in ilist:
        dict[item]=raw_input('%s: ' % item)
    
    contents+='[%s]\n%s' % (sname,list2string(dict2list(dict,';;'),'\n'))

    fopen=open(fpath,'wb')
    fopen.write(contents+'\n')
    fopen.close()
    return contents

def pyconfig_read(fpath,sname,ilist):
    fopen=open(fpath,'rb')
    contents=fopen.read()
    fopen.close()
    clist=contents.split('\n')
    if not '[%s]' % sname in clist:
        contents=pyconfig_write(fpath,sname,contents,ilist)
    section=contents.split('[%s]' % sname)[1].split('[')[0]
    slist=section.split('\n')[1:]
    odict={}
    for item in slist:
        if item != '':
            kv=item.split(';;')
            if kv[1]=='True':kv[1]=True
            if kv[1]=='False':kv[1]=False
            odict[kv[0]]=kv[1]
    return odict

def dict2list(idict,sep):
    output=[]
    for key in idict:
        output.append('%s%s%s' % (key, sep, idict[key]))
    return output

def list2string(ilist=[],sep='\n'):
    if type(ilist)!=type([]):return ilist
    return sep.join(ilist)
    #output=""
    #for element in ilist:
    #    try:
    #        output+=str(element)+sep
    #    except UnicodeEncodeError:
    #        pass
    #    trim=-1*len(sep)
    #return output[:trim]

def bhex2int(bhex):
    return int(binascii.b2a_hex(bhex),16)

def int2bhex(num,bytes):
    """int2bhex(num,bytes)\nTakes an Integer input and a byte length and returns a hex string in byte notation"""
    numashex=hex(num)[2:]#Convert int to hex and strip off leading chars.
    if len(numashex)/2.0 != int(len(numashex)/2.0):# Check to see if the resulting number is odd
        numashex='0'+numashex # Add a leading zero to make it an even number of digits
    bhex=binascii.a2b_hex(numashex)
    while len(bhex)<bytes:
        bhex=binascii.a2b_hex('00')+bhex
    return bhex

def parsearg(ilist,arg):
    """parsearg(ilist,arg)\nReturns the next item in ilist following arg.  Returns False if arg isn't present"""
    if arg in ilist:
        return (ilist[ilist.index(arg)+1],True)
    else:
        return ('',False)

def parseargdict(idict,arglist,strictReturn=False):
    """parseargdict(idict,arglist)\nReturns a dictionary containing commandline options matched with variables provided in idict and a boolean if the command line contains parameters not contained in idict."""
    arglist=arglist[1:] # Strip off the executable
    odict={}
    for k,v in idict.iteritems():
        clArg,argFound=parsearg(arglist,k)
        if clArg=='True':
            clArg=True
        elif clArg=='False':
            clArg=False
        if argFound:
            odict[k]=clArg
        elif not strictReturn:
            odict[k]=v
        if k in arglist:
            i=arglist.index(k)
            del arglist[i+1]
            del arglist[i]
    for arg in arglist:
        if not arg in idict.keys():
            return (odict,True)
    return (odict,False)

def select_func(prompt_txt,idict,default=False):
    """select_func(prompt_txt,idict,default)\ntakes a dictionary and presents a list of the keys for selection.  The function then returns the value for that key pair.  Default can be a key from the dictionary or false which defaults to the first key for a default value"""
    n=1
    keydict={}
    print(prompt_txt)
    keylist=list(idict.keys()) #End run around new dict_keys type
    keylist.sort()
    if not default:
        default=keylist[0]
    for key in keylist:
        keydict[n]=key
        if key==default:
            default_choice=n
        print("\t%s. %s"%(n, key))
        n+=1
    choice=0
    while choice<1 or choice >= n:
        temp=input("Choice [%r]: " % default)
        if temp=="":
            choice=default_choice
        try:
            choice=int(temp)
        except:
            pass
    return idict[keydict[choice]] 
