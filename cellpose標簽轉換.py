import os
import numpy as np
import cv2

NPY_DIR = r"dataset/cellpose_npy1219"
LABEL_DIR = r"dataset/labels122203"
SUFFIX_TO_REMOVE = '_seg'

os.makedirs(LABEL_DIR, exist_ok=True)

for npy_name in os.listdir(NPY_DIR):
    if not npy_name.endswith(".npy"):
        continue

    base = os.path.splitext(npy_name)[0]
    base = base.removesuffix(SUFFIX_TO_REMOVE)

    npy_path = os.path.join(NPY_DIR, npy_name)
    label_path = os.path.join(LABEL_DIR, base + ".txt")

    try:
        data = np.load(npy_path, allow_pickle=True).item()
        masks = data["masks"]
    except Exception as e:
        print(f"❌ 加载失败：{npy_name} | {e}")
        continue

    h, w = masks.shape

    with open(label_path, "w") as f:
        for inst_id in np.unique(masks):
            if inst_id == 0:
                continue

            binary = (masks == inst_id).astype(np.uint8)

            if binary.sum() < 10:
                continue

            contours, _ = cv2.findContours(
                binary,
                cv2.RETR_EXTERNAL,
                cv2.CHAIN_APPROX_SIMPLE
            )

            for cnt in contours:
                cnt = cv2.approxPolyDP(cnt, epsilon=1.5, closed=True)

                if len(cnt) < 6:
                    continue

                # YOLO seg：class + polygon points
                line = "0"

                for p in cnt:
                    x, y = p[0]
                    line += f" {x / w:.6f} {y / h:.6f}"

                f.write(line + "\n")

    print(f"✅ {npy_name} → {os.path.basename(label_path)}")

print("\n🎯 YOLO Seg 标签生成完成")
