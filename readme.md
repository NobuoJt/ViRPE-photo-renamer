# ViRPE - View image, Rename and Proceed by EXIF

変な名前してるけど、ただの個人用ツール。  
pythonほとんど使ってないのでChat GPTくんに助けを借りてGUIツールを作ってみた。  
いちおう読みは「バープ」で。

## Feature / Usage

![alt text](image.png)  
パスのスペル間違えてるのは目をつぶってくれ  

### Component

|上部ボタン||
|-|-|
|フォルダ選択| ```./config.dat``` の1行目を基準にフォルダ選択のウィンドウが出る。
|リネーム(from textbox)|上部テキストボックスのとおりに選択ファイル名が改名。(拡張子含まず)
|リネーム(add EXIF)|シャッタースピード、F値、iso、焦点距離を選択ファイル名に追加。|
|copyToClip(EXIF)|選択ファイルのEXIF情報を上部テキストボックスに表示、クリップボードにコピー。
|excel|外部コマンド1。```./config.dat```の2行目で指定。
|share folder|外部コマンド2。```./config.dat```の3行目で指定。

|コンテンツ||
|-|-|
|タイトルバー|バージョン　📂[フォルダパス]　⌚EXIF撮影日時|
|上部テキストボックス|操作指示、拡張子なしファイル名、exif情報を表示。ファイル名変更も可能。|
|画像ファイルリスト|画像の選択|
|画像表示エリア|マウス左クリックで全体の2倍で表示。右クリックで1倍。|

### Download

[ここ](https://github.com/NobuoJt/ViRPE-photo-renamer/releases/tag/v1.0.0-beta)からwindowsでの実行ファイルをダウンロード可能。  
Windows Defenderに怒られながら産んだのであまりおすすめはしない。

### Memo

```./HelloWorld.py```の5行目は優秀な助手:Chat GPTのリンク
