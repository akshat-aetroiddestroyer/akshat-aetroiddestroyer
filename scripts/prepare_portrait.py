"""
Turns a photo into a clean grayscale cut-out for the dot portrait.

  python scripts/prepare_portrait.py my_photo.jpg [x0 y0 x1 y1]

x0,y0,x1,y1 = crop box around head + shoulders (pixels of the ORIGINAL photo).
Output: scripts/portrait_cutout.png  (background = black, so it produces no dots)

Needs: pip install opencv-python numpy
"""
import sys
import cv2
import numpy as np
from pathlib import Path

FLIP = True      # mirror selfies are reversed; True shows you as others see you
# Rectangles (x0,y0,x1,y1 in ORIGINAL photo pixels) to erase: phone, fingers, objects.
EXCLUDE = [(283, 555, 470, 920), (250, 735, 470, 920)]
OUT = Path(__file__).resolve().parent / "portrait_cutout.png"


def make_cutout(photo, box=None, flip=FLIP):
    img = cv2.imread(str(photo))
    h, w = img.shape[:2]
    x0, y0, x1, y1 = box or (0, int(h * .22), int(w * .35), int(h * .63))

    # 1) separate subject from background (GrabCut seeded with a rectangle)
    gc = np.zeros((h, w), np.uint8)
    pad = 60
    rect = (max(0, x0), max(0, y0 - pad // 2), min(w, x1 + pad) - max(0, x0), min(h, y1 + pad) - max(0, y0 - pad // 2))
    bgd, fgd = np.zeros((1, 65)), np.zeros((1, 65))
    cv2.grabCut(img, gc, rect, bgd, fgd, 10, cv2.GC_INIT_WITH_RECT)
    mask = np.where((gc == 1) | (gc == 3), 255, 0).astype(np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((9, 9), np.uint8))

    for ex0, ey0, ex1, ey1 in EXCLUDE:
        mask[ey0:ey1, ex0:ex1] = 0
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones((13, 13), np.uint8))   # drop thin slivers
    crop, m = img[y0:y1, x0:x1], mask[y0:y1, x0:x1]
    m = cv2.GaussianBlur(m, (0, 0), 1.6).astype(np.float32) / 255

    # 2) luminance, local contrast, sharpen
    L = cv2.cvtColor(crop, cv2.COLOR_BGR2LAB)[:, :, 0]
    L = cv2.createCLAHE(clipLimit=2.6, tileGridSize=(8, 8)).apply(L).astype(np.float32) / 255
    blur = cv2.GaussianBlur(L, (0, 0), 1.4)
    L = np.clip(L + 0.9 * (L - blur), 0, 1)

    # 3) lift dark clothes/hair a little so the bust silhouette is visible, keep face contrast
    L = 0.14 + 0.86 * L
    out = L * m

    # soften the hard crop edge on the side where the body continues
    wpx = out.shape[1]
    fade = np.ones(wpx, np.float32); fade[-45:] = np.linspace(1, 0, 45)
    fade[:22] = np.minimum(fade[:22], np.linspace(0.0, 1, 22) ** 0.8)   # soften where the photo frame cuts you off
    out = out * fade[None, :]
    if flip:
        out = out[:, ::-1]
    return (np.clip(out, 0, 1) * 255).astype(np.uint8)


if __name__ == "__main__":
    box = tuple(map(int, sys.argv[2:6])) if len(sys.argv) >= 6 else None
    cv2.imwrite(str(OUT), make_cutout(sys.argv[1], box))
    print("wrote", OUT)
