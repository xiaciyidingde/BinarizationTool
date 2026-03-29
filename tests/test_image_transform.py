"""
测试图像变换功能
"""

import numpy as np
import pytest
import cv2


class TestImageTransform:
    """测试图像变换功能"""

    @pytest.fixture
    def sample_image(self):
        """创建测试图像"""
        # 创建一个简单的渐变图像
        img = np.zeros((100, 100), dtype=np.uint8)
        for i in range(100):
            img[i, :] = i * 2  # 从0到198的渐变
        return img

    def test_invert(self, sample_image):
        """测试图像反相"""
        inverted = 255 - sample_image
        
        # 检查反相结果
        assert inverted.shape == sample_image.shape
        assert inverted.dtype == sample_image.dtype
        
        # 验证反相逻辑：原图黑色(0)变白色(255)，白色变黑色
        assert inverted[0, 0] == 255  # 原图0变255
        assert inverted[99, 0] == 255 - 198  # 原图198变57

    def test_flip_horizontal(self, sample_image):
        """测试水平翻转"""
        flipped = cv2.flip(sample_image, 1)
        
        # 检查形状
        assert flipped.shape == sample_image.shape
        assert flipped.dtype == sample_image.dtype
        
        # 验证水平翻转：左右对称
        assert np.array_equal(flipped[:, 0], sample_image[:, -1])
        assert np.array_equal(flipped[:, -1], sample_image[:, 0])

    def test_flip_vertical(self, sample_image):
        """测试垂直翻转"""
        flipped = cv2.flip(sample_image, 0)
        
        # 检查形状
        assert flipped.shape == sample_image.shape
        assert flipped.dtype == sample_image.dtype
        
        # 验证垂直翻转：上下对称
        assert np.array_equal(flipped[0, :], sample_image[-1, :])
        assert np.array_equal(flipped[-1, :], sample_image[0, :])

    def test_double_flip(self, sample_image):
        """测试双重翻转应该恢复原图"""
        # 水平翻转两次
        flipped_h = cv2.flip(sample_image, 1)
        flipped_h_h = cv2.flip(flipped_h, 1)
        assert np.array_equal(flipped_h_h, sample_image)
        
        # 垂直翻转两次
        flipped_v = cv2.flip(sample_image, 0)
        flipped_v_v = cv2.flip(flipped_v, 0)
        assert np.array_equal(flipped_v_v, sample_image)

    def test_double_invert(self, sample_image):
        """测试双重反相应该恢复原图"""
        inverted = 255 - sample_image
        inverted_inverted = 255 - inverted
        assert np.array_equal(inverted_inverted, sample_image)

    def test_combined_transforms(self, sample_image):
        """测试组合变换"""
        # 反相 + 水平翻转
        inverted = 255 - sample_image
        flipped = cv2.flip(inverted, 1)
        
        # 应该等于先翻转再反相
        flipped_first = cv2.flip(sample_image, 1)
        inverted_second = 255 - flipped_first
        
        assert np.array_equal(flipped, inverted_second)

    def test_color_image_invert(self):
        """测试彩色图像反相"""
        # 创建彩色图像
        color_img = np.zeros((50, 50, 3), dtype=np.uint8)
        color_img[:, :, 0] = 100  # 蓝色通道
        color_img[:, :, 1] = 150  # 绿色通道
        color_img[:, :, 2] = 200  # 红色通道
        
        inverted = 255 - color_img
        
        assert inverted.shape == color_img.shape
        assert inverted[:, :, 0][0, 0] == 155
        assert inverted[:, :, 1][0, 0] == 105
        assert inverted[:, :, 2][0, 0] == 55

    def test_color_image_flip(self):
        """测试彩色图像翻转"""
        # 创建彩色图像
        color_img = np.zeros((50, 50, 3), dtype=np.uint8)
        color_img[:25, :, 0] = 255  # 上半部分蓝色
        color_img[25:, :, 1] = 255  # 下半部分绿色
        
        # 垂直翻转
        flipped = cv2.flip(color_img, 0)
        
        assert flipped.shape == color_img.shape
        # 上半部分应该变成绿色
        assert flipped[0, 0, 1] == 255
        assert flipped[0, 0, 0] == 0
        # 下半部分应该变成蓝色
        assert flipped[-1, 0, 0] == 255
        assert flipped[-1, 0, 1] == 0
