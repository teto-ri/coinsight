import json
import pandas as pd
import os
base_directory = "data"
all_data = []

for folder_name in os.listdir(base_directory):
    folder_path = os.path.join(base_directory, folder_name)
    
    # 폴더인지 확인
    if os.path.isdir(folder_path):
        result_file_path = os.path.join(folder_path, "result.json")
        
        # result.json 파일이 있는지 확인
        if os.path.exists(result_file_path):
            # JSON 파일 로드
            with open(result_file_path, "r", encoding="utf-8") as file:
                json_data = json.load(file)
            
            # 채팅방 이름
            chat_name = json_data.get("name", "Unknown Chat")
            
            # 메시지 데이터 추출
            messages = json_data.get("messages", [])
            for message in messages:
                message_id = message.get("id")
                message_date = message.get("date")
                sender = message.get("from")
                text_content = ""

                # 텍스트가 여러 조각으로 나뉘어 있는 경우 처리
                if isinstance(message.get("text"), list):
                    for item in message["text"]:
                        if isinstance(item, dict) and "text" in item:
                            text_content += item["text"]
                        elif isinstance(item, str):
                            text_content += item
                elif isinstance(message.get("text"), str):
                    text_content = message["text"]

                # \n 제거
                text_content = text_content.replace("\n", " ")

                # 데이터 추가
                all_data.append({
                    "chat_name": chat_name,
                    "message_id": message_id,
                    "date": message_date,
                    "sender": sender,
                    "text": text_content
                })

# 데이터프레임 생성
df = pd.DataFrame(all_data)

# 결과 확인
print(df)
output_file_path = "output_all_chats.csv"
df.to_csv(output_file_path, index=False, encoding="utf-8-sig")
print(f"모든 채팅 데이터를 {output_file_path}에 저장했습니다.")
