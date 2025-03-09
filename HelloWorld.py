import sys
from PyQt6.QtWidgets import QApplication, QLabel, QVBoxLayout, QWidget

# アプリケーション作成
app = QApplication(sys.argv)

# ウィンドウ
window = QWidget()
window.setWindowTitle("Hello PyQt!")
window.setGeometry(100, 100, 300, 200) #(x,y,width,height)

#ラベル
label = QLabel("Hello World!", parent=window)

#レイアウト
layout=QVBoxLayout()
layout.addWidget(label)
window.setLayout(layout)

#ウィンドウ表示
window.show()

#イベントループ
sys.exit(app.exec())