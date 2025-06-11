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

    return [f for f in input_files if os.path.basename(f) not in processed_basenames]

class CropViewer:
    def __init__(self, root, image_paths, output_dir):
        self.root = root
        self.root.title("画像一括トリミングビューア")

        self.image_paths = image_paths
        self.output_dir = output_dir
        self.current_index = 0
        self.image = None
        self.tk_image = None
        self.zoom_factor = 1.0
        self.mouse_x = 0
        self.mouse_y = 0
        self.crop_rect_id = None
        self.history = []
        self.state = "editing_1"
        self.crop_infos = {}

        self.build_ui()

        self.canvas_left.bind("<Motion>", self.on_mouse_move)
        self.canvas_left.bind("<Button-1>", self.save_and_progress_crop)
        self.canvas_left.bind("<Button-3>", self.go_back)
        self.canvas_center.bind("<Button-1>", lambda e: self.select_crop(1))
        self.canvas_right.bind("<Button-1>", lambda e: self.select_crop(2))
        self.root.bind("z", lambda e: self.adjust_zoom(0.1))
        self.root.bind("x", lambda e: self.adjust_zoom(-0.1))
        self.root.bind("q", lambda e: self.quit())
        self.root.bind_all("<MouseWheel>", self.on_mousewheel)

        self.load_image()

    def build_ui(self):
        frame = tk.Frame(self.root)
        frame.pack()
        self.canvas_left = tk.Canvas(frame, bg="gray")
        self.canvas_center = tk.Canvas(frame, bg="white")
        self.canvas_right = tk.Canvas(frame, bg="gray")

        self.canvas_left.pack(side=tk.LEFT)
        self.canvas_center.pack(side=tk.LEFT)
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
        for canvas in [self.canvas_left, self.canvas_center, self.canvas_right]:
            canvas.config(width=w, height=h)
            canvas.delete("all")

        self.canvas_left.create_image(0, 0, anchor='nw', image=self.tk_image)

        self.state = "editing_1"
        self.crop_infos = {}
        self.draw_crop_rect()
        self.update_center_preview()
        self.set_gray_on_right()

        print(f"[{self.current_index + 1}/{len(self.image_paths)}] {os.path.basename(path)} を処理中...")

    def set_gray_on_right(self):
        w, h = self.image.size
        gray = Image.new("RGB", (w, h), (200, 200, 200))
        self.tk_gray = ImageTk.PhotoImage(gray)
        self.canvas_right.create_image(0, 0, anchor='nw', image=self.tk_gray)

    def on_mouse_move(self, event):
        self.mouse_x = event.x
        self.mouse_y = event.y
        self.draw_crop_rect()
        if self.state == "editing_1":
            self.update_center_preview()
        elif self.state == "editing_2":
            self.update_right_preview()

    def adjust_zoom(self, delta):
        self.zoom_factor = max(1.0, round(self.zoom_factor + delta, 2))
        self.draw_crop_rect()
        if self.state == "editing_1":
            self.update_center_preview()
        elif self.state == "editing_2":
            self.update_right_preview()

    def on_mousewheel(self, event):
        self.adjust_zoom(-0.1 if event.delta > 0 else 0.1)

    def draw_crop_rect(self):
        if self.crop_rect_id:
            self.canvas_left.delete(self.crop_rect_id)
            self.crop_rect_id = None  # 念のためリセット

        if not self.image or self.state == "confirming":
            return  # ここで return しても、削除は先に実行される

        left, top, right, bottom = self.calculate_crop_coords(self.zoom_factor)
        self.crop_rect_id = self.canvas_left.create_rectangle(
            left, top, right, bottom, outline="red", width=2
        )

    def calculate_crop_coords(self, zoom):
        w, h = self.image.size
        crop_w = int(w / zoom)
        crop_h = int(h / zoom)
        half_w = crop_w // 2
        half_h = crop_h // 2
        cx = min(max(half_w, self.mouse_x), w - half_w)
        cy = min(max(half_h, self.mouse_y), h - half_h)
        return cx - half_w, cy - half_h, cx + half_w, cy + half_h

    def crop_at_zoom(self, zoom):
        left, top, right, bottom = self.calculate_crop_coords(zoom)
        return self.image.crop((left, top, right, bottom))

    def update_center_preview(self):
        w, h = self.image.size
        crop = self.crop_at_zoom(self.zoom_factor)
        preview = crop.resize((w, h), Image.LANCZOS)
        self.tk_preview_1 = ImageTk.PhotoImage(preview)
        self.canvas_center.delete("all")
        self.canvas_center.create_image(0, 0, anchor='nw', image=self.tk_preview_1)

    def update_right_preview(self):
        w, h = self.image.size
        crop = self.crop_at_zoom(self.zoom_factor)
        preview = crop.resize((w, h), Image.LANCZOS)
        self.tk_preview_2 = ImageTk.PhotoImage(preview)
        self.canvas_right.delete("all")
        self.canvas_right.create_image(0, 0, anchor='nw', image=self.tk_preview_2)

    def save_and_progress_crop(self, event=None):
        if self.state == "editing_1":
            self.crop_infos["1"] = self.crop_at_zoom(self.zoom_factor)
            self.crop_infos["zoom1"] = self.zoom_factor
            self.update_center_preview()
            self.state = "editing_2"
            self.zoom_factor = 1.0
            print("案1を確定しました。次に案2を設定してください。")
        elif self.state == "editing_2":
            self.crop_infos["2"] = self.crop_at_zoom(self.zoom_factor)
            self.crop_infos["zoom2"] = self.zoom_factor
            self.update_right_preview()
            self.state = "confirming"
            print("案2を確定しました。案1または案2をクリックして保存してください。")
        elif self.state == "confirming":
            print("案1・案2確定済み。元画像をコピー保存して次へ進みます。")
            self.save_original_copy()
            self.advance()

    def select_crop(self, variant):
        if variant == 1:
            if "1" in self.crop_infos:
                print("案1を保存して次へ進みます。")
                self.save_crop_variant(1)
            else:
                print("案1が未確定なので元画像をコピー保存します。")
                self.save_original_copy()
        elif variant == 2:
            if "2" in self.crop_infos:
                print("案2を保存して次へ進みます。")
                self.save_crop_variant(2)
            else:
                print("案2が未確定なので元画像をコピー保存します。")
                self.save_original_copy()

        self.advance()

    def advance(self):
        self.history.append(self.current_index)
        self.current_index += 1
        self.load_image()

    def save_crop_variant(self, variant):
        os.makedirs(self.output_dir, exist_ok=True)
        base_name = os.path.basename(self.image_path)
        name, ext = os.path.splitext(base_name)

        zoom = self.crop_infos.get(f'zoom{variant}', 1.0)

        if zoom == 1.0:
            save_name = f"{name}{ext}"
            save_path = os.path.join(self.output_dir, save_name)
            shutil.copy2(self.image_path, save_path)
            print(f"コピー保存（1.0x）: {save_name}")
            return

        zoom_suffix = f"_{zoom:.1f}x"
        save_name = f"{name}{zoom_suffix}{ext}"
        save_path = os.path.join(self.output_dir, save_name)

        cropped = self.crop_infos[str(variant)]
        w, h = self.image.size
        resized = cropped.resize((w, h), Image.LANCZOS)
        resized.save(save_path)
        print(f"保存: {save_name}")

    def save_original_copy(self):
        os.makedirs(self.output_dir, exist_ok=True)
        base_name = os.path.basename(self.image_path)
        save_path = os.path.join(self.output_dir, base_name)
        shutil.copy2(self.image_path, save_path)
        print(f"元画像コピー保存: {base_name}")

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
