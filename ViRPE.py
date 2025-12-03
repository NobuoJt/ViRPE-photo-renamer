import sys
import os
import re
from PIL import Image
import piexif
import yaml
import logging
import ctypes
from PyQt6.QtWidgets import QApplication, QLabel, QListWidget, QVBoxLayout, QWidget, QFileDialog, QPushButton, QGridLayout, QHBoxLayout, QTextEdit, QScrollArea, QComboBox
from PyQt6.QtGui import QPixmap, QMouseEvent, QKeyEvent, QIcon
from PyQt6.QtCore import Qt, QEvent, QSize
from datetime import datetime
from fractions import Fraction
import pyperclip
import subprocess
version="v1.0.6"

# logging
LOG_LEVEL = logging.DEBUG if os.environ.get('VIPRE_DEBUG') == '1' else logging.INFO
logging.basicConfig(level=LOG_LEVEL, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

# On Windows, setting an explicit AppUserModelID helps Windows associate
# the running GUI windows with the executable's icon (taskbar/pin behavior).
def _maybe_set_app_user_model_id(app_id: str = "NobuoJt.ViRPE"):
    if os.name != 'nt':
        return
    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(app_id)
    except Exception:
        pass

class ImageViewer(QWidget):
    """メインクラス"""

    name="ViPRE "+version
    def __init__(self):
        super().__init__()

        config = load_config()
        self.custom_command1_name = config.get('custom_command1_name', 'custom1')
        self.custom_command2_name = config.get('custom_command2_name', 'custom2')

        #ウィンドウ設定
        self.setWindowTitle(self.name)
        # ウィンドウアイコンを設定（リポジトリルートにある ViRPE.ico を優先）
        try:
            icon_path = os.path.join(os.path.dirname(__file__), 'ViRPE.ico')
            if os.path.exists(icon_path):
                icon = QIcon(icon_path)
                self.setWindowIcon(icon)
                try:
                    QApplication.setWindowIcon(icon)
                except Exception:
                    pass
        except Exception:
            pass
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

        #custom_command1起動ボタン
        self.btn_custom_command1=QPushButton(self.custom_command1_name)
        self.btn_custom_command1.clicked.connect(self.custom_command1)
        self.btn_custom_command1.setDefault(True)
        self.layout.topButton.addWidget(self.btn_custom_command1)

        #外部フォルダアクセス用
        self.btn_custom_command2=QPushButton(self.custom_command2_name)
        self.btn_custom_command2.clicked.connect(self.custom_command2)
        self.btn_custom_command2.setDefault(True)
        self.layout.topButton.addWidget(self.btn_custom_command2)

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

        # 表示モード選択 (Fit / 100%)
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["Fit to Area", "Zoom"])
        self.mode_combo.setCurrentIndex(0)
        self.mode_combo.currentIndexChanged.connect(lambda _: self._update_display_mode())
        self.layout.topButton.addWidget(self.mode_combo)

        # 画像表示領域: QScrollArea + QLabel (パン対応)
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)

        class PanLabel(QLabel):
            def __init__(self, parent=None, scroll_area=None):
                super().__init__(parent)
                self.setBackgroundRole(self.backgroundRole())
                self.setSizePolicy(self.sizePolicy())
                self.setAlignment(Qt.AlignmentFlag.AlignCenter)
                self._dragging = False
                self._last_pos = None
                self._scroll_area = scroll_area
                self.setMouseTracking(True)
                self.setCursor(Qt.CursorShape.OpenHandCursor)

            def mousePressEvent(self, ev: QMouseEvent):
                if ev.button() == Qt.MouseButton.LeftButton:
                    self._dragging = True
                    # use local position to compute deltas
                    try:
                        self._last_pos = ev.position()
                    except Exception:
                        self._last_pos = ev.pos()
                    self.setCursor(Qt.CursorShape.ClosedHandCursor)
                    logger.debug("PanLabel.mousePressEvent pos=%s", self._last_pos)
                    ev.accept()
                else:
                    super().mousePressEvent(ev)

            def mouseMoveEvent(self, ev: QMouseEvent):
                if self._dragging and self._last_pos is not None and self._scroll_area:
                    try:
                        cur = ev.position()
                    except Exception:
                        cur = ev.pos()
                    dx = cur.x() - self._last_pos.x()
                    dy = cur.y() - self._last_pos.y()
                    hbar = self._scroll_area.horizontalScrollBar()
                    vbar = self._scroll_area.verticalScrollBar()
                    # subtract dx/dy to move content with mouse drag direction
                    hbar.setValue(int(hbar.value() - dx))
                    vbar.setValue(int(vbar.value() - dy))
                    logger.debug("PanLabel.mouseMoveEvent dx=%.1f dy=%.1f h=%d v=%d", dx, dy, hbar.value(), vbar.value())
                    self._last_pos = cur
                    ev.accept()
                else:
                    super().mouseMoveEvent(ev)

            def mouseReleaseEvent(self, ev: QMouseEvent):
                if ev.button() == Qt.MouseButton.LeftButton:
                    self._dragging = False
                    self._last_pos = None
                    self.setCursor(Qt.CursorShape.OpenHandCursor)
                    logger.debug("PanLabel.mouseReleaseEvent")
                    ev.accept()
                else:
                    super().mouseReleaseEvent(ev)

        # 内部ラベルを作成してスクロールエリアに設定
        self.image_label = PanLabel(scroll_area=self.scroll_area)
        self.image_label.setText("画像表示領域")
        # 不要な固定の最大/最小サイズ制約を外して、pixmap に合わせてラベルをリサイズする
        self.image_label.setScaledContents(False)
        self.scroll_area.setWidget(self.image_label)
        self.layout.addWidget(self.scroll_area)

        # ビューポート用のパン状態
        self._panning = False
        self._pan_last_pos = None
        self.scroll_area.viewport().setMouseTracking(True)
        self.scroll_area.viewport().installEventFilter(self)
        # ラベル自体がビューポートを覆っている場合があるので、ラベルにもフィルタを設置
        self.image_label.setMouseTracking(True)
        self.image_label.installEventFilter(self)

        # 内部で保持する現在のpixmap（元サイズ）
        self._current_pixmap = None
        # ズーム係数: None=Fitモードに対応、float=倍率(1.0=100%)
        self._zoom = None

        #レイアウトを適用
        self.setLayout(self.layout)

    text_require_sel_pix="画像を選択してください。\n選択後、拡張子なしファイル名を表示・此処で変更可能です。"

    def load_images(self):
        """フォルダを選択して画像一覧を表示"""

        config = load_config()
        default_folder = config.get('default_folder', os.getcwd())
        folder = QFileDialog.getExistingDirectory(self, "フォルダ選択", default_folder)
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
        from PyQt6.QtWidgets import QApplication, QLabel, QListWidget, QVBoxLayout, QWidget, QFileDialog, QPushButton, QGridLayout, QHBoxLayout, QTextEdit, QScrollArea, QComboBox
        self.text_widget.setText(os.path.splitext(item)[0])

    def rename_image_2(self):
        if hasattr(self,"image_path") and self.image_path:
            new_path = rename_exif(self.image_path)
            self.image_path=new_path
            self.reload_images(new_path)
    def rename_image_3(self):
        """テキストボックスの文字列で画像ファイル名をリネームする関数"""
        if hasattr(self,"image_path") and self.image_path:
            if self.text_require_sel_pix == self.text_widget.toPlainText():
                return False

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
                if pixmap.isNull():
                    return

                # 保存しておく（元サイズ）
                self._current_pixmap = pixmap

                # Fit モード: ビューポートに合わせてアスペクト比維持で縮小表示
                if getattr(self, 'mode_combo', None) and self.mode_combo.currentIndex() == 0:
                    # Fit モード: ビューポートに合わせてアスペクト比維持で縮小表示
                    vp_size = self.scroll_area.viewport().size()
                    scaled = pixmap.scaled(vp_size.width(), vp_size.height(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                    self.image_label.setPixmap(scaled)
                    # ラベルのサイズをピクセルに合わせる（スクロールしない）
                    self.image_label.setFixedSize(scaled.size())
                    self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                    # ビューポート内で小さい画像は中央に表示する
                    try:
                        self.scroll_area.setAlignment(Qt.AlignmentFlag.AlignCenter)
                    except Exception:
                        pass
                    self.scroll_area.setWidgetResizable(False)
                    # Fit モード時はズーム係数を None にする
                    self._zoom = None
                else:
                    # 100% モード: 元ピクセルで表示し、スクロールでパンする
                    # ズーム係数が未設定なら100%に初期化
                    if self._zoom is None:
                        self._zoom = 1.0
                    # 表示は元ピクセル * ズーム係数
                    try:
                        new_w = max(1, int(self._current_pixmap.width() * self._zoom))
                        new_h = max(1, int(self._current_pixmap.height() * self._zoom))
                        scaled = self._current_pixmap.scaled(new_w, new_h, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                    except Exception:
                        scaled = pixmap
                    self.image_label.setPixmap(scaled)
                    self.image_label.setFixedSize(scaled.size())
                    # 初期表示は中央に置く（スクロール可能なサイズになればスクロールでパン）
                    self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                    self.scroll_area.setWidgetResizable(False)
                    # UI 更新（ズーム表示）
                    # モード表示は固定のまま（拡大率は表示しない）

                # パスを保存
                self.image_path = path
                self.image_path_simple = os.path.splitext(os.path.basename(path))[0]

                exif = get_exif(path)
                if exif is None:
                    break
                self.text_widget.setText(self.image_path_simple)
                title_time = exif.get("DateTimeOriginal", "no DateTime")
                self.setWindowTitle(self.name + " 📂[" + os.path.dirname(self.image_path) + "] ⌚" + title_time)

                break

    def mousePressEvent(self, event:QMouseEvent):
        # 全体クリックは特別扱いしない（パンは PanLabel が処理）
        super().mousePressEvent(event)

    def zoom_pix(self,click_x_on_label,click_y_on_label,isZoom:bool):
        # 旧来の強引なズーム処理は廃止。将来的にズーム機能を追加する場合はここを実装。
        return

    def eventFilter(self, source, event):
        # scroll_area のビューポート上でのドラッグを拾ってパンする
        try:
            is_viewport = (source is self.scroll_area.viewport())
        except Exception:
            is_viewport = False

        # パンは 100% モードのみ有効にする
        mode_ok = getattr(self, 'mode_combo', None) and self.mode_combo.currentIndex() == 1
        if not mode_ok:
            return super().eventFilter(source, event)

        # source がビューポートまたはラベルの場合に処理
        try:
            is_label = (source is self.image_label)
        except Exception:
            is_label = False

        if is_viewport or is_label:
            if event.type() == QEvent.Type.MouseButtonPress and event.button() == Qt.MouseButton.LeftButton:
                try:
                    self._pan_last_pos = event.position()
                except Exception:
                    self._pan_last_pos = event.pos()
                self._panning = True
                logger.debug("eventFilter: start panning at %s (source=%s)", self._pan_last_pos, 'label' if is_label else 'viewport')
                return True

            if event.type() == QEvent.Type.MouseMove and self._panning and self._pan_last_pos is not None:
                try:
                    cur = event.position()
                except Exception:
                    cur = event.pos()
                dx = cur.x() - self._pan_last_pos.x()
                dy = cur.y() - self._pan_last_pos.y()
                hbar = self.scroll_area.horizontalScrollBar()
                vbar = self.scroll_area.verticalScrollBar()
                hbar.setValue(int(hbar.value() - dx))
                vbar.setValue(int(vbar.value() - dy))
                logger.debug("eventFilter: move dx=%.1f dy=%.1f -> h=%d v=%d", dx, dy, hbar.value(), vbar.value())
                self._pan_last_pos = cur
                return True

            if event.type() == QEvent.Type.MouseButtonRelease and event.button() == Qt.MouseButton.LeftButton:
                logger.debug("eventFilter: stop panning (source=%s)", 'label' if is_label else 'viewport')
                self._panning = False
                self._pan_last_pos = None
                return True

            # ホイールでズーム（Zoom モード時）
            if event.type() == QEvent.Type.Wheel:
                # 100%（Zoom）モードのみ
                if getattr(self, 'mode_combo', None) and self.mode_combo.currentIndex() == 1 and self._current_pixmap is not None:
                    # Qt の角度デルタ
                    try:
                        delta = event.angleDelta().y()
                    except Exception:
                        # 古い Qt イベント互換
                        delta = 0
                    if delta == 0:
                        return True

                    # ホイールの刻みを元に倍率を決定
                    factor = 1.001 ** delta  # 滑らかな調整
                    old_zoom = self._zoom or 1.0
                    new_zoom = max(0.05, min(6.0, old_zoom * factor))

                    # 画像の中央基準でズームする（上下左右中央を固定）
                    hbar = self.scroll_area.horizontalScrollBar()
                    vbar = self.scroll_area.verticalScrollBar()
                    vp = self.scroll_area.viewport()
                    vp_w = vp.width()
                    vp_h = vp.height()

                    # ビューポート中心の座標（画像上の座標）
                    try:
                        cur_pixmap = self.image_label.pixmap()
                    except Exception:
                        cur_pixmap = None
                    if cur_pixmap is None:
                        return True
                    cur_w = cur_pixmap.width()
                    cur_h = cur_pixmap.height()
                    if cur_w == 0 or cur_h == 0:
                        return True

                    view_center_x = hbar.value() + vp_w/2
                    view_center_y = vbar.value() + vp_h/2

                    # ホイールズームの基準はマウスポインタ位置（ビューポート座標）に戻す
                    try:
                        pos = event.position()
                    except Exception:
                        pos = event.pos()

                    # ビューポート中心を原点とした signed 座標（ログ用）
                    vp = self.scroll_area.viewport()
                    vp_w = vp.width()
                    vp_h = vp.height()
                    offset_x = pos.x() - (vp_w / 2)
                    offset_y = pos.y() - (vp_h / 2)

                    # 現在ポインタが指している画像内のピクセル座標
                    hbar = self.scroll_area.horizontalScrollBar()
                    vbar = self.scroll_area.verticalScrollBar()
                    img_x = hbar.value() + pos.x()
                    img_y = vbar.value() + pos.y()

                    # 画像上の比率（現在表示されている画像サイズを基準に）
                    cur_pixmap = self.image_label.pixmap()
                    if cur_pixmap is None:
                        return True
                    cur_w = cur_pixmap.width()
                    cur_h = cur_pixmap.height()
                    if cur_w == 0 or cur_h == 0:
                        return True

                    rel_x = img_x / cur_w
                    rel_y = img_y / cur_h

                    # 新しい表示サイズ
                    orig_w = self._current_pixmap.width()
                    orig_h = self._current_pixmap.height()
                    new_w = max(1, int(orig_w * new_zoom))
                    new_h = max(1, int(orig_h * new_zoom))

                    scaled = self._current_pixmap.scaled(new_w, new_h, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                    self.image_label.setPixmap(scaled)
                    self.image_label.setFixedSize(scaled.size())

                    # マウスポインタ位置が同じ画像上の位置を指すようスクロール位置を調整（ポインタ基準）
                    new_img_x = int(rel_x * scaled.width())
                    new_img_y = int(rel_y * scaled.height())
                    new_h_val = int(new_img_x - pos.x())
                    new_v_val = int(new_img_y - pos.y())
                    # clamp to scrollbar range
                    new_h_val = max(0, min(new_h_val, hbar.maximum()))
                    new_v_val = max(0, min(new_v_val, vbar.maximum()))
                    hbar.setValue(new_h_val)
                    vbar.setValue(new_v_val)

                    # 状態更新 + UI 更新（モード表示に拡大率を反映）
                    self._zoom = new_zoom
                    try:
                        self.mode_combo.setItemText(1, f"Zoom({int(self._zoom*100)}%)")
                    except Exception:
                        pass

                    logger.debug("eventFilter: wheel zoom old=%.3f new=%.3f rel=(%.3f,%.3f) offset=(%+.1f,%+.1f) img=(%d,%d) -> scroll=(%d,%d)", old_zoom, new_zoom, rel_x, rel_y, offset_x, offset_y, int(img_x), int(img_y), hbar.value(), vbar.value())
                    return True

            # 上記条件に該当しない場合はデフォルト処理へ戻す（常に bool を返す）
            return super().eventFilter(source, event)

    def _update_display_mode(self):
        # モード切替時に現在表示中の画像を再描画
        if hasattr(self, 'image_path') and self.image_path:
            # find the corresponding item in the list
            base = os.path.basename(self.image_path)
            for i in range(self.list_widget.count()):
                it = self.list_widget.item(i)
                if it.text() == base:
                    self.display_image(it)
                    break

    def resizeEvent(self, event):
        # ウィンドウリサイズ時に Fit モードなら再スケール
        super().resizeEvent(event)
        try:
            if getattr(self, 'mode_combo', None) and self.mode_combo.currentIndex() == 0 and self._current_pixmap is not None:
                vp_size = self.scroll_area.viewport().size()
                scaled = self._current_pixmap.scaled(vp_size.width(), vp_size.height(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                self.image_label.setPixmap(scaled)
        except Exception:
            pass

    def custom_command1(self):
        config = load_config()
        cmd = config.get('custom_command1')
        if cmd:
            subprocess.Popen(cmd)
        return False
    
    def custom_command2(self):
        config = load_config()
        cmd = config.get('custom_command2')
        if cmd:
            subprocess.Popen(cmd)
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
        focal_length_actual = exif_info.get('FocalLength') # 実際のレンズ焦点距離
        focal_length_35mm = exif_info.get('FocalLengthIn35mmFilm') # 35mm換算焦点距離
        focal_length_multiplier = focal_length_35mm/focal_length_actual if focal_length_actual and focal_length_35mm else None # 焦点距離倍率
        is_apsc = focal_length_multiplier and focal_length_multiplier == 1.5     #APSCサイズ
        is_fullframe = focal_length_multiplier and focal_length_multiplier == 1 #フルサイズ

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
        if is_apsc:
            focal_length_str = f" {int(focal_length_actual)}mm(35:{int(focal_length_35mm)})" if focal_length_actual else ""
        elif is_fullframe:
            focal_length_str = f" {int(focal_length_actual)}mm(f)" if focal_length_actual else ""
        else:
            focal_length_str = f" {int(focal_length_actual)}mm(35:{int(focal_length_35mm)} mul:{focal_length_multiplier} apsc:{is_apsc} full:{is_fullframe})" if focal_length_actual else ""

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


def load_config() -> dict:
    """`config.yaml` を読み込み、辞書を返す。存在しないか読み込み失敗なら空辞書を返す。"""
    config_path = 'config.yaml'
    if not os.path.exists(config_path):
        return {}
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f) or {}
            if isinstance(data, dict):
                return data
            return {}
    except Exception:
        return {}

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
    # On Windows, set AppUserModelID before creating the QApplication
    try:
        _maybe_set_app_user_model_id()
    except Exception:
        pass

    app= QApplication(sys.argv)
    viewer = ImageViewer()
    viewer.show()
    sys.exit(app.exec())

