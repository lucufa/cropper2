import tkinter as tk
from PIL import Image, ImageTk
import os
import sys
import glob
import argparse
import shutil
import re

def natural_sort_key(s):
    return [int(text) if text.isdigit() else text.lower()
            for text in re.split(r'(\d+)', os.path.basename(s))]

def strip_zoom_suffix(filename):
    """ファイル名から _1.2x のような倍率部分を除去"""
    name, ext = os.path.splitext(filename)
    if '_' in name:
        base, maybe_zoom = name.rsplit('_', 1)
        if re.fullmatch(r"\d+(\.\d+)?x", maybe_zoom):
            return f"{base}{ext}"
    return filename

def collect_images_from_directory(input_dir, output_dir):
    input_files = glob.glob(os.path.join(input_dir, "*.png"))
    input_files = sorted(input_files, key=natural_sort_key)

    output_files = glob.glob(os.path.join(output_dir, "*.png"))
    processed_basenames = {
        strip_zoom_suffix(os.path.basename(f)) for f in output_files
    }

    filtered = []
    for f in input_files:
        base_name = os.path.basename(f)
        if base_name not in processed_basenames:
            filtered.append(f)
        else:
            print(f"スキップ（すでにバリエーションあり）: {base_name}")
    return filtered

class CropViewer:
    def __init__(self, root, image_paths, output_dir):
        self.root = root
        self.root.title("画像一括トリミングビューア")

        self.image_paths = image_paths
        self.output_dir = output_dir
        self.current_index = 0
        self.image = None
        self.tk_image = None
        self.tk_preview = None
        self.zoom_factor = 1.0
        self.mouse_x = 0
        self.mouse_y = 0
        self.crop_rect_id = None
        self.current_crop = None
        self.history = []

        self.build_ui()

        self.canvas_left.bind("<Motion>", self.on_mouse_move)
        self.canvas_left.bind("<Button-1>", self.save_and_next)
        self.canvas_left.bind("<Button-3>", self.go_back)
        self.root.bind("z", lambda e: self.adjust_zoom(0.1))
        self.root.bind("x", lambda e: self.adjust_zoom(-0.1))
        self.root.bind("q", lambda e: self.quit())
        self.root.bind_all("<MouseWheel>", self.on_mousewheel)

        self.load_image()

    def build_ui(self):
        frame = tk.Frame(self.root)
        frame.pack()
        self.canvas_left = tk.Canvas(frame, bg="gray")
        self.canvas_left.pack(side=tk.LEFT)
        self.canvas_right = tk.Canvas(frame, bg="white")
        self.canvas_right.pack(side=tk.LEFT)

    def load_image(self):
        if self.current_index >= len(self.image_paths):
            print("すべての画像の処理が完了しました。")
            self.root.destroy()
            return

        path = self.image_paths[self.current_index]
        self.image_path = path
        self.zoom_factor = 1.0
        self.image = Image.open(path)
        self.tk_image = ImageTk.PhotoImage(self.image)

        w, h = self.image.size
        self.canvas_left.config(width=w, height=h)
        self.canvas_right.config(width=w, height=h)
        self.canvas_left.delete("all")
        self.canvas_right.delete("all")
        self.canvas_left.create_image(0, 0, anchor='nw', image=self.tk_image)

        self.draw_crop_rect()
        self.update_preview()
        print(f"[{self.current_index + 1}/{len(self.image_paths)}] {os.path.basename(path)} を処理中...")

    def on_mouse_move(self, event):
        self.mouse_x = event.x
        self.mouse_y = event.y
        self.draw_crop_rect()
        self.update_preview()

    def adjust_zoom(self, delta):
        self.zoom_factor = max(1.0, round(self.zoom_factor + delta, 2))
        self.draw_crop_rect()
        self.update_preview()

    def calculate_crop_coords(self):
        w, h = self.image.size
        crop_w = int(w / self.zoom_factor)
        crop_h = int(h / self.zoom_factor)
        half_w = crop_w // 2
        half_h = crop_h // 2

        cx = min(max(half_w, self.mouse_x), w - half_w)
        cy = min(max(half_h, self.mouse_y), h - half_h)

        left = cx - half_w
        top = cy - half_h
        right = left + crop_w
        bottom = top + crop_h

        return left, top, right, bottom

    def draw_crop_rect(self):
        if not self.image:
            return

        left, top, right, bottom = self.calculate_crop_coords()

        if self.crop_rect_id:
            self.canvas_left.delete(self.crop_rect_id)

        self.crop_rect_id = self.canvas_left.create_rectangle(
            left, top, right, bottom, outline="red", width=2
        )

    def update_preview(self):
        if not self.image:
            return

        left, top, right, bottom = self.calculate_crop_coords()
        cropped = self.image.crop((left, top, right, bottom))
        w, h = self.image.size
        preview = cropped.resize((w, h), Image.LANCZOS)
        self.tk_preview = ImageTk.PhotoImage(preview)
        self.canvas_right.delete("all")
        self.canvas_right.create_image(0, 0, anchor='nw', image=self.tk_preview)

        self.current_crop = cropped

    def save_crop(self):
        if not self.image_path:
            return

        os.makedirs(self.output_dir, exist_ok=True)
        base_name = os.path.basename(self.image_path)
        name, ext = os.path.splitext(base_name)

        if self.zoom_factor == 1.0:
            save_path = os.path.join(self.output_dir, base_name)
            shutil.copy2(self.image_path, save_path)
            print(f"コピー: {base_name}（倍率1.0）")
        else:
            zoom_suffix = f"_{self.zoom_factor:.1f}x"
            save_name = f"{name}{zoom_suffix}{ext}"
            save_path = os.path.join(self.output_dir, save_name)

            if not self.current_crop:
                return
            w, h = self.image.size
            resized = self.current_crop.resize((w, h), Image.LANCZOS)
            resized.save(save_path)
            print(f"保存: {save_name}")

    def save_and_next(self, event=None):
        self.save_crop()
        self.history.append(self.current_index)
        self.current_index += 1
        self.load_image()

    def go_back(self, event=None):
        if self.history:
            self.current_index = self.history.pop()
            print(f"戻る: {os.path.basename(self.image_paths[self.current_index])}")
            self.load_image()
        else:
            print("戻れる画像がありません。")

    def quit(self):
        print("ユーザーによって処理が終了されました。")
        self.root.destroy()

    def on_mousewheel(self, event):
        self.adjust_zoom(0.1 if event.delta > 0 else -0.1)

def parse_args():
    parser = argparse.ArgumentParser(description="画像の一括トリミング＆リサイズビューア")
    parser.add_argument("-i", "--input_dir", default="input", help="入力ディレクトリ（デフォルト: input）")
    parser.add_argument("-o", "--output_dir", default="output", help="出力ディレクトリ（デフォルト: output）")
    return parser.parse_args()

if __name__ == "__main__":
    args = parse_args()
    image_list = collect_images_from_directory(args.input_dir, args.output_dir)

    if not image_list:
        print("すべての画像が既に処理済みです。")
        sys.exit()

    root = tk.Tk()
    app = CropViewer(root, image_list, args.output_dir)
    root.mainloop()
