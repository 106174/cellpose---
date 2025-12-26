import os
import cv2
import numpy as np

IMG_DIR = r"C:\Users\Administrator\PycharmProjects\YOLOimg_cutoff\dataset\dataset122202\images1222"
LABEL_DIR = r"C:\Users\Administrator\PycharmProjects\YOLOimg_cutoff\dataset\dataset122202\labels122203"

img_list = [f for f in os.listdir(IMG_DIR) if f.endswith((".jpg", ".png"))]

for img_name in img_list:
    base = os.path.splitext(img_name)[0]
    img_path = os.path.join(IMG_DIR, img_name)
    label_path = os.path.join(LABEL_DIR, base + ".txt")

    img = cv2.imread(img_path)
    if img is None:
        continue

    h, w = img.shape[:2]

    if not os.path.exists(label_path):
        print(f"[WARN] No label for {img_name}")
        continue

    with open(label_path, "r") as f:
        lines = f.readlines()

    for line in lines:
        parts = list(map(float, line.strip().split()))
        if len(parts) < 11:
            print(f"[ERROR] Invalid seg label: {label_path}")
            continue

        cls = int(parts[0])
        cx, cy, bw, bh = parts[1:5]
        poly = parts[5:]

        # ---------- bbox ----------
        x1 = int((cx - bw / 2) * w)
        y1 = int((cy - bh / 2) * h)
        x2 = int((cx + bw / 2) * w)
        y2 = int((cy + bh / 2) * h)

        cv2.rectangle(img, (x1, y1), (x2, y2), (0, 255, 0), 2)

        # ---------- polygon ----------
        pts = []
        for i in range(0, len(poly), 2):
            px = int(poly[i] * w)
            py = int(poly[i + 1] * h)
            pts.append([px, py])

        pts = np.array(pts, np.int32).reshape((-1, 1, 2))
        cv2.polylines(img, [pts], isClosed=True, color=(0, 0, 255), thickness=2)

    cv2.imshow("YOLO Seg Label Check", img)
    key = cv2.waitKey(0)

    if key == 27:  # ESC 退出
        break

cv2.destroyAllWindows()
