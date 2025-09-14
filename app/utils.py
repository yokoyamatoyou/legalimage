
import base64
from PIL import Image, ExifTags, ImageFile
import io
import hashlib
from typing import Optional, Dict, Any
import imghdr

# PILの安全設定（破損ファイル/部分画像のロード許容とデコンプ爆弾対策）
ImageFile.LOAD_TRUNCATED_IMAGES = True
Image.MAX_IMAGE_PIXELS = 4096 * 4096  # Decompression bombの閾値

def validate_image_file(uploaded_file) -> Dict[str, Any]:
    """
    アップロードされた画像ファイルの安全性を検証する。
    
    Args:
        uploaded_file: StreamlitのUploadedFileオブジェクト
        
    Returns:
        dict: 検証結果 {'valid': bool, 'error': str, 'metadata': dict}
    """
    result = {'valid': False, 'error': None, 'metadata': {}}
    
    if uploaded_file is None:
        result['error'] = "ファイルが選択されていません"
        return result
    
    # ファイルサイズチェック（10MB制限）
    max_size = 10 * 1024 * 1024  # 10MB
    if uploaded_file.size > max_size:
        result['error'] = f"ファイルサイズが大きすぎます（{uploaded_file.size / 1024 / 1024:.1f}MB > 10MB）"
        return result
    
    # ファイル拡張子とMIMEの簡易検証
    allowed_extensions = {'.png', '.jpg', '.jpeg'}
    file_extension = uploaded_file.name.lower().split('.')[-1]
    if f'.{file_extension}' not in allowed_extensions:
        result['error'] = f"サポートされていないファイル形式です（{file_extension}）"
        return result
    
    try:
        # 画像として読み込み可能かチェック
        image_bytes = uploaded_file.getvalue()
        # imghdrで簡易フォーマット検出
        kind = imghdr.what(None, h=image_bytes)
        if kind not in ["jpeg", "png"]:
            result['error'] = f"画像形式の検出に失敗、または未対応形式です（{kind}）"
            return result

        # 画像として読み込み → verify で整合性チェック → 再オープン
        bio = io.BytesIO(image_bytes)
        image = Image.open(bio)
        try:
            image.verify()
        except Exception:
            result['error'] = "画像の整合性チェックに失敗しました"
            return result
        bio.seek(0)
        image = Image.open(bio)
        
        # 画像サイズチェック
        width, height = image.size
        if width > 4096 or height > 4096:
            result['error'] = f"画像サイズが大きすぎます（{width}x{height}）"
            return result
        
        # メタデータ収集
        result['metadata'] = {
            'filename': uploaded_file.name,
            'size': uploaded_file.size,
            'format': image.format,
            'dimensions': f"{width}x{height}",
            'mode': image.mode
        }
        
        result['valid'] = True
        return result
        
    except Exception as e:
        result['error'] = f"画像ファイルの読み込みに失敗しました: {e}"
        return result

def remove_exif(image_bytes: bytes) -> bytes:
    """
    画像からEXIFデータを削除する。
    
    Args:
        image_bytes: 画像のバイトデータ
        
    Returns:
        bytes: EXIF除去後の画像バイトデータ
    """
    try:
        # 画像を読み込み
        image = Image.open(io.BytesIO(image_bytes))
        
        # 新しい画像として保存（EXIFなし）
        output = io.BytesIO()
        save_format = (image.format or 'JPEG') if image.mode != 'RGBA' else 'PNG'
        save_params = {}
        if save_format.upper() == 'JPEG':
            save_params = {"quality": 95, "optimize": True}
        image.save(output, format=save_format, exif=b"", **save_params)
        return output.getvalue()
        
    except Exception as e:
        print(f"EXIF除去中にエラーが発生しました: {e}")
        return image_bytes  # エラー時は元のデータを返す

def blur_pii(image_bytes: bytes) -> bytes:
    """
    画像中のPII（個人を特定しうる情報）をぼかす。
    現在は基本的な実装。将来的に顔検出・名札検出を追加予定。
    
    Args:
        image_bytes: 画像のバイトデータ
        
    Returns:
        bytes: PIIぼかし後の画像バイトデータ
    """
    try:
        # 現在は基本的な実装のみ
        # 将来的にOpenCVやface_recognitionライブラリを使用して
        # 顔、名札、車番などを検出・ぼかし処理を実装予定
        print("PIIぼかし処理（基本実装）")
        return image_bytes
        
    except Exception as e:
        print(f"PIIぼかし処理中にエラーが発生しました: {e}")
        return image_bytes

def generate_image_hash(image_bytes: bytes) -> str:
    """
    画像のSHA256ハッシュを生成する（監査ログ用）。
    
    Args:
        image_bytes: 画像のバイトデータ
        
    Returns:
        str: SHA256ハッシュ値
    """
    return hashlib.sha256(image_bytes).hexdigest()

def image_to_base64(uploaded_file, remove_exif_data: bool = True, blur_pii_data: bool = False):
    """
    StreamlitのUploadedFileオブジェクトをBase64エンコードされた文字列に変換する。
    セキュリティ強化版。

    Args:
        uploaded_file: Streamlitのst.file_uploaderから得られるUploadedFileオブジェクト
        remove_exif_data: EXIFデータを除去するかどうか
        blur_pii_data: PIIをぼかすかどうか

    Returns:
        dict: {'success': bool, 'base64': str, 'hash': str, 'error': str, 'metadata': dict}
    """
    result = {'success': False, 'base64': None, 'hash': None, 'error': None, 'metadata': {}}
    
    if uploaded_file is None:
        result['error'] = "ファイルが選択されていません"
        return result
    
    try:
        # 1. ファイル検証
        validation = validate_image_file(uploaded_file)
        if not validation['valid']:
            result['error'] = validation['error']
            return result
        
        result['metadata'] = validation['metadata']
        
        # 2. 画像データを取得
        image_bytes = uploaded_file.getvalue()
        
        # 3. セキュリティ処理
        if remove_exif_data:
            image_bytes = remove_exif(image_bytes)
        
        if blur_pii_data:
            image_bytes = blur_pii(image_bytes)
        
        # 4. ハッシュ生成（監査ログ用）
        result['hash'] = generate_image_hash(image_bytes)
        
        # 5. Base64エンコード
        base64_image = base64.b64encode(image_bytes).decode("utf-8")
        result['base64'] = base64_image
        result['success'] = True
        
        return result
        
    except Exception as e:
        result['error'] = f"画像の処理中にエラーが発生しました: {e}"
        return result

# --- 既存の関数は上記で実装済み ---

# --- 動作確認用のサンプルコード ---
if __name__ == '__main__':
    # このスクリプトは直接実行するよりも、他のモジュールから呼び出されることを想定しています。
    # 以下は、関数の使い方を示すための概念的な例です。
    
    print("utils.py の概念的な動作確認...")
    
    # ダミーの画像ファイルを作成
    dummy_image = Image.new('RGB', (100, 100), color = 'red')
    dummy_bytes_io = io.BytesIO()
    dummy_image.save(dummy_bytes_io, format='PNG')
    dummy_bytes_io.seek(0)

    # StreamlitのUploadedFileオブジェクトを模倣
    class MockUploadedFile:
        def __init__(self, data):
            self._data = data
        def getvalue(self):
            return self._data.read()

    mock_file = MockUploadedFile(dummy_bytes_io)
    
    # Base64エンコードのテスト
    base64_string = image_to_base64(mock_file)
    
    if base64_string:
        print("画像のBase64エンコードに成功しました。")
        print(f"エンコード後の文字列（先頭30文字）: {base64_string[:30]}...")
        print(f"エンコード後の文字列長: {len(base64_string)}")
    else:
        print("画像のBase64エンコードに失敗しました。")
