import sys
import os
import glob
import shutil
from PyQt5.QtWidgets import QApplication, QMainWindow, QLabel, QVBoxLayout, QWidget, QGridLayout, QScrollArea, QDialog, QHBoxLayout, QTextEdit, QTreeView, QFileSystemModel, QMenu
from PyQt5.QtGui import QPixmap, QDrag
from PyQt5.QtCore import Qt, pyqtSignal, QDir, QMimeData, QUrl
from PyQt5.QtWidgets import QFileDialog

from PIL import Image
from PIL.ExifTags import TAGS
import mod_sdiffusion
from qss import *

sd = mod_sdiffusion.SDChunk()

OPTION_SHOW_IMAGE = True
IMAGE_ROOT_PATH = 'image'
__FocusFolder = None

def sanitize_path(path):
    # 実行フォルダ内のパスに制限
    base_path = os.path.abspath(os.getcwd())
    full_path = os.path.abspath(os.path.join(base_path, path))
    if not full_path.startswith(base_path):
        raise ValueError("Invalid path")
    return full_path

def qt_copy_image_to_clipboard(image_path):
    # クリップボードに画像をコピーする
    mime_data = QMimeData()
    mime_data.setUrls([QUrl.fromLocalFile(image_path)])
    clipboard = QApplication.clipboard()
    clipboard.setMimeData(mime_data)


class ClickableLabel(QLabel):
    clicked = pyqtSignal(str)  # クリックされたときに画像のパスを送信するシグナル

    def __init__(self, image_path, parent=None):
        super().__init__(parent)
        self.image_path = image_path

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self.image_path)  # 画像のパスをシグナルに渡す
        elif event.button() == Qt.RightButton:
            self.show_context_menu(event.pos())

    def show_context_menu(self, pos):
        menu = QMenu(self)
        copy_action = menu.addAction("Copy")
        delete_action = menu.addAction("Delete")
        action = menu.exec_(self.mapToGlobal(pos))
        if action == copy_action:
            mime_data = QMimeData()
            url = QUrl.fromLocalFile(self.image_path)
            mime_data.setUrls([url])
            clipboard = QApplication.clipboard()
            clipboard.setMimeData(mime_data)
        elif action == delete_action:
            os.remove(self.image_path)
            self.setParent(None)
            self.parent().parent().parent().display_images(sanitize_path(IMAGE_ROOT_PATH))
            os.remove(self.image_path)
            self.setParent(None)

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton:
            drag = QDrag(self)
            mime_data = QMimeData()
            mime_data.setText(self.image_path)
            drag.setMimeData(mime_data)
            drag.exec_(Qt.MoveAction)

class ImageInfoWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout()
        self.image_label = QLabel()
        self.image_label.setFixedSize(300, 300)  # 表示サイズを幅300高さ300に設定
        self.info_label = QTextEdit()
        self.info_label.setReadOnly(True)
        self.info_label.setAcceptRichText(True)  # HTML形式のテキストを受け入れるように設定
        self.layout.addWidget(self.image_label)
        self.layout.addWidget(self.info_label)
        self.setLayout(self.layout)

    def display_image_info(self, image_path):
        pixmap = QPixmap(image_path)
        if OPTION_SHOW_IMAGE:
            scaled_pixmap = pixmap.scaled(300, 300, Qt.KeepAspectRatio)
            self.image_label.setPixmap(scaled_pixmap)
        info_text = f"Image Path: {image_path}\nSize: {pixmap.width()} x {pixmap.height()}"
        info_text = info_text.replace("\n", "<br>")  # 改行文字を <br> に置き換え
        self.info_label.setHtml(info_text)  # HTML形式でテキストを設定

        # メタデータの表示
        if image_path.lower().endswith('.jpg') or image_path.lower().endswith('.jpeg'):
            image = Image.open(image_path)
            exif_data = image._getexif()
            if exif_data:
                metadata = {TAGS.get(tag): value for tag, value in exif_data.items()}
                parameters = metadata.get('UserComment', 'No parameters found')
                self.info_label.append(f"Parameters: {parameters}")
        elif image_path.lower().endswith('.png'):
            meta_dat = sd.create_data({'path':image_path}, 'image')
            if meta_dat:
                self.info_label.append(f"Prompt: \n{meta_dat['data']['prompt']}")
                self.info_label.append(f"Negative: \n{meta_dat['data']['negative']}")
                self.info_label.append(f"Options: \n{meta_dat['data']['options']}")

class ImageManager(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle('Simple AImage Manager')
        self.setGeometry(100, 100, 1600, 900)  # ウィンドウのサイズを維持

        main_layout = QHBoxLayout()

        # 左側のフォルダツリー表示エリア
        global __FocusFolder
        __FocusFolder = sanitize_path('.')
        print('FocusFolder:', __FocusFolder)
        self.folder_model = QFileSystemModel()
        self.folder_model.setRootPath(__FocusFolder)
        self.folder_view = QTreeView()
        self.folder_view.setModel(self.folder_model)
        self.folder_view.setRootIndex(self.folder_model.index(__FocusFolder))
        self.folder_view.setDragEnabled(True)
        self.folder_view.setAcceptDrops(True)
        self.folder_view.setDropIndicatorShown(True)
        self.folder_view.clicked.connect(self.on_folder_clicked)
        self.folder_view.setContextMenuPolicy(Qt.CustomContextMenu)
        self.folder_view.customContextMenuRequested.connect(self.show_folder_context_menu)
        main_layout.addWidget(self.folder_view, 1)  # 左側（フォルダツリー）の幅を設定

        # 中央のスクロールエリア
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        self.image_widget = QWidget()
        self.layout = QGridLayout(self.image_widget)
        scroll_area.setWidget(self.image_widget)
        main_layout.addWidget(scroll_area, 2)  # 中央（画像表示）の幅を設定

        # 右側の画像情報表示エリア
        self.info_widget = ImageInfoWidget()
        main_layout.addWidget(self.info_widget, 1)  # 右側（情報表示）の幅を設定

        container = QWidget()
        container.setLayout(main_layout)
        self.setCentralWidget(container)

        apply_styles(container)

        self.setAcceptDrops(True)  # ウィンドウ全体でドロップを受け付けるように設定

        # QTreeViewに対してイベントを設定
        self.folder_view.dragEnterEvent = self.dragEnterEvent
        self.folder_view.dragMoveEvent = self.dragMoveEvent
        self.folder_view.dropEvent = self.dropEvent


    def on_folder_clicked(self, index):
        folder_path = self.folder_model.filePath(index)
        # 画像がクリックされた場合
        if any(folder_path.lower().endswith(ext) for ext in ('.png', '.jpg', '.jpeg')):
            for i in range(self.layout.count()):
                widget = self.layout.itemAt(i).widget()
                # sanitize_pathでパスを正規化しなければ、「/」「\\」で区切られたパスが異なる場合に正しく比較できない
                if isinstance(widget, ClickableLabel) and sanitize_path(widget.image_path) == sanitize_path(folder_path):
                    # widget.setStyleSheet("border: 2px solid blue;")
                    self.show_image_info(folder_path)
                    return
            return
        # png, jpg, jpeg 以外のファイルがクリックされた場合
        if not os.path.isdir(folder_path):
            return
        # フォルダがクリックされた場合
        self.display_images(sanitize_path(folder_path))

    def display_images(self, folder_path):
        image_files = []
        for root, dirs, files in os.walk(folder_path):
            for file in files:
                if file.lower().endswith(('.png', '.jpg', '.jpeg')):
                    image_files.append(os.path.join(root, file))

        row = 0
        col = 0
        fixed_width = 200
        fixed_height = 300

        # 既存の画像をクリア
        for i in reversed(range(self.layout.count())):
            widget = self.layout.itemAt(i).widget()
            if widget is not None:
                widget.setParent(None)

        for image_file in image_files:
            pixmap = QPixmap(image_file)
            scaled_pixmap = pixmap.scaled(fixed_width, fixed_height, Qt.KeepAspectRatio)
            image_label = ClickableLabel(image_file)
            image_label.setPixmap(scaled_pixmap)
            image_label.setFixedSize(fixed_width, fixed_height)
            image_label.setScaledContents(True)
            image_label.clicked.connect(self.show_image_info)
            self.layout.addWidget(image_label, row, col)
            col += 1
            if col > 2:
                col = 0
                row += 1

    def show_image_info(self, image_path):
        self.info_widget.display_image_info(image_path)

    def create_treeview_context_menu(self, menu, index):
        add_actions = []
        if index.isValid():
            # ファイルを右クリックした場合
            add_actions.append(menu.addAction("Copy Image"))
            add_actions.append(menu.addAction("Delete Image"))
        else:
            # 全体を右クリックした場合
            add_actions.append(menu.addAction("Add Image"))
        return add_actions

    def show_folder_context_menu(self, pos):
        index = self.folder_view.indexAt(pos)
        menu = QMenu(self)

        add_actions = self.create_treeview_context_menu(menu, index)

        action = menu.exec_(self.folder_view.viewport().mapToGlobal(pos))
        # add_actions を走査して action がどのアクションかを判定
        for add_action in add_actions:
            if add_action == action and add_action.text() == "Add Image":
                # フォルダに画像を追加する
                if not index.isValid():
                    index = self.folder_view.rootIndex()
                folder_path = self.folder_model.filePath(index)
                self.add_image_to_folder(folder_path)
            elif add_action == action and add_action.text() == "Copy Image":
                # クリップボードに画像をコピーする
                print('Copy Image:', self.folder_model.filePath(index))
                qt_copy_image_to_clipboard(self.folder_model.filePath(index))
            elif add_action == action and add_action.text() == "Delete Image":
                # ここに画像を削除する処理を実装
                print('Delete Image:', self.folder_model.filePath(index))
                os.remove(self.folder_model.filePath(index))

    def add_image_to_folder(self, folder_path):
        # ここに画像ファイルを追加する処理を実装
        options = QFileDialog.Options()
        file_path, _ = QFileDialog.getOpenFileName(self, "Select Image to Add", "", "Images (*.jpg *.jpeg *.png)", options=options)
        if file_path:
            destination_path = os.path.join(folder_path, os.path.basename(file_path))
            with open(file_path, 'rb') as src_file:
                with open(destination_path, 'wb') as dst_file:
                    dst_file.write(src_file.read())
            print(f'Added {file_path} to {folder_path}')
        print('add_image_to_folder:', folder_path)

    def dragEnterEvent(self, event):
        print('dragEnterEvent')
        if event.mimeData().hasUrls():  # URL形式のデータも受け付ける
            event.acceptProposedAction()

    def dragMoveEvent(self, event):
        print('dragMoveEvent')
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        print('dropEvent')
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                file_path = url.toLocalFile()
                print('Dropped file:', file_path)
                # ここにファイルをフォルダに追加する処理を実装
                global __FocusFolder
                if os.path.isdir(__FocusFolder):
                    destination_path = os.path.join(__FocusFolder, os.path.basename(file_path))
                    if os.path.isfile(file_path):
                        with open(file_path, 'rb') as src_file:
                            with open(destination_path, 'wb') as dst_file:
                                dst_file.write(src_file.read())
                        print(f'Copied {file_path} to {destination_path}')
            event.acceptProposedAction()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = ImageManager()
    window.show()

    window.display_images(sanitize_path(IMAGE_ROOT_PATH))

    sys.exit(app.exec_())
