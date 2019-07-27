"""

Designed and Developed by-
Udayraj Deshmukh 
https://github.com/Udayraj123

"""

# In[62]:
import re
import os
import sys
import cv2
import glob
from csv import QUOTE_NONNUMERIC
import argparse
from time import localtime,strftime,time
from random import randint, sample as randomSample
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import imutils
from globals import *
from utils import *
from template import *

# TODO: Sometime later-
# from colorama import init
# init()
# from colorama import Fore, Back, Style

def move(error_code, filepath,filepath2):
    print("Dummy Move:  "+filepath, " --> ",filepath2)
    global filesNotMoved
    filesNotMoved += 1
    return True
    # if(error_code!=NO_MARKER_ERR):
    #     print("Error Code: "+str(error_code))

    global filesMoved
    if(not os.path.exists(filepath)):
        print('File already moved')
        return False
    if(os.path.exists(filepath2)):
        print('ERROR : Duplicate file at '+filepath2)
        return False

    print("Moved:  "+filepath, " --> ",filepath2)
    os.rename(filepath,filepath2)
    filesMoved+=1
    return True


def processOMR(squad, omrResp):
    # Note: This is a reference function. It is not part of the OMR checker 
    #       So its implementation is completely subjective to user's requirements.
    
    # Additional Concatenation key
    omrResp['Squad'] = squad 
    resp={}
    # symbol for absent response
    UNMARKED = '' # 'X'

    # Multi-Integer Type Qs / RollNo / Name
    for qNo, respKeys in TEMPLATES[squad].concats.items():
        resp[qNo] = ''.join([omrResp.get(k,UNMARKED) for k in respKeys])
    # Normal Questions
    for qNo in TEMPLATES[squad].singles:
        resp[qNo] = omrResp.get(qNo,UNMARKED)
    # Note: Concatenations and Singles together should be mutually exclusive 
    # and should cover all questions in the template(exhaustive)
    # ^TODO add a warning if omrResp has unused keys remaining
    
    return resp

# In[76]:

def report(Status,streak,scheme,qNo,marked,ans,prevmarks,currmarks,marks):
    print('%s \t %s \t\t %s \t %s \t %s \t %s \t %s ' % (qNo,
          Status,str(streak), '['+scheme+'] ',(str(prevmarks)+' + '+str(currmarks)+' ='+str(marks)),str(marked),str(ans)))

# check sectionwise only.
def evaluate(resp,squad,explain=False):
    global Answers,Sections
    marks = 0
    answers = Answers[squad]
    if(explain):
        print('Question\tStatus \t Streak\tSection \tMarks_Update\tMarked:\tAnswer:')
    for scheme,section in Sections[squad].items():
        sectionques = section['ques']
        prevcorrect=None
        allflag=1
        streak=0
        for q in sectionques:
            qNo = 'q'+str(q)
            ans = answers[qNo]
            marked = resp.get(qNo, 'X')
            firstQ = sectionques[0]
            lastQ = sectionques[len(sectionques)-1]
            unmarked = marked=='X' or marked==''
            bonus = 'BONUS' in ans
            correct = bonus or (marked in ans)
            inrange=0

# ('q13(Power2) Correct(streak0) -3 + 2 = -1', 'C', ['C'])
# ('q14(Power2) Correct(streak0) -1 + 2 = 1', 'A', ['A'])
# ('q15(Power2) Incorrect(streak0) 1 + -1 = 0', 'C', ['B'])

            if(unmarked or int(q)==firstQ):
                streak=0
            elif(prevcorrect == correct):
                streak+=1
            else:
                streak=0


            if( 'allNone' in scheme):
                #loop on all sectionques
                allflag = allflag and correct
                if(q == lastQ ):
                    #at the end check allflag
                    prevcorrect = correct
                    currmarks = section['marks'] if allflag else 0
                else:
                    currmarks = 0

            elif('Proxy' in scheme):
                a=int(ans[0])
                #proximity check
                inrange = 1 if unmarked else (float(abs(int(marked) - a))/float(a) <= 0.25)
                currmarks = section['+marks'] if correct else (0 if inrange else -section['-marks'])

            elif('Fibo' in scheme or 'Power' in scheme or 'Boom' in scheme):
                currmarks = section['+seq'][streak] if correct else (0 if unmarked else -section['-seq'][streak])
            elif('TechnoFin' in scheme):
                currmarks = 0
            else:
                print('Invalid Sections')
            prevmarks=marks
            marks += currmarks

            if(explain):
                if bonus:
                    report('BonusQ',streak,scheme,qNo,marked,ans,prevmarks,currmarks,marks)
                elif correct:
                    report('Correct',streak,scheme,qNo,marked,ans,prevmarks,currmarks,marks)
                elif unmarked:
                    report('Unmarked',streak,scheme,qNo,marked,ans,prevmarks,currmarks,marks)
                elif inrange:
                    report('InProximity',streak,scheme,qNo,marked,ans,prevmarks,currmarks,marks)
                else:
                    report('Incorrect',streak,scheme,qNo,marked,ans,prevmarks,currmarks,marks)

            prevcorrect = correct

    return marks

# os.sep is not an issue here in iglob (handled internally)
allOMRs = list(glob.iglob(OMR_INPUT_DIR+'*/*/*.jpg')) + list(glob.iglob(OMR_INPUT_DIR+'*/*/*.png'))

timeNowHrs=strftime("%I%p",localtime())
start_time = int(time())

# construct the argument parse and parse the arguments
argparser = argparse.ArgumentParser()
# https://docs.python.org/3/howto/argparse.html
# store_true: if the option is specified, assign the value True to args.verbose. Not specifying it implies False.
argparser.add_argument("-c", "--noCropping", required=False, dest='noCropping', action='store_true', help="Disable page contour detection - the program will take image as it is.")
argparser.add_argument("-m", "--noMarkers", required=False, dest='noMarkers', action='store_true', help="Disable marker detection - if page is already cropped at marker points.")
argparser.add_argument("-a", "--noAlign", required=False, dest='noAlign', action='store_true', help="Disable automatic template alignment - if columns are not varying significantly(saves computation).")
argparser.add_argument("-l", "--setLayout", required=False, dest='setLayout', action='store_true', help="Use this option to set up OMR template layout by modifying your '*_template.json' file interactively")

args, unknown = argparser.parse_known_args()
args = vars(args)
if(len(unknown)>0):
    print("\nError: Unknown arguments:",unknown)
    argparser.print_help()
    exit(0)

OUTPUT_SET, respCols, emptyResp, filesObj, filesMap = {}, {}, {}, {}, {}
print("\nChecking Files...")
# Loop over squads
for squad in templJSON.keys():
    # Concats + Singles includes : all template keys including RollNo if present
    # sort qNos using integer instead of alphabetically
    KEY_FN_SORTING = lambda x: int(x[1:]) if ord(x[1]) in range(48,58) else 0
    respCols[squad] = sorted( list(TEMPLATES[squad].concats.keys()) + TEMPLATES[squad].singles, key=KEY_FN_SORTING)
    emptyResp[squad] = ['']*len(respCols[squad])
    sheetCols = ['file_id','input_path','output_path','score']+respCols[squad]
    
    OUTPUT_SET[squad] = []
    filesObj[squad] = {}
    filesMap[squad] = {
        "Results": resultDir+'Results_'+squad+'_'+timeNowHrs+'.csv',
        "MultiMarked": manualDir+'MultiMarkedFiles_'+squad+'.csv',
        "Errors": manualDir+'ErrorFiles_'+squad+'.csv',
        "BadRollNos": manualDir+'BadRollNoFiles_'+squad+'.csv'
    }
    for fileKey,fileName in filesMap[squad].items():
        if(not os.path.exists(fileName)):
            print("Note: Created new file: %s" % (fileName))
            filesObj[squad][fileKey] = open(fileName,'a') # still append mode req [THINK!]
            # Create Header Columns
            pd.DataFrame([sheetCols], dtype = str).to_csv(filesObj[squad][fileKey], quoting = QUOTE_NONNUMERIC,header=False, index=False) 
        else:
            print('Present : appending to %s' % (fileName))
            filesObj[squad][fileKey] = open(fileName,'a')

squadlang="XXdummySquad"
inputFolderName="dummyFolder"

filesCounter=0
mws, mbs = [],[]
# PRELIM_CHECKS for thresholding
if(PRELIM_CHECKS):
    # TODO: add more using unit testing
    TEMPLATE = TEMPLATES["H"]
    ALL_WHITE = 255 * np.ones((TEMPLATE.dims[1],TEMPLATE.dims[0]), dtype='uint8')
    OMRresponseDict,final_marked,MultiMarked,multiroll = readResponse("H",ALL_WHITE,name = "ALL_WHITE", savedir = None, noAlign=True)
    print("ALL_WHITE",OMRresponseDict)
    if(OMRresponseDict!={}):
        print("Preliminary Checks Failed.")
        exit(0)
    ALL_BLACK = np.zeros((TEMPLATE.dims[1],TEMPLATE.dims[0]), dtype='uint8')
    OMRresponseDict,final_marked,MultiMarked,multiroll = readResponse("H",ALL_BLACK,name = "ALL_BLACK", savedir = None, noAlign=True)
    print("ALL_BLACK",OMRresponseDict)
    show("Confirm : All bubbles are black",final_marked,1,1)

print('\nConfig:')
print("\tPages Cropped   : "+str(args["noCropping"]))
print("\tMarkers Present : "+str(not args["noMarkers"]))
print("\tAuto Alignment  : "+str(not args["noAlign"]))
print("\n %d total images present." % (len(allOMRs)))

for filepath in allOMRs:
    filesCounter+=1
    # In windows: all '\' will be replaced by '/'
    filepath = filepath.replace(os.sep,'/')

    # Prefixing a 'r' to use raw string (escape character '\' is taken literally)
    finder = re.search(r'.*/(.*)/(.*)/(.*)',filepath,re.IGNORECASE)
    if(finder):
        inputFolderName, squadlang, filename = finder.groups()
        #FIXME : SEE FOR HINDI ISSUES
        squad,lang = squadlang[0],squadlang[1]
        squadlang = squadlang+"/"
    else:
        filename = 'dummyFile'+str(filesCounter)
        print("Error: Filepath not matching to Regex: "+filepath)
        continue

    if(squad not in templJSON.keys()):
        print("Error: Template not present for squad:",squad, 'Filepath:', filepath)
        continue
    # TODO make it independent of squad rule
    if(squad not in ['H','J']):
        print("Error: Unexpected Squad Folder-",squad, 'Filepath:', filepath)
        exit(0)

    inOMR = cv2.imread(filepath,cv2.IMREAD_GRAYSCALE)
    print('')
    print('(%d) Opening image: \t' % (filesCounter),filepath, "\tResolution: ",inOMR.shape)
    # show("inOMR",inOMR,1,1)
    OMRcrop = getROI(inOMR,filename, noCropping=args["noCropping"], noMarkers=args["noMarkers"])
    if(OMRcrop is None):
        newfilepath = errorsDir+squadlang+filename
        OUTPUT_SET[squad].append([filename]+emptyResp[squad])
        if(move(NO_MARKER_ERR, filepath, newfilepath)):
            err_line = [filename,filepath,newfilepath,"NA"]+emptyResp[squad]
            pd.DataFrame(err_line, dtype=str).T.to_csv(filesObj[squad]["Errors"], quoting = QUOTE_NONNUMERIC,header=False,index=False)
        continue

    if(args["setLayout"]):
        # show("Sample OMR", resize_util_h(OMRcrop,display_height), 0) <-- showimglvl 2 does the job
        templateLayout = drawTemplateLayout(OMRcrop, TEMPLATES[squad], shifted=False, border=2)
        show("Template Layout", templateLayout,1,1)
        print('Setup Layout Note: Press Q to continue, Ctrl+C in terminal to exit')
        continue
    #uniquify
    newfilename = inputFolderName + '_' + filename
    savedir = saveMarkedDir+squadlang
    OMRresponseDict,final_marked,MultiMarked,multiroll = readResponse(squad,OMRcrop,name = newfilename, savedir = savedir, noAlign=args["noAlign"])

    #convert to ABCD, getRoll,etc
    resp = processOMR(squad,OMRresponseDict)
    print("Read Response: \t", resp)

    #This evaluates and returns the score attribute
    score = evaluate(resp, squad,explain=explain)
    respArray=[]
    for k in respCols[squad]:
        respArray.append(resp[k])
    OUTPUT_SET[squad].append([filename]+respArray)
    # if((multiroll or not (resp['Roll'] is not None and len(resp['Roll'])==11))):
    if(MultiMarked == 0):
        filesNotMoved+=1;
        newfilepath = savedir+newfilename
        # Enter into Results sheet-
        results_line = [filename,filepath,newfilepath,score]+respArray
        # Write/Append to results_line file(opened in append mode)
        pd.DataFrame(results_line, dtype=str).T.to_csv(filesObj[squad]["Results"], quoting = QUOTE_NONNUMERIC,header=False,index=False)
        print("[%d] Graded with score: %.2f" % (filesCounter, score), '\t',newfilename)
        # print(filesCounter,newfilename,resp['Roll'],'score : ',score)
    else:
        # MultiMarked file
        print('[%d] MultiMarked, moving File: %s' % (filesCounter, newfilename))
        newfilepath = multiMarkedDir+squadlang+filename
        if(move(MULTI_BUBBLE_WARN, filepath, newfilepath)):
            mm_line = [filename,filepath,newfilepath,"NA"]+respArray
            pd.DataFrame(mm_line, dtype=str).T.to_csv(filesObj[squad]["MultiMarked"], quoting = QUOTE_NONNUMERIC,header=False,index=False)
        # else:
        #     Add appropriate record handling here
        #     pass
            
    #else if: 
    # TODO: Apply validation on columns like roll no to make use of badRollsArray
    
    # flush after every 20 files
    if(filesCounter % 20 == 0):
        for squad in templJSON.keys():
            for fileKey in filesMap[squad].keys():
                filesObj[squad][fileKey].flush()
        break
# x = x.sort_values(by=['score','num_correct','num_wrong'],ascending=False)
# x.to_sql('test.sql','SQLAlchemy')

for squad in templJSON.keys():
    for fileKey in filesMap[squad].keys():
        filesObj[squad][fileKey].close()
    
timeChecking=float(time()-start_time) if filesCounter else 1
print('')
print('Total files processed : %d ' % (filesCounter))
print('Total files moved : %d ' % (filesMoved))
print('Total files not moved (Sum should tally) : %d ' % (filesNotMoved))
if(filesCounter==0):
    print("\n\tINFO: No Images found at "+OMR_INPUT_DIR+'*/*/*.jpg'+". Check your directory structure.")
else:
    if(showimglvl<=0):
        print('\nFinished Checking %d files in %.1f seconds i.e. ~%.1f minutes.' % 
        (filesCounter, timeChecking, timeChecking/60))
        print('OMR Processing Rate :\t  ~%.2f sec/OMR' % (timeChecking/filesCounter))
        print('OMR Processing Speed :\t ~%.2f OMRs/minute' % ((filesCounter*60)/timeChecking))
    else:
        print("\nTotal script time :", timeChecking,"seconds")


if(showimglvl<=1):
    # colorama this
    print("\nTip: To see some awesome visuals, open globals.py and increase 'showimglvl'")


for squad in templJSON.keys():
    TEST_FILE = 'inputs/TechnothlonOMRDataset_'+squad+'.csv'
    if(os.path.exists(TEST_FILE)):
        print("\nStarting evaluation for: "+TEST_FILE)

        TEST_COLS = ['file_id']+respCols[squad]
        y_df = pd.read_csv(TEST_FILE, dtype=str)[TEST_COLS].replace(np.nan,'',regex=True).set_index('file_id')
        
        if(np.any(y_df.index.duplicated)):
            y_df_filtered = y_df.loc[~y_df.index.duplicated(keep='first')]
            print("WARNING: Found duplicate File-ids in file %s. Removed %d rows from testing data. Rows remaining: %d" % (TEST_FILE, y_df.shape[0] - y_df_filtered.shape[0], y_df_filtered.shape[0] ))
            y_df = y_df_filtered
        
        x_df = pd.DataFrame(OUTPUT_SET[squad], dtype=str, columns=TEST_COLS).set_index('file_id')
        # print("x_df",x_df.head())
        # print("\ny_df",y_df.head())
        
        intersection = y_df.index.intersection(x_df.index)
        #checking the merge is okay
        if(intersection.size == x_df.index.size): 
            y_df = y_df.loc[intersection]
            x_df['TestResult'] = (x_df==y_df).all(axis=1).astype(int)
            print(x_df.head())
            print("\n\t Accuracy on the %s Dataset: %.6f" %(TEST_FILE, (x_df['TestResult'].sum()/x_df.shape[0])))
        else:
            print("\nERROR: Insufficient Testing Data: Have you appended MultiMarked data yet?")
            print("Missing File-ids: ", list(x_df.index.difference(intersection)))



# Use this data to train as +ve feedback
if(showimglvl>=0 and filesCounter>10):
    for x in [thresholdCircles]:#,badThresholds,veryBadPoints, mws, mbs]:
        if(x != []):
            x = pd.DataFrame(x)
            print( x.describe() )
            plt.plot(range(len(x)),x)
            plt.title("Mystery Plot")
            plt.show()
        else:
            print(x)

