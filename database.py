import os
from sqlalchemy import create_engine, text

# Renderの環境変数からデータベースURLを取得
DATABASE_URL = os.environ.get('DATABASE_URL')

# RenderのURL(postgres://)を、SQLAlchemyが認識できる形式(postgresql+psycopg2://)に書き換える
if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+psycopg2://", 1)

engine = create_engine(DATABASE_URL) if DATABASE_URL else None

def init_db():
    """データベースとテーブルを初期化（なければ作成）する関数"""
    if not engine:
        print("データベースURLが設定されていないため、初期化をスキップします。")
        return
    
    with engine.connect() as connection:
        connection.execute(text('''
            CREATE TABLE IF NOT EXISTS users (
                user_id TEXT PRIMARY KEY,
                state TEXT,
                city_name TEXT,
                lat REAL,  -- 緯度を保存
                lon REAL   -- 経度を保存
            )
        '''))
        connection.commit()

def set_user_state(user_id, state):
    """ユーザーの状態を設定または更新する関数"""
    if not engine: return
    with engine.connect() as connection:
        connection.execute(text("""
            INSERT INTO users (user_id, state) VALUES (:user_id, :state)
            ON CONFLICT(user_id) DO UPDATE SET state = :state
        """), {"user_id": user_id, "state": state})
        connection.commit()

def get_user_state(user_id):
    """ユーザーの状態を取得する関数"""
    if not engine: return None
    with engine.connect() as connection:
        result = connection.execute(text("SELECT state FROM users WHERE user_id = :user_id"), {"user_id": user_id}).fetchone()
        return result[0] if result else None

def set_user_location(user_id, city_name, lat, lon):
    """ユーザーの登録地と、状態を'normal'にリセットする関数"""
    if not engine: return
    with engine.connect() as connection:
        # 地点情報と、状態を'normal'にリセット
        connection.execute(text("""
            INSERT INTO users (user_id, state, city_name, lat, lon) VALUES (:user_id, 'normal', :city_name, :lat, :lon)
            ON CONFLICT(user_id) DO UPDATE SET 
                state = 'normal', city_name = :city_name, lat = :lat, lon = :lon
        """), {"user_id": user_id, "city_name": city_name, "lat": lat, "lon": lon})
        connection.commit()

def get_user_location(user_id):
    """ユーザーの登録地（地名、緯度、経度）を取得する関数"""
    if not engine: return (None, None, None)
    with engine.connect() as connection:
        result = connection.execute(text("SELECT city_name, lat, lon FROM users WHERE user_id = :user_id"), {"user_id": user_id}).fetchone()
        return result if result else (None, None, None)

def get_all_users_with_location():
    """登録地がある全ユーザーの情報を取得する関数（自動通知用）"""
    if not engine: return []
    with engine.connect() as connection:
        result = connection.execute(text("SELECT user_id, city_name, lat, lon FROM users WHERE city_name IS NOT NULL AND lat IS NOT NULL AND lon IS NOT NULL")).fetchall()
        return result

def get_users_without_location():
    """地点情報が登録されていない（city_name, lat, lonのいずれかがNULLの）全ユーザーの情報を取得する関数"""
    if not engine: return []
    with engine.connect() as connection:
        result = connection.execute(text("SELECT user_id FROM users WHERE city_name IS NULL OR lat IS NULL OR lon IS NULL")).fetchall()
        return [row[0] for row in result]