"""
SAM (Segment Anything Model) 处理器

提供基于 SAM 模型的智能图像分割功能。
"""

import os
import numpy as np
from typing import Optional, Tuple, List


class SAMProcessor:
    """
    SAM 模型处理器
    
    使用 MobileSAM 进行快速图像分割。
    """
    
    def __init__(self, encoder_path: str, decoder_path: str):
        """
        初始化 SAM 处理器
        
        Args:
            encoder_path: 编码器模型路径
            decoder_path: 解码器模型路径
        """
        self.encoder_path = encoder_path
        self.decoder_path = decoder_path
        self.encoder_session = None
        self.decoder_session = None
        self.image_embedding = None
        self.high_res_feats = None  # SAM2的高分辨率特征
        self.current_image_shape = None
        self.is_loaded = False
    
    def load_model(self, progress_callback=None) -> bool:
        """
        加载 SAM 模型
        
        Args:
            progress_callback: 可选的进度回调函数，接收 0-100 的进度值
        
        Returns:
            True 如果加载成功，否则 False
        """
        try:
            import onnxruntime as ort
            
            # 设置日志级别
            ort.set_default_logger_severity(3)
            
            if progress_callback:
                progress_callback(10)
            
            # 加载编码器
            if not os.path.exists(self.encoder_path):
                print(f"编码器模型不存在: {self.encoder_path}")
                return False
            
            sess_options = ort.SessionOptions()
            sess_options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
            
            self.encoder_session = ort.InferenceSession(
                self.encoder_path,
                sess_options=sess_options,
                providers=['CPUExecutionProvider']
            )
            
            if progress_callback:
                progress_callback(50)
            
            # 加载解码器
            if not os.path.exists(self.decoder_path):
                print(f"解码器模型不存在: {self.decoder_path}")
                return False
            
            self.decoder_session = ort.InferenceSession(
                self.decoder_path,
                sess_options=sess_options,
                providers=['CPUExecutionProvider']
            )
            
            if progress_callback:
                progress_callback(100)
            
            self.is_loaded = True
            return True
            
        except ImportError:
            print("onnxruntime 未安装")
            return False
        except Exception as e:
            print(f"加载 SAM 模型失败: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def set_image(self, image: np.ndarray, progress_callback=None) -> bool:
        """
        设置并编码图像（只需执行一次）
        
        Args:
            image: 输入图像 (H, W, 3) RGB 格式
            progress_callback: 可选的进度回调函数
            
        Returns:
            True 如果成功，否则 False
        """
        if not self.is_loaded:
            print("模型未加载")
            return False
        
        try:
            if progress_callback:
                progress_callback(10)
            
            # 预处理图像
            input_image = self._preprocess_image(image)
            
            if progress_callback:
                progress_callback(30)
            
            # 根据编码器期望的格式调整输入
            input_name = self.encoder_session.get_inputs()[0].name
            input_shape = self.encoder_session.get_inputs()[0].shape
            
            if len(input_shape) == 4:
                # 期望 (N, C, H, W) 格式
                if len(input_image.shape) == 3:
                    # 当前是 (H, W, C)，需要转换为 (1, C, H, W)
                    input_image = np.transpose(input_image, (2, 0, 1))  # (C, H, W)
                    input_image = np.expand_dims(input_image, axis=0)  # (1, C, H, W)
            
            # 编码图像
            encoder_outputs = self.encoder_session.run(None, {input_name: input_image})
            
            # 保存所有编码器输出
            # SAM2编码器输出顺序：[high_res_feats_0, high_res_feats_1, image_embed]
            if len(encoder_outputs) == 3:
                # SAM2: 3个输出
                self.high_res_feats_0 = encoder_outputs[0]  # (1, 32, 256, 256)
                self.high_res_feats_1 = encoder_outputs[1]  # (1, 64, 128, 128)
                self.image_embedding = encoder_outputs[2]   # (1, 256, 64, 64)
            else:
                # SAM1/MobileSAM: 只有一个输出
                self.image_embedding = encoder_outputs[0]
                self.high_res_feats_0 = None
                self.high_res_feats_1 = None
            
            self.current_image_shape = image.shape[:2]
            
            if progress_callback:
                progress_callback(100)
            
            return True
            
        except Exception as e:
            print(f"图像编码失败: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def predict(
        self,
        point_coords: List[Tuple[int, int]],
        point_labels: List[int]
    ) -> Optional[Tuple[np.ndarray, float]]:
        """
        根据提示点预测分割掩码
        
        Args:
            point_coords: 提示点坐标列表 [(x, y), ...]
            point_labels: 提示点标签列表 [1, 1, ...] (1=前景, 0=背景)
            
        Returns:
            (分割掩码, IoU分数) 元组，掩码值为 0-255，如果失败返回 None
        """
        if not self.is_loaded or self.image_embedding is None:
            return None
        
        try:
            # 准备输入
            point_coords_array = np.array(point_coords, dtype=np.float32)
            point_labels_array = np.array(point_labels, dtype=np.float32)
            
            # 归一化坐标到编码器输入尺寸 (1024x1024)
            # 官方实现：先归一化到[0,1]，再乘以编码器输入尺寸
            h, w = self.current_image_shape
            encoder_size = 1024.0
            
            point_coords_normalized = point_coords_array.copy()
            point_coords_normalized[:, 0] = (point_coords_normalized[:, 0] / w) * encoder_size
            point_coords_normalized[:, 1] = (point_coords_normalized[:, 1] / h) * encoder_size
            
            # 添加批次维度
            point_coords_input = point_coords_normalized[np.newaxis, :, :]  # (1, N, 2)
            point_labels_input = point_labels_array[np.newaxis, :]  # (1, N)
            
            # 准备解码器输入
            # SAM2解码器输入顺序：image_embed, high_res_feats_0, high_res_feats_1, point_coords, point_labels, mask_input, has_mask_input
            onnx_mask_input = np.zeros((1, 1, 256, 256), dtype=np.float32)
            onnx_has_mask_input = np.zeros(1, dtype=np.float32)
            
            decoder_inputs = {
                'image_embed': self.image_embedding,        # (1, 256, 64, 64)
                'high_res_feats_0': self.high_res_feats_0,  # (1, 32, 256, 256)
                'high_res_feats_1': self.high_res_feats_1,  # (1, 64, 128, 128)
                'point_coords': point_coords_input,
                'point_labels': point_labels_input,
                'mask_input': onnx_mask_input,
                'has_mask_input': onnx_has_mask_input,
            }
            
            # 运行解码器
            outputs = self.decoder_session.run(None, decoder_inputs)
            
            masks = outputs[0]  # 掩码 (1, 3, H, W) - logits
            iou_predictions = outputs[1] if len(outputs) > 1 else None
            
            # 选择最佳掩码（基于IoU分数）
            best_iou = 0.0
            if iou_predictions is not None:
                best_idx = np.argmax(iou_predictions[0])
                best_iou = float(iou_predictions[0, best_idx])
                mask = masks[0, best_idx]
            else:
                mask = masks[0, 0]
            
            # 调整大小到原始图像尺寸
            import cv2
            mask_resized = cv2.resize(mask, (w, h), interpolation=cv2.INTER_LINEAR)
            
            # 二值化 - 直接使用0作为阈值（logits > 0 相当于 sigmoid > 0.5）
            mask_binary = (mask_resized > 0.0).astype(np.uint8) * 255
            
            return mask_binary, best_iou
            
        except Exception as e:
            print(f"SAM预测失败: {e}")
            return None
    
    def _preprocess_image(self, image: np.ndarray) -> np.ndarray:
        """
        预处理图像到模型输入格式
        
        Args:
            image: 输入图像 (H, W, 3) RGB
            
        Returns:
            预处理后的图像 (1024, 1024, 3) - SAM2格式
        """
        import cv2
        
        # 确保是RGB格式
        if len(image.shape) == 2:
            # 灰度图转RGB
            image = cv2.cvtColor(image, cv2.COLOR_GRAY2RGB)
        elif image.shape[2] == 4:
            # RGBA转RGB
            image = cv2.cvtColor(image, cv2.COLOR_RGBA2RGB)
        
        # 直接resize到 1024x1024（不保持宽高比，与官方实现一致）
        target_size = 1024
        resized = cv2.resize(image, (target_size, target_size), interpolation=cv2.INTER_LINEAR)
        
        # SAM标准归一化：先转换为float并除以255，然后应用ImageNet归一化
        normalized = resized.astype(np.float32) / 255.0
        
        # ImageNet归一化参数
        mean = np.array([0.485, 0.456, 0.406], dtype=np.float32)
        std = np.array([0.229, 0.224, 0.225], dtype=np.float32)
        
        # 应用归一化
        normalized = (normalized - mean) / std
        
        return normalized
    
    def unload_model(self):
        """卸载模型，释放资源"""
        self.encoder_session = None
        self.decoder_session = None
        self.image_embedding = None
        self.current_image_shape = None
        self.is_loaded = False
    
    def is_model_loaded(self) -> bool:
        """检查模型是否已加载"""
        return self.is_loaded
