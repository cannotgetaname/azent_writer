from typing import List, Dict, Optional, Callable
import os
import json
import time
import re
import hashlib
import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

class DocumentProcessor:
    VERSION = "1.0.0"
    
    def __init__(self):
        try:
            # 初始化基本属性
            self.documents = []
            self.knowledge_base = {}
            self.vector_store = {}
            
            # 加载配置文件
            self.config = self._load_config()
            if not self.config:
                raise ValueError("无法加载配置文件")
                
            # 设置知识库目录
            self.knowledge_base_dir = os.path.join(os.path.dirname(__file__), 
                                                 self.config.get('knowledge_base_dir', 'knowledge_base'))
            os.makedirs(self.knowledge_base_dir, exist_ok=True)
            
            # 初始化模型
            try:
                model_name = self.config.get('model', 'paraphrase-multilingual-MiniLM-L12-v2')
                print(f"正在加载模型: {model_name}")
                self._model = SentenceTransformer(model_name)
            except Exception as e:
                raise RuntimeError(f"模型加载失败: {str(e)}")
                
            # 加载知识库
            self._load_knowledge_base()
            
            # 设置文本处理参数
            self.max_chunk_size = self.config.get('max_chunk_size', 512)
            self.min_chunk_size = self.config.get('min_chunk_size', 100)
            self.chunk_overlap = self.config.get('chunk_overlap', 50)
            
            print("文档处理器初始化完成")
            
        except Exception as e:
            print(f"初始化文档处理器失败: {str(e)}")
            raise

    def _load_config(self) -> dict:
        """加载配置文件"""
        try:
            config_path = os.path.join(os.path.dirname(__file__), 'config.json')
            if not os.path.exists(config_path):
                print(f"配置文件不存在: {config_path}")
                return {}
                
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
                print(f"成功加载配置文件: {config_path}")
                return config
                
        except json.JSONDecodeError as e:
            print(f"配置文件格式错误: {str(e)}")
            return {}
        except Exception as e:
            print(f"加载配置文件失败: {str(e)}")
            return {}

    def _process_single_document(self, file_path: str) -> bool:
        try:
            normalized_path = os.path.normpath(file_path)
            doc_id = hashlib.md5(normalized_path.encode('utf-8')).hexdigest()
            
            # 文件读取和编码检测
            content = self._read_file_with_encoding(normalized_path)
            if content is None:
                return False
                
            # 文本分块处理
            texts = self._split_text(content)
            if not texts:
                print(f"文件内容分块失败: {normalized_path}")
                return False
                
            # 生成向量
            embeddings = self._generate_embeddings(texts, normalized_path)
            if embeddings is None:
                return False
                
            # 保存处理结果
            if not self._save_document_data(doc_id, normalized_path, texts, embeddings):
                return False
                
            return True
            
        except Exception as e:
            print(f"处理文档失败: {str(e)}")
            return False

    def _read_file_with_encoding(self, file_path: str) -> Optional[str]:
        """读取文件并自动检测编码"""
        try:
            with open(file_path, 'rb') as f:
                raw_data = f.read()
                for encoding in self.config.get('encodings', ['utf-8', 'gbk', 'gb2312', 'gb18030', 'utf-16']):
                    try:
                        return raw_data.decode(encoding)
                    except UnicodeDecodeError:
                        continue
            print(f"文件编码无法识别: {file_path}")
            return None
        except Exception as e:
            print(f"文件读取失败: {str(e)}")
            return None

    def _split_text(self, content: str) -> List[str]:
        """将文本分割成小块"""
        max_chunk_size = self.config.get('max_chunk_size', 512)
        min_chunk_size = self.config.get('min_chunk_size', 100)
        
        # 分段
        paragraphs = re.split(r'\n{2,}|\r\n{2,}', content.strip())
        if not paragraphs:
            return []
            
        texts = []
        current_chunk = []
        current_size = 0
        
        for para in paragraphs:
            para = para.strip()
            if not para:
                continue
                
            # 分句处理长段落
            if len(para) > max_chunk_size:
                sentences = re.split(r'([。！？.!?])', para)
                sentences = [''.join(i) for i in zip(sentences[::2], sentences[1::2] + [''])]
            else:
                sentences = [para]
                
            for sentence in sentences:
                sentence = sentence.strip()
                if not sentence:
                    continue
                    
                # 检查是否需要开始新的块
                if current_size + len(sentence) > max_chunk_size and current_chunk:
                    texts.append('\n'.join(current_chunk))
                    current_chunk = []
                    current_size = 0
                    
                current_chunk.append(sentence)
                current_size += len(sentence)
                
        # 处理剩余内容
        if current_chunk and current_size >= min_chunk_size:
            texts.append('\n'.join(current_chunk))
            
        return texts

    def _generate_embeddings(self, texts: List[str], file_path: str) -> Optional[np.ndarray]:
        """生成文本向量"""
        try:
            print(f"正在为 {len(texts)} 个文本块生成嵌入向量...")
            embeddings = self._model.encode(texts, convert_to_numpy=True)
            
            if embeddings.shape[0] != len(texts):
                print(f"嵌入向量生成异常: 预期 {len(texts)} 个向量，实际生成 {embeddings.shape[0]} 个")
                return None
                
            print(f"成功生成 {embeddings.shape[0]} 个嵌入向量，维度 {embeddings.shape[1]}")
            return embeddings
            
        except Exception as e:
            print(f"嵌入向量生成失败[{file_path}]: {str(e)}")
            return None

    def _save_document_data(self, doc_id: str, file_path: str, texts: List[str], embeddings: np.ndarray) -> bool:
        """保存文档数据"""
        try:
            # 创建FAISS索引
            index = faiss.IndexFlatL2(self._model.get_sentence_embedding_dimension())
            if embeddings.shape[0] > 0:
                index.add(embeddings)
                
            # 保存向量数据
            safe_filename = self._get_safe_filename(doc_id)
            vector_file = os.path.join(self.knowledge_base_dir, f"{safe_filename}_vectors.npz")
            np.savez(vector_file, texts=texts, embeddings=embeddings)
            
            # 保存FAISS索引
            index_file = os.path.join(self.knowledge_base_dir, f"{safe_filename}_index.faiss")
            faiss.write_index(index, index_file)
            
            # 更新知识库状态
            self.knowledge_base[file_path]["processed"] = True
            self.knowledge_base[file_path]["preview"] = texts[0] if texts else ""
            self._save_knowledge_base()
            
            # 更新内存存储
            self.vector_store[doc_id] = {
                'texts': texts,
                'embeddings': embeddings,
                'index': index
            }
            
            return True
            
        except Exception as e:
            print(f"保存文档数据失败: {str(e)}")
            return False

    def add_document(self, file_path: str) -> bool:
        normalized_path = os.path.normpath(file_path)
        
        if not os.path.exists(normalized_path):
            print(f"文件不存在: {normalized_path}")
            return False

        try:
            doc_id = hashlib.md5(normalized_path.encode('utf-8')).hexdigest()
            self.knowledge_base[normalized_path] = {
                "doc_id": doc_id,
                "timestamp": os.path.getmtime(file_path),
                "processed": False,
                "preview": "点击处理按钮生成预览"
            }
            self._save_knowledge_base()
            return True
        except Exception as e:
            print(f"添加文档失败: {str(e)}")
            return False

    def _load_knowledge_base(self):
        """从本地文件加载知识库"""
        try:
            knowledge_base_file = os.path.join(self.knowledge_base_dir, 'knowledge_base.json')
            if os.path.exists(knowledge_base_file):
                with open(knowledge_base_file, 'r', encoding='utf-8') as f:
                    self.knowledge_base = json.load(f)
                print(f"已加载知识库文件: {knowledge_base_file}")
                
                # 加载已处理文档的向量数据
                for file_path, info in self.knowledge_base.items():
                    if info.get('processed', False):
                        doc_id = info['doc_id']
                        safe_filename = self._get_safe_filename(doc_id)
                        
                        try:
                            # 加载向量数据
                            vector_file = os.path.join(self.knowledge_base_dir, f"{safe_filename}_vectors.npz")
                            if os.path.exists(vector_file):
                                data = np.load(vector_file, allow_pickle=True)
                                texts = data['texts'].tolist()
                                embeddings = data['embeddings']
                                
                                # 加载FAISS索引
                                index_file = os.path.join(self.knowledge_base_dir, f"{safe_filename}_index.faiss")
                                if os.path.exists(index_file):
                                    index = faiss.read_index(index_file)
                                    
                                    # 存储到内存
                                    self.vector_store[doc_id] = {
                                        'texts': texts,
                                        'embeddings': embeddings,
                                        'index': index
                                    }
                                    print(f"已加载文档向量: {os.path.basename(file_path)}")
                        except Exception as e:
                            print(f"加载文档向量失败[{file_path}]: {str(e)}")
                            continue
            else:
                print("知识库文件不存在，将创建新的知识库")
                self.knowledge_base = {}
        except Exception as e:
            print(f"加载知识库时出错: {str(e)}")
            self.knowledge_base = {}

    def _save_knowledge_base(self):
        """保存知识库到本地文件"""
        try:
            knowledge_base_file = os.path.join(self.knowledge_base_dir, 'knowledge_base.json')
            with open(knowledge_base_file, 'w', encoding='utf-8') as f:
                json.dump(self.knowledge_base, f, ensure_ascii=False, indent=2)
            print(f"已保存知识库文件: {knowledge_base_file}")
        except Exception as e:
            print(f"保存知识库时出错: {str(e)}")

    def _get_safe_filename(self, doc_id: str) -> str:
        """生成安全的文件名
        
        Args:
            doc_id: 文档ID
            
        Returns:
            str: 安全的文件名
        """
        return re.sub(r'[<>:"/\\|?*]', '_', doc_id)

    def search_similar(self, query: str, top_k: int = None) -> List[Dict[str, any]]:
        """搜索相似内容
        
        Args:
            query: 查询文本
            top_k: 返回结果数量，默认使用配置文件中的设置
            
        Returns:
            List[Dict]: 搜索结果列表
        """
        try:
            if not self.vector_store:
                raise RuntimeError("知识库为空，请先添加并处理文档")
                
            if top_k is None:
                top_k = self.config.get('search_settings', {}).get('top_k', 5)
                
            results = []
            min_score = self.config.get('search_settings', {}).get('min_score', 0.01)
            seen_texts = set()  # 用于去重
                
            # 生成查询向量
            query_vector = self._model.encode([query], convert_to_numpy=True)
            print(f"查询向量维度: {query_vector.shape}")
            print(f"知识库文档数量: {len(self.knowledge_base)}")
            print(f"向量存储数量: {len(self.vector_store)}")
            
            # 创建哈希值到原始文件路径的映射
            doc_id_to_path = {info['doc_id']: path for path, info in self.knowledge_base.items()}
            
            # 在所有文档中搜索
            for doc_id, doc_data in self.vector_store.items():
                # 获取原始文件路径
                original_path = doc_id_to_path.get(doc_id, '')
                
                # 获取当前文档的FAISS索引
                doc_index = doc_data['index']
                local_top_k = min(top_k, doc_index.ntotal)
                
                if local_top_k == 0:
                    continue
                    
                # 在当前文档中搜索
                D, I = doc_index.search(query_vector, local_top_k)
                
                # 添加结果（带去重）
                for score, idx in zip(D[0], I[0]):
                    text = doc_data['texts'][idx]
                    if text in seen_texts:
                        continue
                    seen_texts.add(text)
                    
                    # 修改相似度计算方法
                    normalized_score = 1 / (1 + np.sqrt(score))  # 使用平方根来调整分数分布
                    if normalized_score < min_score:
                        continue
                    
                    results.append({
                        'document': os.path.basename(original_path),  # 使用原始文件名
                        'text': text,
                        'score': round(normalized_score * 100, 2)
                    })
            
            # 按相似度排序并限制返回数量
            results.sort(key=lambda x: x['score'], reverse=True)
            return results[:top_k]
            
        except Exception as e:
            print(f"搜索失败: {str(e)}")
            raise RuntimeError(f"搜索失败: {str(e)}")

    def process_documents(self, file_paths: list, progress_callback: Callable[[float, str], None] = None) -> List[bool]:
        """处理多个文档
        
        Args:
            file_paths: 文档路径列表
            progress_callback: 进度回调函数
            
        Returns:
            List[bool]: 处理结果列表
        """
        results = []
        total = len(file_paths)
        
        for idx, file_path in enumerate(file_paths, 1):
            try:
                normalized_path = os.path.normpath(file_path)
                
                # 仅处理未处理的文档
                if not self.knowledge_base.get(normalized_path, {}).get("processed", False):
                    success = self._process_single_document(normalized_path)
                    results.append(success)
                    
                    # 更新预览
                    if success:
                        self.knowledge_base[normalized_path]["preview"] = self._read_preview_content(normalized_path)
                        self._save_knowledge_base()
                    
                # 更新进度
                if progress_callback:
                    progress = (idx / total) * 100
                    status = f"正在处理: {os.path.basename(normalized_path)}"
                    progress_callback(progress, status)
                
            except Exception as e:
                print(f"处理文件失败 {file_path}: {str(e)}")
                results.append(False)
                if progress_callback:
                    progress_callback((idx / total) * 100, f"处理失败: {str(e)}")
        
        # 完成处理
        if progress_callback:
            progress_callback(100.0, "处理完成！")
        
        return results

    def get_loaded_documents_info(self) -> List[Dict[str, str]]:
        """获取已加载文档的信息列表
        
        Returns:
            List[Dict[str, str]]: 包含文档信息的列表，每个文档包含 name 和 status
        """
        docs_info = []
        for file_path, info in self.knowledge_base.items():
            docs_info.append({
                'name': os.path.basename(file_path),
                'status': '已处理' if info.get('processed', False) else '未处理'
            })
        return docs_info

    def get_document_preview(self, file_path: str) -> str:
        """获取文档的预览内容
        
        Args:
            file_path: 文档路径
            
        Returns:
            str: 预览内容
        """
        normalized_path = os.path.normpath(file_path)
        if normalized_path in self.knowledge_base:
            return self.knowledge_base[normalized_path].get('preview', '暂无预览')
        return '文档未找到'

    def _read_preview_content(self, file_path: str) -> str:
        """读取文档的预览内容
        
        Args:
            file_path: 文档路径
            
        Returns:
            str: 预览内容
        """
        try:
            content = self._read_file_with_encoding(file_path)
            if content:
                # 返回前500个字符作为预览
                return content[:500] + ('...' if len(content) > 500 else '')
            return '无法读取文件内容'
        except Exception as e:
            return f'读取预览失败: {str(e)}'
