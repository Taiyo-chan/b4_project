# gui_face_recognition.py
# 顔撮影用GUI

import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk
import cv2
import os
import datetime
import pykakasi  # ローマ字変換用ライブラリをインポート
import subprocess # 12.pyを自動的に実行するために必要


# encode_faces.py の関数をインポート
from encode_faces import encode_faces

# recognize_faces() を収録しているスクリプトをインポート
from test_multi_realtime import recognize_faces

#発話者の名前をグローバル変数として定義
recognized_name = None

launched_names = set()

# ─── 定数 ───────────────────────────────────────────────
DATASET_DIR = "face_dataset"   # 顔画像を保存するフォルダ名

# ─── グローバル変数 ───────────────────────────────────────
unknown_detected = False   # Unknown 顔が検出されたか
countdown = 0              # カウントダウン用（秒）
capturing = False          # 撮影中フラグ
current_frame = None       # 最後に取得したフレームを保持
paused = False             # 入力中は True になり、ビデオを一時停止する
# pykakasi の初期化
kakasi = pykakasi.kakasi()

# ─── Tkinter ウィンドウ初期設定 ─────────────────────────────────
root = tk.Tk()
root.title("1:N 顔認識 GUI (Encode自動実行付き)")
root.geometry("1200x720")   # 必要に応じて微調整してください

# ─── 左フレーム：新規登録用フォーム ─────────────────────────────────
left_frame = ttk.Frame(root, width=400, padding=10)
left_frame.pack(side=tk.LEFT, fill=tk.Y)

ttk.Label(left_frame, text="新規登録", font=("Helvetica", 16)).pack(pady=(0, 10))

# 「姓」「名」の漢字／ふりがなを格納する変数
surname_kanji_var = tk.StringVar()
givenname_kanji_var = tk.StringVar()
surname_furigana_var = tk.StringVar()
givenname_furigana_var = tk.StringVar()

def validate_entries(*args):
    """
    すべての入力欄に文字が入っていて、unknown_detected == True のときだけ
    「決定」ボタンを有効化する。
    """
    if unknown_detected \
       and surname_kanji_var.get().strip() \
       and givenname_kanji_var.get().strip() \
       and surname_furigana_var.get().strip() \
       and givenname_furigana_var.get().strip():
        decide_button.config(state=tk.NORMAL)
    else:
        decide_button.config(state=tk.DISABLED)

# (1) 姓（漢字）
ttk.Label(left_frame, text="姓（漢字）").pack(anchor=tk.W, pady=(10, 0))
surname_kanji_entry = ttk.Entry(left_frame, textvariable=surname_kanji_var, state=tk.DISABLED)
surname_kanji_entry.pack(fill=tk.X)

# (2) 名（漢字）
ttk.Label(left_frame, text="名（漢字）").pack(anchor=tk.W, pady=(10, 0))
givenname_kanji_entry = ttk.Entry(left_frame, textvariable=givenname_kanji_var, state=tk.DISABLED)
givenname_kanji_entry.pack(fill=tk.X)

# (3) 姓（ふりがな）
ttk.Label(left_frame, text="姓（ふりがな）").pack(anchor=tk.W, pady=(10, 0))
surname_furigana_entry = ttk.Entry(left_frame, textvariable=surname_furigana_var, state=tk.DISABLED)
surname_furigana_entry.pack(fill=tk.X)

# (4) 名（ふりがな）
ttk.Label(left_frame, text="名（ふりがな）").pack(anchor=tk.W, pady=(10, 0))
givenname_furigana_entry = ttk.Entry(left_frame, textvariable=givenname_furigana_var, state=tk.DISABLED)
givenname_furigana_entry.pack(fill=tk.X)

# 決定ボタン（最初は無効化）
decide_button = ttk.Button(left_frame, text="決定", state=tk.DISABLED)
decide_button.pack(pady=(20, 0))

# 変数が書き換わるたびに validate_entries() を呼ぶ
for var in (surname_kanji_var, givenname_kanji_var, surname_furigana_var, givenname_furigana_var):
    var.trace_add("write", validate_entries)

# ─── Entry にフォーカスイン／アウトイベントをバインド ─────────────────────────────
def on_focus_in(event):
    global paused
    paused = True  # Entry にフォーカスしたらビデオ停止

def on_focus_out(event):
    global paused
    paused = False  # フォーカスが外れたらビデオ再開

for entry in (surname_kanji_entry, givenname_kanji_entry,
              surname_furigana_entry, givenname_furigana_entry):
    entry.bind("<FocusIn>", on_focus_in)
    entry.bind("<FocusOut>", on_focus_out)

# ─── 右フレーム：カメラ映像表示用 ─────────────────────────────────
right_frame = ttk.Frame(root)
right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

video_label = ttk.Label(right_frame)
video_label.pack(fill=tk.BOTH, expand=True)

# ─── カウントダウンラベルを right_frame の子として作成 ───────────────────────────────
countdown_label = tk.Label(
    right_frame,
    text="",
    font=("Helvetica", 48),
    fg="red",
    bg="black",
    anchor="center"
)
countdown_label.place_forget()  # 初期状態は非表示

# OpenCV でカメラキャプチャを開始
video = cv2.VideoCapture(0)


# ─── 新規登録：決定ボタン押下時の処理 ───────────────────────────────
def start_capture():
    global countdown, capturing
    decide_button.config(state=tk.DISABLED)
    surname_kanji_entry.config(state=tk.DISABLED)
    givenname_kanji_entry.config(state=tk.DISABLED)
    surname_furigana_entry.config(state=tk.DISABLED)
    givenname_furigana_entry.config(state=tk.DISABLED)

    countdown = 3
    capturing = True
    show_countdown()


def show_countdown():
    """
    1秒ごとにカウントダウンを更新し、0秒になったら写真を撮る。
    今回は「right_frame の右上」に 1/8 サイズで表示する。
    """
    global countdown
    if countdown > 0:
        countdown_label.config(text=str(countdown))
        countdown_label.place(
            relx=1.0,         # 親フレーム（right_frame）の右端
            rely=0.0,         # 親フレームの上端
            relwidth=0.3,   # 親フレームの幅の 1/4
            relheight=0.3,  # 親フレームの高さの 1/4
            anchor="ne"       # 親フレームの右上（north-east）に合わせる
        )
        countdown -= 1
        root.after(1000, show_countdown)
    else:
        countdown_label.place_forget()
        take_photo()
        



def take_photo():
    """
    カウントダウン後に最新フレームを JPEG として保存し、
    その後 encode_faces.encode_faces() を呼び出して known_faces.pkl を更新する。
    """
    global capturing, unknown_detected
    # current_speaker.txt を更新
    recognized_name = surname_kanji_var.get().strip() + givenname_kanji_var.get().strip()
    with open("current_speaker.txt", "w", encoding="utf-8") as f:
        f.write(recognized_name)

    # 12.py 起動（初回のみ）
    if recognized_name not in launched_names:
        subprocess.Popen(["python", "12.py"])
        launched_names.add(recognized_name)


    if current_frame is None:
        capturing = False
        return

    # 平仮名の苗字をローマ字に変換
    surname_furigana = surname_furigana_var.get().strip()
    surname_romaji = kakasi.convert(surname_furigana)[0]['hepburn']

    # フォルダ名を「ローマ字の姓＋名（漢字）」で作成
    # フォルダ名を「姓＋名（漢字）」で作成
    full_name_kanji = surname_kanji_var.get().strip() + givenname_kanji_var.get().strip()
    surname_romaji = kakasi.convert(surname_furigana)[0]['hepburn']
    save_dir = os.path.join(DATASET_DIR, surname_romaji)
    os.makedirs(save_dir, exist_ok=True)

    # タイムスタンプ付きファイル名を生成して保存
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{full_name_kanji}_{timestamp}.jpg"
    save_path = os.path.join(save_dir, filename)


    cv2.imwrite(save_path, current_frame)
    print(f"Saved: {save_path}")

    # ─── 写真を保存した直後に encode_faces() を実行 ───────────────────────────
    #encode_faces()

    capturing = False
    unknown_detected = False
    clear_form()



def clear_form():
    """
    フォームの内容を空にし、すべての入力欄を再度無効化する。
    """
    surname_kanji_var.set("")
    givenname_kanji_var.set("")
    surname_furigana_var.set("")
    givenname_furigana_var.set("")

    surname_kanji_entry.config(state=tk.DISABLED)
    givenname_kanji_entry.config(state=tk.DISABLED)
    surname_furigana_entry.config(state=tk.DISABLED)
    givenname_furigana_entry.config(state=tk.DISABLED)
    decide_button.config(state=tk.DISABLED)

# 「決定」ボタンにコマンドを設定
decide_button.config(command=start_capture)


# ─── メインループ：カメラフレームを取得→顔認識→Tkinter に表示 ────────────────────
def update_frame():
    """
    30ms 毎に呼び出される。paused が True なら新しいフレームを取得せず、
    最後に表示したままの静止画を維持する。paused が False なら通常動作。
    """
    global current_frame, unknown_detected

    if paused:
        root.after(30, update_frame)
        return

    ret, frame = video.read()
    if not ret:
        root.after(30, update_frame)
        return

    current_frame = frame.copy()
    detections = recognize_faces(frame)


    detected_unknown = False
    # 検出結果に応じて枠と名前を描画
    for (top, right, bottom, left, name) in detections:
        if name == "Unknown":
            detected_unknown = True
        cv2.rectangle(frame, (left, top), (right, bottom), (0, 255, 0), 2)
        cv2.putText(frame, name, (left, top - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.75, (0, 255, 0), 2)
        
    global recognized_name
    for (_, _, _, _, name) in detections:
        if name != "Unknown":
            recognized_name = name
            with open("current_speaker.txt", "w", encoding="utf-8") as f:
                f.write(recognized_name)
            
            if recognized_name not in launched_names:
                print(f"🚀 {recognized_name} を対象に 12.py を起動します")
                subprocess.Popen(["python", "12.py"])  # ←非同期で起動（ウィンドウ閉じない）
                launched_names.add(recognized_name)
            break  # 最初に見つけた人物だけ保存（複数検出時の対策）

    # Unknown が検出されていて、なおかつまだ撮影中でなければフォームを有効化
    if detected_unknown and not capturing:
        if not unknown_detected:
            unknown_detected = True
            surname_kanji_entry.config(state=tk.NORMAL)
            givenname_kanji_entry.config(state=tk.NORMAL)
            surname_furigana_entry.config(state=tk.NORMAL)
            givenname_furigana_entry.config(state=tk.NORMAL)
            validate_entries()
    else:
        # Unknown がいなくなったらフォームをクリア
        if not capturing and unknown_detected:
            unknown_detected = False
            clear_form()

    # OpenCV の BGR → RGB → PIL → ImageTk 変換
    img_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    pil_image = Image.fromarray(img_rgb)
    imgtk = ImageTk.PhotoImage(image=pil_image)
    video_label.imgtk = imgtk
    video_label.config(image=imgtk)

    root.after(30, update_frame)


# アプリ起動時にフレーム更新をスタート
root.after(0, update_frame)

# ─── ウィンドウを閉じるときの後処理 ──────────────────────────────────────
def on_closing():
    print("🧠 顔エンコーディングを開始します...")
    encode_faces()
    print("✅ エンコーディング完了")
    video.release()
    root.destroy()

root.protocol("WM_DELETE_WINDOW", on_closing)
root.mainloop()
