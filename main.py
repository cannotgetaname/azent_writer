import tkinter as tk
from ui import AzentWriterUI
from processor import DocumentProcessor
from threading import Thread  # Add this import

class AzentWriter:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Azent Writer")
        
        try:
            print("正在初始化文档处理器...")
            self.processor = DocumentProcessor()
            # 将 processor 设置为 root 的属性
            self.root.processor = self.processor
        except Exception as e:
            error_msg = f"初始化文档处理器失败：\n{str(e)}"
            print(error_msg)
            tk.messagebox.showerror("初始化错误", error_msg)
            self.root.destroy()
            raise RuntimeError(error_msg)
        
        try:
            self.ui = AzentWriterUI(
                self.root,
                on_file_added=self.on_file_added,
                on_process_files=self.on_process_files
            )
            self.ui.on_search = self.on_search
            
            # 更新知识库列表
            self.update_library_list()
            
        except Exception as e:
            error_msg = f"初始化界面失败：\n{str(e)}"
            print(error_msg)
            tk.messagebox.showerror("初始化错误", error_msg)
            self.root.destroy()
            raise RuntimeError(error_msg)
        
        # 设置窗口关闭处理
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # 更新知识库列表
        self.update_library_list()
        
    def on_closing(self):
        """窗口关闭处理"""
        try:
            # 保存知识库
            self.processor._save_knowledge_base()
        except Exception as e:
            print(f"保存知识库失败: {str(e)}")
        self.root.destroy()

    def on_file_added(self, file_path):
        """当UI添加文件时的回调函数"""
        if self.processor.add_document(file_path):
            self.update_library_list()
            preview = self.processor.get_document_preview(file_path)
            self.ui.update_preview(preview)  # 显示初始化预览

    def on_search(self, query):
        """当UI触发知识库查询时的回调函数"""
        try:
            results = self.processor.search_similar(query)
            if results:
                summary = "查询结果:\n\n" + "\n\n---\n\n".join(
                    f"文档: {result['document']}\n"
                    f"相似度: {result['score']:.2f}\n"
                    f"内容: {result['text']}" 
                    for result in results
                )
            else:
                summary = "未找到相关内容"
        except Exception as e:
            summary = f"搜索过程中出错: {str(e)}"
        self.ui.update_preview(summary)

    def update_library_list(self):
        """更新知识库列表显示"""
        docs_info = self.processor.get_loaded_documents_info()
        self.ui.update_library_list(docs_info)

    def on_process_files(self, files, progress_callback=None):
        """当UI触发处理文件时的回调函数"""
        # 先添加所有文件到知识库
        added_files = [f for f in files if self.processor.add_document(f)]
        
        # 处理已添加的文件
        if added_files:
            results = self.processor.process_documents(added_files, progress_callback)
            summary = f"已处理 {len(added_files)} 个文件\n成功: {sum(results)} 个"
        else:
            summary = "没有需要处理的新文件"
            
        self.ui.update_preview(summary)
        self.update_library_list()
        # 强制刷新UI显示
        self.root.update()

    def run(self):
        """启动应用程序"""
        self.root.mainloop()

def main():
    import os
    os.environ['QT_LOGGING_RULES'] = '*.debug=false;qt.qpa.*=false'
    app = AzentWriter()
    app.run()

if __name__ == "__main__":
    main()
