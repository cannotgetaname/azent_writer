import os  # 添加这行导入
import tkinter as tk
from tkinter import ttk, messagebox
from tkinter import filedialog
from typing import Callable, List, Dict
from threading import Thread

class AzentWriterUI:
    def __init__(self, root: tk.Tk, on_file_added: Callable[[str], None], on_process_files: Callable[[list, Callable[[float, str], None]], None]):
        self.root = root
        self.on_file_added = on_file_added
        self.on_process_files = on_process_files
        self.processing = False
        
        # 直接从 root 获取 processor
        if hasattr(root, 'processor'):
            self.processor = root.processor
        else:
            raise RuntimeError("无法获取文档处理器实例")
        
        # 设置窗口大小和布局
        self.root.geometry('800x600')
        self.setup_ui()
    
    def setup_ui(self):
        # 创建主框架
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        
        # 创建按钮区域
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # 添加文件按钮
        add_file_btn = ttk.Button(button_frame, text="添加文件", command=self.add_file)
        add_file_btn.grid(row=0, column=0, padx=(0, 5))
        
        # 处理文件按钮
        process_btn = ttk.Button(button_frame, text="处理文件", command=self.process_files)
        process_btn.grid(row=0, column=1, padx=(0, 5))
        
        # 添加查询框和按钮
        self.query_var = tk.StringVar()
        query_entry = ttk.Entry(button_frame, textvariable=self.query_var, width=30)
        query_entry.grid(row=0, column=2, padx=(0, 5))
        
        search_btn = ttk.Button(button_frame, text="查询", command=self.search_knowledge_base)
        search_btn.grid(row=0, column=3)
        
        # 添加删除向量按钮
        delete_vector_btn = ttk.Button(button_frame, text="删除向量", command=self.delete_vector)
        delete_vector_btn.grid(row=0, column=4, padx=(5, 0))
        
        # 创建进度条
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(main_frame, variable=self.progress_var, maximum=100)
        self.progress_bar.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # 创建预览区域
        preview_frame = ttk.LabelFrame(main_frame, text="预览区域", padding="5")
        preview_frame.grid(row=2, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 修改知识库列表区域
        library_frame = ttk.LabelFrame(main_frame, text="已加载知识库", padding="5")
        library_frame.grid(row=3, column=0, sticky=(tk.W, tk.E), pady=5)
        
        # 创建知识库列表框架
        list_frame = ttk.Frame(library_frame)
        list_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 创建列表框
        self.library_listbox = tk.Listbox(list_frame, height=5, width=80, selectmode=tk.MULTIPLE)
        library_scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.library_listbox.yview)
        self.library_listbox.configure(yscrollcommand=library_scrollbar.set)
        
        self.library_listbox.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        library_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        list_frame.columnconfigure(0, weight=1)
        
        # 继续现有的布局配置
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(2, weight=1)
        
        # 添加预览文本框和滚动条
        self.preview_text = tk.Text(preview_frame, wrap=tk.WORD, width=80, height=20)
        scrollbar = ttk.Scrollbar(preview_frame, orient=tk.VERTICAL, command=self.preview_text.yview)
        self.preview_text.configure(yscrollcommand=scrollbar.set)
        
        self.preview_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        preview_frame.columnconfigure(0, weight=1)
        preview_frame.rowconfigure(0, weight=1)
    
    def add_file(self):
        """打开文件选择对话框并添加文件"""
        file_path = filedialog.askopenfilename(
            title="选择文件",
            filetypes=[
                ("文本文件", "*.txt"),
                ("所有文件", "*.*")
            ]
        )
        if file_path:
            self.on_file_added(file_path)
    
    def process_files(self):
        """触发文件处理"""
        if self.processing:
            tk.messagebox.showwarning("提示", "文件正在处理中，请等待...")
            return
            
        # 获取所有未处理的文件
        files_to_process = []
        for file_path, info in self.processor.knowledge_base.items():
            if not info.get('processed', False):
                files_to_process.append(file_path)
        
        if not files_to_process:
            self.update_preview("没有需要处理的文件")
            return
            
        self.processing = True
        self.progress_var.set(0)
        
        # 禁用按钮
        for widget in self.root.winfo_children():
            if isinstance(widget, ttk.Button):
                widget.configure(state='disabled')
                
        # 启动处理线程
        Thread(target=lambda: self._process_files_thread(files_to_process)).start()
    
    def _process_files_thread(self, files_to_process):
        """在新线程中处理文件"""
        try:
            def update_progress(progress: float, status: str):
                self.progress_var.set(progress)
                self.update_preview(status)
                
            self.on_process_files(files_to_process, update_progress)
            
        except Exception as e:
            self.update_preview(f"处理失败: {str(e)}")
            
        finally:
            self.processing = False
            # 恢复按钮状态
            for widget in self.root.winfo_children():
                if isinstance(widget, ttk.Button):
                    widget.configure(state='normal')
    
    def update_preview(self, content: str):
        """更新预览区域的内容"""
        self.preview_text.delete(1.0, tk.END)
        self.preview_text.insert(tk.END, content)
        
    def search_knowledge_base(self):
        """触发知识库查询"""
        query = self.query_var.get().strip()
        if not query:
            self.update_preview("请输入搜索内容")
            return
            
        if query and hasattr(self, 'on_search') and self.on_search:
            try:
                self.on_search(query)
            except RuntimeError as e:
                self.update_preview(str(e))

    def update_library_list(self, docs_info: List[Dict[str, any]]):
        """更新知识库列表显示"""
        self.library_listbox.delete(0, tk.END)
        for doc in docs_info:
            self.library_listbox.insert(tk.END, f"{doc['name']} - {doc['status']}")
    
    def delete_vector(self):
        """删除选中文档的向量数据"""
        try:
            # 获取选中的项目
            selected_indices = self.library_listbox.curselection()
            if not selected_indices:
                tk.messagebox.showwarning("提示", "请先选择要删除向量的文档")
                return
            
            # 获取选中的文件名
            selected_items = [self.library_listbox.get(idx) for idx in selected_indices]
            
            # 显示确认对话框
            if not tk.messagebox.askyesno("确认", 
                f"确定要删除以下文档的向量数据吗？\n{chr(10).join(selected_items)}\n(原始文件将保留)"):
                return
            
            # 获取文件路径并删除向量
            deleted_indices = []  # 记录要删除的列表项索引
            for idx, item in enumerate(selected_items):
                if " - " in item:  # 文件名格式: "filename - status"
                    filename = item.split(" - ")[0]
                    # 查找完整路径
                    for path in list(self.processor.knowledge_base.keys()):  # 使用list复制keys
                        if os.path.basename(path) == filename:
                            if self.processor.remove_vector_data(path):
                                deleted_indices.append(selected_indices[idx])
                                deleted = True
                            break
            
            if deleted:
                # 从列表框中删除对应项
                for idx in reversed(deleted_indices):  # 从后向前删除
                    self.library_listbox.delete(idx)
                self.update_preview("文档及其向量数据已删除")
                    
        except Exception as e:
            tk.messagebox.showerror("错误", f"删除向量数据失败: {str(e)}")