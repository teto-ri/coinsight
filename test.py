from transformers import AutoTokenizer, AutoModelForSequenceClassification
import torch

# 모델을 CPU에서 최적화하여 로드
device = torch.device('cpu')  # CPU에서 실행

# KR-FinBert-SC 모델과 토크나이저 로드
tokenizer = AutoTokenizer.from_pretrained('snunlp/KR-FinBert-SC')
model = AutoModelForSequenceClassification.from_pretrained('snunlp/KR-FinBert-SC').to(device)

# 모델을 'half-precision' (float16)으로 변환하여 메모리 최적화
model = model.half()  # 모델을 float16으로 변환 (가능한 경우)

texts = ["주식 시장의 불확실성은 여전히 높지만, 기업 실적은 회복세를 보이고 있다.",
         "경제 지표는 긍정적이지만, 시장의 변동성은 여전히 높다."]

inputs = tokenizer(texts, return_tensors='pt', truncation=True, padding=True, max_length=512).to(device)

with torch.no_grad():
    outputs = model(**inputs)
    
labels = ['positive', 'neutral', 'negative']

logits = outputs.logits
predicted_classes = torch.argmax(logits, dim=-1).cpu().numpy()
predicted_sentiments = [labels[predicted_class] for predicted_class in predicted_classes]

for text, sentiment in zip(texts, predicted_sentiments):
    print(f"Text: {text}")
    print(f"Predicted Sentiment: {sentiment}")

