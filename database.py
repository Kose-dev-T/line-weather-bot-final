import os
from sqlalchemy import create_engine, text

DATABASE_URL = os.environ.get('DATABASE_URL')

# RenderのURL(postgres://)を、SQLAlchemyがpsycopg2を確実に使うための形式に書き換える
if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+psycopg2://", 1)

engine = create_engine(DATABASE_URL) if DATABASE_URL else None

def init_db():
    if not engine:
        print("DATABASE_URL is not set. Skipping DB initialization.")
        return
    
    with engine.connect() as connection:
        connection.execute(text('''
            CREATE TABLE IF NOT EXISTS users (
                user_id TEXT PRIMARY KEY,
                state TEXT,
                city_name TEXT,
                lat REAL,
                lon REAL
            )
        '''))
        connection.commit()

def set_user_state(user_id, state):
    if not engine: return
    with engine.connect() as connection:
        connection.execute(text("""
            INSERT INTO users (user_id, state) VALUES (:user_id, :state)
            ON CONFLICT(user_id) DO UPDATE SET state = :state
        """), {"user_id": user_id, "state": state})
        connection.commit()

def get_user_state(user_id):
    if not engine: return None
    with engine.connect() as connection:
        result = connection.execute(text("SELECT state FROM users WHERE user_id = :user_id"), {"user_id": user_id}).fetchone()
        return result[0] if result else None

def set_user_location(user_id, city_name, lat, lon):
    if not engine: return
    with engine.connect() as connection:
        connection.execute(text("""
            INSERT INTO users (user_id, state, city_name, lat, lon) VALUES (:user_id, 'normal', :city_name, :lat, :lon)
            ON CONFLICT(user_id) DO UPDATE SET 
                state = 'normal', city_name = :city_name, lat = :lat, lon = :lon
        """), {"user_id": user_id, "city_name": city_name, "lat": lat, "lon": lon})
        connection.commit()

def get_all_users_with_location():
    if not engine: return []
    with engine.connect() as connection:
        result = connection.execute(text("SELECT user_id, city_name, lat, lon FROM users WHERE city_name IS NOT NULL")).fetchall()
        return result
