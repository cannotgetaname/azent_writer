# Azent Writer

一个基于向量数据库的本地知识库管理工具。

## 功能特点

- 支持多种文本文件格式
- 自动编码检测（支持 UTF-8、GBK、GB2312、GB18030、UTF-16）
- 智能文本分块处理
- 基于 FAISS 的向量化存储和检索
- 高效的相似度搜索
- 本地知识库管理
- 文档预览功能
- 批量文档处理
- 实时处理进度显示

## 技术栈

- Python 3.10+
- sentence-transformers (文本向量化)
- FAISS (向量索引和搜索)
- NumPy (数值计算)
- Tkinter (图形界面)

## 使用说明

1. 安装依赖
```bash
pip install -r requirements.txt