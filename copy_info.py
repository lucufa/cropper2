import os
from PIL import Image, PngImagePlugin

def copy_png_info(from_folder, to_folder):
    # フォルダ内のファイルをループ
    for file_name in os.listdir(from_folder):
        # ファイルの拡張子をチェック
        if file_name.lower().endswith(('.png', '.jpeg', '.jpg')):
            from_file_path = os.path.join(from_folder, file_name)
            to_file_path = os.path.join(to_folder, file_name)

            # toフォルダに同名ファイルが存在するか確認
            if os.path.exists(to_file_path):
                try:
                    # fromフォルダの画像を開く
                    from_img = Image.open(from_file_path)

                    # toフォルダの画像を開く
                    to_img = Image.open(to_file_path)

                    # PNG Infoをコピー
                    if isinstance(from_img.info, dict):
                        png_info = PngImagePlugin.PngInfo()
                        for key, value in from_img.info.items():
                            # 値を文字列に変換
                            if not isinstance(value, str):
                                value = str(value)
                            png_info.add_text(key, value)

                        # toフォルダの画像にPNG Infoを保存して上書き
                        to_img.save(to_file_path, "png", pnginfo=png_info)
                        #print(f"Copied PNG Info from {from_file_path} to {to_file_path}")
                    else:
                        print(f"No PNG Info found in {from_file_path}")

                except Exception as e:
                    print(f"Error processing {file_name}: {e}")

if __name__ == "__main__":
    from_folder = "input"  # `from`フォルダのパス
    to_folder   = "output" # `to`フォルダのパス

    # スクリプトのディレクトリを取得
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)

    copy_png_info(from_folder, to_folder)
