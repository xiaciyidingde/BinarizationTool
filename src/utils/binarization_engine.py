"""
二值化引擎

提供图像预处理和多种二值化算法。
"""

import numpy as np
import cv2


class ImageEnhancer:
    """图像增强处理类"""
    
    @staticmethod
    def apply_histogram_enhancement(img, equalize=False, clahe=False):
        """直方图增强"""
        if equalize:
            img = cv2.equalizeHist(img.astype(np.uint8)).astype(np.float32)
        if clahe:
            clahe_obj = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            img = clahe_obj.apply(img.astype(np.uint8)).astype(np.float32)
        return img
    
    @staticmethod
    def apply_local_enhancement(img, local_contrast=0, detail_enhance=0, edge_enhance=0):
        """局部增强"""
        # 局部对比度增强
        if local_contrast > 0:
            sigma = local_contrast * 0.5
            gaussian = cv2.GaussianBlur(img, (0, 0), sigma)
            img = cv2.addWeighted(img, 1 + local_contrast/50, gaussian, -local_contrast/50, 0)
        
        # 细节增强
        if detail_enhance > 0:
            blur = cv2.GaussianBlur(img, (0, 0), 3)
            detail = cv2.addWeighted(img, 1.0 + detail_enhance/50, blur, -detail_enhance/50, 0)
            img = cv2.addWeighted(img, 0.7, detail, 0.3, 0)
        
        # 边缘增强
        if edge_enhance > 0:
            sobelx = cv2.Sobel(img, cv2.CV_32F, 1, 0, ksize=3)
            sobely = cv2.Sobel(img, cv2.CV_32F, 0, 1, ksize=3)
            gradient = cv2.magnitude(sobelx, sobely)
            gradient = cv2.normalize(gradient, None, 0, 255, cv2.NORM_MINMAX)
            img = cv2.addWeighted(img, 1.0, gradient, edge_enhance/100.0, 0)
            
        return img

    @staticmethod
    def apply_denoise(img, method=0, strength=0):
        """
        降噪
        
        Args:
            img: 输入图像
            method: 降噪方法
                0 - 高斯降噪
                1 - 中值滤波
                2 - 双边滤波
                3 - NLMeans降噪
                4 - 形态学-开运算
                5 - 形态学-闭运算
            strength: 降噪强度 (0-100)
        
        Returns:
            降噪后的图像
        """
        if strength <= 0:
            return img
            
        if method == 0:  # 高斯降噪
            kernel_size = int(strength / 10) * 2 + 3
            sigma = strength / 20.0
            return cv2.GaussianBlur(img, (kernel_size, kernel_size), sigma)
        elif method == 1:  # 中值滤波
            kernel_size = int(strength / 10) * 2 + 3
            return cv2.medianBlur(img.astype(np.uint8), kernel_size).astype(np.float32)
        elif method == 2:  # 双边滤波
            d = int(strength)
            return cv2.bilateralFilter(img.astype(np.uint8), d, 75, 75).astype(np.float32)
        elif method == 3:  # NLMeans降噪
            h = strength * 2
            return cv2.fastNlMeansDenoising(img.astype(np.uint8), 
                                          h=h,
                                          templateWindowSize=7,
                                          searchWindowSize=21).astype(np.float32)
        elif method == 4:  # 形态学降噪 - 开运算（去除小的孤立点）
            kernel_size = int(strength / 20) + 1
            kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (kernel_size, kernel_size))
            # 开运算 = 先腐蚀后膨胀，去除小的白色噪点
            return cv2.morphologyEx(img.astype(np.uint8), cv2.MORPH_OPEN, kernel).astype(np.float32)
        elif method == 5:  # 形态学降噪 - 闭运算（填充小孔）
            kernel_size = int(strength / 20) + 1
            kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (kernel_size, kernel_size))
            # 闭运算 = 先膨胀后腐蚀，填充小的黑色孔洞
            return cv2.morphologyEx(img.astype(np.uint8), cv2.MORPH_CLOSE, kernel).astype(np.float32)
        
        return img

    @staticmethod
    def apply_basic_adjustments(img, exposure=0, contrast=0, gamma=1.0):
        """基础调整"""
        # 伽马校正
        if gamma != 1.0:
            img = np.power(img / 255.0, gamma) * 255.0
        
        # 曝光度调整
        if exposure != 0:
            factor = 1.0 + (exposure / 50.0)
            img = cv2.multiply(img, factor)
        
        # 对比度调整
        if contrast != 0:
            factor = (259.0 * (contrast + 255.0)) / (255.0 * (259.0 - contrast))
            img = factor * (img - 128.0) + 128.0
            
        return img

    @staticmethod
    def apply_sharpening(img, sharpen=0):
        """锐化"""
        if sharpen <= 0:
            return img
            
        # 根据锐化强度选择不同的核
        if sharpen < 33:
            kernel = np.array([[-1, -1, -1],
                             [-1, 9, -1],
                             [-1, -1, -1]]) * (sharpen / 100.0)
        elif sharpen < 66:
            kernel = np.array([[-2, -2, -2],
                             [-2, 17, -2],
                             [-2, -2, -2]]) * (sharpen / 100.0)
        else:
            kernel = np.array([[-3, -3, -3],
                             [-3, 25, -3],
                             [-3, -3, -3]]) * (sharpen / 100.0)
        
        return cv2.filter2D(img, -1, kernel)

    @staticmethod
    def apply_edge_detection(img, mode=0, strength=50, threshold2=150):
        """
        边缘检测增强
        
        Args:
            img: 输入图像
            mode: 边缘检测模式
                0 - 关闭
                1 - Canny 边缘检测
                2 - 边缘增强
                3 - 轮廓保留
            strength: 边缘强度 (0-100)
                - Canny 模式：控制低阈值
                - 增强模式：控制叠加权重
                - 轮廓模式：控制形态学核大小
            threshold2: Canny 高阈值 (仅 Canny 模式使用)
        
        Returns:
            处理后的图像
        """
        if mode == 0 or strength <= 0:
            return img
        
        img_uint8 = img.astype(np.uint8)
        
        if mode == 1:  # Canny 边缘检测
            # 计算阈值
            threshold1 = int(strength * 2.55)  # 0-100 映射到 0-255
            threshold2 = max(threshold1 + 50, threshold2)  # 确保高阈值大于低阈值
            
            # Canny 边缘检测
            edges = cv2.Canny(img_uint8, threshold1, threshold2)
            
            # 将边缘叠加到原图（白色边缘）
            result = img.copy()
            result[edges > 0] = 255
            return result
        
        elif mode == 2:  # 边缘增强（叠加到原图）
            # 使用 Sobel 算子检测边缘
            sobelx = cv2.Sobel(img_uint8, cv2.CV_32F, 1, 0, ksize=3)
            sobely = cv2.Sobel(img_uint8, cv2.CV_32F, 0, 1, ksize=3)
            gradient = cv2.magnitude(sobelx, sobely)
            gradient = cv2.normalize(gradient, None, 0, 255, cv2.NORM_MINMAX)
            
            # 根据强度叠加边缘
            weight = strength / 100.0
            result = cv2.addWeighted(img, 1.0, gradient, weight, 0)
            return result
        
        elif mode == 3:  # 轮廓保留（形态学梯度）
            # 计算核大小
            kernel_size = max(3, int(strength / 20) * 2 + 1)
            kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (kernel_size, kernel_size))
            
            # 形态学梯度 = 膨胀 - 腐蚀
            gradient = cv2.morphologyEx(img_uint8, cv2.MORPH_GRADIENT, kernel)
            
            # 叠加到原图
            weight = min(1.0, strength / 50.0)
            result = cv2.addWeighted(img, 1.0, gradient.astype(np.float32), weight, 0)
            return result
        
        return img


class BinarizationEngine:
    """
    二值化处理引擎
    
    提供图像预处理和多种二值化算法。
    """
    
    @staticmethod
    def convert_to_grayscale(image: np.ndarray) -> np.ndarray:
        """
        将彩色图片转换为灰度图
        
        Args:
            image: 输入图片，可以是灰度图 (H, W) 或彩色图 (H, W, 3/4)
            
        Returns:
            灰度图，形状为 (H, W)，dtype=uint8
        """
        if len(image.shape) == 2:
            # 已经是灰度图
            return image
        elif len(image.shape) == 3:
            if image.shape[2] == 3:
                # RGB 图片
                return cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
            elif image.shape[2] == 4:
                # RGBA 图片
                return cv2.cvtColor(image, cv2.COLOR_RGBA2GRAY)
        
        # 默认返回原图
        return image
    
    @staticmethod
    def apply_floyd_steinberg(image: np.ndarray, strength: float = 1.0) -> np.ndarray:
        """
        Floyd-Steinberg 抖动算法
        
        经典的误差扩散算法，保留灰度细节。
        
        Args:
            image: 输入灰度图
            strength: 抖动强度 (0.0-1.0)，默认 1.0
        
        Returns:
            二值化图片
        """
        # 确保是灰度图
        img = BinarizationEngine.convert_to_grayscale(image)
        img = img.astype(float)
        h, w = img.shape
        
        for y in range(h):
            for x in range(w):
                old_pixel = img[y, x]
                new_pixel = 255 if old_pixel > 127 else 0
                img[y, x] = new_pixel
                
                error = (old_pixel - new_pixel) * strength
                
                # 扩散误差到相邻像素
                if x + 1 < w:
                    img[y, x + 1] += error * 7/16
                if y + 1 < h:
                    if x > 0:
                        img[y + 1, x - 1] += error * 3/16
                    img[y + 1, x] += error * 5/16
                    if x + 1 < w:
                        img[y + 1, x + 1] += error * 1/16
        
        return np.clip(img, 0, 255).astype(np.uint8)
    
    @staticmethod
    def apply_ordered_dithering(image: np.ndarray, matrix_size: int = 8) -> np.ndarray:
        """
        Ordered Dithering (有序抖动)
        
        使用 Bayer 矩阵产生网点效果，适合打印。
        
        Args:
            image: 输入灰度图
            matrix_size: Bayer 矩阵大小 (2, 4, 8, 16)
        
        Returns:
            二值化图片
        """
        # 确保是灰度图
        img = BinarizationEngine.convert_to_grayscale(image)
        
        # 生成 Bayer 矩阵
        def generate_bayer_matrix(n):
            """递归生成 Bayer 矩阵"""
            if n == 1:
                return np.array([[0]])
            else:
                smaller = generate_bayer_matrix(n // 2)
                return np.block([
                    [4 * smaller + 0, 4 * smaller + 2],
                    [4 * smaller + 3, 4 * smaller + 1]
                ])
        
        # 确保 matrix_size 是 2 的幂
        matrix_size = max(2, min(16, matrix_size))
        if matrix_size not in [2, 4, 8, 16]:
            matrix_size = 8
        
        bayer_matrix = generate_bayer_matrix(matrix_size)
        threshold_map = (bayer_matrix / (matrix_size * matrix_size)) * 255
        
        h, w = img.shape
        result = np.zeros_like(img)
        
        for y in range(h):
            for x in range(w):
                threshold = threshold_map[y % matrix_size, x % matrix_size]
                result[y, x] = 255 if img[y, x] > threshold else 0
        
        return result
    
    @staticmethod
    def apply_atkinson(image: np.ndarray, strength: float = 1.0) -> np.ndarray:
        """
        Atkinson 抖动算法
        
        Mac 风格的误差扩散，产生艺术效果。
        误差扩散更轻，保留更多高光。
        
        Args:
            image: 输入灰度图
            strength: 抖动强度 (0.0-1.0)，默认 1.0
        
        Returns:
            二值化图片
        """
        # 确保是灰度图
        img = BinarizationEngine.convert_to_grayscale(image)
        img = img.astype(float)
        h, w = img.shape
        
        for y in range(h):
            for x in range(w):
                old_pixel = img[y, x]
                new_pixel = 255 if old_pixel > 127 else 0
                img[y, x] = new_pixel
                
                # Atkinson 使用 1/8 的误差扩散（比 Floyd-Steinberg 更轻）
                error = (old_pixel - new_pixel) * strength / 8
                
                # 扩散误差到相邻像素（6个方向）
                if x + 1 < w:
                    img[y, x + 1] += error
                if x + 2 < w:
                    img[y, x + 2] += error
                if y + 1 < h:
                    if x > 0:
                        img[y + 1, x - 1] += error
                    img[y + 1, x] += error
                    if x + 1 < w:
                        img[y + 1, x + 1] += error
                if y + 2 < h:
                    img[y + 2, x] += error
        
        return np.clip(img, 0, 255).astype(np.uint8)
    
    @staticmethod
    def apply_preprocess(img: np.ndarray, **kwargs) -> np.ndarray:
        """
        图像预处理
        
        Args:
            img: 输入图像
            **kwargs: 预处理参数
                - exposure: 曝光度 (-100 到 100)
                - contrast: 对比度 (-100 到 100)
                - sharpen: 锐化 (0 到 100)
                - gamma: 伽马校正 (0.1 到 3.0)
                - smooth: 平滑强度 (0 到 100)
                - denoise_method: 降噪方法 (0-6)
                - denoise: 降噪强度 (0 到 100)
                - equalize: 直方图均衡化 (bool)
                - clahe: CLAHE增强 (bool)
                - local_contrast: 局部对比度 (0 到 100)
                - detail_enhance: 细节增强 (0 到 100)
                - edge_enhance: 边缘增强 (0 到 100)
                - edge_mode: 边缘检测模式 (0-3)
                - edge_strength: 边缘检测强度 (0 到 100)
                - edge_threshold: Canny 高阈值 (0 到 255)
        
        Returns:
            预处理后的图像
        """
        enhancer = ImageEnhancer()
        
        img = img.astype(np.float32)
        
        # 直方图增强
        img = enhancer.apply_histogram_enhancement(
            img, 
            equalize=kwargs.get('equalize', False),
            clahe=kwargs.get('clahe', False)
        )
        
        # 局部增强
        img = enhancer.apply_local_enhancement(
            img,
            local_contrast=kwargs.get('local_contrast', 0),
            detail_enhance=kwargs.get('detail_enhance', 0),
            edge_enhance=kwargs.get('edge_enhance', 0)
        )
        
        # 平滑（简单的高斯模糊）
        smooth_strength = kwargs.get('smooth', 0)
        if smooth_strength > 0:
            kernel_size = int(smooth_strength / 10) * 2 + 3
            sigma = smooth_strength / 20.0
            img = cv2.GaussianBlur(img, (kernel_size, kernel_size), sigma)
        
        # 降噪（高级降噪方法）
        img = enhancer.apply_denoise(
            img,
            method=kwargs.get('denoise_method', 0),
            strength=kwargs.get('denoise', 0)
        )
        
        # RGB 通道调整
        red_adjust = kwargs.get('red_channel', 0)
        green_adjust = kwargs.get('green_channel', 0)
        blue_adjust = kwargs.get('blue_channel', 0)
        
        if red_adjust != 0 or green_adjust != 0 or blue_adjust != 0:
            # 确保图像是彩色的（如果是灰度图，转换为 RGB）
            if len(img.shape) == 2:
                img = cv2.cvtColor(img.astype(np.uint8), cv2.COLOR_GRAY2RGB).astype(np.float32)
            
            # 调整各通道
            if red_adjust != 0:
                img[:, :, 2] = np.clip(img[:, :, 2] + red_adjust * 2.55, 0, 255)
            if green_adjust != 0:
                img[:, :, 1] = np.clip(img[:, :, 1] + green_adjust * 2.55, 0, 255)
            if blue_adjust != 0:
                img[:, :, 0] = np.clip(img[:, :, 0] + blue_adjust * 2.55, 0, 255)
        
        # 基础调整
        img = enhancer.apply_basic_adjustments(
            img,
            exposure=kwargs.get('exposure', 0),
            contrast=kwargs.get('contrast', 0),
            gamma=kwargs.get('gamma', 1.0)
        )
        
        # 边缘检测
        img = enhancer.apply_edge_detection(
            img,
            mode=kwargs.get('edge_mode', 0),
            strength=kwargs.get('edge_strength', 50),
            threshold2=kwargs.get('edge_threshold', 150)
        )
        
        # 锐化
        img = enhancer.apply_sharpening(
            img,
            sharpen=kwargs.get('sharpen', 0)
        )
        
        # 裁剪到有效范围
        img = np.clip(img, 0, 255)
        return img.astype(np.uint8)
    
    @staticmethod
    def apply_threshold(image: np.ndarray, threshold_method: int = 1, 
                       threshold_value: int = 150, **kwargs) -> np.ndarray:
        """
        应用阈值处理（支持多种方法）
        
        Args:
            image: 输入灰度图
            threshold_method: 阈值方法
                0 - 固定阈值
                1 - 自适应阈值（默认）
                2 - Otsu 阈值
                3 - Sauvola 阈值
                4 - Wolf 阈值
                5 - Nick 阈值
                6 - Bernsen 阈值
                7 - Floyd-Steinberg 抖动
                8 - Ordered 抖动
                9 - Atkinson 抖动
            threshold_value: 阈值参数（用于固定阈值和自适应阈值的 C 参数）
            **kwargs: 额外参数
                - block_size: 自适应阈值的块大小 (3-51奇数，默认自动计算)
                - window_size: Sauvola/Wolf/Nick/Bernsen的窗口大小 (3-51奇数，默认自动计算)
                - sauvola_k: Sauvola的k参数 (0.0-1.0，默认0.2)
                - sauvola_r: Sauvola的R参数 (0-255，默认128)
                - wolf_k: Wolf的k参数 (0.0-1.0，默认0.5)
                - nick_k: Nick的k参数 (-1.0-0.0，默认-0.1)
                - bernsen_contrast: Bernsen的对比度阈值 (0-255，默认15)
                - dither_strength: 抖动强度 (0.0-1.0，默认1.0)
                - dither_matrix_size: Ordered抖动的矩阵大小 (2/4/8/16，默认8)
        
        Returns:
            二值化图片
        """
        # 确保是灰度图
        img = BinarizationEngine.convert_to_grayscale(image)
        
        # 抖动算法 (7-9)
        if threshold_method == 7:  # Floyd-Steinberg 抖动
            strength = kwargs.get('dither_strength', 100) / 100.0
            return BinarizationEngine.apply_floyd_steinberg(img, strength)
        
        elif threshold_method == 8:  # Ordered 抖动
            matrix_size = kwargs.get('dither_matrix_size', 8)
            return BinarizationEngine.apply_ordered_dithering(img, matrix_size)
        
        elif threshold_method == 9:  # Atkinson 抖动
            strength = kwargs.get('dither_strength', 100) / 100.0
            return BinarizationEngine.apply_atkinson(img, strength)
        
        # 传统二值化方法 (0-6)
        if threshold_method == 0:  # 固定阈值
            return cv2.threshold(img, threshold_value, 255, cv2.THRESH_BINARY)[1]
        
        elif threshold_method == 1:  # 自适应阈值
            # 获取块大小参数，如果未指定则自动计算
            block_size = kwargs.get('block_size', None)
            if block_size is None or block_size == 0:
                block_size = min(img.shape) // 8
                if block_size % 2 == 0:
                    block_size += 1
                block_size = max(3, min(block_size, 51))
            
            # 优化自适应阈值参数
            C = max(0, threshold_value / 10 - 10)
            return cv2.adaptiveThreshold(img, 255, 
                                       cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                       cv2.THRESH_BINARY, 
                                       block_size, C)
        
        elif threshold_method == 2:  # Otsu阈值
            return cv2.threshold(img, 0, 255, 
                               cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]
        
        elif threshold_method == 3:  # Sauvola阈值
            # 获取窗口大小参数，如果未指定则自动计算
            window = kwargs.get('window_size', None)
            if window is None or window == 0:
                window = min(img.shape) // 8
                if window % 2 == 0:
                    window += 1
                window = max(3, min(window, 51))
            
            # 计算局部均值和标准差
            mean = cv2.boxFilter(img.astype(float), -1, (window, window))
            mean_square = cv2.boxFilter(img.astype(float)**2, -1, (window, window))
            std = np.sqrt(mean_square - mean**2)
            
            # Sauvola参数（可自定义）
            k = kwargs.get('sauvola_k', 0.2)
            R = kwargs.get('sauvola_r', 128)
            threshold = mean * (1 + k * ((std / R) - 1))
            
            return np.where(img >= threshold, 255, 0).astype(np.uint8)
        
        elif threshold_method == 4:  # Wolf阈值
            # 获取窗口大小参数，如果未指定则自动计算
            window = kwargs.get('window_size', None)
            if window is None or window == 0:
                window = min(img.shape) // 8
                if window % 2 == 0:
                    window += 1
                window = max(3, min(window, 51))
            
            # 计算局部均值和标准差
            mean = cv2.boxFilter(img.astype(float), -1, (window, window))
            mean_square = cv2.boxFilter(img.astype(float)**2, -1, (window, window))
            std = np.sqrt(mean_square - mean**2)
            
            # Wolf参数（可自定义）
            k = kwargs.get('wolf_k', 0.5)
            R = 128
            min_std = 2
            threshold = mean - k * std * (1 - std/(R * np.clip(std, min_std, None)))
            
            return np.where(img >= threshold, 255, 0).astype(np.uint8)
        
        elif threshold_method == 5:  # Nick阈值
            # 获取窗口大小参数，如果未指定则自动计算
            window = kwargs.get('window_size', None)
            if window is None or window == 0:
                window = min(img.shape) // 8
                if window % 2 == 0:
                    window += 1
                window = max(3, min(window, 51))
            
            # 计算局部均值和标准差
            mean = cv2.boxFilter(img.astype(float), -1, (window, window))
            mean_square = cv2.boxFilter(img.astype(float)**2, -1, (window, window))
            std = np.sqrt(mean_square - mean**2)
            
            # Nick参数（可自定义）
            k = kwargs.get('nick_k', -0.1)
            threshold = mean + k * std
            
            return np.where(img >= threshold, 255, 0).astype(np.uint8)
        
        elif threshold_method == 6:  # Bernsen阈值
            # 获取窗口大小参数，如果未指定则自动计算
            window = kwargs.get('window_size', None)
            if window is None or window == 0:
                window = min(img.shape) // 8
                if window % 2 == 0:
                    window += 1
                window = max(3, min(window, 51))
            
            # 计算局部最大值和最小值
            kernel = np.ones((window, window), np.uint8)
            local_max = cv2.dilate(img, kernel)
            local_min = cv2.erode(img, kernel)
            
            # Bernsen参数（可自定义）
            contrast_threshold = kwargs.get('bernsen_contrast', 15)
            local_contrast = local_max - local_min
            local_mean = (local_max + local_min) / 2
            
            # 对比度太低的区域使用全局阈值
            global_threshold = cv2.threshold(img, 0, 255, cv2.THRESH_OTSU)[0]
            mask = local_contrast < contrast_threshold
            threshold = np.where(mask, global_threshold, local_mean)
            
            return np.where(img >= threshold, 255, 0).astype(np.uint8)
        
        else:  # 默认使用固定阈值
            return cv2.threshold(img, threshold_value, 255, cv2.THRESH_BINARY)[1]
    
    # 保留旧的方法以保持兼容性
    @staticmethod
    def apply_fixed_threshold(image: np.ndarray, threshold: int) -> np.ndarray:
        """固定阈值（兼容方法）"""
        return BinarizationEngine.apply_threshold(image, 0, threshold)
    
    @staticmethod
    def apply_otsu(image: np.ndarray) -> np.ndarray:
        """Otsu 阈值（兼容方法）"""
        return BinarizationEngine.apply_threshold(image, 2, 0)
    
    @staticmethod
    def apply_adaptive(image: np.ndarray, block_size: int = 11, c: int = 2) -> np.ndarray:
        """自适应阈值（兼容方法）"""
        return BinarizationEngine.apply_threshold(image, 1, c * 10 + 100)
