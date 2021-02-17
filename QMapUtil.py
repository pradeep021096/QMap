# ==============================================================================================================
# MIT License
# Copyright (c) 2020 Pradeep Kumar

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
# ==============================================================================================================


import csv
from PIL import Image, ImageOps
import numpy as np
import cv2
from simplekml import Kml

class QMapUtil:

    '''
        CONST_TOTAL: Default Geo Bounds for Qlik Map Object
        CONST_ORIGION: Default (0,0) Geo Origin
        CONST_TILE_SIZE: Tile size | 256px Grid
        CONST_BG_COLOR: Default background color | Used in _simplify
    '''

    CONST_TOTAL = (40075016, -40075016)
    CONST_ORIGIN = (-20037508, 20037508)
    CONST_TILE_SIZE = 256
    CONST_BG_COLOR = (255, 255, 255)

    '''
        get PIL Image object
        Args:
            path: image path
        Return: 
            PIL Image
    '''
    @staticmethod
    def getImage(path):
        return Image.open(path)

    '''
        get GreyScale Image
        Args:
            img: PIL Image object
        Return
            GreyScale PIL Image
    '''
    @staticmethod
    def getGreyScaleImage(img):
        return ImageOps.grayscale(img)

    '''
        Store PIL Image
        Args: 
            img: PIL Image Object
            save_as: String - Abs path with image name | Default = current Directory/index.png
        Return:
            status
    '''
    @staticmethod
    def storeImage(img, save_as='./index.png'):
        img.save(save_as)
        return True

    '''
		Simplify Image by fitting image into smallest size x size container image
		Args:
			img: PIL image object
		Return: 
			PIL image object
	'''
    @staticmethod
    def _simplify(img):

        width, height = img.size
        best_fit = QMapUtil.CONST_TILE_SIZE

        while(best_fit <= width or best_fit <= height):
            best_fit *= 2

        final_img = Image.new(mode="RGB", size=(
            best_fit, best_fit), color=QMapUtil.CONST_BG_COLOR)

        offset = ((best_fit-width)//2, (best_fit-height)//2)
        final_img.paste(img, offset)

        return final_img

    '''
		Generate images for TMS
		Args:
			img: PIL image object
			output_folder: output folder path | Default = Current Directory
			zoom_limit: level of required Map zoom i.e. 1x,2x,... | Default 3x
		Return: status
	'''
    @staticmethod
    def generateMapTile(img, output_folder='./', zoom_limit=3):

        img = QMapUtil._simplify(img)

        for zoom in range(zoom_limit+1):

            gridCount = 2**zoom
            gridSize = gridCount * QMapUtil.CONST_TILE_SIZE

            imgTemp = img.resize((gridSize, gridSize))
            QMapUtil._tmsStore(imgTemp, gridCount, zoom, output_folder)

        return True

    '''
		Store images for TMS
		Args:
			img: Simplified PIL Image
			gridCount: No. of grids as per zoom level
			zoom: current zoom level
			output_folder: folder to store 
			tile_size:
		Return: status
	'''
    @staticmethod
    def _tmsStore(img, gridCount, zoom, output_folder):

        for x in range(gridCount):
            for y in range(gridCount):

                cropSize = (QMapUtil.CONST_TILE_SIZE*x,  QMapUtil.CONST_TILE_SIZE*y,
                            QMapUtil.CONST_TILE_SIZE*x + QMapUtil.CONST_TILE_SIZE,  QMapUtil.CONST_TILE_SIZE*y + QMapUtil.CONST_TILE_SIZE)
                currImg = img.crop(cropSize)
                title = 'tile'+'_z'+str(zoom)+'_x'+str(x)+'_y'+str(y)+'.png'
                QMapUtil.storeImage(currImg, output_folder+title)

        return True

    '''
        Generate Geo-Coordinate for given pixel value in image
        Args:
            x: x pixel coordinate
            y: y pixel coordinate
		Return:
            latitude: Geo Lat. Data
            logitude: Geo Long. Data
	'''
    @staticmethod
    def _geoCoordinate(x, y, img):

        width, height = img.size
        logitude = round(
            x * QMapUtil.CONST_TOTAL[0] / width + QMapUtil.CONST_ORIGIN[0])
        latitude = round(
            y * QMapUtil.CONST_TOTAL[1] / height + QMapUtil.CONST_ORIGIN[1])

        return latitude, logitude

    '''
        Detect Center points for each blob in Mask image
        Args:
            mask: Array representation of mask Image
		Return: 
            List[] of Connected component centroid
	'''
    @staticmethod
    def _centroids(mask):
        output = cv2.connectedComponentsWithStats(mask, 8, cv2.CV_32S)
        centroids = output[3][1:]
        return centroids

    '''
        Create Mask for Red Color
        Args:
            img: PIL image
            save_mask: to save generated mask | For Debugging
            kernel_size: Kernel size for Image Blurring | odd int
		Return 
            Mask: Array representation of mask Image
	'''
    @staticmethod
    def _redMask(img, save_mask=False, kernel_size = 3):

        img = np.array(img)
        blur = cv2.blur(img, (kernel_size,kernel_size))
        hsv = cv2.cvtColor(blur, cv2.COLOR_BGR2HSV)

        red_lower = np.array([120, 210, 230])
        red_upper = np.array([180, 255, 255])

        mask = cv2.inRange(hsv, red_lower, red_upper)

        if save_mask:
            cv2.imwrite("GeneratedMask.png", mask)

        return mask

    '''
        Save corresponting Geo Data for each centroid into CSV
        Args:
            centroid: List[] of Connected component centroid
            output_folder: Target storage path
            img: PIL Image
		Return: 
            csv file path
	'''
    @staticmethod
    def _storeCSV(centroids, output_folder, img):

        with open(output_folder+'output.csv', mode='w', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(('Lat', 'Long', 'x', 'y'))

            for point in centroids:
                x, y = (int(point[0]), int(point[1]))
                latitude, logitude = QMapUtil._geoCoordinate(x, y, img)
                writer.writerow((latitude, logitude, x, y))

        return output_folder+'output.csv'

    '''
        Generate Geo Data from Marked greyscale image
        Args:
            img: PIL Image | greyscale version of original image with red blobs / dots
            output_folder: Target folder | Default is current directory
            save_mask: Save Generated Mask | Always saves in current working Directory | Use if Debugging
            kernel_size: Kernel size for Image Blurring | odd int
		Return: 
            file path
	'''
    @staticmethod
    def extractGeoData(img, output_folder='./', save_mask=False, kernel_size = 3):

        img = QMapUtil._simplify(img.convert('RGB'))
        mask = QMapUtil._redMask(img, save_mask,kernel_size)
        centroids = QMapUtil._centroids(mask)

        output_file_path = QMapUtil._storeCSV(centroids, output_folder, img)

        return output_file_path
    '''
        Find contours from simplified poly image
        Args:
            img: PIL Image | simplified Red Polygon image
        Return:
            List of List [[data]..] : Polygon list with [y,x]
    '''
    @staticmethod
    def _findPoly(img):
        
        contours, hierarchy = cv2.findContours(img, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
        result = []
        for poly in contours:
            poly_list = np.vstack(poly).squeeze().tolist()
            poly_list.append(poly_list[0])
            result.append(poly_list)
        return result

    '''
        Generate Simple KML File
        Args:
            img : PIL Image | simplified Red Polygon image
            output_folder: Target folder | Default is current directory
            save_mask: to save generated mask | For Debugging
            kernel_size: Kernel size for Image Blurring | odd int
        Return:
            string : KML File path
    '''
    @staticmethod
    def generateKML(img, output_folder='./', save_mask=False, kernel_size = 1):
        
        img = QMapUtil._simplify(img.convert('RGB'))
        mask = QMapUtil._redMask(img, save_mask, kernel_size)

        polygons = QMapUtil._findPoly(mask)
        file_kml = Kml()
        i = 0 
        
        for poly in polygons:
            i+=1
            result = [] 
            for data in poly:
                x,y = QMapUtil._geoCoordinate(data[0],data[1],img)
                result.append([y,x])

            file_kml.newpolygon(name = '_'+str(i), outerboundaryis = result )

        file_kml.save( output_folder+'output.kml')
        
        return output_folder+'output.kml'


'''
    Sample Usage Calls
'''


def main():

    img_Path = './Floor_Plan.jpg'
    img = QMapUtil.getImage(img_Path)
    QMapUtil.generateMapTile(img, output_folder='./Output/', zoom_limit=4)

    marked_img_Path = './Floor_Plan_marked.jpg'
    marked_img = QMapUtil.getImage(marked_img_Path)
    QMapUtil.extractGeoData(marked_img, save_mask=True)

    poly_img_Path = './Body_Poly.jpg'
    img = QMapUtil.getImage(poly_img_Path)
    QMapUtil.generateKML(img, output_folder='./Output/', save_mask=True)


if __name__ == '__main__':
    main()
