"""

Designed and Developed by-
Udayraj Deshmukh 
https://github.com/Udayraj123

"""

"""
Constants
"""
display_height = int(480)
display_width  = int(640)
windowWidth = 1280
windowHeight = 720

saveMarked = 1
showimglvl = 2
saveimglvl = 0
PRELIM_CHECKS=0
saveImgList = {}
resetpos = [0,0]
explain= 1
# autorotate=1

BATCH_NO=1000
NO_MARKER_ERR=12
MULTI_BUBBLE_WARN=15

# For preProcessing
GAMMA_LOW = 0.7
GAMMA_HIGH = 1.25

ERODE_SUB_OFF = 1

# For new ways of determining threshold
MIN_GAP, MIN_STD = 30, 25
MIN_JUMP = 20
# If only not confident, take help of globalTHR
CONFIDENT_JUMP = MIN_JUMP+15
JUMP_DELTA = 40
# MIN_GAP : worst case gap of black and gray

# Templ alignment parameters
ALIGN_RANGE  = range(-5,6,1) 
#TODO ^THIS SHOULD BE IN LAYOUT FILE AS ITS RELATED TO DIMENSIONS
# ALIGN_RANGE  = [-6,-4,-2,-1,0,1,2,4,6]

# max threshold difference for template matching
thresholdVar = 0.41

# TODO: remove unnec variables here- 
thresholdCircle = 0.3 #matchTemplate returns 0 to 1
# thresholdCircle = 0.4 #matchTemplate returns 0 to 1
markerScaleRange=(35,100)
markerScaleSteps = 10 
templ_scale_fac = 17

# Presentation variables

uniform_height = int(1231 / 1.5)
uniform_width = int(1000 / 1.5)
# Original dims are about (3527, 2494)

## Any input images should be resized to this--
uniform_width_hd = int(uniform_width*1.5)
uniform_height_hd = int(uniform_height*1.5)

TEXT_SIZE=0.95
CLR_BLACK = (50,150,150)
CLR_WHITE = (250,250,250)
CLR_GRAY = (120,120,120)
# CLR_DARK_GRAY = (190,190,190)
CLR_DARK_GRAY = (90,90,90)

MIN_PAGE_AREA = 80000

OMR_INPUT_DIR ='inputs/OMR_Files/'
saveMarkedDir='outputs/CheckedOMRs/' 
resultDir='outputs/Results/'
manualDir='outputs/Manual/'
errorsDir=manualDir+'ErrorFiles/'
badRollsDir=manualDir+'BadRollNosFiles/'
multiMarkedDir=manualDir+'MultiMarkedFiles/'


"""
Variables
"""
filesMoved=0
filesNotMoved=0

# for positioning image windows
windowX,windowY = 0,0 


# TODO: move to template or similar json
Answers={
	'J':{
		'q1': ['C'],'q2':['A'],'q3':['A'],'q4': ['B'],'q5': ['C'],'q6': ['13'],'q7': ['98'],
		'q8': ['24'],    'q9': ['62'],    'q10': ['13'],'q11': ['C'],'q12': ['BONUS'],'q13': ['B'],
	'q14': ['B'],'q15': ['A'],'q16': ['C'],'q17': ['A'],'q18': ['D','GOD'],'q19': ['B'],'q20': ['B'],'q21': ['B'],'q22': ['D','GOD']},
	'H':{
		'q1': ['D'],'q2':['A'],'q3':['C'],'q4': ['D'],'q5': ['A'],'q6': ['13'],'q7': ['0'],
		'q8': ['2','02'],    'q9': ['0'],'q10': ['C'],'q11': ['A'],'q12': ['BONUS'],'q13': ['B'],
	'q14': ['B','GOD'],'q15': ['A','C'],'q16': ['A','B'],'q17': ['B'],'q18': ['A','D'],'q19': ['30'],'q20': ['31'],'q21' : ['21'],'q22' : ['4','04','GOD']},
	'JK':{
		'q1': ['C'],'q2':['A'],'q3':['A'],'q4': ['B'],'q5': ['C'],'q6': ['13'],'q7': ['98'],
		'q8': ['24'],    'q9': ['62'],    'q10': ['13'],'q11': ['C'],'q12': ['BONUS'],'q13': ['B'],
	'q14': ['B'],'q15': ['A'],'q16': ['C'],'q17': ['A'],'q18': ['D','GOD'],'q19': ['B'],'q20': ['B'],'q21': ['B'],'q22': ['D','GOD']},
	'HK':{
		'q1': ['D'],'q2':['A'],'q3':['C'],'q4': ['D'],'q5': ['A'],'q6': ['13'],'q7': ['0'],
		'q8': ['2','02'],    'q9': ['0'],'q10': ['C'],'q11': ['A'],'q12': ['BONUS'],'q13': ['B'],
	'q14': ['B','GOD'],'q15': ['A','C'],'q16': ['A','B'],'q17': ['B'],'q18': ['A','D'],'q19': ['30'],'q20': ['31'],'q21' : ['21'],'q22' : ['4','04','GOD']},
	}

# Fibo is across the sections - Q4,5,6,7,13,
Sections = {
	'J':{
		'Boom1':{'ques':[1,2,3,4,5],'+seq':[3,3,3,3,3],'-seq':[1,1,1,1,1]},
		'Proxy1':{'ques':[6,7,8,9,10],'marks':[3,1,-1]},
		'Fibo1':{'ques':[11,12,13,14],'+seq':[2,3,5,8],'-seq':[0,1,1,2]},
		'Power1':{'ques':[15,16,17,18],'+seq':[1,2,4,8],'-seq':[0,0,0,0]},
		'Fibo2':{'ques':[19,20,21,22],'+seq':[2,3,5,8],'-seq':[0,1,1,2]},
	},
	'H':{
		'Fibo1':{'ques':[1,2,3,4,5],'+seq':[2,3,5,8,13],'-seq':[0,1,1,2,3]},
		'Proxy1':{'ques':[6,7,8,9],'marks':[3,1,-1]},
		'Power1':{'ques':[10,11,12,13,14],'+seq':[1,2,4,8],'-seq':[0,0,0,0]},
		'allNone1':{'ques':[15,16,17,18],'marks':12},
		'Proxy1':{'ques':[19,20,21,22],'marks':[3,1,-1]}
	},
}
1 3 9 27
1 => 1 
3 => 3 + 1 => 4
7 => 7 + 1 + 5 => 13

