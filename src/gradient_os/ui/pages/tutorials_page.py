import os
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QListWidget, QTextBrowser


class TutorialsPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        layout = QVBoxLayout()

        label = QLabel("Tutorials & Docs")
        label.setAlignment(Qt.AlignCenter)
        layout.addWidget(label)

        self.doc_list = QListWidget()
        self.load_docs()
        self.doc_list.itemClicked.connect(self.display_doc)
        layout.addWidget(self.doc_list)

        self.doc_viewer = QTextBrowser()
        layout.addWidget(self.doc_viewer)

        self.setLayout(layout)

    def load_docs(self):
        docs_dir = 'docs'
        if os.path.exists(docs_dir):
            for file in os.listdir(docs_dir):
                if file.endswith('.md'):
                    self.doc_list.addItem(file)

    def display_doc(self, item):
        doc_path = os.path.join('docs', item.text())
        with open(doc_path, 'r') as f:
            content = f.read()
            self.doc_viewer.setMarkdown(content)


