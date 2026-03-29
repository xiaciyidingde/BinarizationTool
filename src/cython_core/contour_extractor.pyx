# cython: language_level=3
# cython: boundscheck=False
# cython: wraparound=False
# cython: cdivision=True

"""
Cython 加速的轮廓提取模块

提供高性能的选区轮廓提取功能
"""

import numpy as np
cimport numpy as cnp
cimport cython
from cython.parallel import prange
from libc.stdlib cimport malloc, free

# 初始化 numpy
cnp.import_array()


@cython.boundscheck(False)
@cython.wraparound(False)
def downsample_mask(cnp.ndarray[cnp.uint8_t, ndim=2] mask, int scale):
    """
    快速降采样蒙版
    
    Args:
        mask: 输入蒙版 (H, W), uint8
        scale: 降采样倍数
    
    Returns:
        降采样后的蒙版
    """
    cdef int h = mask.shape[0]
    cdef int w = mask.shape[1]
    cdef int new_h = h // scale
    cdef int new_w = w // scale
    cdef int y, x, sy, sx
    cdef cnp.uint8_t value
    
    cdef cnp.ndarray[cnp.uint8_t, ndim=2] result = np.zeros((new_h, new_w), dtype=np.uint8)
    cdef cnp.uint8_t[:, :] mask_view = mask
    cdef cnp.uint8_t[:, :] result_view = result
    
    # 并行降采样
    with nogil:
        for y in prange(new_h, schedule='static'):
            for x in range(new_w):
                # 采样中心点
                sy = y * scale
                sx = x * scale
                if sy < h and sx < w:
                    result_view[y, x] = mask_view[sy, sx]
    
    return result


@cython.boundscheck(False)
@cython.wraparound(False)
def scale_contour_points(cnp.ndarray[cnp.int32_t, ndim=2] points, int scale):
    """
    快速缩放轮廓点坐标
    
    Args:
        points: 轮廓点 (N, 2), int32
        scale: 缩放倍数
    
    Returns:
        缩放后的轮廓点
    """
    cdef int n = points.shape[0]
    cdef int i
    
    cdef cnp.ndarray[cnp.int32_t, ndim=2] result = np.empty((n, 2), dtype=np.int32)
    cdef cnp.int32_t[:, :] points_view = points
    cdef cnp.int32_t[:, :] result_view = result
    
    # 并行缩放
    with nogil:
        for i in prange(n, schedule='static'):
            result_view[i, 0] = points_view[i, 0] * scale
            result_view[i, 1] = points_view[i, 1] * scale
    
    return result


@cython.boundscheck(False)
@cython.wraparound(False)
def extract_region_mask(cnp.ndarray[cnp.uint8_t, ndim=2] mask, 
                        int x1, int y1, int x2, int y2, int margin):
    """
    快速提取区域蒙版（用于增量更新）
    
    Args:
        mask: 完整蒙版 (H, W), uint8
        x1, y1, x2, y2: 区域边界
        margin: 边界扩展
    
    Returns:
        区域蒙版和实际边界 (sub_mask, actual_x1, actual_y1)
    """
    cdef int h = mask.shape[0]
    cdef int w = mask.shape[1]
    
    # 扩展边界
    cdef int ax1 = max(0, x1 - margin)
    cdef int ay1 = max(0, y1 - margin)
    cdef int ax2 = min(w, x2 + margin)
    cdef int ay2 = min(h, y2 + margin)
    
    cdef int sub_h = ay2 - ay1
    cdef int sub_w = ax2 - ax1
    
    if sub_h <= 0 or sub_w <= 0:
        return np.zeros((0, 0), dtype=np.uint8), ax1, ay1
    
    # 提取子区域
    cdef cnp.ndarray[cnp.uint8_t, ndim=2] sub_mask = np.empty((sub_h, sub_w), dtype=np.uint8)
    cdef cnp.uint8_t[:, :] mask_view = mask
    cdef cnp.uint8_t[:, :] sub_view = sub_mask
    
    cdef int y, x
    
    # 并行复制
    with nogil:
        for y in prange(sub_h, schedule='static'):
            for x in range(sub_w):
                sub_view[y, x] = mask_view[ay1 + y, ax1 + x]
    
    return sub_mask, ax1, ay1


@cython.boundscheck(False)
@cython.wraparound(False)
def check_mask_empty(cnp.ndarray[cnp.uint8_t, ndim=2] mask):
    """
    快速检查蒙版是否为空（并行）
    
    Args:
        mask: 蒙版 (H, W), uint8
    
    Returns:
        True 如果全为 0
    """
    cdef int h = mask.shape[0]
    cdef int w = mask.shape[1]
    cdef int y, x
    cdef cnp.uint8_t[:, :] mask_view = mask
    cdef int found = 0
    
    # 并行搜索非零值
    with nogil:
        for y in prange(h, schedule='guided'):
            if found:
                break
            for x in range(w):
                if mask_view[y, x] != 0:
                    found = 1
                    break
    
    return found == 0
