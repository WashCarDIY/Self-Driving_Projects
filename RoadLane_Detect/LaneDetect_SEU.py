#! /usr/bin/env python
# -*- coding: utf-8 -*-
# __author__ = "XiaolongWang"
# Date: 2019/3/22


import os
import cv2
import numpy as np


# --------------------------- lane feature extract ---------------------------------#
#-----------------------------------------------------------------------------------#
def abs_sobel_thresh(img,orient='x',thresh_min=0,thresh_max=255):
    gray = cv2.cvtColor(img,cv2.COLOR_RGB2GRAY)
    if orient == 'x':
        abs_sobel = np.absolute(cv2.Sobel(gray,cv2.CV_64F,1,0))
    if orient =='y':
        abs_sobel = np.absolute(cv2.Sobel(gray, cv2.CV_64F, 0, 1))
    scaled_sobel = np.uint8(255*abs_sobel/np.max(abs_sobel))
    binary_output = np.zeros_like(scaled_sobel)
    binary_output[(scaled_sobel >= thresh_min) & (scaled_sobel <= thresh_max)] = 1
    return binary_output

def dir_threshold(img, sobel_kernel=3, thresh=(0, np.pi/2)):
    gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
    # Calculate the x and y gradients
    sobelx = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=sobel_kernel)
    sobely = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=sobel_kernel)
    # Take the absolute value of the gradient direction,
    # apply a threshold, and create a binary image result
    absgraddir = np.arctan2(np.absolute(sobely), np.absolute(sobelx))
    binary_output = np.zeros_like(absgraddir)
    binary_output[(absgraddir >= thresh[0]) & (absgraddir <= thresh[1])] = 1

    # Return the binary image
    return binary_output

def mag_threshold(img, sobel_kernel=3, mag_thresh=(0, 255)):
    gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
    # Take both Sobel x and y gradients
    sobelx = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=sobel_kernel)
    sobely = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=sobel_kernel)
    # Calculate the gradient magnitude
    gradmag = np.sqrt(sobelx ** 2 + sobely ** 2)
    # Rescale to 8 bit
    scale_factor = np.max(gradmag) / 255
    gradmag = (gradmag / scale_factor).astype(np.uint8)
    # Create a binary image of ones where threshold is met, zeros otherwise
    binary_output = np.zeros_like(gradmag)
    binary_output[(gradmag >= mag_thresh[0]) & (gradmag <= mag_thresh[1])] = 1
    return binary_output

def hls_select(img,channel='s',thresh=(0, 255)):
    hls = cv2.cvtColor(img, cv2.COLOR_RGB2HLS)
    if channel == 'h':
        channel = hls[:, :, 0]
    elif channel == 'l':
        channel = hls[:, :, 1]
    else:
        channel = hls[:, :, 2]
    binary_output = np.zeros_like(channel)
    binary_output[(channel > thresh[0]) & (channel <= thresh[1])] = 1
    return binary_output

def luv_select(img, thresh=(0, 255)):
    luv = cv2.cvtColor(img, cv2.COLOR_RGB2LUV)
    l_channel = luv[:, :, 0]
    binary_output = np.zeros_like(l_channel)
    binary_output[(l_channel > thresh[0]) & (l_channel <= thresh[1])] = 1
    return binary_output

def lab_select(img, thresh=(0, 255)):
    lab = cv2.cvtColor(img, cv2.COLOR_RGB2Lab)
    b_channel = lab[:,:,2]
    binary_output = np.zeros_like(b_channel)
    binary_output[(b_channel > thresh[0]) & (b_channel <= thresh[1])] = 1
    return binary_output

def thresholding(img):
#    x_thresh = utils.abs_sobel_thresh(img, orient='x', thresh_min=55, thresh_max=100)
#    mag_thresh = utils.mag_thresh(img, sobel_kernel=3, mag_thresh=(70, 255))
#    dir_thresh = utils.dir_threshold(img, sobel_kernel=3, thresh=(0.7, 1.3))
#    s_thresh = utils.hls_select(img,channel='s',thresh=(160, 255))
#    s_thresh_2 = utils.hls_select(img,channel='s',thresh=(200, 240))
#
#    white_mask = utils.select_white(img)
#    yellow_mask = utils.select_yellow(img)

    x_thresh = abs_sobel_thresh(img, orient='x', thresh_min=25 ,thresh_max=255)
    mag_thresh = mag_threshold(img, sobel_kernel=3, mag_thresh=(40, 250))
    dir_thresh = dir_threshold(img, sobel_kernel=3, thresh=(0.7, 1.7))
    hls_thresh = hls_select(img, thresh=(90, 255))
    hls_thresh_white = hls_select(img,channel='l', thresh=(180, 255))
    hls_thresh_yellow = hls_select(img,channel='h', thresh=(90, 120))
    lab_thresh = lab_select(img, thresh=(155, 200))
    luv_thresh = luv_select(img, thresh=(225, 255))
    #Thresholding combination
    #threshholded = np.zeros_like(x_thresh)
    #threshholded[((x_thresh == 1) & (mag_thresh == 1)) | ((dir_thresh == 1) & (hls_thresh == 1)) | (lab_thresh == 1) | (luv_thresh == 1)] = 1

    threshholded = np.zeros_like(x_thresh)
    threshholded[((hls_thresh_white == 1) | (hls_thresh_yellow == 1)) & ((dir_thresh == 1)| (x_thresh == 1) | (mag_thresh == 1)) ]=1

    return threshholded

#----------------------------Get M and Minv ----------------------------------------#
#-----------------------------------------------------------------------------------#
def get_M_Minv():
    src = np.float32([[(125, 707), (545, 345), (705, 343), (1177, 707)]])
    dst = np.float32([[(125, 707), (125, 100), (1177, 100), (1177, 707)]])
    M = cv2.getPerspectiveTransform(src, dst)
    Minv = cv2.getPerspectiveTransform(dst,src)
    return M,Minv


# --------------------------- Define a lane class---------------------------------#
#-----------------------------------------------------------------------------------#
# Define a class to receive the characteristics of each line detection
class Line():
    def __init__(self):
        # was the line detected in the last iteration?
        self.detected = False
        # x values of the last n fits of the line
        self.recent_fitted = [np.array([False])]
        # average x values of the fitted line over the last n iterations
        self.bestx = None
        # polynomial coefficients averaged over the last n iterations
        self.best_fit = None
        # polynomial coefficients for the most recent fit
        self.current_fit = [np.array([False])]
        # radius of curvature of the line in some units
        self.radius_of_curvature = None
        # distance in meters of vehicle center from the line
        self.line_base_pos = None
        # difference in fit coefficients between last and new fits
        self.diffs = np.array([0, 0, 0], dtype='float')
        # x values for detected line pixels
        self.allx = None
        # y values for detected line pixels
        self.ally = None

    def check_detected(self):
        if (self.diffs[0] < 0.01 and self.diffs[1] < 10.0 and self.diffs[2] < 1000.) and len(self.recent_fitted) > 0:
            return True
        else:
            return False

    def update(self, fit):
        if fit is not None:
            if self.best_fit is not None:
                self.diffs = abs(fit - self.best_fit)
                if self.check_detected():
                    self.detected = True
                    if len(self.recent_fitted) > 10:
                        self.recent_fitted = self.recent_fitted[1:]
                        self.recent_fitted.append(fit)
                    else:
                        self.recent_fitted.append(fit)
                    self.best_fit = np.average(self.recent_fitted, axis=0)
                    self.current_fit = fit
                else:
                    self.detected = False
            else:
                self.best_fit = fit
                self.current_fit = fit
                self.detected = True
                self.recent_fitted.append(fit)

#------------------------find line-------------------------------------------#
#----------------------------------------------------------------------------#

def find_line(binary_warped):
    # Take a histogram of the bottom half of the image
    histogram = np.sum(binary_warped[binary_warped.shape[0] // 2:, :], axis=0)
    # Find the peak of the left and right halves of the histogram
    # These will be the starting point for the left and right lines
    midpoint = np.int(histogram.shape[0] / 2)
    leftx_base = np.argmax(histogram[:midpoint])
    rightx_base = np.argmax(histogram[midpoint:]) + midpoint

    # Choose the number of sliding windows
    nwindows = 9
    # Set height of windows
    window_height = np.int(binary_warped.shape[0] / nwindows)
    # Identify the x and y positions of all nonzero pixels in the image
    nonzero = binary_warped.nonzero()
    nonzeroy = np.array(nonzero[0])
    nonzerox = np.array(nonzero[1])
    # Current positions to be updated for each window
    leftx_current = leftx_base
    rightx_current = rightx_base
    # Set the width of the windows +/- margin
    margin = 100
    # Set minimum number of pixels found to recenter window
    minpix = 50
    # Create empty lists to receive left and right lane pixel indices
    left_lane_inds = []
    right_lane_inds = []

    # Step through the windows one by one
    for window in range(nwindows):
        # Identify window boundaries in x and y (and right and left)
        win_y_low = binary_warped.shape[0] - (window + 1) * window_height
        win_y_high = binary_warped.shape[0] - window * window_height
        win_xleft_low = leftx_current - margin
        win_xleft_high = leftx_current + margin
        win_xright_low = rightx_current - margin
        win_xright_high = rightx_current + margin
        # Identify the nonzero pixels in x and y within the window
        good_left_inds = ((nonzeroy >= win_y_low) & (nonzeroy < win_y_high) &
                          (nonzerox >= win_xleft_low) & (nonzerox < win_xleft_high)).nonzero()[0]
        good_right_inds = ((nonzeroy >= win_y_low) & (nonzeroy < win_y_high) &
                           (nonzerox >= win_xright_low) & (nonzerox < win_xright_high)).nonzero()[0]
        # Append these indices to the lists
        left_lane_inds.append(good_left_inds)
        right_lane_inds.append(good_right_inds)
        # If you found > minpix pixels, recenter next window on their mean position
        if len(good_left_inds) > minpix:
            leftx_current = np.int(np.mean(nonzerox[good_left_inds]))
        if len(good_right_inds) > minpix:
            rightx_current = np.int(np.mean(nonzerox[good_right_inds]))

    # Concatenate the arrays of indices
    left_lane_inds = np.concatenate(left_lane_inds)
    right_lane_inds = np.concatenate(right_lane_inds)

    # Extract left and right line pixel positions
    leftx = nonzerox[left_lane_inds]
    lefty = nonzeroy[left_lane_inds]
    rightx = nonzerox[right_lane_inds]
    righty = nonzeroy[right_lane_inds]

    # Fit a second order polynomial to each
    left_fit = np.polyfit(lefty, leftx, 2)
    right_fit = np.polyfit(righty, rightx, 2)

    return left_fit, right_fit, left_lane_inds, right_lane_inds


def find_line_by_previous(binary_warped, left_fit, right_fit):
    nonzero = binary_warped.nonzero()
    nonzeroy = np.array(nonzero[0])
    nonzerox = np.array(nonzero[1])
    margin = 100
    left_lane_inds = ((nonzerox > (left_fit[0] * (nonzeroy ** 2) + left_fit[1] * nonzeroy +
                                   left_fit[2] - margin)) & (nonzerox < (left_fit[0] * (nonzeroy ** 2) +
                                                                         left_fit[1] * nonzeroy + left_fit[
                                                                             2] + margin)))

    right_lane_inds = ((nonzerox > (right_fit[0] * (nonzeroy ** 2) + right_fit[1] * nonzeroy +
                                    right_fit[2] - margin)) & (nonzerox < (right_fit[0] * (nonzeroy ** 2) +
                                                                           right_fit[1] * nonzeroy + right_fit[
                                                                               2] + margin)))

    # Again, extract left and right line pixel positions
    leftx = nonzerox[left_lane_inds]
    lefty = nonzeroy[left_lane_inds]
    rightx = nonzerox[right_lane_inds]
    righty = nonzeroy[right_lane_inds]
    # Fit a second order polynomial to each
    left_fit = np.polyfit(lefty, leftx, 2)
    right_fit = np.polyfit(righty, rightx, 2)
    return left_fit, right_fit, left_lane_inds, right_lane_inds


#-------------------------------calculate the result-----------------------------------#
#------------------------------------------------------------------------------------#
def calculate_curv_and_pos(binary_warped, left_fit, right_fit):
    # Define y-value where we want radius of curvature

    ploty = np.linspace(0, binary_warped.shape[0] - 1, binary_warped.shape[0])
    leftx = left_fit[0] * ploty ** 2 + left_fit[1] * ploty + left_fit[2]
    rightx = right_fit[0] * ploty ** 2 + right_fit[1] * ploty + right_fit[2]
    # Define conversions in x and y from pixels space to meters
    ym_per_pix = 30.0 / 720  # meters per pixel in y dimension
    print(ym_per_pix)
    xm_per_pix = 3.7 / 700  # meters per pixel in x dimension
    y_eval = np.max(ploty)

    # Fit new polynomials to x,y in world space

    left_fit_cr = np.polyfit(ploty * ym_per_pix, leftx * xm_per_pix, 2)

    right_fit_cr = np.polyfit(ploty * ym_per_pix, rightx * xm_per_pix, 2)
    # Calculate the new radii of curvature
    left_curverad = ((1 + (2 * left_fit_cr[0] * y_eval * ym_per_pix + left_fit_cr[1]) ** 2) ** 1.5) / np.absolute(
        2 * left_fit_cr[0])
    right_curverad = ((1 + (2 * right_fit_cr[0] * y_eval * ym_per_pix + right_fit_cr[1]) ** 2) ** 1.5) / np.absolute(
        2 * right_fit_cr[0])

    curvature = ((left_curverad + right_curverad) / 2)
    # print(curvature)
    lane_width = np.absolute(leftx[719] - rightx[719])
    lane_xm_per_pix = 3.7 / lane_width
    veh_pos = (((leftx[719] + rightx[719]) * lane_xm_per_pix) / 2.)
    cen_pos = ((binary_warped.shape[1] * lane_xm_per_pix) / 2.)
    distance_from_center = cen_pos - veh_pos
    return curvature, distance_from_center


#-------------------------------display the result-----------------------------------#
#------------------------------------------------------------------------------------#
def draw_area(undist, binary_warped, Minv, left_fit, right_fit):
    # Generate x and y values for plotting
    ploty = np.linspace(0, binary_warped.shape[0] - 1, binary_warped.shape[0])
    left_fitx = left_fit[0] * ploty ** 2 + left_fit[1] * ploty + left_fit[2]
    right_fitx = right_fit[0] * ploty ** 2 + right_fit[1] * ploty + right_fit[2]
    # Create an image to draw the lines on
    warp_zero = np.zeros_like(binary_warped).astype(np.uint8)
    color_warp = np.dstack((warp_zero, warp_zero, warp_zero))

    # Recast the x and y points into usable format for cv2.fillPoly()
    pts_left = np.array([np.transpose(np.vstack([left_fitx, ploty]))])
    pts_right = np.array([np.flipud(np.transpose(np.vstack([right_fitx, ploty])))])
    pts = np.hstack((pts_left, pts_right))

    # Draw the lane onto the warped blank image
    cv2.fillPoly(color_warp, np.int_([pts]), (0, 255, 0))

    # Warp the blank back to original image space using inverse perspective matrix (Minv)
    newwarp = cv2.warpPerspective(color_warp, Minv, (undist.shape[1], undist.shape[0]))
    # Combine the result with the original image
    result = cv2.addWeighted(undist, 1, newwarp, 0.3, 0)
    return result


def draw_values(img, curvature, distance_from_center):
    font = cv2.FONT_HERSHEY_SIMPLEX
    radius_text = "Radius of Curvature: %sm" % (round(curvature))

    if distance_from_center > 0:
        pos_flag = 'right'
    else:
        pos_flag = 'left'

    cv2.putText(img, radius_text, (100, 100), font, 1, (255, 255, 255), 2)
    center_text = "Vehicle is %.3fm %s of center" % (abs(distance_from_center), pos_flag)
    cv2.putText(img, center_text, (100, 150), font, 1, (255, 255, 255), 2)
    return img

#-----------------------------------------main process----------------------------------#
#---------------------------------------------------------------------------------------#
def processing(img, M, Minv, left_line, right_line):
    thresholded = thresholding(img)
    cv2.imshow("thresholded",thresholded)
    thresholded_wraped = cv2.warpPerspective(thresholded, M, img.shape[1::-1], flags=cv2.INTER_LINEAR)
    if left_line.detected and right_line.detected:
        left_fit, right_fit, left_lane_inds, right_lane_inds = find_line_by_previous(thresholded_wraped,
                                                                                              left_line.current_fit,
                                                                                              right_line.current_fit)
    else:
        left_fit, right_fit, left_lane_inds, right_lane_inds = find_line(thresholded_wraped)
    left_line.update(left_fit)
    right_line.update(right_fit)
    area_img = draw_area(img, thresholded_wraped, Minv, left_fit, right_fit)
    curvature, pos_from_center = calculate_curv_and_pos(thresholded_wraped, left_fit, right_fit)
    result = draw_values(area_img, curvature, pos_from_center)
    return result


def main():
    # #----- test image---------#
    # img = cv2.imread('white01.jpg')
    # M, Minv = get_M_Minv()
    # thresholded_wraped = cv2.warpPerspective(img, M, img.shape[1::-1], flags=cv2.INTER_LINEAR)
    # left_line = Line()
    # right_line = Line()
    # result_img = processing(img,M,Minv,left_line,right_line)
    # cv2.imshow('Threashold', thresholded_wraped)
    # cv2.imshow('result', result_img)
    # cv2.waitKey(0)
    # cv2.destroyAllWindows()

    #--------test video--------#
    cap = cv2.VideoCapture('test1.MOV')
    while(cap.isOpened()):
        ret,frame = cap.read()
        x,y = frame.shape[0:2]
        frame = cv2.resize(frame,(1080,720))
        M, Minv = get_M_Minv()
        thresholded_wraped = cv2.warpPerspective(frame, M, frame.shape[1::-1], flags=cv2.INTER_LINEAR)
        cv2.imshow('image',frame)
        cv2.imshow('Threashold', thresholded_wraped)

        M, Minv = get_M_Minv()

        left_line = Line()
        right_line = Line()
        result_video = processing(frame, M, Minv, left_line, right_line)
        cv2.imshow('result', result_video)
        k = cv2.waitKey(20)
        if (k & 0xff == ord('q')):
            break
    cap.release()
    cv2.destroyAllWindows()

if __name__ == '__main__':
    main()