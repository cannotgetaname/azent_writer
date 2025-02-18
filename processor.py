from typing import List, Dict
import os
import json
from sentence_transformers import SentenceTransformer
import faiss
import numpy as np
from typing import Optional, Callable
import hashlib

class DocumentProcessor:
    VERSION = "1.0.0"  # 添加版本号
    
    def __init__(self):
        self.documents = []
        self.knowledge_base = {}
        self.knowledge_base_dir = os.path.join(os.path.dirname(__file__), 'knowledge_base')
        os.makedirs(self.knowledge_base_dir, exist_ok=True)
        self.vector_store = {}
        # 先初始化模型，再加载知识库
        self._model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
        self._load_knowledge_base()

    def _get_safe_filename(self, filename: str) -> str:
        """生成安全的文件名
        
        Args:
            filename: 原始文件名
            
        Returns:
            str: 安全的文件名（使用MD5哈希）
        """
        return hashlib.md5(filename.encode('utf-8')).hexdigest()

    def _load_knowledge_base(self):
        """从本地文件同步加载知识库"""
        knowledge_base_file = os.path.join(self.knowledge_base_dir, 'knowledge_base.json')
        print(f"正在加载知识库文件: {knowledge_base_file}")
        if os.path.exists(knowledge_base_file):
            try:
                with open(knowledge_base_file, 'r', encoding='utf-8') as f:
                    self.knowledge_base = json.load(f)
                    loaded_docs = 0
                    failed_docs = 0
                    skipped_docs = 0
                    
                    # 获取模型预期的向量维度
                    expected_dim = self._model.get_sentence_embedding_dimension()  # 修改这里：self.model -> self._model
                    
                    for doc_path in self.knowledge_base.keys():
                        try:
                            doc_id = os.path.basename(doc_path)
                            # 使用相同的哈希方法获取安全文件名
                            safe_filename = self._get_safe_filename(doc_id)
                            
                            # 检查向量存储文件是否存在
                            vector_file = os.path.join(self.knowledge_base_dir, f"{safe_filename}_vectors.npz")
                            index_file = os.path.join(self.knowledge_base_dir, f"{safe_filename}_index.faiss")
                            
                            if not os.path.exists(vector_file) or not os.path.exists(index_file):
                                print(f"跳过文档 {doc_id}: 向量存储文件不存在")
                                print(f"预期文件路径: {vector_file}")
                                skipped_docs += 1
                                continue
                            
                            # 加载向量数据
                            data = np.load(vector_file, allow_pickle=True)
                            if 'texts' not in data or 'embeddings' not in data:
                                print(f"跳过文档 {doc_id}: 向量存储文件格式错误")
                                skipped_docs += 1
                                continue
                            
                            texts = data['texts'].tolist()
                            embeddings = data['embeddings']
                            
                            # 检查向量维度
                            if embeddings.shape[1] != expected_dim:
                                print(f"跳过文档 {doc_id}: 向量维度不匹配 (期望 {expected_dim}, 实际 {embeddings.shape[1]})")
                                skipped_docs += 1
                                continue
                            
                            # 加载向量索引
                            try:
                                index = faiss.read_index(index_file)
                                # 确保向量被添加到索引中
                                if index.ntotal == 0 and embeddings.shape[0] > 0:
                                    index.add(embeddings)
                                elif index.ntotal != len(texts):
                                    print(f"跳过文档 {doc_id}: 向量索引数量不匹配 (文本数量 {len(texts)}, 索引数量 {index.ntotal})")
                                    skipped_docs += 1
                                    continue
                                    
                                # 初始化向量存储
                                self.vector_store[doc_id] = {
                                    'texts': texts,
                                    'embeddings': embeddings,
                                    'index': index
                                }
                                loaded_docs += 1
                                print(f"成功加载文档: {doc_id}")
                                
                            except Exception as e:
                                print(f"加载文档 {doc_id} 的向量索引失败: {str(e)}")
                                failed_docs += 1
                                continue
                                
                        except Exception as e:
                            print(f"处理文档 {doc_id} 时出错: {str(e)}")
                            failed_docs += 1
                            continue
                    
                    print(f"知识库加载完成: 成功 {loaded_docs} 个, 失败 {failed_docs} 个, 跳过 {skipped_docs} 个")
                    
            except json.JSONDecodeError as e:
                print(f"知识库文件格式错误: {str(e)}")
                self.knowledge_base = {}
            except Exception as e:
                print(f"加载知识库失败: {str(e)}")
                self.knowledge_base = {}
    def get_loaded_documents_info(self) -> List[Dict[str, any]]:
        """获取已加载的知识库文档信息
        
        Returns:
            List[Dict]: 包含文档名称和状态的列表
        """
        loaded_docs = []
        for doc_path in self.knowledge_base.keys():
            doc_id = os.path.basename(doc_path)
            status = "已加载" if doc_id in self.vector_store else "未加载向量"
            loaded_docs.append({
                "name": doc_id,
                "status": status,
                "path": doc_path
            })
        return loaded_docs

    def search_similar(self, query: str, top_k: int = 5) -> List[Dict[str, any]]:
        """搜索与查询最相似的文本片段
        
        Args:
            query: 查询文本
            top_k: 返回的最相似结果数量
            
        Returns:
            List[Dict]: 包含文档名称、相似度分数和文本内容的结果列表
        """
        if not self.vector_store:
            return []
            
        query_vector = self._model.encode([query], convert_to_numpy=True)
        results = []
        
        for doc_id, store in self.vector_store.items():
            if not store['texts'] or not store['index'].ntotal:
                continue
                
            distances, indices = store['index'].search(query_vector, min(top_k, len(store['texts'])))
            for dist, idx in zip(distances[0], indices[0]):
                if idx < len(store['texts']):
                    results.append({
                        'document': doc_id,
                        'text': store['texts'][idx],
                        'score': float(1 / (1 + dist))
                    })
        
        # 按相似度分数排序
        results.sort(key=lambda x: x['score'], reverse=True)
        return results[:top_k]
