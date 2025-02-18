import tkinter as tk
from ui import AzentWriterUI
from processor import DocumentProcessor
from threading import Thread  # Add this import

class AzentWriter:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Azent Writer")
        self.processor = DocumentProcessor()
        self.ui = AzentWriterUI(self.root, 
                               on_file_added=self.on_file_added,
                               on_process_files=self.on_process_files)
        self.ui.on_search = self.on_search
        
        # 直接更新知识库列表
        self.update_library_list()

    def on_file_added(self, file_path):
        """当UI添加文件时的回调函数"""
        if self.processor.add_document(file_path):
            preview = self.processor.get_document_preview(file_path)
            self.ui.update_preview(preview)

    def on_search(self, query):
        """当UI触发知识库查询时的回调函数
        
        Args:
            query: 查询文本
        """
        results = self.processor.search_similar(query)
        if results:
            summary = "查询结果:\n" + "\n\n".join(
                f"文档: {result['document']}\n相似度: {result['score']:.2f}\n内容: {result['text']}" 
                for result in results
            )
        else:
            summary = "未找到相关内容"
        self.ui.update_preview(summary)

    def update_library_list(self):
        """更新知识库列表显示"""
        docs_info = self.processor.get_loaded_documents_info()
        self.ui.update_library_list(docs_info)

    def on_process_files(self, files, progress_callback=None):
        """当UI触发处理文件时的回调函数"""
        results = self.processor.process_documents(progress_callback)
        summary = "处理结果:\n" + "\n".join(
            f"{file}: {'成功' if isinstance(result, str) else '失败'}" 
            for file, result in results.items()
        )
        self.ui.update_preview(summary)
        self.update_library_list()  # 添加这行

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