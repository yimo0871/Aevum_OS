"""Code embedder - 代码向量化.

为代码内容生成特征向量，用于代码经验相似度检索。
轻量级本地向量化器，无需外部 API。

特征提取维度:
- 行数、函数数、类数、导入数
- 圈复杂度近似（分支/循环关键字计数）
- 语言关键字与标识符的哈希分布
"""

from __future__ import annotations

import hashlib
import math
import re
from typing import Any


# ── 语言关键字映射 ──
LANGUAGE_KEYWORDS: dict[str, list[str]] = {
    "python": [
        "def", "class", "import", "from", "if", "elif", "else", "for",
        "while", "try", "except", "finally", "with", "return", "yield",
        "async", "await", "lambda", "global", "nonlocal", "raise",
        "assert", "break", "continue", "pass", "in", "is", "not", "and",
        "or", "as", "del", "True", "False", "None",
    ],
    "javascript": [
        "function", "class", "import", "export", "from", "if", "else",
        "for", "while", "try", "catch", "finally", "return", "yield",
        "async", "await", "const", "let", "var", "new", "this", "typeof",
        "instanceof", "in", "of", "break", "continue", "throw", "switch",
        "case", "default", "do", "extends", "super",
    ],
    "java": [
        "public", "private", "protected", "class", "interface", "extends",
        "implements", "import", "package", "if", "else", "for", "while",
        "do", "try", "catch", "finally", "return", "new", "this", "super",
        "static", "final", "void", "int", "long", "double", "float",
        "boolean", "String", "throw", "throws", "switch", "case", "break",
        "continue", "instanceof", "synchronized", "abstract",
    ],
    "go": [
        "func", "package", "import", "type", "struct", "interface", "if",
        "else", "for", "range", "switch", "case", "default", "return",
        "go", "defer", "select", "chan", "map", "var", "const", "break",
        "continue", "fallthrough", "nil", "true", "false",
    ],
}

# 圈复杂度贡献关键字（分支/循环/异常）
COMPLEXITY_KEYWORDS: dict[str, list[str]] = {
    "python": ["if", "elif", "for", "while", "except", "and", "or", "with"],
    "javascript": ["if", "else", "for", "while", "catch", "&&", "||", "case"],
    "java": ["if", "else", "for", "while", "catch", "&&", "||", "case"],
    "go": ["if", "else", "for", "switch", "case", "select", "&&", "||"],
}


class CodeEmbedder:
    """代码向量化器 - 从代码特征生成本地向量.

    使用特征提取 + 哈希分布生成固定维度的向量。
    相同代码生成相同向量，结构相似的代码生成相近向量。
    """

    DEFAULT_DIM = 64

    def __init__(self, dim: int = DEFAULT_DIM) -> None:
        self._dim = dim

    @property
    def dimension(self) -> int:
        return self._dim

    def extract_features(self, code: str) -> dict[str, Any]:
        """提取代码结构特征.

        Returns:
            包含 lines, functions, classes, imports, complexity 等
            结构化特征的字典。
        """
        if not code:
            return {
                "lines": 0,
                "code_lines": 0,
                "functions": 0,
                "classes": 0,
                "imports": 0,
                "complexity": 0,
                "comments": 0,
                "avg_line_length": 0.0,
                "language": "python",
            }

        lines = code.splitlines()
        non_empty = [ln for ln in lines if ln.strip()]
        code_lines = [ln for ln in non_empty if not ln.strip().startswith("#")]

        # 函数定义计数
        func_patterns = [
            r"^\s*def\s+",            # python
            r"^\s*function\s+",       # javascript
            r"^\s*func\s+",           # go
            r"(public|private|protected|static)?\s*\w+\s+\w+\s*\(",  # java
        ]
        functions = sum(
            1 for ln in non_empty
            if any(re.search(p, ln) for p in func_patterns)
        )

        # 类定义计数
        class_patterns = [r"^\s*class\s+", r"^\s*interface\s+", r"^\s*struct\s+"]
        classes = sum(
            1 for ln in non_empty
            if any(re.search(p, ln) for p in class_patterns)
        )

        # 导入计数
        import_patterns = [
            r"^\s*import\s+", r"^\s*from\s+\S+\s+import", r"^\s*require\s*\(",
            r"^\s*package\s+",
        ]
        imports = sum(
            1 for ln in non_empty
            if any(re.search(p, ln) for p in import_patterns)
        )

        # 复杂度（圈复杂度近似）
        complexity = 1  # 基础复杂度
        for ln in non_empty:
            for kw in COMPLEXITY_KEYWORDS.get("python", []):
                # 使用单词边界匹配，避免误匹配（如 "information" 中的 "for"）
                complexity += len(re.findall(rf"\b{re.escape(kw)}\b", ln))

        # 注释计数
        comments = sum(
            1 for ln in lines
            if ln.strip().startswith("#") or ln.strip().startswith("//")
        )

        avg_line_length = (
            sum(len(ln) for ln in code_lines) / len(code_lines)
            if code_lines else 0.0
        )

        return {
            "lines": len(lines),
            "code_lines": len(code_lines),
            "functions": functions,
            "classes": classes,
            "imports": imports,
            "complexity": complexity,
            "comments": comments,
            "avg_line_length": round(avg_line_length, 2),
            "language": "python",
        }

    def embed_code(self, code: str, language: str = "python") -> list[float]:
        """生成代码特征向量.

        通过结构特征与词法 token 的哈希分布生成固定维度向量，
        并进行 L2 归一化。

        Args:
            code: 代码文本
            language: 编程语言（影响关键字集合）

        Returns:
            L2 归一化的浮点向量（维度默认 64）
        """
        vector = [0.0] * self._dim

        if not code or not code.strip():
            return vector

        # ── 1. 词法 token 哈希分布 ──
        tokens = self._tokenize(code, language)
        keywords = set(LANGUAGE_KEYWORDS.get(language, LANGUAGE_KEYWORDS["python"]))

        for token in tokens:
            h = int(hashlib.md5(token.encode()).hexdigest(), 16)
            # 每个 token 影响 4 个维度
            for i in range(4):
                idx = (h + i * 137) % self._dim
                val = ((h >> (i * 4)) & 0xFF) / 127.5 - 1.0
                # 关键字权重更高
                weight = 2.0 if token in keywords else 1.0
                vector[idx] += val * weight

        # ── 2. 结构特征贡献 ──
        features = self.extract_features(code)
        # 将归一化的特征值散布到向量的前若干维度
        feature_values = [
            min(features["functions"] / 10.0, 1.0),
            min(features["classes"] / 5.0, 1.0),
            min(features["imports"] / 10.0, 1.0),
            min(features["complexity"] / 20.0, 1.0),
            min(features["code_lines"] / 100.0, 1.0),
            min(features["comments"] / 20.0, 1.0),
            min(features["avg_line_length"] / 80.0, 1.0),
        ]
        for i, val in enumerate(feature_values):
            if i < self._dim:
                vector[i] += val

        # ── 3. L2 归一化 ──
        norm = math.sqrt(sum(v * v for v in vector))
        if norm > 0:
            vector = [v / norm for v in vector]

        return vector

    def _tokenize(self, code: str, language: str = "python") -> list[str]:
        """词法分析 - 提取 token.

        保留关键字、标识符、运算符，去除纯空白与注释。
        """
        # 去除注释
        cleaned = re.sub(r"#.*$", "", code, flags=re.MULTILINE)
        cleaned = re.sub(r"//.*$", "", cleaned, flags=re.MULTILINE)

        # 提取 token：标识符、数字、运算符
        token_pattern = r"[A-Za-z_]\w*|\d+|==|!=|<=|>=|&&|\|\||[-+*/%=<>!&|^~]"
        return re.findall(token_pattern, cleaned)

    @staticmethod
    def compute_similarity(vec1: list[float], vec2: list[float]) -> float:
        """计算两个向量的余弦相似度."""
        if len(vec1) != len(vec2) or len(vec1) == 0:
            return 0.0

        dot = sum(a * b for a, b in zip(vec1, vec2, strict=False))
        norm1 = math.sqrt(sum(a * a for a in vec1))
        norm2 = math.sqrt(sum(b * b for b in vec2))

        if norm1 == 0 or norm2 == 0:
            return 0.0

        return dot / (norm1 * norm2)
