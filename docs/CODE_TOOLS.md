# 代码工具指南

本文档介绍项目使用的开发工具及其基本用法。

---

## 代码质量工具

### Ruff - 快速代码检查和格式化

**用途**：代码风格检查、自动修复、格式化、导入排序

**安装**：
```bash
pip install ruff
```

**常用命令**：
```bash
# 检查代码
ruff check src

# 自动修复
ruff check --fix src

# 格式化代码
ruff format src
```

**配置文件**：`pyproject.toml`

**VS Code 扩展**：搜索安装 "Ruff"

---

### Pylint - 深度代码分析

**用途**：代码质量检查、重复代码检测、复杂度分析

**安装**：
```bash
pip install pylint
```

**常用命令**：
```bash
# 检查代码
pylint src

# 检查单个文件
pylint src/views/main_window.py

# 生成报告
pylint src --output-format=text > pylint_report.txt
```

**配置文件**：`.pylintrc`（可选）

**主要功能**：
- 检测代码重复（duplicate-code）
- 分析代码复杂度
- 检查命名规范
- 发现潜在 bug

---

## 测试工具

### Pytest - 单元测试框架

**用途**：编写和运行单元测试

**安装**：
```bash
pip install pytest
```

**常用命令**：
```bash
# 运行所有测试
pytest

# 运行特定测试文件
pytest tests/test_image_data.py

# 显示详细输出
pytest -v

# 生成覆盖率报告
pytest --cov=src --cov-report=html
```

**配置文件**：`pytest.ini`

---

### Hypothesis - 属性测试

**用途**：基于属性的自动化测试，生成大量测试用例

**安装**：
```bash
pip install hypothesis
```

**使用示例**：
```python
from hypothesis import given
import hypothesis.strategies as st

@given(st.integers())
def test_function(x):
    assert my_function(x) >= 0
```

**特点**：
- 自动生成测试数据
- 发现边界情况
- 缩小失败用例

---

## 构建工具

### Cython - Python 扩展编译

**用途**：将 Python 代码编译为 C 扩展，提升性能

**安装**：
```bash
pip install cython
```

**使用**：
```bash
# 编译 Cython 扩展
python build.py
```

**项目中的应用**：
- `src/cython_core/dithering.pyx` - 抖动算法加速

---

## 快速开始

### 安装所有开发工具

```bash
pip install -r requirements-dev.txt
```

### 代码检查流程

```bash
# 1. Ruff 快速检查和修复
ruff check --fix src
ruff format src

# 2. Pylint 深度分析
pylint src

# 3. 运行测试
pytest

# 4. 编译 Cython 扩展
python build.py
```

---

## VS Code 集成

推荐安装的扩展：
- **Ruff** - 实时代码检查和格式化
- **Pylint** - 深度代码分析
- **Python Test Explorer** - 测试管理

配置文件：`.vscode/settings.json`

---

## 最佳实践

1. **提交前检查**：
   ```bash
   ruff check src && pylint src && pytest
   ```

2. **保持代码整洁**：
   - 使用 Ruff 自动格式化
   - 定期运行 Pylint 检查重复代码
   - 保持测试覆盖率

3. **性能优化**：
   - 使用 Cython 优化性能瓶颈
   - 编译后测试性能提升

---

## 参考资料

- [Ruff 文档](https://docs.astral.sh/ruff/)
- [Pylint 文档](https://pylint.readthedocs.io/)
- [Pytest 文档](https://docs.pytest.org/)
- [Hypothesis 文档](https://hypothesis.readthedocs.io/)
- [Cython 文档](https://cython.readthedocs.io/)
