from setuptools import setup, Extension
from setuptools.command.build_ext import build_ext
from Cython.Build import cythonize
import numpy as np
import sys
import os
import shutil


class CustomBuildExt(build_ext):
    """自定义构建扩展，确保输出到正确的目录"""
    
    def run(self):
        """运行构建，预先创建可能需要的目录"""
        # 如果是 inplace 模式，预先创建错误路径的目录（setuptools 的 bug）
        if self.inplace:
            wrong_path = os.path.join('src', 'src', 'cython_core')
            os.makedirs(wrong_path, exist_ok=True)
            print(f"Pre-creating directory: {wrong_path}")
        
        # 调用父类的 run 方法
        super().run()
        
        # 编译完成后，修复文件位置
        if self.inplace:
            wrong_path = os.path.join('src', 'src', 'cython_core')
            correct_path = os.path.join('src', 'cython_core')
            
            if os.path.exists(wrong_path):
                print(f"Fixing output path...")
                # 移动文件到正确位置
                for filename in os.listdir(wrong_path):
                    if filename.endswith(('.pyd', '.so', '.c')):
                        src_file = os.path.join(wrong_path, filename)
                        dst_file = os.path.join(correct_path, filename)
                        if os.path.exists(dst_file):
                            os.remove(dst_file)
                        print(f"  Moving: {filename}")
                        shutil.move(src_file, dst_file)
                
                # 清理错误的目录结构
                try:
                    shutil.rmtree(os.path.join('src', 'src'))
                    print("Output path fixed successfully")
                except Exception as e:
                    print(f"Warning: Failed to clean directory: {e}")


# 定义扩展模块
extensions = [
    Extension(
        "src.cython_core.dithering",
        ["src/cython_core/dithering.pyx"],
        include_dirs=[np.get_include()],
        extra_compile_args=['-O3'] if sys.platform != 'win32' else ['/O2'],
    ),
    Extension(
        "src.cython_core.contour_extractor",
        ["src/cython_core/contour_extractor.pyx"],
        include_dirs=[np.get_include()],
        extra_compile_args=['-O3', '-fopenmp'] if sys.platform != 'win32' else ['/O2', '/openmp:llvm'],
        extra_link_args=['-fopenmp'] if sys.platform != 'win32' else [],
    ),
]

setup(
    name="BinarizationTool",
    ext_modules=cythonize(
        extensions,
        compiler_directives={
            'language_level': "3",
            'boundscheck': False,
            'wraparound': False,
            'cdivision': True,
        }
    ),
    cmdclass={'build_ext': CustomBuildExt},
    zip_safe=False,
)
