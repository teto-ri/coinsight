import pandas as pd
import psycopg2
from psycopg2.extras import execute_values
from db_connector import get_db_connection

# 1. CSV 파일 읽기

def get_chat_df(path):
    df = pd.read_csv(path)
    df['timestamp'] = pd.to_datetime(df['date'])
    df['source'] = 'Telegram'
    df = df.rename(columns={
        'chat_name': 'chat_name',
        'message_id': 'message_id',
        'sender': 'sender',
        'text': 'reaction_text'
    })
    return df

# 3. 데이터베이스 연결 및 데이터 삽입
def insert_chat_data(df, batch_size=1000):
    try:
        # 연결 생성
        conn = get_db_connection("data_collector")
        cur = conn.cursor()

        # SQL INSERT 문 (UUID는 DB에서 기본 생성, 중복 방지 위해 ON CONFLICT 사용)
        insert_query = """
        INSERT INTO public.Community_Reactions (timestamp, reaction_text, chat_name, sender, source)
        VALUES %s
        ON CONFLICT (timestamp, chat_name, sender)
        DO NOTHING;
        """

        # 데이터 배치 삽입
        for start in range(0, len(df), batch_size):
            batch_data = df.iloc[start:start + batch_size]
            data = [
                (row['timestamp'], row['reaction_text'], row['chat_name'], row['sender'], row['source'])
                for _, row in batch_data.iterrows()
            ]

            # 배치 삽입
            execute_values(cur, insert_query, data)
            conn.commit()
            print(f"Inserted batch {start // batch_size + 1} / {len(df) // batch_size + 1}")

        print("All data inserted successfully.")

    except Exception as e:
        print(f"Error: {e}")

    finally:
        if conn:
            cur.close()
            conn.close()

def main():
    # CSV 파일 경로
    csv_path = "output_all_chats.csv"

    # 데이터프레임 생성
    chat_df = get_chat_df(csv_path)

    # 데이터베이스 삽입
    insert_chat_data(chat_df)
    
if __name__ == "__main__":
    main()