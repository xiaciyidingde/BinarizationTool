from setuptools import setup, Extension
from Cython.Build import cythonize
import numpy as np
import sys

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
    zip_safe=False,
)
