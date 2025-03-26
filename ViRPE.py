import sys
import os
import re
from PIL import Image
import piexif
from PyQt6.QtWidgets import QApplication, QLabel, QListWidget, QVBoxLayout, QWidget, QFileDialog, QPushButton,QGridLayout,QHBoxLayout,QTextEdit
from PyQt6.QtGui import QPixmap, QMouseEvent,QKeyEvent
from PyQt6.QtCore import Qt
from datetime import datetime
from fractions import Fraction
import pyperclip
import subprocess
version="v1.0.2"

class ImageViewer(QWidget):
    """メインクラス"""

    name="ViPRE "+version
    def __init__(self):
        super().__init__()

        #ウィンドウ設定
        self.setWindowTitle(self.name)
        self.setGeometry(100,100,600,400)

        #レイアウト
        self.layout=QVBoxLayout()
        self.layout.topButton=QHBoxLayout()
        self.layout.addLayout(self.layout.topButton)

        #フォルダ選択ボタン
        self.btn_open=QPushButton("フォルダ選択")
        self.btn_open.clicked.connect(self.load_images)
        self.btn_open.setDefault(True)
        self.layout.topButton.addWidget(self.btn_open)

        #exifリネームボタン
        self.btn_rename=QPushButton("リネーム(from textbox)")
        self.btn_rename.clicked.connect(self.rename_image_3)
        self.btn_rename.setDefault(True)
        self.layout.topButton.addWidget(self.btn_rename)

        #exifリネームボタン
        self.btn_exif_rename=QPushButton("リネーム(add EXIF)")
        self.btn_exif_rename.clicked.connect(self.rename_image_2)
        self.btn_exif_rename.setDefault(True)
        self.layout.topButton.addWidget(self.btn_exif_rename)

        #exifクリップボードコピーボタン
        self.btn_exifCopy=QPushButton("copyToClip(EXIF)")
        self.btn_exifCopy.clicked.connect(self.exif_clip_2)
        self.btn_exifCopy.setDefault(True)
        self.layout.topButton.addWidget(self.btn_exifCopy)

        #Excel起動ボタン
        self.btn_excel=QPushButton("excel")
        self.btn_excel.clicked.connect(self.openExcel)
        self.btn_excel.setDefault(True)
        self.layout.topButton.addWidget(self.btn_excel)

        #外部フォルダアクセス用
        self.btn_share=QPushButton("share folder")
        self.btn_share.clicked.connect(self.share)
        self.btn_share.setDefault(True)
        self.layout.topButton.addWidget(self.btn_share)

        #入出力テキストボックス
        self.text_widget=ModifiedTextEdit("フォルダを選択してください")
        self.text_widget.setMaximumHeight(45)
        self.text_widget.func_rename=self.rename_image_3
        self.text_widget.func_rename_exif=self.rename_image_2
        self.layout.addWidget(self.text_widget)

        #画像リスト
        self.list_widget=QListWidget()
        self.list_widget.setMinimumHeight(140)
        self.list_widget.setMaximumHeight(140)
        self.list_widget.itemClicked.connect(self.display_image)
        self.list_widget.itemActivated.connect(self.display_image)
        self.layout.addWidget(self.list_widget)

        #画像表示ラベル
        self.image_label=QLabel("画像表示領域")
        self.image_label.setMaximumSize(1980, 1080)
        self.image_label.setMinimumSize(600, 400)
        self.image_label.setScaledContents(False)
        self.layout.addWidget(self.image_label)

        # 拡大時の倍率
        self.zoom_factor = 2  # 拡大倍率（2倍にする例）

        #レイアウトを適用
        self.setLayout(self.layout)

    text_require_sel_pix="画像を選択してください。\n選択後、拡張子なしファイル名を表示・此処で変更可能です。"

    def load_images(self):
        """フォルダを選択して画像一覧を表示"""

        f=open('config.dat','r')
        line=f.readlines()

        folder=QFileDialog.getExistingDirectory(self,"フォルダ選択",line[0])
        if not folder:
            return
        
        self.setWindowTitle(self.name+" 📂["+folder+"]")

        self.list_widget.clear()
        self.image_files =[]
        self.text_widget.setText(self.text_require_sel_pix)

        for file in os.listdir(folder):
            if file.lower().endswith(('.png','.jpg','jpeg','bmp','gif')):
                self.list_widget.addItem(file)
                self.image_files.append(os.path.join(folder,file))

    def reload_images(self,item):
        """画像一覧をリロード"""
        if not hasattr(self,"image_path"):
            return
        folder=os.path.dirname(self.image_path)
        self.list_widget.clear()
        self.image_files =[]

        for file in os.listdir(folder):
            if file.lower().endswith(('.png','.jpg','jpeg','bmp','gif')):
                self.list_widget.addItem(file)
                self.image_files.append(os.path.join(folder,file))

        if item:
            item=os.path.basename(item)
            for i in range(self.list_widget.count()):
                if self.list_widget.item(i).text()==item:
                    self.list_widget.setCurrentItem(self.list_widget.item(i))
                    break
                
        self.text_widget.setText(os.path.splitext(item)[0])

    def rename_image_2(self):
        if hasattr(self,"image_path") and self.image_path:
            new_path = rename_exif(self.image_path)
            self.image_path=new_path
            self.reload_images(new_path)

    def rename_image_3(self):
        """テキストボックスの文字列で画像ファイル名をリネームする関数"""
        if hasattr(self,"image_path") and self.image_path:
            if self.text_require_sel_pix == self.text_widget.toPlainText():return False

            # 新しいファイル名を作成
            new_name = self.text_widget.toPlainText().replace('\x00',"").replace('/','／').replace('\n',' ')
            new_name += os.path.splitext(self.image_path)[1]  # 拡張子を追加

            # ファイルをリネーム
            if self.text_require_sel_pix not in new_name:
                new_path = os.path.join(os.path.dirname(self.image_path), replace_invalid_chars(new_name))        
                os.rename(self.image_path, new_path)
            self.image_path=new_path
            self.reload_images(new_path)
            return new_path
        return

    def exif_clip_2(self):
        """Exif情報を使って画像ファイル名をリネームする関数"""
        if hasattr(self,"image_path") and self.image_path:
            exif_info = get_exif(self.image_path)
            if not exif_info:return
            content=""

            # 取得したExifデータをクリップボードにコピー
            for key, value in exif_info.items():
                content+=(f"{key}: {value}\n")\

            pyperclip.copy(content)
            self.text_widget.setText(content)

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
                self.image_path_simple = os.path.splitext(os.path.basename(path))[0]

                exif=get_exif(path)
                if exif is None: break
                self.text_widget.setText(self.image_path_simple)
                self.setWindowTitle(self.name+" 📂["+os.path.dirname(self.image_path)+"] ⌚"
                                    +exif["DateTimeOriginal"] if "DateTimeOriginal" in exif else "no DateTime")



                break

    def mousePressEvent(self, event:QMouseEvent):
        """画像をクリックした位置を基準に拡大表示"""
        if hasattr(self,"image_path") and self.image_path:

            # クリック位置を取得
            click_pos = event.position()  # 位置を取得

            click_x_on_label = ((click_pos.x()-self.image_label.x())/self.image_label.width())  # x座標
            click_y_on_label = ((click_pos.y()-self.image_label.y())/self.image_label.height())  # y座標

            if 0 < click_x_on_label < 1 and 0 < click_y_on_label < 1: # label内クリック
                if event.button() == Qt.MouseButton.LeftButton: #左クリック
                    self.zoom_pix(click_x_on_label,click_y_on_label,True)
                
            if 0 < click_x_on_label < 1 and 0 < click_y_on_label < 1: # label内クリック
                if event.button() == Qt.MouseButton.RightButton: #右クリック
                    self.zoom_pix(click_x_on_label,click_y_on_label,False)

    def zoom_pix(self,click_x_on_label,click_y_on_label,isZoom:bool):
        pixmap=QPixmap(self.image_path)

        # 画像を拡大（トリミングを意識した処理）
        new_width = round(self.width() * (self.zoom_factor if isZoom else 0.9))
        new_height = round(self.height() * (self.zoom_factor if isZoom else 0.9))

        #拡大画像をスケーリングして表示(クリック位置基準)
        scaled_pixmap=pixmap.scaled(new_width,new_height,Qt.AspectRatioMode.KeepAspectRatio)

        #トリミング
        crop_center_x=max(0,round(click_x_on_label*scaled_pixmap.width())) if isZoom else 0
        crop_center_y=(round((click_y_on_label-0.5)*scaled_pixmap.height()*1.5)) if isZoom else 0
        
        crop_rect=scaled_pixmap.rect().adjusted(crop_center_x - self.width() // 2, crop_center_y - self.height() // 2,
                                                crop_center_x + self.width() // 2, crop_center_y + self.height() // 2)
        cropped_pixmap=scaled_pixmap.copy(crop_rect)

        self.image_label.setPixmap(cropped_pixmap)

    def openExcel(self):
        f=open('config.dat','r')
        line=f.readlines()
        subprocess.Popen(line[1])
        return False
    
    def share(self):
        f=open('config.dat','r')
        line=f.readlines()
        subprocess.Popen(''+line[2]+"")
        return False

def get_exif(file_path):
    """Exif情報を取得する関数"""
    exif_data=None
    try:
        exif_data=piexif.load(file_path)
    except Exception as e:
        if(e):return
    finally:
        if not exif_data:return

        # Exif情報を辞書として登録
        exif_dict ={}

        # 各IFD（Exif情報のカテゴリ）を走査
        for ifd_name in exif_data:
            if isinstance(exif_data[ifd_name], dict):  # items() を使うため辞書かチェック
                for tag, value in exif_data[ifd_name].items():
                    tag_name = piexif.TAGS[ifd_name].get(tag, {"name": tag})["name"]

                    # `bytes` 型ならデコード（例: メーカー名など）
                    if isinstance(value, bytes):
                        try:
                            value = value.decode("utf-8",errors="replace").replace('\x00','')
                        except UnicodeDecodeError:
                            value = value.hex()  # デコードできなければ16進数に変換

                    # `Rational`（分数表記）を処理
                    if isinstance(value, tuple) and len(value) == 2:
                        value = Fraction(value[0], value[1])  # 分子/分母 → Fractionに変換

                    exif_dict[tag_name] = value

        return exif_dict

def rename_exif(file_path):
    """Exif情報を使って画像ファイル名をリネームする関数"""
    exif_info = get_exif(file_path)

    # Exifの撮影日時を取得
    datetime_str = exif_info['DateTimeOriginal']
    match = re.search(r"\d{4}:\d{2}:\d{2} \d{2}:\d{2}:\d{2}", datetime_str)
    if match:

        # Exif情報を取得
        shutter_speed = exif_info.get('ExposureTime')
        f_number = exif_info.get('FNumber')
        iso = exif_info.get('ISOSpeedRatings') or exif_info.get('PhotographicSensitivity')
        focal_length = exif_info.get('FocalLength')

        # シャッタースピードの整形
        if isinstance(shutter_speed, Fraction):
            shutter_speed_str = f" {shutter_speed.numerator}／{shutter_speed.denominator}秒"
        elif isinstance(shutter_speed, (int, float)):
            shutter_speed_str = f" {shutter_speed:.1f}秒"
        else:
            shutter_speed_str = ""

        # F値の整形
        f_number_str_o = f" F{float(f_number)}" if f_number else ""
        f_number_str=f_number_str_o.replace("/","／")

        # ISOの整形
        iso_str = f" ISO{iso}" if iso else ""

        # 焦点距離の整形
        focal_length_str = f" {int(focal_length)}mm" if focal_length else ""

        # 新しいファイル名を作成
        new_name = os.path.splitext(file_path)[0]
        new_name += replace_invalid_chars(f"{shutter_speed_str}{f_number_str}{iso_str}{focal_length_str}")
        new_name += os.path.splitext(file_path)[1]  # 拡張子を追加

        # ファイルをリネーム
        new_path = os.path.join(os.path.dirname(file_path), new_name)
        if "ISO" not in os.path.basename(file_path):
            os.rename(file_path, new_path)
        else:
            return file_path

        return new_path


    return file_path  # Exif情報がなければ変更しない


def replace_invalid_chars(filename: str) -> str:
    # 置換用のマッピング（半角→全角）
    replacement_table = {
        '\\': '￥',   # バックスラッシュ → 全角円記号
        '/':  '／',   # スラッシュ → 全角スラッシュ
        ':':  '：',   # コロン → 全角コロン
        '*':  '＊',   # アスタリスク → 全角アスタリスク
        '?':  '？',   # クエスチョンマーク → 全角クエスチョンマーク
        '"':  '”',   # ダブルクォート → 全角ダブルクォート（例）
        '<':  '＜',   # 小なり → 全角小なり
        '>':  '＞',   # 大なり → 全角大なり
        '|':  '｜'    # パイプ → 全角パイプ
    }
    
    # マッピングに従って文字を置換
    for char, replacement in replacement_table.items():
        filename = filename.replace(char, replacement)
    
    return filename

class ModifiedTextEdit(QTextEdit):
    def func_rename(self):return False
    def func_rename_exif(self):return False
    def keyPressEvent(self, event: QKeyEvent):
        if event.key() == Qt.Key.Key_Return and not event.modifiers()==Qt.KeyboardModifier.ShiftModifier:
            self.func_rename()
        elif event.key() == Qt.Key.Key_Return and event.modifiers()==Qt.KeyboardModifier.ShiftModifier :
            self.func_rename_exif()
        else:
            super().keyPressEvent(event)  # 通常の動作

if __name__=="__main__":

    app= QApplication(sys.argv)
    viewer = ImageViewer()
    viewer.show()
    sys.exit(app.exec())

