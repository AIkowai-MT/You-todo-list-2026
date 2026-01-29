import os
import json
import requests
import traceback
import time
import pickle
from flask import Flask, request, jsonify, send_file, session, redirect, url_for
from youtube_transcript_api import YouTubeTranscriptApi
from urllib.parse import urlparse, parse_qs
from google_auth_oauthlib.flow import Flow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from dotenv import load_dotenv

# .envファイルから環境変数を読み込む
load_dotenv()

app = Flask(__name__)
# セッション管理用の秘密鍵（本来は環境変数などにすべきだが、デモ用に固定値）
app.secret_key = 'super_secret_key_for_task_app'

# APIキーの取得
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

# Google OAuth設定
CLIENT_SECRETS_FILE = "client_secret.json"
SCOPES = ['https://www.googleapis.com/auth/tasks']
API_SERVICE_NAME = 'tasks'
API_VERSION = 'v1'

# 開発環境用: HTTPSを要求しない設定
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

def get_google_service():
    """
    保存された認証情報からGoogle Tasks APIサービスを構築する
    """
    creds = None
    if 'credentials' in session:
        # セッションから復元（簡易実装: 本番ではDB等推奨）
        import google.oauth2.credentials
        creds_data = session['credentials']
        creds = google.oauth2.credentials.Credentials(**creds_data)
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
            session['credentials'] = credentials_to_dict(creds)
        else:
            return None
            
    return build(API_SERVICE_NAME, API_VERSION, credentials=creds)

def credentials_to_dict(credentials):
    return {
        'token': credentials.token,
        'refresh_token': credentials.refresh_token,
        'token_uri': credentials.token_uri,
        'client_id': credentials.client_id,
        'client_secret': credentials.client_secret,
        'scopes': credentials.scopes
    }

import json

# ... (imports)

def get_flow(state=None):
    """
    Flowオブジェクトを作成するヘルパー関数
    環境変数 GOOGLE_CLIENT_SECRET_JSON があればそれを優先し、
    なければファイル client_secret.json を使用する。
    """
    # 1. 環境変数から読み込み（クラウド用）
    client_config_json = os.environ.get('GOOGLE_CLIENT_SECRET_JSON')
    if client_config_json:
        try:
            client_config = json.loads(client_config_json)
            return Flow.from_client_config(
                client_config,
                scopes=SCOPES,
                state=state
            )
        except json.JSONDecodeError as e:
            print(f"Error parsing GOOGLE_CLIENT_SECRET_JSON: {e}")
            # フォールバックせずエラーにするか、ファイルを見るか。ここはファイルを見るようにする。

    # 2. ファイルから読み込み（ローカル用）
    if os.path.exists(CLIENT_SECRETS_FILE):
        return Flow.from_client_secrets_file(
            CLIENT_SECRETS_FILE,
            scopes=SCOPES,
            state=state
        )
    
    raise FileNotFoundError("Google Client Secrets not found (env or file)")

@app.route('/google/login')
def google_login():
    """Google認証を開始する"""
    try:
        flow = get_flow()
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
    # リダイレクトURIはGoogle Cloud Consoleの設定と一致させる必要がある
    flow.redirect_uri = url_for('google_callback', _external=True)
    
    authorization_url, state = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true')
    
    session['state'] = state
    return redirect(authorization_url)

@app.route('/google/callback')
def google_callback():
    """Google認証からのコールバック"""
    state = session['state']
    
    try:
        flow = get_flow(state=state)
    except Exception as e:
         return jsonify({"error": str(e)}), 500

    flow.redirect_uri = url_for('google_callback', _external=True)
    
    authorization_response = request.url
    # http->httpsの強制変換（プロキシ対策: Renderなどはhttpで受けるため）
    if os.environ.get('RENDER'):
        authorization_response = authorization_response.replace('http:', 'https:')

    flow.fetch_token(authorization_response=authorization_response)
    
    credentials = flow.credentials
    session['credentials'] = credentials_to_dict(credentials)
    
    return redirect('/')

@app.route('/api/google/status')
def google_status():
    """Google連携状態を確認"""
    service = get_google_service()
    return jsonify({"connected": service is not None})

@app.route('/api/google/tasklists')
def get_tasklists():
    """ユーザーのタスクリスト一覧を取得"""
    service = get_google_service()
    if not service:
        return jsonify({"error": "Not authenticated"}), 401
    
    try:
        results = service.tasklists().list(maxResults=10).execute()
        items = results.get('items', [])
        return jsonify(items)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/google/tasks', methods=['POST'])
def add_tasks():
    """タスクを追加する"""
    service = get_google_service()
    if not service:
        return jsonify({"error": "Not authenticated"}), 401
        
    data = request.json
    tasklist_id = data.get('tasklist_id')
    tasks = data.get('tasks', []) # [{'title': '...', 'notes': '...'}]
    
    if not tasklist_id or not tasks:
        return jsonify({"error": "Missing tasklist_id or tasks"}), 400
        
    results = []
    print(f"Adding {len(tasks)} tasks to list {tasklist_id}...")
    
    for task in tasks:
        try:
            body = {
                'title': task.get('title'),
                'notes': task.get('notes', '')
            }
            result = service.tasks().insert(tasklist=tasklist_id, body=body).execute()
            results.append({"status": "success", "id": result.get('id'), "title": result.get('title')})
            # レート制限回避のため少しウェイト
            time.sleep(0.5) 
        except Exception as e:
            print(f"Error adding task: {e}")
            results.append({"status": "error", "error": str(e), "title": task.get('title')})
            
    return jsonify(results)

def extract_video_id(url):
    """YouTube URLから動画IDを抽出する"""
    try:
        parsed_url = urlparse(url)
        if parsed_url.hostname == 'youtu.be':
            return parsed_url.path[1:]
        if parsed_url.hostname in ('www.youtube.com', 'youtube.com'):
            if parsed_url.path == '/watch':
                p = parse_qs(parsed_url.query)
                return p['v'][0]
            if parsed_url.path[:7] == '/embed/':
                return parsed_url.path.split('/')[2]
            if parsed_url.path[:3] == '/v/':
                return parsed_url.path.split('/')[2]
    except:
        pass
    return None

def extract_text_safe(transcript_data):
    """
    字幕データからテキストを安全に抽出するヘルパー関数
    """
    text_parts = []
    if not transcript_data:
        return ""
    if not isinstance(transcript_data, list):
        transcript_data = [transcript_data]

    for item in transcript_data:
        try:
            if hasattr(item, 'text'):
                text_parts.append(item.text)
            elif isinstance(item, dict) and 'text' in item:
                text_parts.append(item['text'])
            elif isinstance(item, str):
                text_parts.append(item)
            else:
                s = str(item)
                text_parts.append(s)
        except Exception as e:
            print(f"Error parsing item: {e}")
            continue
    return " ".join(text_parts)

def get_available_gemini_models(api_key):
    """
    利用可能なGeminiモデルを動的に取得し、優先順位順にリストで返す
    """
    # キャッシュなどを検討しても良いが、一旦毎回確認（安全重視）
    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
        response = requests.get(url)
        
        if response.status_code != 200:
            print(f"ListModels failed: {response.status_code} {response.text}")
            return []

        data = response.json()
        models = data.get('models', [])
        
        # generateContentをサポートするモデルを抽出
        candidates = []
        for m in models:
            methods = m.get('supportedGenerationMethods', [])
            if 'generateContent' in methods:
                candidates.append(m['name'])
        
        if not candidates:
            return []

        # 優先順位に基づいて並べ替え
        priority_keywords = ['gemini-1.5-flash', 'gemini-1.5-pro', 'gemini-2.0', 'gemini-pro']
        sorted_models = []
        
        for keyword in priority_keywords:
            for model_name in candidates:
                if keyword in model_name and model_name not in sorted_models:
                    sorted_models.append(model_name)
        
        for model_name in candidates:
            if model_name not in sorted_models:
                sorted_models.append(model_name)

        return sorted_models

    except Exception as e:
        print(f"Error checking models: {e}")
        return []

def call_gemini_api(prompt_text, api_key):
    """
    Gemini APIを呼び出す共通関数
    """
    print("Calling Gemini API...")
    available_models = get_available_gemini_models(api_key)
    
    if available_models:
        models_to_try = available_models
    else:
        models_to_try = [
            "models/gemini-1.5-flash",
            "models/gemini-1.5-flash-001",
            "models/gemini-pro",
            "models/gemini-1.0-pro"
        ]

    payload = {
        "contents": [{"parts": [{"text": prompt_text}]}],
        "generationConfig": {"response_mime_type": "application/json"}
    }
    
    last_error = None

    for model in models_to_try:
        if not model: continue
        if not model.startswith("models/"): model = f"models/{model}"

        try:
            print(f"Trying model: {model}...")
            api_url = f"https://generativelanguage.googleapis.com/v1beta/{model}:generateContent?key={api_key}"
            response = requests.post(api_url, json=payload, headers={'Content-Type': 'application/json'})
            
            if response.status_code == 200:
                result_json = response.json()
                if 'candidates' in result_json and result_json['candidates']:
                    content_text = result_json['candidates'][0]['content']['parts'][0]['text']
                    return json.loads(content_text)
                else:
                    raise Exception("No candidates in response")
            elif response.status_code == 429:
                print(f"Model {model} quota exceeded. Trying next...")
                last_error = f"Quota exceeded for {model}"
            else:
                print(f"Model {model} failed: {response.status_code}")
                last_error = f"{model} error: {response.text}"
                
        except Exception as e:
            print(f"Error model {model}: {e}")
            last_error = f"{e} (Traceback: {traceback.format_exc()})"
            
    raise Exception(f"All models failed. Last error: {last_error}")

def process_single_video(url, api_key, provided_transcript=None):
    """
    単一の動画を解析する (Map処理)
    provided_transcript: クライアント側ですでに取得した字幕があればこれを使う
    """
    print(f"Processing URL: {url}")
    video_id = extract_video_id(url)
    if not video_id:
        return {"error": "Invalid URL", "url": url}

    transcript_text = ""
    
    # 0. クライアント提供の字幕があれば優先使用 (サーバーサイドブロック回避の切り札)
    if provided_transcript:
        print("Using provided transcript from client (skipping server-side fetch)")
        transcript_text = provided_transcript
    else: 
        # 以下、従来のサーバーサイド取得ロジックのための変数初期化
        cookies_file_path = None
    
        # Cookiesの準備
        if os.path.exists('cookies.txt'):
             cookies_file_path = 'cookies.txt'
             print(f"Using cookies from local file: {cookies_file_path}")
        elif os.environ.get('YOUTUBE_COOKIES'):
            try:
                import tempfile
                with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as tf:
                    tf.write(os.environ.get('YOUTUBE_COOKIES'))
                    cookies_file_path = tf.name
                print(f"Using cookies from env: {cookies_file_path}")
            except Exception as e:
                print(f"Failed to create cookies file: {e}")

    # transcript_text がまだ空（クライアント提供なし）の場合のみサーバーサイド取得を実行
    if not transcript_text:
        try:
            # 方法A: youtube-transcript-api (既存)
            print("Attempting youtube-transcript-api...")
            yt_instance = YouTubeTranscriptApi()
        raw_data = None
        
        methods = [
            lambda: yt_instance.list_transcripts(video_id, cookies=cookies_file_path).find_transcript(['ja', 'en']).fetch(),
            lambda: yt_instance.get_transcript(video_id, cookies=cookies_file_path),
            lambda: YouTubeTranscriptApi.get_transcript(video_id, languages=['ja', 'en'], cookies=cookies_file_path)
        ]
        
        for method in methods:
            try:
                data = method()
                if hasattr(data, 'find_transcript'): 
                     try: t = data.find_transcript(['ja', 'en']); raw_data = t.fetch()
                     except: raw_data = next(iter(data)).fetch()
                else:
                     raw_data = data
                if raw_data: break
            except: continue
            
        if raw_data:
            transcript_text = extract_text_safe(raw_data)
        
        # 方法B: yt-dlp (フォールバック)
        if not transcript_text:
            print("youtube-transcript-api failed, trying yt-dlp...")
            import yt_dlp
            
            ydl_opts = {
                'skip_download': True,
                'writesubtitles': True,
                'writeautomaticsub': True,
                'subtitleslangs': ['ja', 'en'],
                'subtitlesformat': 'json3', # JSON形式で取得
                'quiet': True,
                'cookiefile': cookies_file_path
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                # 字幕データを探す
                import json
                
                # 自動字幕と手動字幕の両方を探す
                subtitles = info.get('subtitles', {}) or info.get('automatic_captions', {})
                
                target_lang = None
                if 'ja' in subtitles: target_lang = 'ja'
                elif 'en' in subtitles: target_lang = 'en'
                else: 
                     # 他の言語でもあれば使う
                     for lang in subtitles:
                         if lang.startswith('ja') or lang.startswith('en'):
                             target_lang = lang
                             break
                     if not target_lang and subtitles:
                         target_lang = list(subtitles.keys())[0]

                if target_lang:
                    # JSON3形式の字幕URLを取得
                    subs_list = subtitles[target_lang]
                    json3_url = next((s['url'] for s in subs_list if s.get('ext') == 'json3'), None)
                    
                    if not json3_url:
                        # json3がない場合はvttなどを取得して無理やりテキスト化もできるが、
                        # 今回はjson3が取れるケース（yt-dlp内部処理）に期待するか、
                        # download=Trueにしてファイルを読む手が普通。
                        # メモリ上で完結させるため、requestsでjson3を取る
                        json3_url = subs_list[0]['url'] # とりあえず最初のURL
                        
                    print(f"Fetching subtitles from: {json3_url}")
                    allow_redirects = True
                    # json3リクエストにもcookiesが必要な場合がある
                    # yt-dlpのcookie jarを使うのがベストだが、ここでは簡易的にrequestsでトライ
                    # requestsのcookies引数にcookiejarを渡すのは手間なので、headersで試みるか、
                    # あるいはyt-dlpのdownload機能を使ってファイルに落とすのが確実。
                    
                    # 確実性を取ってファイルダウンロード方式に変更
                    # ファイルは /tmp/ (Render対応) に保存
                    
            # 再度 yt-dlp (ファイルダウンロード方式)
            print("Trying yt-dlp file download mode...")
            import tempfile
            with tempfile.TemporaryDirectory() as tmpdir:
                out_tmpl = os.path.join(tmpdir, '%(id)s')
                ydl_opts = {
                    'skip_download': True,
                    'writesubtitles': True,
                    'writeautomaticsub': True,
                    'subtitleslangs': ['ja', 'en'],
                    'quiet': False, # ログ出力有効化
                    'verbose': True, # デバッグモード
                    'cookiefile': cookies_file_path,
                    'outtmpl': out_tmpl,
                    'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    'http_headers': {
                        'Referer': 'https://www.youtube.com/',
                        'Accept-Language': 'ja-JP,ja;q=0.9,en-US;q=0.8,en;q=0.7'
                    },
                    'nocheckcertificate': True,
                }
                
                try:
                    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                        ydl.download([url])
                    
                    # 生成されたファイルを探索 (.ja.vtt, .en.vtt など)
                    found_text = ""
                    for filename in os.listdir(tmpdir):
                        if filename.endswith('.vtt'):
                            print(f"Found subtitle file: {filename}")
                            # vttを簡易パース
                            with open(os.path.join(tmpdir, filename), 'r', encoding='utf-8') as f:
                                lines = f.readlines()
                                # WEBVTTヘッダーやタイムスタンプを除去してテキストのみ抽出
                                seen_lines = set() # 重複除去
                                for line in lines:
                                    line = line.strip()
                                    if not line: continue
                                    if line == 'WEBVTT': continue
                                    if '-->' in line: continue
                                    if line.isdigit(): continue # 行番号
                                    if line not in seen_lines:
                                        found_text += line + " "
                                        seen_lines.add(line)
                            break # 1つ見つかればOK
                    
                    transcript_text = found_text
                    
                except Exception as e:
                    print(f"yt-dlp download failed: {e}")
                    traceback.print_exc()

    except Exception as e:
        print(f"Subtitle extraction overall failed: {e}")
        traceback.print_exc()

    # 一時ファイルの削除
    if cookies_file_path and os.path.exists(cookies_file_path) and os.environ.get('YOUTUBE_COOKIES'):
            try: os.unlink(cookies_file_path)
            except: pass

    # 方法C: Invidious API (第3の矢: IPブロック回避)
    if not transcript_text:
        print("yt-dlp failed. Trying Invidious API fallback...")
        # インスタンスリストを拡充
        invidious_instances = [
            "https://inv.tux.pizza",
            "https://vid.puffyan.us",
            "https://inv.nadeko.net",
            "https://invidious.jing.rocks",
            "https://yt.artemislena.eu",
            "https://invidious.flokinet.to",
            "https://invidious.privacydev.net", 
            "https://iv.ggtyler.dev"
        ]
        
        # ランダムシャッフルして負荷分散（毎回同じ順序だと最初が落ちていると遅い）
        import random
        random.shuffle(invidious_instances)
        
        for instance in invidious_instances:
            try:
                print(f"Trying Invidious instance: {instance}")
                
                # 動画メタデータからキャプション情報を得る
                meta_url = f"{instance}/api/v1/videos/{video_id}"
                meta_res = requests.get(meta_url, timeout=15) # タイムアウト延長
                
                if meta_res.status_code != 200:
                    print(f"  -> Meta fetch failed: {meta_res.status_code}")
                    continue
                    
                meta_data = meta_res.json()
                captions = meta_data.get('captions', [])
                
                target_caption = None
                # 日本語優先
                for cap in captions:
                    if cap.get('language') == 'ja':
                        target_caption = cap
                        break
                # なければ英語
                if not target_caption:
                    for cap in captions:
                        if cap.get('language') == 'en':
                            target_caption = cap
                            break
                            
                if not target_caption:
                    print(f"  -> No Japanese/English caption found in {instance}")
                    continue
                
                cap_path = target_caption.get('url')
                full_cap_url = f"{instance}{cap_path}" if cap_path.startswith('/') else f"{instance}/{cap_path}"
                
                print(f"Fetching caption from: {full_cap_url}")
                cap_res = requests.get(full_cap_url, timeout=15)
                
                if cap_res.status_code == 200:
                    vtt_content = cap_res.text
                    # WebVTT to Text (簡易パーサー)
                    lines = vtt_content.splitlines()
                    found_text = ""
                    seen_lines = set()
                    for line in lines:
                        line = line.strip()
                        if not line: continue
                        if line == 'WEBVTT': continue
                        if '-->' in line: continue
                        if line.isdigit(): continue
                        # 重複排除しつつテキスト化
                        if line not in seen_lines:
                            found_text += line + " "
                            seen_lines.add(line)
                    
                    transcript_text = found_text
                    if transcript_text:
                        print(f"Successfully fetched from Invidious ({instance})!")
                        break
                else:
                    print(f"  -> Caption fetch failed: {cap_res.status_code}")
                    
            except Exception as e:
                print(f"Invidious instance {instance} error: {e}")
                continue

    if not transcript_text:
        # 詳細なログをサーバーに残すためprint
        print(f"All methods failed for {url}")
        return {"error": "Subtitle not found (Server blocked by YouTube. Cookies setup required or invalid).", "url": url}



    # 2. Gemini解析 (単体)
    try:
        prompt = f"""
        以下のYouTube動画の字幕テキストを解析し、情報を抽出してください。
        
        出力JSON形式:
        {{
            "title": "動画タイトル(推測)",
            "summary": "要約(200文字以内)",
            "tasks": [{{ "id": 1, "text": "タスク内容", "completed": false }}]
        }}
        
        字幕:
        {transcript_text[:10000]}
        """
        result = call_gemini_api(prompt, api_key)
        result['url'] = url
        result['transcript'] = transcript_text # 個別ダウンロード用
        return result
    except Exception as e:
        error_trace = traceback.format_exc()
        print(f"Error in process_single_video for {url}: {e}\n{error_trace}")
        return {
            "error": f"AI analysis error: {str(e)}", 
            "error_detail": error_trace,
            "url": url, 
            "transcript": transcript_text
        }


@app.route('/')
def index():
    return send_file('index.html')

@app.route('/api/analyze', methods=['POST'])
def analyze_videos():
    if not GEMINI_API_KEY:
        return jsonify({"error": "Gemini APIキーが設定されていません。"}), 500

    data = request.json
    
    # 新仕様: items [{"url": "...", "transcript": "..."}]
    items = data.get('items', [])
    
    # 旧仕様: urls ["..."] (後方互換)
    urls = data.get('urls', [])
    if 'url' in data and data['url']:
        urls.append(data['url'])
        
    # itemsがない場合はurlsから構築
    if not items and urls:
        items = [{"url": u.strip(), "transcript": None} for u in urls if u.strip()]
    
    if not items:
        return jsonify({"error": "URLまたはアイテムが必要です"}), 400

    print(f"Start analyzing {len(items)} videos...")
    
    results = []
    valid_results = []
    
    # 1. Mapフェーズ: 個別解析
    for item in items:
        url = item.get('url')
        provided_transcript = item.get('transcript')
        
        # URLがない場合はスキップ（transcriptだけでの解析は今回は想定外だが、将来的にありかも）
        if not url: continue
        
        res = process_single_video(url, GEMINI_API_KEY, provided_transcript=provided_transcript)
        results.append(res)
        if "error" not in res:
            valid_results.append(res)

    # 単一動画の場合はそのまま返す
    if len(items) == 1:
        if "error" in results[0]:
            return jsonify({"error": results[0]["error"]}), 500
        return jsonify(results[0])

    # 2. Reduceフェーズ: 統合解析 (複数動画の場合のみ)
    if not valid_results:
         return jsonify({
             "error": "全ての動画の解析に失敗しました。",
             "details": results
         }), 500

    print("Consolidating results...")
    
    # 統合用の入力を生成
    consolidation_input = ""
    for i, res in enumerate(valid_results):
        consolidation_input += f"""
        [動画{i+1}: {res.get('title', '不明')}]
        要約: {res.get('summary', '')}
        タスク: {json.dumps(res.get('tasks', []), ensure_ascii=False)}
        
        """

    try:
        prompt = f"""
        あなたは「複数の動画から情報を集約し、マスタータスクリストを作る」エキスパートです。
        以下の複数の動画の解析結果（要約とタスク）を読み込み、全てを統合した「マスター要約」と「マスタータスクリスト」を作成してください。
        
        ルール:
        1. タスクリストは、重複している内容があれば統合してください。
        2. 全体としてどのような学びやアクションが必要かを要約してください。
        3. 出力は以下のJSON形式のみです。
        
        {{
            "title": "統合レポート: {valid_results[0].get('title', '')} 他{len(valid_results)-1}本",
            "summary": "全動画の統合要約(300文字以内)",
            "tasks": [
                {{ "id": 1, "text": "統合されたタスク1", "completed": false }}
            ]
        }}
        
        入力データ:
        {consolidation_input}
        """
        
        final_result = call_gemini_api(prompt, GEMINI_API_KEY)
        
        # 個別結果もクライアントに返すために含める
        final_result['individual_results'] = results
        
        # 統合トランスクリプト（ダウンロード用）
        combined_transcript = ""
        for res in valid_results:
            combined_transcript += f"【動画: {res.get('title','')}】\n{res.get('transcript','')}\n\n{'='*20}\n\n"
        final_result['transcript'] = combined_transcript

        return jsonify(final_result)

    except Exception as e:
        error_detail = traceback.format_exc()
        print(f"Consolidation error: {e}\n{error_detail}")
        # 統合に失敗しても個別結果は返す
        return jsonify({
            "title": "解析完了（統合失敗）",
            "summary": "動画の個別解析は完了しましたが、統合処理に失敗しました。各動画の結果は下に表示されています。",
            "tasks": [],
            "individual_results": results,
            "error": str(e),
            "error_detail": error_detail
        })

@app.route('/api/debug_info')
def debug_info():
    """デバッグ情報を返す (認証なし・開発用)"""
    import yt_dlp
    
    cookies_exists = os.path.exists('cookies.txt')
    env_cookies_len = len(os.environ.get('YOUTUBE_COOKIES', ''))
    
    # yt-dlpからバージョン取得
    ytdlp_version = yt_dlp.version.__version__
    
    # 実際にクッキーファイルが生成できるかテスト
    temp_cookie_path = "Not created"
    if os.environ.get('YOUTUBE_COOKIES'):
        try:
            import tempfile
            with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as tf:
                tf.write(os.environ.get('YOUTUBE_COOKIES'))
                temp_cookie_path = tf.name
            # すぐ消す
            os.unlink(temp_cookie_path)
            temp_cookie_path = "Created successfully"
        except Exception as e:
            temp_cookie_path = f"Error: {e}"

    return jsonify({
        "cookies_txt_exists": cookies_exists,
        "cookies_txt_size": os.path.getsize('cookies.txt') if cookies_exists else 0,
        "env_YOUTUBE_COOKIES_len": env_cookies_len,
        "temp_cookie_creation_test": temp_cookie_path,
        "yt_dlp_version": ytdlp_version,
        "cwd": os.getcwd(),
        "ls_cwd": os.listdir('.')
    })

if __name__ == '__main__':
    print("----------------------------------------------------------------")
    print("Server starting at http://localhost:8000")
    print("Google Auth: Ready (client_secret.json found)" if os.path.exists(CLIENT_SECRETS_FILE) else "Google Auth: WARNING (client_secret.json not found)")
    print("----------------------------------------------------------------")
    print("Server starting...")
    print("----------------------------------------------------------------")
    # Renderなどのクラウド環境ではPORT環境変数が渡される
    port = int(os.environ.get('PORT', 8000))
    app.run(host='0.0.0.0', port=port)
