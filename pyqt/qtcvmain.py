import sys
import cv2
import numpy as np
from PyQt4 import QtGui, QtCore, Qt
from ui import Ui_MainWindow
import numpy as np
import dlib
import imutils
from math import sqrt

class Flags():
	isSet_fwd = False
	isSet_back = False
	isSet_left = False
	isSet_right = False
	isSet_stop = False

	def set_fwd(self):
		self.isSet_fwd = True
		self.isSet_back = False
		self.isSet_stop = False
		self.isSet_left = False
		self.isSet_right = False

	def set_back(self):
		self.isSet_back = True
		self.isSet_fwd = False
		self.isSet_stop = False
		self.isSet_left = False
		self.isSet_right = False

	def set_left(self):
		self.isSet_left = True
		self.isSet_right = False
		self.isSet_fwd = False
		self.isSet_back = False
		self.isSet_stop = False

	def set_right(self):
		self.isSet_right = True
		self.isSet_left = False
		self.isSet_fwd = False
		self.isSet_back = False
		self.isSet_stop = False

	def set_stop(self):
		self.isSet_stop = True
		self.isSet_fwd = False
		self.isSet_back = False
		self.isSet_left = False
		self.isSet_right = False

class Dlib():
	def __init__(self):
		self.PREDICTOR_PATH = "/home/wa/Documents/OpenCV2/shape_predictor_68_face_landmarks.dat"
		MOUTH_POINTS = list(range(48, 61))
		self.OVERLAY_POINTS = [MOUTH_POINTS]

		self.detector = dlib.get_frontal_face_detector()
		self.predictor = dlib.shape_predictor(self.PREDICTOR_PATH)
	
	def get_landmarks(self,img):
		rects = self.detector(img, 0)
		
		if len(rects) > 1:
			print 'TooManyFaces'
		if len(rects) == 0:
			raise ValueError('Error: NoFaces!!')

		return np.matrix([[p.x, p.y] for p in self.predictor(img, rects[0]).parts()])


	def get_face_mask(self,img,landmarks):
		for group in self.OVERLAY_POINTS:
			hull = cv2.convexHull(landmarks[group])
			cv2.fillConvexPoly(img, hull, 0)


class Video():
	def __init__(self,capture):
		self.capture = capture
		self.currentFrame=np.array([])
 		self.dlib_obj = Dlib()
 		self.font = cv2.FONT_HERSHEY_SIMPLEX
	def captureNextFrame(self):
		"""                           
		capture frame and reverse RBG BGR and return opencv image                                      
		"""
		ret, readFrame=self.capture.read()
		
		if not ret :
			print "Error reading Frame!!"
			sys.exit(0)

		readFrame = self.processFrame(readFrame)
		self.currentFrame=cv2.cvtColor(readFrame,cv2.COLOR_BGR2RGB)
 
	def convertFrame(self):
		"""     converts frame to format suitable for QtGui            """
		try:
			height,width=self.currentFrame.shape[:2]
			img=QtGui.QImage(self.currentFrame,
							  width,
							  height,
							  QtGui.QImage.Format_RGB888)
			img=QtGui.QPixmap.fromImage(img)
			#self.previousFrame = self.currentFrame
			return img
		except Exception,e:
			print "convertFrame: ",e
			return None
	
	def processFrame(self,img):
		x1=0		# hand_box = [(x1,y1),(x2,y2)]
		y1=50
		x2=250
		y2=500

		x3=300		# head_box = [(x3,y3),(x4,y4)]
		y3=50
		x4=600
		y4=500

		cv2.rectangle(img,(x1,y1),(x2,y2),(255,255,255),1)
		cv2.rectangle(img,(x3,y3),(x4,y4),(50,50,50),1)

		head_frame = img[y3:y4,x3:x4]
		try:
			img[y3:y4,x3:x4] = self.lipSegment(head_frame)
		except ValueError, e:
			#print 'processFrame: ',e
			flags.set_stop()
			pass		# To suppress No face Error


		hand_frame = img[y1:y2,x1:x2]
			
		try:
			mask,counter,hull,(cx,cy),list_far,list_end = self.count_fingers(hand_frame)
			
			if(cv2.contourArea(hull)>3000) and list_far:
				cv2.drawContours(hand_frame,[hull],0,(0,255,0),1)
				[cv2.circle(hand_frame,far,5,[0,0,0],-1) for far in list_far]
				[cv2.circle(hand_frame,end,5,[150,150,150],-1) for end in list_end]
				cv2.putText(hand_frame,"Fingers = "+str(counter+1),(10,250),self.font, 1,(0,0,255),1,1)

		except ZeroDivisionError, e:
			print "Count_fingers ZeroDivisionError: ",e
		except UnboundLocalError,e:
			print "Count_fingers UnboundLocalError: ",e

		return img

	def lipSegment(self,img):
		img = imutils.resize(img,width=300,height=450)
		img_copy = img.copy()

		landmarks = self.dlib_obj.get_landmarks(img)
		self.dlib_obj.get_face_mask(img_copy, landmarks)
		
		output_img = img-img_copy
		output_img = cv2.cvtColor(output_img,cv2.COLOR_BGR2GRAY)
		
		contours,hierarchy = cv2.findContours(output_img.copy(), cv2.cv.CV_RETR_EXTERNAL, cv2.cv.CV_CHAIN_APPROX_SIMPLE)  #cv2.findContours(image, mode, method
		cv2.drawContours(img, contours, -1, (0,0,255), 1,maxLevel=0)
		
		cnt = contours[0]
		ellipse = cv2.fitEllipse(cnt)
		(x,y),(MA,ma),angle = cv2.fitEllipse(cnt)
		
		
		a = ma/2
		b = MA/2


		eccentricity = sqrt(pow(a,2)-pow(b,2))
		eccentricity = round(eccentricity/a,2)

		cv2.putText(img,'E = '+str(round(eccentricity,3)),(10,350), self.font, 1,(255,0,0),1)
		
		if(eccentricity < 0.9):
			cv2.putText(img,'Cmd = O',(10,300), self.font, 1,(0,0,255),1,16)
			flags.set_back()
		else:
			cv2.putText(img,'Cmd = E',(10,300), self.font, 1,(0,0,255),1,16)
			flags.set_fwd()

		if angle < 80:
			flags.set_left()
		elif angle>100:
			flags.set_right()

		#cv2.putText(img,'Angle = '+str(angle),(10,300),self.font,1,(0,0,255),1,16)
		return img

	def count_fingers(self,img):
		img = cv2.cvtColor(img,cv2.COLOR_BGR2GRAY)

		# Otsu's thresholding after Gaussian filtering
		img = cv2.GaussianBlur(img,(5,5),0)
		ret,mask = cv2.threshold(img,0,255,cv2.THRESH_BINARY_INV+cv2.THRESH_OTSU)
		
		(cnts,_)=cv2.findContours(mask.copy(),cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)

		list_far=[]
		list_end=[]
		if cnts:
			areas = [cv2.contourArea(c) for c in cnts]
			max_index = np.argmax(areas)
			cnt=cnts[max_index]

			M = cv2.moments(cnt)
			cx = int(M['m10']/M['m00'])
			cy = int(M['m01']/M['m00'])
			
			hull1 = cv2.convexHull(cnt)
			
			hull2 = cv2.convexHull(cnt,returnPoints = False)
			
			try:
				defects = cv2.convexityDefects(cnt,hull2)
			except Exception, e:
				defects = None
				print e

			counter = 0
			if defects is not None:
				for i in range(defects.shape[0]):
					s,e,f,d = defects[i,0]
					start = tuple(cnt[s][0])
					end = tuple(cnt[e][0])
					far = tuple(cnt[f][0])
					if d<20000:
						continue
										
					if far[1] >= (cy+40):
						continue
					else:
						pass
					
					list_far.append(far)
					list_end.append(end)
					counter +=1
			
		return mask,counter,hull1,(cx,cy),list_far,list_end			
 
class Gui(QtGui.QMainWindow):
	def __init__(self,parent=None):
		QtGui.QWidget.__init__(self,parent)
		self.ui = Ui_MainWindow()
		self.ui.setupUi(self)
		self.video = Video(cv2.VideoCapture(0))
		self._timer = QtCore.QTimer(self)
		self._timer.timeout.connect(self.play)
		self._timer.start(20)
		self.update()
 
	def play(self):
		try:
			self.video.captureNextFrame()
			self.ui.videoFrame.setPixmap(
				self.video.convertFrame())
			self.ui.videoFrame.setScaledContents(True)
			self.checkFlags()
		except Exception,e:
			print "play(): ",e
	
	def checkFlags(self): 
		if flags.isSet_fwd:
			self.ui.up_arrow.setEnabled(True)
		else:
			self.ui.up_arrow.setEnabled(False)
		
		if flags.isSet_back:
			self.ui.down_arrow.setEnabled(True)
		else:
			self.ui.down_arrow.setEnabled(False)
		
		if flags.isSet_left:
			self.ui.left_arrow.setEnabled(True)
		else:
			self.ui.left_arrow.setEnabled(False)
		
		if flags.isSet_right:
			self.ui.right_arrow.setEnabled(True)
		else:
			self.ui.right_arrow.setEnabled(False)

		if flags.isSet_stop:
			self.ui.stop.setStyleSheet('background-color :rgb(255, 0, 0) ;border-color: rgb(42, 42, 42);')
		else:
			self.ui.stop.setStyleSheet('background-color :rgb(197, 197, 197) ;border-color: rgb(42, 42, 42);')
		

def main():
	app = QtGui.QApplication(sys.argv)
	ex = Gui()
	ex.show()
	sys.exit(app.exec_())
 
if __name__ == '__main__':
	flags = Flags()
	main()