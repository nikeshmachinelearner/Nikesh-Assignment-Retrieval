import os, json, joblib
from flask import Flask, request, jsonify, render_template

BASE = os.path.dirname(__file__)
DATA = os.path.join(BASE, "data")
MODELS = os.path.join(BASE, "models")
NB = os.path.join(MODELS, "nb_pipeline.joblib")
LR = os.path.join(MODELS, "lr_pipeline.joblib")
BEST = os.path.join(MODELS, "best_pipeline.joblib")
METRICS = os.path.join(DATA, "metrics.json")

app = Flask(__name__)

def models_ready():
    return all(os.path.exists(p) for p in [NB, LR, BEST])

def load_pipeline(name):
    path = {"nb": NB, "lr": LR, "auto": BEST}[name]
    if not os.path.exists(path): raise RuntimeError("Model not found. Run: python train.py")
    return joblib.load(path)

def top_terms(model, label, k=12):
    try:
        import numpy as np
        vec = model.named_steps["tfidf"]; clf = model.named_steps["clf"]
        feat = np.array(vec.get_feature_names_out())
        if hasattr(clf, "coef_"):
            idx = list(clf.classes_).index(label)
            coefs = clf.coef_[idx]; top = np.argsort(coefs)[-k:][::-1]; return feat[top].tolist()
        if hasattr(clf, "feature_log_prob_"):
            idx = list(clf.classes_).index(label)
            logp = clf.feature_log_prob_[idx]; top = np.argsort(logp)[-k:][::-1]; return feat[top].tolist()
    except Exception: pass
    return []

@app.get('/')
def home():
    return render_template('index.html', ready=models_ready())

@app.get('/metrics')
def metrics():
    if not os.path.exists(METRICS): return jsonify({'error':'metrics not found; run python train.py'}), 404
    return jsonify(json.load(open(METRICS,'r',encoding='utf-8')))

@app.post('/predict')
def predict():
    if not models_ready(): return jsonify({'error':'models not trained; run python train.py'}), 400
    data = request.get_json(force=True)
    text = (data.get('text') or '').strip()
    model = (data.get('model') or 'auto').lower()
    if not text: return jsonify({'error':'empty text'}), 400
    if model not in ('nb','lr','auto'): model='auto'
    clf = load_pipeline(model if model in ('nb','lr') else 'auto')
    label = clf.predict([text])[0]
    probs = None
    if hasattr(clf, 'predict_proba'):
        proba = clf.predict_proba([text])[0].tolist()
        classes = clf.named_steps['clf'].classes_.tolist()
        probs = sorted(list(zip(classes, [float(x) for x in proba])), key=lambda x:x[1], reverse=True)
    return jsonify({'label':label, 'probabilities':probs, 'top_terms': top_terms(clf, label, k=15)})

if __name__ == '__main__':
    app.run(debug=True)
