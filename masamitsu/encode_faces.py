# encode_faces.py

import os
import face_recognition
import pickle

def encode_faces():
    """
    face_datasetディレクトリ内の全サブフォルダを巡回し、
    画像から顔エンコーディングを生成して known_faces.pkl に保存する。
    """
    KNOWN_FACES_DIR = "face_dataset"
    encodings = []
    names = []

    # 各人フォルダを走査
    for name in os.listdir(KNOWN_FACES_DIR):
        person_dir = os.path.join(KNOWN_FACES_DIR, name)
        if not os.path.isdir(person_dir):
            continue

        for filename in os.listdir(person_dir):
            image_path = os.path.join(person_dir, filename)
            image = face_recognition.load_image_file(image_path)
            locations = face_recognition.face_locations(image)

            if len(locations) != 1:
                print(f"⚠️ スキップ: {image_path}（顔が1つではない）")
                continue

            encoding = face_recognition.face_encodings(image, locations)[0]
            encodings.append(encoding)
            names.append(name)

    # pickled で保存
    with open("known_faces.pkl", "wb") as f:
        pickle.dump({"encodings": encodings, "names": names}, f)

    print("✅ 全ての顔エンコードを保存しました。")

if __name__ == "__main__":
    encode_faces()
