import cv2
import face_recognition   # → pip install face_recognition が前提
import pickle
import numpy as np
from PIL import Image, ImageDraw, ImageFont

# ─── 顔データの読み込み ───────────────────────────────
with open("known_faces.pkl", "rb") as f:
    data = pickle.load(f)

# ─── 距離のしきい値（この値以下で一致と判定） ───────────────────────────────
THRESHOLD = 0.40

def recognize_faces(frame):
    """
    与えられた BGR 画像（frame）を顔認識し、
    検出されたすべての顔について (top, right, bottom, left, name) のリストを返す。
    """
    # ─── 顔データの読み込み ───────────────────────────────
    with open("known_faces.pkl", "rb") as f:
        data = pickle.load(f)

    # ① BGR → RGB に変換
    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

    # ② 顔の位置を検出
    face_locations = face_recognition.face_locations(rgb_frame)

    # ③ 顔特徴量を抽出
    face_encodings = face_recognition.face_encodings(rgb_frame, face_locations)

    results = []
    for (top, right, bottom, left), face_encoding in zip(face_locations, face_encodings):
        name = "Unknown"
        # 登録済みのすべての顔特徴量との距離を計算
        face_distances = face_recognition.face_distance(data["encodings"], face_encoding)
        if len(face_distances) > 0:
            best_match_index = face_distances.argmin()
            min_distance = face_distances[best_match_index]
            if min_distance < THRESHOLD:
                name = data["names"][best_match_index]
        results.append((top, right, bottom, left, name))

    return results

def main():
    """
    CLI でこのファイルを直接実行したときのリアルタイム顔認識デモ。
    """
    # カメラ映像取得
    video = cv2.VideoCapture(0)
    print("🎥 リアルタイム顔認識開始（'q' で終了）")

    # ─── 日本語フォントの指定 ──────────────────────────────
    # macOS の場合（例）：ヒラギノ角ゴシックを指定
    # Windows/Linux の場合は適宜、お手元の日本語対応フォントを指定してください
    # 例（macOS）: "/System/Library/Fonts/ヒラギノ角ゴシック W6.ttc"
    # 例（Windows）: "C:/Windows/Fonts/msgothic.ttc"
    # 例（同フォントを同ディレクトリに置いている場合）: "japanese_font.ttf"
    FONT_PATH = "/System/Library/Fonts/ヒラギノ角ゴシック W6.ttc"
    FONT_SIZE = 32  # お好みで調整してください

    # PIL 用フォントオブジェクトを作成
    font = ImageFont.truetype(FONT_PATH, FONT_SIZE)

    while True:
        ret, frame = video.read()
        if not ret:
            continue

        detections = recognize_faces(frame)

        # (1) まず OpenCV で矩形を描画
        for (top, right, bottom, left, name) in detections:
            cv2.rectangle(frame, (left, top), (right, bottom), (0, 255, 0), 2)

        # (2) OpenCV の BGR フレームを PIL Image に変換
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        pil_img = Image.fromarray(rgb_frame)
        draw = ImageDraw.Draw(pil_img)

        # (3) 各検出位置に対して PIL で文字列（漢字）を描画
        for (top, right, bottom, left, name) in detections:
            # テキストの位置を決定（例では顔矩形の左上の少し上に置く）
            text_position = (left, max(0, top - FONT_SIZE - 5))
            # 文字色を (R,G,B) で指定（ここでは緑）
            draw.text(text_position, name, font=font, fill=(0, 255, 0))

        # (4) PIL Image を再び OpenCV の BGR フレームに戻す
        frame_with_text = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)

        # 表示
        cv2.imshow("1:N 顔認識 (日本語対応)", frame_with_text)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    video.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
