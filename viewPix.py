import sys
import os
from PyQt6.QtWidgets import QApplication, QLabel, QListWidget, QVBoxLayout, QWidget, QFileDialog, QPushButton
from PyQt6.QtGui import QPixmap, QMouseEvent
from PyQt6.QtCore import Qt

class ImageViewer(QWidget):
    def __init__(self):
        super().__init__()

        #ウィンドウ設定
        self.setWindowTitle("画像ビューア")
        self.setGeometry(100,100,600,400)

        #レイアウト
        self.layout=QVBoxLayout()

        #フォルダ選択ボタン
        self.btn_open=QPushButton("フォルダを選択")
        self.btn_open.clicked.connect(self.load_images)
        self.layout.addWidget(self.btn_open)

        #画像リスト
        self.list_widget=QListWidget()
        self.list_widget.setMaximumHeight(200)
        self.list_widget.itemClicked.connect(self.display_image)
        self.layout.addWidget(self.list_widget)

        #画像表示ラベル
        self.image_label=QLabel("画像を選択してください")
        self.image_label.setMaximumSize(1980, 1080)
        self.image_label.setMinimumSize(600, 400)
        self.image_label.setScaledContents(False)
        self.layout.addWidget(self.image_label)

        # 拡大時の倍率
        self.zoom_factor = 2  # 拡大倍率（2倍にする例）

        #レイアウトを適用
        self.setLayout(self.layout)

    def load_images(self):
        """フォルダを選択して画像一覧を表示"""
        folder=QFileDialog.getExistingDirectory(self,"フォルダ選択")
        if not folder:
            return
        
        self.list_widget.clear()
        self.image_files =[]

        for file in os.listdir(folder):
            if file.lower().endswith(('.png','.jpg','jpeg','bmp','gif')):
                self.list_widget.addItem(file)
                self.image_files.append(os.path.join(folder,file))

    def display_image(self,item):
        """選択した画像を表示"""
        file_name=item.text()
        for path in self.image_files:
            if file_name in path:
                pixmap = QPixmap(path)

                # QLabel のサイズを基準にリサイズ
                label_width = self.image_label.width()
                label_height = self.image_label.height()

                # 画像を QLabel のサイズに収める（アスペクト比維持）
                scaled_pixmap = pixmap.scaled(label_width, label_height, Qt.AspectRatioMode.KeepAspectRatio)
                self.image_label.setPixmap(scaled_pixmap)

                # パスを保存
                self.image_path = path

                break

    def mousePressEvent(self, event):
        """画像をクリックした位置を基準に拡大表示"""
        if hasattr(self,"image_path") and self.image_path:

            # クリック位置を取得
            click_pos = event.position()  # 位置を取得

            click_x_on_label = ((click_pos.x()-self.image_label.x())/self.image_label.width())  # x座標
            click_y_on_label = ((click_pos.y()-self.image_label.y())/self.image_label.height())  # y座標

            if 0 < click_x_on_label < 1 and 0 < click_y_on_label < 1: # label内の左クリック

                pixmap=QPixmap(self.image_path)

                # 画像を拡大（トリミングを意識した処理）
                new_width = self.width() * self.zoom_factor
                new_height = self.height() * self.zoom_factor

                

                #拡大画像をスケーリングして表示(クリック位置基準)
                scaled_pixmap=pixmap.scaled(new_width,new_height,Qt.AspectRatioMode.KeepAspectRatio)

                #トリミング
                crop_center_x=max(0,round(click_x_on_label*scaled_pixmap.width()))
                crop_center_y=(round((click_y_on_label-0.5)*scaled_pixmap.height()*1.5))
                
                crop_rect=scaled_pixmap.rect().adjusted(crop_center_x - self.width() // 2, crop_center_y - self.height() // 2,
                                                        crop_center_x + self.width() // 2, crop_center_y + self.height() // 2)
                cropped_pixmap=scaled_pixmap.copy(crop_rect)

                self.image_label.setPixmap(cropped_pixmap)


if __name__=="__main__":

    app= QApplication(sys.argv)
    viewer = ImageViewer()
    viewer.show()
    sys.exit(app.exec())

