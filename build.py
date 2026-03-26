#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Nuitka 编译脚本
用于将 BinarizationTool 打包为单个可执行文件
支持 Windows、Linux、macOS
"""

import os
import shutil
import subprocess
import sys
import platform
from pathlib import Path

# 导入版本号
try:
    from src.__version__ import __version__, __app_name__
    APP_VERSION = __version__
    APP_NAME = __app_name__
except ImportError:
    print("❌ 无法导入版本信息，使用默认值")
    APP_VERSION = "1.4.0.1"
    APP_NAME = "BinarizationTool"


def check_nuitka():
    """检查 Nuitka 是否已安装"""
    # 首先尝试通过 Python 模块方式运行
    try:
        result = subprocess.run(
            [sys.executable, "-m", "nuitka", "--version"],
            capture_output=True,
            check=True,
            text=True,
        )
        print(f"找到 Nuitka: {result.stdout.strip()}")
        return f"{sys.executable} -m nuitka"
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass

    # 尝试 nuitka3 命令
    try:
        result = subprocess.run(
            ["nuitka3", "--version"], capture_output=True, check=True, text=True
        )
        print(f"找到 Nuitka3: {result.stdout.strip()}")
        return "nuitka3"
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass

    # 尝试 nuitka 命令
    try:
        result = subprocess.run(
            ["nuitka", "--version"], capture_output=True, check=True, text=True
        )
        print(f"找到 Nuitka: {result.stdout.strip()}")
        return "nuitka"
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass

    return None


def install_nuitka():
    """安装 Nuitka"""
    print("正在安装 Nuitka...")
    try:
        subprocess.run([sys.executable, "-m", "pip", "install", "nuitka"], check=True)
        print("Nuitka 安装成功！")
        return True
    except subprocess.CalledProcessError:
        print("Nuitka 安装失败，请手动安装：pip install nuitka")
        return False


def get_compile_mode():
    """获取编译模式选择 - 默认使用多文件模式"""
    print("\n使用多文件模式 (--standalone) - 生成文件夹，体积较小，启动较快")
    return "standalone"


def check_project_files():
    """检查项目文件完整性"""
    current_dir = Path.cwd()

    # 必需的文件和目录
    required_items = [
        "main.py",
        "src/__init__.py",
        "src/__version__.py",
        "src/models/__init__.py",
        "src/views/__init__.py",
        "src/utils/__init__.py",
        "src/utils/binarization_engine.py",
        "src/cython_core/__init__.py",
        "themes/light_theme.qss",
    ]

    missing_items = []
    for item in required_items:
        if not (current_dir / item).exists():
            missing_items.append(item)

    if missing_items:
        print("❌ 缺少以下必需文件：")
        for item in missing_items:
            print(f"   - {item}")
        return False

    print("✅ 项目文件检查完成，所有必需文件存在")
    return True


def compile_cython_modules():
    """编译 Cython 模块"""
    print("\n正在编译 Cython 模块...")
    print("-" * 40)
    
    current_dir = Path.cwd()
    
    try:
        # 检查是否有 setup.py
        if not (current_dir / "setup.py").exists():
            print("⚠️  未找到 setup.py，跳过 Cython 编译")
            return True
        
        # 编译 Cython 模块
        result = subprocess.run(
            [sys.executable, "setup.py", "build_ext", "--inplace"],
            cwd=current_dir,
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            print("✅ Cython 模块编译成功")
            return True
        else:
            print("⚠️  Cython 模块编译失败，将使用纯 Python 降级版本")
            print(f"错误信息: {result.stderr}")
            return True  # 继续编译，使用降级版本
            
    except Exception as e:
        print(f"⚠️  Cython 编译出错: {e}")
        print("将使用纯 Python 降级版本")
        return True


def compile_project():
    """编译项目"""
    # 获取当前目录
    current_dir = Path.cwd()

    # 检查项目文件完整性
    if not check_project_files():
        print("请确保所有必需文件存在后再进行编译")
        return False

    # 编译 Cython 模块
    compile_cython_modules()

    # 获取编译模式
    compile_mode = get_compile_mode()

    # 检查 Nuitka
    nuitka_cmd = check_nuitka()
    if not nuitka_cmd:
        print("未找到 Nuitka，正在安装...")
        if not install_nuitka():
            return False
        nuitka_cmd = check_nuitka()
        if not nuitka_cmd:
            print("Nuitka 安装失败")
            return False

    print(f"使用 {nuitka_cmd} 编译项目...")

    # 从 __version__.py 获取版本号
    version = APP_VERSION
    print(f"当前版本号：{version}")

    # 根据模式设置输出文件名
    if compile_mode == "onefile":
        output_filename = f"{APP_NAME}v{version}.exe"
    else:
        output_filename = "main"  # 临时文件名

    # 构建基础编译参数
    base_params = [
        "--show-progress",  # 显示进度
        "--show-memory",  # 显示内存使用
        "--lto=yes",  # 启用链接时优化
        "--plugin-enable=pyside6",  # 启用 PySide6 插件
        "--follow-imports",  # 跟踪导入
        "--include-package=src",  # 包含整个 src 包
        "--include-module=numpy",  # 显式包含 numpy
        "--include-module=cv2",  # 显式包含 opencv
        "--include-module=PIL",  # 显式包含 Pillow
        "--include-module=PySide6",  # 显式包含 PySide6
        "--assume-yes-for-downloads",  # 自动确认下载
        # ========== 体积优化：排除不需要的 PySide6/Qt 模块 ==========
        "--noinclude-qt-translations",  # 排除 Qt 翻译文件
        "--noinclude-dlls=Qt6WebEngine*",  # 排除 WebEngine
        "--noinclude-dlls=Qt6Quick*",  # 排除 QML/Quick
        "--noinclude-dlls=Qt63D*",  # 排除 3D 模块
        "--noinclude-dlls=Qt6Multimedia*",  # 排除多媒体模块
        "--noinclude-dlls=Qt6Pdf*",  # 排除 PDF 模块
        "--noinclude-dlls=Qt6Sql*",  # 排除数据库模块
        "--noinclude-dlls=Qt6Designer*",  # 排除 Designer
        "--noinclude-dlls=Qt6Charts*",  # 排除图表模块
        "--noinclude-dlls=Qt6DataVisualization*",  # 排除数据可视化
        "--noinclude-dlls=Qt6RemoteObjects*",  # 排除远程对象
        "--noinclude-dlls=Qt6Sensors*",  # 排除传感器模块
        "--noinclude-dlls=Qt6SerialPort*",  # 排除串口模块
        "--noinclude-dlls=Qt6Test*",  # 排除测试模块
        "--noinclude-dlls=Qt6Bluetooth*",  # 排除蓝牙模块
        "--noinclude-dlls=Qt6Nfc*",  # 排除 NFC 模块
        "--noinclude-dlls=Qt6Positioning*",  # 排除定位模块
        "--noinclude-dlls=Qt6Location*",  # 排除位置模块
        # ========== 体积优化：排除未使用的 Python 包 ==========
        "--nofollow-import-to=unittest",  # 排除单元测试
        "--nofollow-import-to=test",  # 排除测试模块
        "--nofollow-import-to=tests",  # 排除测试目录
        "--nofollow-import-to=pytest",  # 排除 pytest
        "--nofollow-import-to=hypothesis",  # 排除 hypothesis
        "--nofollow-import-to=setuptools",  # 排除安装工具
        "--nofollow-import-to=pip",  # 排除 pip
        "--nofollow-import-to=distutils",  # 排除分发工具
        "--nofollow-import-to=tkinter",  # 排除 tkinter
        "--nofollow-import-to=pandas",  # 排除 pandas
        "--nofollow-import-to=matplotlib",  # 排除 matplotlib
        "--nofollow-import-to=scipy",  # 排除 scipy
        f"--copyright=Copyright © 2026 夏次一定de. All rights reserved.",  # 版权信息
    ]
    
    # 平台特定参数
    system = platform.system()
    if system == "Windows":
        # Windows 特定参数
        base_params.extend([
            "--mingw64",  # 使用 MinGW64
            "--windows-disable-console",  # 隐藏控制台窗口
            f"--windows-product-version={version}",  # 产品版本
            f"--windows-file-version={version}",  # 文件版本
            f"--windows-product-name={APP_NAME}",  # 产品名称
            "--windows-company-name=夏次一定de",  # 作者/公司名称
            f"--windows-file-description=二值化图片编辑器",  # 文件描述
        ])
    elif system == "Linux":
        # Linux 特定参数
        base_params.extend([
            "--linux-icon=icon.png",  # Linux 图标（如果存在）
        ])
    else:
        print(f"⚠️  不支持的操作系统: {system}")
        print("   本脚本仅支持 Windows 和 Linux")
        return False

    # 单文件模式需要指定输出文件名
    if compile_mode == "onefile":
        base_params.append(f"--output-filename={output_filename}")

    # 根据编译模式添加参数
    if compile_mode == "onefile":
        mode_params = ["--onefile"]  # 单文件模式
    else:
        mode_params = ["--standalone"]  # 独立模式

    # 构建编译命令
    if nuitka_cmd.startswith(sys.executable):
        # 使用 Python 模块方式
        compile_cmd = nuitka_cmd.split() + mode_params + base_params + ["main.py"]
    else:
        # 使用直接命令方式
        compile_cmd = [nuitka_cmd] + mode_params + base_params + ["main.py"]

    # 如果图标文件存在，添加图标参数
    if system == "Windows":
        if (current_dir / "icon" / "icon.ico").exists():
            compile_cmd.insert(-1, "--windows-icon-from-ico=icon/icon.ico")
        elif (current_dir / "icon.ico").exists():
            compile_cmd.insert(-1, "--windows-icon-from-ico=icon.ico")
        elif (current_dir / "1.ico").exists():
            compile_cmd.insert(-1, "--windows-icon-from-ico=1.ico")
    elif system == "Linux":
        if (current_dir / "icon" / "icon.png").exists():
            compile_cmd.insert(-1, "--linux-icon=icon/icon.png")
        elif (current_dir / "icon.png").exists():
            compile_cmd.insert(-1, "--linux-icon=icon.png")

    # 包含 themes 目录
    if (current_dir / "themes").exists():
        compile_cmd.insert(-1, "--include-data-dir=themes=themes")
        print("✅ 检测到 themes 目录，将包含在编译中")

    # 包含 locales 目录（多语言翻译文件）
    if (current_dir / "locales").exists():
        compile_cmd.insert(-1, "--include-data-dir=locales=locales")
        print("✅ 检测到 locales 目录，将包含在编译中")

    # 包含 Cython 编译的 .pyd/.so 文件
    system = platform.system()
    if system == "Windows":
        cython_pattern = "*.pyd"
    else:
        cython_pattern = "*.so"
    
    cython_files = list((current_dir / "src" / "cython_core").glob(cython_pattern))
    if cython_files:
        for cython_file in cython_files:
            compile_cmd.insert(-1, f"--include-data-file={cython_file}=src/cython_core/{cython_file.name}")
        print(f"✅ 检测到 {len(cython_files)} 个 Cython 模块，将包含在编译中")

    print("编译命令：")
    print(" ".join(compile_cmd))
    print("\n开始编译...")

    try:
        # 执行编译
        result = subprocess.run(compile_cmd, cwd=current_dir)

        if result.returncode == 0:
            print("\n✅ 编译成功！")

            # 查找生成的文件
            if compile_mode == "onefile":
                # 单文件模式 - 查找 exe 文件
                exe_file = current_dir / f"{output_filename}"
                if exe_file.exists():
                    file_size = exe_file.stat().st_size / (1024 * 1024)  # MB
                    print(f"生成的可执行文件：{exe_file}")
                    print(f"文件大小：{file_size:.2f} MB")
                else:
                    # 查找其他可能的 exe 文件
                    for file in current_dir.glob("*.exe"):
                        if "main" in file.name.lower():
                            file_size = file.stat().st_size / (1024 * 1024)
                            print(f"生成的可执行文件：{file}")
                            print(f"文件大小：{file_size:.2f} MB")
                            break
            else:
                # 多文件模式 - 查找文件夹
                main_dist_folder = current_dir / "main.dist"
                target_folder_name = f"{APP_NAME}v{version}"
                target_folder = current_dir / target_folder_name

                # 如果存在 main.dist，重命名为目标名称
                if main_dist_folder.exists():
                    try:
                        if target_folder.exists():
                            shutil.rmtree(target_folder)
                            print(f"已删除旧的输出文件夹：{target_folder}")

                        main_dist_folder.rename(target_folder)
                        print(f"✅ 已将 main.dist 重命名为：{target_folder_name}")
                    except Exception as e:
                        print(f"⚠️  重命名文件夹失败：{e}")
                        target_folder = main_dist_folder

                # 检查目标文件夹是否存在
                if target_folder.exists():
                    # 计算文件夹总大小
                    total_size = sum(
                        f.stat().st_size
                        for f in target_folder.rglob("*")
                        if f.is_file()
                    ) / (1024 * 1024)
                    print(f"生成的应用程序文件夹：{target_folder}")
                    print(f"总大小：{total_size:.2f} MB")

                    # 重命名 main.exe 为 BinarizationTool.exe
                    main_exe = target_folder / "main.exe"
                    target_exe = target_folder / f"{APP_NAME}.exe"
                    if main_exe.exists():
                        try:
                            if target_exe.exists():
                                target_exe.unlink()
                            main_exe.rename(target_exe)
                            print(f"✅ 已将 main.exe 重命名为：{APP_NAME}.exe")
                            print(f"主可执行文件：{target_exe}")
                        except Exception as e:
                            print(f"⚠️  重命名 main.exe 失败：{e}")
                            print(f"主可执行文件：{main_exe}")
                    elif target_exe.exists():
                        print(f"主可执行文件：{target_exe}")

            return True
        else:
            print(f"\n⚠️  编译过程返回非零退出码：{result.returncode}")
            return False

    except Exception as e:
        print(f"\n❌ 编译过程中出现错误：{e}")
        return False


def clean_old_files():
    """清理旧的编译文件"""
    import stat

    current_dir = Path.cwd()

    # 要删除的文件和目录列表
    items_to_delete = [
        current_dir / "main.build",
        current_dir / "main.dist",
    ]
    
    # 查找所有 BinarizationToolv* 文件夹
    for folder in current_dir.glob("BinarizationToolv*"):
        if folder.is_dir():
            items_to_delete.append(folder)

    print("\n" + "=" * 60)
    print("清理旧的编译文件")
    print("=" * 60)

    def handle_remove_readonly(func, path, exc):
        """处理只读文件"""
        os.chmod(path, stat.S_IWRITE)
        func(path)

    deleted_count = 0
    failed_items = []

    for item in items_to_delete:
        if item.exists():
            try:
                if item.is_dir():
                    shutil.rmtree(item, onerror=handle_remove_readonly)
                    print(f"✅ 已删除目录: {item.name}")
                    deleted_count += 1
                else:
                    item.unlink()
                    print(f"✅ 已删除文件: {item.name}")
                    deleted_count += 1
            except Exception as e:
                failed_items.append((item.name, str(e)))

    if deleted_count == 0 and len(failed_items) == 0:
        print("✅ 无需清理，所有文件都是干净的")
    else:
        if deleted_count > 0:
            print(f"✅ 清理完成，共删除 {deleted_count} 项")
        if failed_items:
            print(f"\n⚠️  以下 {len(failed_items)} 项删除失败（文件被占用）：")
            for name, _ in failed_items:
                print(f"   - {name}")
            print("   编译会尝试覆盖这些文件继续进行")


def main():
    """主函数"""
    print("=" * 60)
    print(f"{APP_NAME} - Nuitka 编译脚本")
    print(f"版本: {APP_VERSION}")
    print("=" * 60)

    current_dir = Path.cwd()

    # 清理旧文件
    clean_old_files()

    try:
        # 编译主项目
        if compile_project():
            print("\n🎉 编译完成！")

            # 查找输出目录
            target_folder_name = f"{APP_NAME}v{APP_VERSION}"
            output_folder = current_dir / target_folder_name

            if output_folder.exists():
                # 计算最终大小
                total_size = sum(
                    f.stat().st_size for f in output_folder.rglob("*") if f.is_file()
                ) / (1024 * 1024)
                print(f"\n📦 最终输出目录: {output_folder}")
                print(f"📦 总大小: {total_size:.2f} MB")

                # 编译完成后清理 main.build
                print("\n清理编译临时文件...")
                main_build = current_dir / "main.build"
                if main_build.exists():
                    import stat

                    def handle_remove_readonly(func, path, exc):
                        os.chmod(path, stat.S_IWRITE)
                        func(path)

                    try:
                        shutil.rmtree(main_build, onerror=handle_remove_readonly)
                        print("✅ 已删除 main.build")
                    except Exception as e:
                        print(f"⚠️  删除 main.build 失败: {e}")

                # 写入版本锁定文件
                version_lock_file = output_folder / ".version"
                try:
                    with open(version_lock_file, "w", encoding="utf-8") as f:
                        f.write(APP_VERSION)
                    print(f"✅ 已写入版本锁定文件: {APP_VERSION}")
                except Exception as e:
                    print(f"⚠️  写入版本锁定文件失败: {e}")
        else:
            print("\n❌ 编译失败！")
            return 1

    except KeyboardInterrupt:
        print("\n\n编译被用户中断")
        return 1
    except Exception as e:
        print(f"\n❌ 发生未预期的错误：{e}")
        return 1

    input("\n按回车键退出...")
    return 0


if __name__ == "__main__":
    sys.exit(main())
