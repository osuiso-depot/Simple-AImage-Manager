import os
import uuid
import hashlib
import datetime
import pytz
import struct
import zlib
import regex as re

class SDChunk:
    def conv_local_date(self, t: str, frmt: str = "%Y-%m-%d %H:%M:%S.%f") -> str:
        """
        ローカル時間に変換＋ミリ秒を3桁
        """
        dt = datetime.datetime.fromtimestamp(int(t) / 1000.0, tz=pytz.utc)
        local_dt = dt.astimezone()  # システムのローカルタイムゾーンに変換
        return local_dt.strftime(frmt)[:-3]  # ミリ秒を3桁に調整

    def create_data(self, fileobject, savedir: str):
        """
        保存するデータをオブジェクトにまとめる関数。
        作成できなければ None を返す
        """
        try:
            chunks = self.png_chunk(fileobject['path'])

            # 生成パラメータは PNG chunk の parameters のキーで格納されている
            params = next((chunk for chunk in chunks if chunk['keyword'] == "parameters"), None)
            if not params or 'text' not in params:
                raise ValueError(f"ERROR: {__file__} {fileobject['path']} a img has irregular chunk")

            data = self.parse_parameter(params['text'])

            # ファイル情報の取得
            name = os.path.basename(fileobject['path'])
            size = os.path.getsize(fileobject['path'])
            file_type = 'image/png'  # 固定値
            with open(fileobject['path'], 'rb') as f:
                file_hash = hashlib.sha256(f.read()).hexdigest()
            latest = str(int(os.path.getmtime(fileobject['path']) * 1000))
            path = os.path.abspath(fileobject['path'])

            # UI情報
            ui = {
                'localizeDate': self.conv_local_date(latest),
                'checked': False,
            }
            user = {
                'comment': ""
            }

            return {
                'index': None,  # 必要に応じて設定
                'uuid': str(uuid.uuid4()),
                'name': name,
                'size': size,
                'type': file_type,
                'hash': file_hash,
                'latest': latest,
                'path': path,
                'data': data,
                'ui': ui,
                'user': user
            }
        except Exception as e:
            print(e)
            return None

    def parse_parameter(self, text: str) -> dict:
        """
        prompt parameter text を objectに整形する
        SDWebUIで生成されたprompt, negative prompt, optionsのパラメータを文字列から分割して
        オブジェクトに格納して返す
        """
        sptext = text.split("\n")
        line_i = 0
        prompt = ""
        negative = ""
        options = ""
        pattern_negaline = r"Negative prompt: "

        while line_i < len(sptext) and not sptext[line_i].strip().startswith("Negative prompt"):
            prompt += sptext[line_i].strip() + "\n"
            line_i += 1

        while line_i < len(sptext) and not re.match(r"Steps: \d+", sptext[line_i].strip()):
            negative += re.sub(pattern_negaline, "", sptext[line_i].strip()) + "\n"
            line_i += 1

        if line_i < len(sptext):
            options = sptext[line_i].strip()

        return {'prompt': prompt, 'negative': negative, 'options': options}

    # 本のコード
    def png_chunk(self, pngpath: str) -> list:
        """
        PNGファイルのtEXtおよびiTXtチャンクを解析し、内容を返す。
        非コピー可能な文字を適切に処理する。
        """
        try:
            with open(pngpath, 'rb') as f:
                data = f.read()

            chunks = []
            offset = 8  # PNGシグネチャの後から開始
            while offset < len(data):
                length = struct.unpack('>I', data[offset:offset + 4])[0]
                chunk_type = data[offset + 4:offset + 8].decode('ascii')
                chunk_data = data[offset + 8:offset + 8 + length]
                offset += 12 + length  # 長さ + タイプ + CRC

                if chunk_type in ('tEXt', 'iTXt'):
                    try:
                        keyword, text = chunk_data.split(b'\x00', 1)
                        keyword_str = keyword.decode('utf-8', errors='replace')
                        text_str = text.decode('utf-8', errors='ignore')

                        # ヌル文字が先頭に含まれることがあるので削除
                        text_str = text_str.replace('\x00', '')

                        chunks.append({
                            'keyword': keyword_str,
                            'text': text_str
                        })
                    except Exception as e:
                        chunks.append({
                            'keyword': 'Invalid',
                            'text': f'Error decoding text: {e}'
                        })

            return chunks
        except Exception as err:
            raise ValueError(f"Error processing PNG file: {err}")

# 使用例
# fileobject = type('FileObject', (object,), {'path': 'path_to_png_file.png'})
# sd_chunk = SDChunk()
# data = sd_chunk.create_data(fileobject, 'save_directory')
# print(data)
