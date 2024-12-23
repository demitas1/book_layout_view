import sys
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                           QHBoxLayout, QLabel, QScrollArea, QMenuBar, QMenu, 
                           QFileDialog, QFrame, QSizePolicy, QGridLayout,
                           QInputDialog, QSpacerItem, QMessageBox)
from PyQt6.QtCore import Qt, QMimeData, QSize, QTimer
from PyQt6.QtGui import QPixmap, QClipboard, QAction, QContextMenuEvent
import os
import math
import json

class PageNumberLabel(QLabel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setMinimumHeight(20)  # 番号表示用の最小高さを確保
        self.setVisible(True)

class PageWidget(QWidget):
    def __init__(self, page_width=300, page_number=1, parent=None):
        super().__init__(parent)
        self.page_number = page_number

        # メインレイアウト
        self.layout = QVBoxLayout(self)
        self.layout.setSpacing(0)
        self.layout.setContentsMargins(0, 0, 0, 0)

        # 画像表示用のラベル
        self.image_label = QLabel()
        self.image_label.setFrameStyle(QFrame.Shape.Box)
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.layout.addWidget(self.image_label)

        # ページ番号ラベル
        self.number_label = PageNumberLabel()
        self.layout.addWidget(self.number_label)

        self.image_path = ""
        self.page_width = page_width
        self.update_size()
        self.update_page_number(page_number)

    def update_size(self):
        self.height = int(self.page_width * 1.414)
        self.image_label.setFixedSize(self.page_width, self.height)
        if self.image_path:
            self.load_image(self.image_path)

    def update_page_number(self, number, visible=True):
        self.page_number = number
        self.number_label.setText(str(number))
        self.number_label.setVisible(visible)

    def load_image(self, image_path):
        self.image_path = image_path
        if image_path:
            pixmap = QPixmap(image_path)
            page_aspect = self.page_width / self.height
            image_aspect = pixmap.width() / pixmap.height()

            if image_aspect > page_aspect:
                scaled_width = self.page_width
                scaled_height = int(self.page_width / image_aspect)
            else:
                scaled_height = self.height
                scaled_width = int(self.height * image_aspect)

            scaled_pixmap = pixmap.scaled(scaled_width, scaled_height,
                                        Qt.AspectRatioMode.KeepAspectRatio,
                                        Qt.TransformationMode.SmoothTransformation)
            self.image_label.setPixmap(scaled_pixmap)
        else:
            self.image_label.clear()
            self.image_path = ""

    def contextMenuEvent(self, event: QContextMenuEvent):
        menu = QMenu(self)

        load_action = QAction("画像の読み込み", self)
        load_action.triggered.connect(self.load_image_from_dialog)
        menu.addAction(load_action)

        # ページ挿入用のセパレータを追加
        menu.addSeparator()

        # 前にページを挿入するアクション
        insert_before_action = QAction("前に新規ページを挿入", self)
        insert_before_action.triggered.connect(lambda: self.window().insert_new_page_before(self))
        menu.addAction(insert_before_action)

        # 後にページを挿入するアクション
        insert_after_action = QAction("後に新規ページを挿入", self)
        insert_after_action.triggered.connect(lambda: self.window().insert_new_page_after(self))
        menu.addAction(insert_after_action)

        # 既存の画像パスコピー機能
        if self.image_path:
            menu.addSeparator()
            copy_path_action = QAction("画像のパス", self)
            copy_path_action.triggered.connect(self.copy_image_path)
            menu.addAction(copy_path_action)

        menu.exec(event.globalPos())

    def load_image_from_dialog(self):
        file_name, _ = QFileDialog.getOpenFileName(
            self,
            "画像を選択",
            "",
            "Images (*.png *.jpg *.jpeg *.bmp *.gif)"
        )
        if file_name:
            self.load_image(file_name)

    def copy_image_path(self):
        if self.image_path:
            clipboard = QApplication.clipboard()
            clipboard.setText(self.image_path)

class SpreadWidget(QWidget):
    def __init__(self, page_width=300, start_number=1, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout()
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(10)

        self.left_page = PageWidget(page_width, start_number)
        self.right_page = PageWidget(page_width, start_number + 1)

        layout.addWidget(self.left_page)
        layout.addWidget(self.right_page)
        self.setLayout(layout)

    def update_page_size(self, width):
        self.left_page.page_width = width
        self.right_page.page_width = width
        self.left_page.update_size()
        self.right_page.update_size()

    def update_page_numbers(self, start_number, visible=True):
        self.left_page.update_page_number(start_number, visible)
        self.right_page.update_page_number(start_number + 1, visible)

    def get_page_index(self, page):
        """指定されたページが左か右かを返す"""
        if page == self.left_page:
            return 0
        elif page == self.right_page:
            return 1
        return -1

class BookLayoutApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Book Layout Manager")
        self.setGeometry(100, 100, 1200, 800)

        self.current_page_width = 300
        self.spreads = []
        self.page_number_start = 1
        self.show_page_numbers = True

        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        self.main_layout = QVBoxLayout(main_widget)

        self.scroll_area = QScrollArea()
        self.scroll_widget = QWidget()
        self.grid_layout = QGridLayout(self.scroll_widget)
        self.grid_layout.setSpacing(20)
        self.scroll_area.setWidget(self.scroll_widget)
        self.scroll_area.setWidgetResizable(True)
        self.main_layout.addWidget(self.scroll_area)

        self.create_menu_bar()
        self.add_new_spread()

        self.resize_timer = QTimer()
        self.resize_timer.setSingleShot(True)
        self.resize_timer.timeout.connect(self.reorganize_layout)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.resize_timer.start(100)

    def reorganize_layout(self):
        while self.grid_layout.count():
            item = self.grid_layout.takeAt(0)
            if item.widget():
                self.grid_layout.removeWidget(item.widget())

        available_width = self.scroll_area.viewport().width()
        spread_width = (self.current_page_width * 2) + 30

        spreads_per_row = max(1, math.floor((available_width + 20) / (spread_width + 20)))

        for i, spread in enumerate(self.spreads):
            row = i // spreads_per_row
            col = i % spreads_per_row
            self.grid_layout.addWidget(spread, row, col)

    def create_menu_bar(self):
        menubar = self.menuBar()

        # ファイルメニュー
        file_menu = menubar.addMenu("ファイル")

        new_book_action = file_menu.addAction("Book新規作成")
        new_book_action.triggered.connect(self.new_book)

        file_menu.addSeparator()

        save_book_action = file_menu.addAction("Bookファイルの保存")
        save_book_action.triggered.connect(self.save_book)

        load_book_action = file_menu.addAction("Bookファイルを開く")
        load_book_action.triggered.connect(self.load_book)

        file_menu.addSeparator()

        new_spread_action = file_menu.addAction("新規ページの作成")
        new_spread_action.triggered.connect(self.add_new_spread)

        file_menu.addSeparator()

        # ページ番号関連のメニュー項目
        toggle_numbers_action = file_menu.addAction("ページ番号の表示切替")
        toggle_numbers_action.setCheckable(True)
        toggle_numbers_action.setChecked(True)
        toggle_numbers_action.triggered.connect(self.toggle_page_numbers)

        set_start_number_action = file_menu.addAction("ページ番号の開始を設定")
        set_start_number_action.triggered.connect(self.set_start_page_number)

        # 表示メニュー
        view_menu = menubar.addMenu("表示")

        zoom_in_action = view_menu.addAction("拡大")
        zoom_in_action.triggered.connect(self.zoom_in)

        zoom_out_action = view_menu.addAction("縮小")
        zoom_out_action.triggered.connect(self.zoom_out)

    def add_new_spread(self):
        start_number = self.page_number_start + (len(self.spreads) * 2)
        spread = SpreadWidget(self.current_page_width, start_number)
        spread.update_page_numbers(start_number, self.show_page_numbers)
        self.spreads.append(spread)
        self.reorganize_layout()

    def toggle_page_numbers(self, checked):
        self.show_page_numbers = checked
        self.update_all_page_numbers()

    def set_start_page_number(self):
        number, ok = QInputDialog.getInt(
            self,
            "開始ページ番号の設定",
            "開始ページ番号を入力してください：",
            value=self.page_number_start,
            min=-99999,
            max=99999
        )
        if ok:
            self.page_number_start = number
            self.update_all_page_numbers()

    def update_all_page_numbers(self):
        for i, spread in enumerate(self.spreads):
            start_number = self.page_number_start + (i * 2)
            spread.update_page_numbers(start_number, self.show_page_numbers)

    def find_spread_and_page(self, target_page):
        """指定されたページを含むスプレッドとそのインデックスを検索"""
        for i, spread in enumerate(self.spreads):
            if target_page in [spread.left_page, spread.right_page]:
                return i, spread
        return -1, None

    def swap_with_prev_page(self, current_page):
        spread_idx, spread = self.find_spread_and_page(current_page)
        if spread_idx == -1:
            return

        page_idx = spread.get_page_index(current_page)

        # 左ページの場合、前のスプレッドの右ページと入れ替え
        if page_idx == 0 and spread_idx > 0:
            prev_spread = self.spreads[spread_idx - 1]
            self.swap_pages(current_page, prev_spread.right_page)

        # 右ページの場合、同じスプレッドの左ページと入れ替え
        elif page_idx == 1:
            self.swap_pages(current_page, spread.left_page)

        self.update_all_page_numbers()

    def swap_with_next_page(self, current_page):
        spread_idx, spread = self.find_spread_and_page(current_page)
        if spread_idx == -1:
            return

        page_idx = spread.get_page_index(current_page)

        # 左ページの場合、同じスプレッドの右ページと入れ替え
        if page_idx == 0:
            self.swap_pages(current_page, spread.right_page)

        # 右ページの場合、次のスプレッドの左ページと入れ替え
        elif page_idx == 1 and spread_idx < len(self.spreads) - 1:
            next_spread = self.spreads[spread_idx + 1]
            self.swap_pages(current_page, next_spread.left_page)

        self.update_all_page_numbers()

    def swap_pages(self, page1, page2):
        """2つのページの内容を入れ替え"""
        temp_path = page1.image_path
        temp_pixmap = page1.image_label.pixmap()

        if page2.image_path:
            page1.load_image(page2.image_path)
        else:
            page1.load_image("")

        if temp_path:
            page2.load_image(temp_path)
        else:
            page2.load_image("")

    def insert_new_page_before(self, current_page):
        spread_idx, spread = self.find_spread_and_page(current_page)
        if spread_idx == -1:
            return

        page_idx = spread.get_page_index(current_page)

        # 左ページの前に挿入する場合
        if page_idx == 0:
            # 前のスプレッドがある場合は、その右ページを分割して新しいスプレッドを作る
            if spread_idx > 0:
                prev_spread = self.spreads[spread_idx - 1]
                # 新しいスプレッドを作成
                new_spread = SpreadWidget(self.current_page_width)
                # 前のスプレッドの右ページの内容を新しいスプレッドの左ページに移動
                new_spread.left_page.load_image(prev_spread.right_page.image_path)
                # 現在のスプレッドの内容を右に移動
                new_spread.right_page.load_image(spread.left_page.image_path)
                spread.left_page.load_image(spread.right_page.image_path)
                # 前のスプレッドの右ページと現在のスプレッドの右ページをクリア
                prev_spread.right_page.load_image("")
                spread.right_page.load_image("")
                # 新しいスプレッドを挿入
                self.spreads.insert(spread_idx, new_spread)
            else:
                # 最初のスプレッドの場合は、新しいスプレッドを作成して現在の内容を移動
                new_spread = SpreadWidget(self.current_page_width)
                # 現在のスプレッドの内容を新しいスプレッドにコピー
                new_spread.left_page.load_image(spread.left_page.image_path)
                new_spread.right_page.load_image(spread.right_page.image_path)
                # 現在のスプレッドの左ページをクリアして右ページに元の左ページの内容を移動
                temp_left_image = spread.left_page.image_path
                spread.left_page.load_image("")
                spread.right_page.load_image(temp_left_image)
                # 新しいスプレッドを追加
                self.spreads.insert(spread_idx + 1, new_spread)

        # 右ページの前に挿入する場合
        elif page_idx == 1:
            # 右ページの内容を新しいスプレッドの左ページに移動
            new_spread = SpreadWidget(self.current_page_width)
            new_spread.left_page.load_image(spread.right_page.image_path)
            spread.right_page.load_image("")
            self.spreads.insert(spread_idx + 1, new_spread)

        self.reorganize_layout()
        self.update_all_page_numbers()

    def insert_new_page_after(self, current_page):
        spread_idx, spread = self.find_spread_and_page(current_page)
        if spread_idx == -1:
            return

        page_idx = spread.get_page_index(current_page)

        # 左ページの後に挿入する場合
        if page_idx == 0:
            # 右ページの内容を新しいスプレッドの左ページに移動
            new_spread = SpreadWidget(self.current_page_width)
            new_spread.left_page.load_image(spread.right_page.image_path)
            spread.right_page.load_image("")
            self.spreads.insert(spread_idx + 1, new_spread)

        # 右ページの後に挿入する場合
        elif page_idx == 1:
            # 次のスプレッドがある場合
            if spread_idx < len(self.spreads) - 1:
                next_spread = self.spreads[spread_idx + 1]
                # 新しいスプレッドを作成
                new_spread = SpreadWidget(self.current_page_width)
                # 次のスプレッドの左ページの内容を新しいスプレッドの右ページに移動
                new_spread.right_page.load_image(next_spread.left_page.image_path)
                # 次のスプレッドの内容を左に移動
                next_spread.left_page.load_image(next_spread.right_page.image_path)
                next_spread.right_page.load_image("")
                # 新しいスプレッドを挿入
                self.spreads.insert(spread_idx + 1, new_spread)
            else:
                # 最後のスプレッドの場合は、新しいスプレッドを追加
                new_spread = SpreadWidget(self.current_page_width)
                self.spreads.append(new_spread)

        self.reorganize_layout()
        self.update_all_page_numbers()

    def delete_page(self, current_page):
        spread_idx, spread = self.find_spread_and_page(current_page)
        if spread_idx == -1:
            return

        page_idx = spread.get_page_index(current_page)

        # 削除前の確認
        reply = QMessageBox.question(
            self,
            'ページの削除',
            'このページを削除してもよろしいですか？',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            # 左ページを削除する場合
            if page_idx == 0:
                if spread_idx > 0:
                    # 前のスプレッドの右ページを現在の左ページに移動
                    prev_spread = self.spreads[spread_idx - 1]
                    spread.left_page.load_image(spread.right_page.image_path)
                    spread.right_page.load_image("")
                else:
                    # 最初のスプレッドの場合は左ページを空にする
                    spread.left_page.load_image("")

            # 右ページを削除する場合
            elif page_idx == 1:
                if spread_idx < len(self.spreads) - 1:
                    # 次のスプレッドの左ページを現在の右ページに移動
                    next_spread = self.spreads[spread_idx + 1]
                    spread.right_page.load_image("")
                else:
                    # 最後のスプレッドの場合は右ページを空にする
                    spread.right_page.load_image("")

            # 空のスプレッドを削除
            if not spread.left_page.image_path and not spread.right_page.image_path:
                if len(self.spreads) > 1:  # 最後の1つは削除しない
                    spread.setParent(None)
                    self.spreads.pop(spread_idx)

            self.reorganize_layout()
            self.update_all_page_numbers()

    def zoom_in(self):
        if self.current_page_width < 1000:
            self.current_page_width = min(1000, int(self.current_page_width * 1.3))
            self.update_all_page_sizes()

    def zoom_out(self):
        if self.current_page_width > 200:
            self.current_page_width = max(200, int(self.current_page_width * 0.7))
            self.update_all_page_sizes()

    def update_all_page_sizes(self):
        for spread in self.spreads:
            spread.update_page_size(self.current_page_width)
        self.reorganize_layout()

    def new_book(self):
        # 確認ダイアログ
        reply = QMessageBox.question(
            self,
            '新規作成の確認',
            '現在の内容をクリアして新規作成しますか？',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            # すべてのスプレッドを削除
            for spread in self.spreads:
                spread.setParent(None)
            self.spreads.clear()

            # 初期値をリセット
            self.current_page_width = 300
            self.page_number_start = 1
            self.show_page_numbers = True

            # 初期ページを追加
            self.add_new_spread()

            self.reorganize_layout()

    def save_book(self):
        # 保存するデータの構築
        book_data = {
            "settings": {
                "page_width": self.current_page_width,
                "page_number_start": self.page_number_start,
                "show_page_numbers": self.show_page_numbers
            },
            "spreads": []
        }

        # 各スプレッドのデータを保存
        for spread in self.spreads:
            spread_data = {
                "left_page": {
                    "image_path": spread.left_page.image_path
                },
                "right_page": {
                    "image_path": spread.right_page.image_path
                }
            }
            book_data["spreads"].append(spread_data)

        # 保存先を選択
        file_name, _ = QFileDialog.getSaveFileName(
            self,
            "Bookファイルの保存",
            "",
            "Book Files (*.book.json);;All Files (*)"
        )

        if file_name:
            if not file_name.endswith('.book.json'):
                file_name += '.book.json'

            try:
                with open(file_name, 'w', encoding='utf-8') as f:
                    json.dump(book_data, f, ensure_ascii=False, indent=2)
            except Exception as e:
                QMessageBox.critical(self, "保存エラー", f"ファイルの保存中にエラーが発生しました:\n{str(e)}")

    def load_book(self):
        # 確認ダイアログ
        if self.spreads:
            reply = QMessageBox.question(
                self,
                '読み込みの確認',
                '現在の内容をクリアして読み込みますか？',
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.No:
                return

        # ファイルを選択
        file_name, _ = QFileDialog.getOpenFileName(
            self,
            "Bookファイルを開く",
            "",
            "Book Files (*.book.json);;All Files (*)"
        )

        if file_name:
            try:
                with open(file_name, 'r', encoding='utf-8') as f:
                    book_data = json.load(f)

                # 現在のスプレッドをクリア
                for spread in self.spreads:
                    spread.setParent(None)
                self.spreads.clear()

                # 設定を読み込み
                settings = book_data.get("settings", {})
                self.current_page_width = settings.get("page_width", 300)
                self.page_number_start = settings.get("page_number_start", 1)
                self.show_page_numbers = settings.get("show_page_numbers", True)

                # スプレッドを再作成
                for spread_data in book_data.get("spreads", []):
                    spread = SpreadWidget(self.current_page_width)

                    # 左ページの画像を読み込み
                    left_image_path = spread_data.get("left_page", {}).get("image_path", "")
                    if left_image_path and os.path.exists(left_image_path):
                        spread.left_page.load_image(left_image_path)

                    # 右ページの画像を読み込み
                    right_image_path = spread_data.get("right_page", {}).get("image_path", "")
                    if right_image_path and os.path.exists(right_image_path):
                        spread.right_page.load_image(right_image_path)

                    self.spreads.append(spread)

                # ページ番号を更新
                self.update_all_page_numbers()
                # レイアウトを再構成
                self.reorganize_layout()

            except Exception as e:
                QMessageBox.critical(self, "読み込みエラー", f"ファイルの読み込み中にエラーが発生しました:\n{str(e)}")

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = BookLayoutApp()
    window.show()
    sys.exit(app.exec())
