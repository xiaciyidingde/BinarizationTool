# cython: language_level=3
# cython: boundscheck=False
# cython: wraparound=False
# cython: cdivision=True

import numpy as np
cimport numpy as cnp
cimport cython

@cython.boundscheck(False)
@cython.wraparound(False)
@cython.cdivision(True)
def floyd_steinberg(cnp.ndarray[cnp.float64_t, ndim=2] img, double strength):
    """
    Floyd-Steinberg 抖动算法（Cython 加速）
    
    Args:
        img: 灰度图像 (H, W)，float64 类型
        strength: 抖动强度 (0.0-1.0)
    
    Returns:
        处理后的图像
    """
    cdef int h = img.shape[0]
    cdef int w = img.shape[1]
    cdef int x, y
    cdef double old_pixel, new_pixel, error
    cdef double[:, :] img_view = img
    
    # 预计算误差权重
    cdef double w_7_16 = 0.4375 * strength  # 7/16
    cdef double w_3_16 = 0.1875 * strength  # 3/16
    cdef double w_5_16 = 0.3125 * strength  # 5/16
    cdef double w_1_16 = 0.0625 * strength  # 1/16
    
    with nogil:
        for y in range(h):
            for x in range(w):
                old_pixel = img_view[y, x]
                new_pixel = 255.0 if old_pixel > 127.0 else 0.0
                img_view[y, x] = new_pixel
                
                error = old_pixel - new_pixel
                
                # 扩散误差到相邻像素（使用预计算的权重）
                if x + 1 < w:
                    img_view[y, x + 1] = img_view[y, x + 1] + error * w_7_16
                if y + 1 < h:
                    if x > 0:
                        img_view[y + 1, x - 1] = img_view[y + 1, x - 1] + error * w_3_16
                    img_view[y + 1, x] = img_view[y + 1, x] + error * w_5_16
                    if x + 1 < w:
                        img_view[y + 1, x + 1] = img_view[y + 1, x + 1] + error * w_1_16
    
    return img

@cython.boundscheck(False)
@cython.wraparound(False)
@cython.cdivision(True)
def atkinson(cnp.ndarray[cnp.float64_t, ndim=2] img, double strength):
    """
    Atkinson 抖动算法（Cython 加速）
    
    Args:
        img: 灰度图像 (H, W)，float64 类型
        strength: 抖动强度 (0.0-1.0)
    
    Returns:
        处理后的图像
    """
    cdef int h = img.shape[0]
    cdef int w = img.shape[1]
    cdef int x, y
    cdef double old_pixel, new_pixel, error
    cdef double[:, :] img_view = img
    cdef double error_weight = strength * 0.125  # 1/8
    
    with nogil:
        for y in range(h):
            for x in range(w):
                old_pixel = img_view[y, x]
                new_pixel = 255.0 if old_pixel > 127.0 else 0.0
                img_view[y, x] = new_pixel
                
                error = (old_pixel - new_pixel) * error_weight
                
                # 扩散误差到相邻像素（6个方向）
                if x + 1 < w:
                    img_view[y, x + 1] = img_view[y, x + 1] + error
                if x + 2 < w:
                    img_view[y, x + 2] = img_view[y, x + 2] + error
                if y + 1 < h:
                    if x > 0:
                        img_view[y + 1, x - 1] = img_view[y + 1, x - 1] + error
                    img_view[y + 1, x] = img_view[y + 1, x] + error
                    if x + 1 < w:
                        img_view[y + 1, x + 1] = img_view[y + 1, x + 1] + error
                if y + 2 < h:
                    img_view[y + 2, x] = img_view[y + 2, x] + error
    
    return img

@cython.boundscheck(False)
@cython.wraparound(False)
@cython.cdivision(True)
def ordered_dithering(cnp.ndarray[cnp.uint8_t, ndim=2] img, cnp.ndarray[cnp.float64_t, ndim=2] threshold_map, int matrix_size):
    """
    Ordered Dithering (有序抖动) - Cython 加速
    
    Args:
        img: 灰度图像 (H, W)，uint8 类型
        threshold_map: Bayer 阈值矩阵
        matrix_size: 矩阵大小
    
    Returns:
        处理后的图像
    """
    cdef int h = img.shape[0]
    cdef int w = img.shape[1]
    cdef int x, y
    cdef double threshold
    cdef unsigned char[:, :] img_view = img
    cdef double[:, :] threshold_view = threshold_map
    cdef cnp.ndarray[cnp.uint8_t, ndim=2] result = np.zeros((h, w), dtype=np.uint8)
    cdef unsigned char[:, :] result_view = result
    
    with nogil:
        for y in range(h):
            for x in range(w):
                threshold = threshold_view[y % matrix_size, x % matrix_size]
                if img_view[y, x] > threshold:
                    result_view[y, x] = 255
                else:
                    result_view[y, x] = 0
    
    return result
