from transformers import AutoTokenizer, AutoModelForSequenceClassification
import torch
import torch.nn.functional as F

tokenizer = AutoTokenizer.from_pretrained("StephanAkkerman/FinTwitBERT-sentiment")
model = AutoModelForSequenceClassification.from_pretrained(
    "StephanAkkerman/FinTwitBERT-sentiment"
)
model.eval()

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
model.to(device)

def hf_predict(text):
    if text is None or text.strip() == "":
        return {"pred_label": None, "pred_score": None}

    inputs = tokenizer(text, return_tensors="pt", truncation=True).to(device)

    with torch.no_grad():
        outputs = model(**inputs)

    probs = F.softmax(outputs.logits, dim=-1)
    pred_id = torch.argmax(probs).item()
    score = float(probs[0][pred_id].item())
    label = model.config.id2label[pred_id]

    return {"pred_label": label, "pred_score": score}
