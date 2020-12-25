import csv
import os
from PIL import Image, ImageOps
import numpy as np
import cv2


imgPath = './Floor_Plan.jpg'
pointImgPath = './Floor_Plan_marked.jpg'
outputFolder = './Output/'

zoom_limit = 4
tile_size = 256
bg_color = (255,255,255)

CONST_TOTAL = (40075016, -40075016)
CONST_ORIGIN = (-20037508, 20037508)

def Simplify(img):
	
	width, height = img.size
	best_fit = tile_size
	
	#Best square grid size
	while(best_fit <= width or  best_fit <= height):
		best_fit *= 2
			
	#Create background image
	finalImg = Image.new(mode = "RGB", size = (best_fit,best_fit), color=bg_color)
	
	#offset original image in center
	offset = ((best_fit-width)//2,(best_fit-height)//2)
	finalImg.paste(img,offset)

	return finalImg


def ZoomAndSplit(imgPath,outputFolder):
	
	img = Simplify(Image.open(imgPath))
	width, height = img.size		
	
	# Compute for all zoom levels
	for zoom in range(zoom_limit+1):
		
		gridCount = 2**zoom					# 2^z Horizontal or vertical grid count
		gridSize = gridCount * tile_size	#GridSize in pixels
		imgSize = (gridSize,gridSize)		#image size (width px, height px)

		imgTemp = img.resize(imgSize)
		
		# for all tiles in zoom level
		for x in range(gridCount):
			for y in range(gridCount):
				#compute tiles and store
				cropSize = ( tile_size*x, tile_size*y, 	\
							 tile_size*x + tile_size, tile_size*y + tile_size )
				currImg = imgTemp.crop(cropSize)
				currImg.save(outputFolder+'tile'+'_z'+str(zoom)+'_x'+str(x)+'_y'+str(y)+'.png')
				


def MarkPoints(imgPath):

	img = Simplify(Image.open(imgPath)).convert('RGB')
	width, height = img.size
	
	#Convert PIL image to Array & RGB to BGR for OpenCV
	open_cv_image = np.array(img) 
	#open_cv_image = cv2.cvtColor(open_cv_image, cv2.COLOR_BGR2RGB).copy()
	
	#apply median blur, 5x5 pixels
	blur = cv2.medianBlur(open_cv_image,5)

	#convert to hsv
	hsv = cv2.cvtColor(blur, cv2.COLOR_BGR2HSV)

	#Red color Mask Limits
	red_lower = np.array([120,210,230])
	red_upper = np.array([180,255,255])

	mask = cv2.inRange(hsv, red_lower, red_upper)
	
	#apply median blur, 5x5 pixels
	mask = cv2.medianBlur(mask,5)
  
	#find connected components
	output = cv2.connectedComponentsWithStats(mask, 8, cv2.CV_32S)

	#get centroids
	centroids = output[3][1:]
	
	#for check only
	cv2.imwrite("GeneratedMask.png",mask)
	
	#save LAT, LONG data in csv
	with open('output.csv', mode='w') as file:
		writer = csv.writer(file)
		writer.writerow(('Lat','Long','x','y'))
		
		for point in centroids:
			x,y = (int(point[0]),int(point[1]))
			long = round( x * CONST_TOTAL[0] / width + CONST_ORIGIN[0])
			lat = round( y * CONST_TOTAL[1] / height + CONST_ORIGIN[1])
			writer.writerow((lat,long,x,y))



if __name__ == '__main__':
	
	# ImageOps.grayscale(Image.open(imgPath)).save('./greyscale.png')
	
	ZoomAndSplit(imgPath,outputFolder)

	MarkPoints(pointImgPath)