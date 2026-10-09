"""
保存路径回归测试

覆盖：
1. save_image() 对 2D 灰度 / 3D RGB 像素的保存（回归：mode="L" 硬编码导致
   3D 数组抛 "Too many dimensions: 3 > 2"）
2. MainWindow._save_to_file 二值化视图 + 用户图层的合成保存分支
3. 保存后文件确实写出且内容可重新读取
"""

import sys

import numpy as np
import pytest
from PIL import Image
from PySide6.QtWidgets import QApplication

from src.models.image_data import ImageData
from src.models.user_layer import UserLayer
from src.utils.file_io import save_image
from src.views.main_window import MainWindow


@pytest.fixture(scope="module")
def qapp():
    """offscreen QApplication（MainWindow 测试需要）"""
    app = QApplication.instance() or QApplication(sys.argv)
    return app


class TestSaveImage:
    """file_io.save_image 的形状分支"""

    def test_save_2d_grayscale(self, tmp_path):
        """2D 灰度像素：mode=L 正常保存"""
        pixels = np.full((20, 20), 200, dtype=np.uint8)
        path = tmp_path / "gray.png"
        save_image(ImageData(pixels), str(path), format="PNG")
        assert path.exists()
        with Image.open(path) as img:
            assert img.mode == "L"

    def test_save_3d_rgb(self, tmp_path):
        """3D RGB 像素：回归——旧代码 mode=L 抛 Too many dimensions"""
        pixels = np.full((20, 20, 3), (128, 64, 32), dtype=np.uint8)
        path = tmp_path / "rgb.png"
        save_image(ImageData(pixels), str(path), format="PNG")
        assert path.exists()
        with Image.open(path) as img:
            assert img.mode == "RGB"

    def test_save_3d_rgb_to_jpeg(self, tmp_path):
        """3D RGB 像素存为 JPEG（mode=RGB 才能通过 JPEG 编码）"""
        pixels = np.zeros((20, 20, 3), dtype=np.uint8)
        pixels[:, :, 0] = 255
        path = tmp_path / "rgb.jpg"
        save_image(ImageData(pixels), str(path), format="JPEG")
        assert path.exists()
        with Image.open(path) as img:
            assert img.mode == "RGB"


class TestMainWindowBinarySave:
    """MainWindow._save_to_file 的二值化视图保存"""

    @pytest.fixture
    def window(self, qapp):
        """构造主窗口并挂载带用户图层的 ImageData"""
        w = MainWindow()
        w.image_data = ImageData(
            np.full((30, 40, 3), 0, dtype=np.uint8),  # 基础层：全黑 RGB
            np.full((30, 40, 3), 255, dtype=np.uint8),  # 原图：全白 RGB
        )
        w.image_data.view_mode = "binary"
        # 用户图层：左上角 10x10 白色方块
        layer_pixels = np.full((10, 10, 3), 255, dtype=np.uint8)
        layer_mask = np.ones((10, 10), dtype=bool)
        w.image_data.user_layers.append(UserLayer("layer1", layer_pixels, layer_mask, (0, 0, 10, 10)))
        yield w
        w.close()  # 触发 closeEvent → canvas.cleanup() 停掉轮廓线程

    def test_binary_with_user_layer_saves(self, window, tmp_path):
        """二值化视图 + 用户图层：合成结果应成功写出（回归点）"""
        path = tmp_path / "out.png"
        window._save_to_file(str(path))
        assert path.exists(), "合成保存不应抛异常且应写出文件"

        # 合成结果 = 基础层全黑 + 左上角白色方块 → 图片左上角为白
        with Image.open(path) as img:
            arr = np.array(img)
        assert arr.shape[:2] == (30, 40), "合成结果应保持图像尺寸"
        assert arr[0, 0].mean() > 200, "用户图层区域应覆盖为白色"
        assert arr[29, 39].mean() < 50, "未覆盖区域应保持基础层黑色"

    def test_binary_no_user_layer_saves(self, window, tmp_path):
        """二值化视图 + 无用户图层：走 save_image 分支也应成功"""
        window.image_data.user_layers.clear()
        path = tmp_path / "out.png"
        window._save_to_file(str(path))
        assert path.exists()
        with Image.open(path) as img:
            arr = np.array(img)
        assert arr.shape[:2] == (30, 40)
