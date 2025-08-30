import os  # For operating system interactions like file paths and directories
import glob  # For finding files using patterns
import json  # For handling JSON data serialization
import random  # For generating random numbers and choices
import warnings  # For managing warning messages
import numpy as np  # For numerical computations and arrays
import pandas as pd  # For data manipulation and analysis using DataFrames
import joblib  # For saving and loading machine learning models
from sklearn.model_selection import train_test_split, StratifiedKFold, cross_val_score  # For splitting data and cross-validation
from sklearn.metrics import accuracy_score, classification_report  # For evaluating model performance
from sklearn.feature_extraction.text import TfidfVectorizer  # For converting text to TF-IDF features
from sklearn.pipeline import Pipeline  # For chaining preprocessing and modeling steps
from sklearn.naive_bayes import MultinomialNB  # Naive Bayes classifier for text data
from sklearn.linear_model import LogisticRegression  # Logistic Regression classifier

warnings.filterwarnings('ignore')  # Suppress all warnings to avoid clutter in output

# Handle base directory for script, with fallback for interactive environments
try:
    BASE = os.path.dirname(__file__)
except NameError:
    BASE = os.getcwd()
DATA_DIR = os.path.join(BASE, "data")  # Directory for data files
MODELS_DIR = os.path.join(BASE, "models")  # Directory for saved models
os.makedirs(DATA_DIR, exist_ok=True)  # Create data directory if it doesn't exist
os.makedirs(MODELS_DIR, exist_ok=True)  # Create models directory if it doesn't exist

# Define terms and templates for synthetic data generation
politics_terms = ['parliament', 'cabinet', 'election', 'minister', 'policy', 'bill', 'vote', 'law', 'campaign', 'opposition', 'coalition', 'budget', 'committee', 'amendment', 'treaty', 'sanctions']
business_terms = ['market', 'stock', 'investor', 'earnings', 'revenue', 'startup', 'merger', 'acquisition', 'IPO', 'shareholder', 'inflation', 'interest rate', 'bond', 'retail', 'dividend', 'portfolio']
health_terms = ['hospital', 'clinic', 'vaccine', 'infection', 'virus', 'public health', 'doctor', 'patient', 'treatment', 'symptom', 'epidemic', 'nurse', 'trial', 'therapy', 'screening', 'immunity']
bridge = ['budget', 'policy', 'insurance', 'funding', 'regulation', 'risk', 'technology', 'forecast']
templates = [
    "The {actor} discussed {topic} and {action} to address {issue}.",
    "{actor} announced new {topic} amid concerns about {issue}.",
    "Experts debated {issue} as {actor} considered {action} on {topic}.",
]
actors = {
    'Politics': ['the minister', 'the government', 'the opposition', 'lawmakers', 'the committee'],
    'Business': ['the company', 'executives', 'investors', 'the board', 'analysts'],
    'Health': ['doctors', 'officials', 'clinicians', 'researchers', 'the hospital']
}
actions = {
    'Politics': ['passing a bill', 'regulatory reform', 'negotiations', 'allocating funds'],
    'Business': ['raising capital', 'guidance updates', 'market expansion', 'a merger'],
    'Health': ['clinical trials', 'vaccination campaigns', 'care protocols', 'screening programs']
}

def ingest_manual(root=os.path.join(DATA_DIR, 'manual')):
    """
    This function ingests manual data from text files organized in category directories.
    """
    rows = []
    for cat in ['Politics', 'Business', 'Health']:
        d = os.path.join(root, cat)
        if not os.path.isdir(d):
            print(f"Warning: Directory {d} does not exist. Skipping.")
            continue
        files_found = False
        for p in glob.glob(os.path.join(d, '*.txt')):
            files_found = True
            try:
                with open(p, 'r', encoding='utf-8') as f:
                    txt = f.read().strip()
            except UnicodeDecodeError as e:
                print(f"Warning: Encoding error in {p}: {str(e)}. Skipping file.")
                continue
            if len(txt.split()) < 10:
                continue
            rows.append({'source': 'manual', 'category': cat, 'title': os.path.basename(p), 'text': txt})
        if not files_found:
            print(f"Warning: No text files found in {d}.")
    return rows

def load_csv(path=os.path.join(DATA_DIR, 'training_used.csv')):
    """
    This function loads data from a CSV file.
    """
    if not os.path.exists(path):
        print(f"Warning: CSV file {path} does not exist. Returning empty list.")
        return []
    df = pd.read_csv(path)
    rows = []
    for _, r in df.iterrows():
        if pd.isna(r.get('text')):
            continue
        rows.append({
            'source': r.get('source', 'csv'),
            'category': str(r.get('category', '')).strip(),
            'title': r.get('title', '(untitled)'),
            'text': str(r['text'])
        })
    return rows

def synth_sentence(cat):
    """
    This function generates a single synthetic sentence for a given category.
    """
    tpl = random.choice(templates)
    if cat == 'Politics':
        topic_weights = [0.8] * len(politics_terms) + [0.2] * len(bridge)
        topic = random.choices(politics_terms + bridge, weights=topic_weights)[0]
        issue_weights = [0.6] * len(politics_terms) + [0.2] * len(bridge) + [0.2] * 5
        issue = random.choices(politics_terms + bridge + health_terms[:5], weights=issue_weights)[0]
    elif cat == 'Business':
        topic_weights = [0.8] * len(business_terms) + [0.2] * len(bridge)
        topic = random.choices(business_terms + bridge, weights=topic_weights)[0]
        issue_weights = [0.6] * len(business_terms) + [0.2] * len(bridge) + [0.2] * 5
        issue = random.choices(business_terms + bridge + politics_terms[:5], weights=issue_weights)[0]
    else:
        topic_weights = [0.8] * len(health_terms) + [0.2] * len(bridge)
        topic = random.choices(health_terms + bridge, weights=topic_weights)[0]
        issue_weights = [0.6] * len(health_terms) + [0.2] * len(bridge) + [0.2] * 5
        issue = random.choices(health_terms + bridge + business_terms[:5], weights=issue_weights)[0]
    base = tpl.format(actor=random.choice(actors[cat]), topic=topic, action=random.choice(actions[cat]), issue=issue)
    extra = " " + " ".join([random.choice(['Stakeholders raised concerns.', 'Analysts noted risks and benefits.', 'Reports highlighted timelines.']) for _ in range(random.randint(1, 2))])
    return base + extra

def synthesize(n_per_class=40):
    """
    This function generates synthetic data rows for each category.
    """
    rows = []
    for cat in ['Politics', 'Business', 'Health']:
        for i in range(n_per_class):
            rows.append({'source': 'synthetic', 'category': cat, 'title': f'{cat} {i+1}', 'text': synth_sentence(cat)})
    return rows

def vec(min_df=3, max_df=0.9):
    """
    This function returns a configured TfidfVectorizer.
    """
    return TfidfVectorizer(lowercase=True, stop_words='english', ngram_range=(1, 2), max_df=max_df, min_df=min_df)

def main(seed=13):
    """
    This is the main function that orchestrates the entire pipeline: data loading, augmentation, model training, evaluation, and saving results.
    """
    random.seed(seed)  # Set random seed for reproducibility
    np.random.seed(seed)  # Set numpy random seed for reproducibility

    # Load and combine data from CSV and manual sources
    rows = load_csv() + ingest_manual()

    # Augment with synthetic data if total rows are less than 100
    if len(rows) < 100:
        need = max(0, 120 - len(rows))
        per = need // 3 if need > 0 else 0
        rows += synthesize(max(20, per))

    # Create DataFrame, clean data by dropping NaNs and duplicates
    df = pd.DataFrame(rows).dropna(subset=['text', 'category']).drop_duplicates(subset=['source', 'title'])

    # Check for sufficient data and balanced classes
    if len(df) < 10 or df['category'].nunique() < 3:
        raise ValueError("Insufficient data after filtering. Need at least 10 samples with all categories (Politics, Business, Health).")
    class_counts = df['category'].value_counts()
    if any(count < 5 for count in class_counts):
        print(f"Warning: Some categories have too few samples: {dict(class_counts)}. Stratification may fail.")

    # Save cleaned data for reference
    df.to_csv(os.path.join(DATA_DIR, 'training_used.csv'), index=False)

    # Prepare features (X) and labels (y)
    X = df['text'].astype(str).tolist()
    y = df['category'].astype(str).tolist()

    # Dynamically adjust min_df based on dataset size
    min_df = max(1, len(X) // 100)

    # Define pipelines for Naive Bayes and Logistic Regression
    nb = Pipeline([('tfidf', vec(min_df=min_df)), ('clf', MultinomialNB())])
    lr = Pipeline([('tfidf', vec(min_df=min_df)), ('clf', LogisticRegression(max_iter=500, class_weight='balanced', solver='lbfgs'))])

    # Perform cross-validation with error handling
    skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    try:
        cv_nb = cross_val_score(nb, X, y, scoring='accuracy', cv=skf)
        cv_lr = cross_val_score(lr, X, y, scoring='accuracy', cv=skf)
    except Exception as e:
        print(f"Warning: Cross-validation failed: {str(e)}. Skipping CV scores.")
        cv_nb = cv_lr = np.array([0.0])

    # Train-test split, fit models, predict, and evaluate with error handling
    try:
        Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
        nb.fit(Xtr, ytr)
        lr.fit(Xtr, ytr)
        yhat_nb = nb.predict(Xte)
        yhat_lr = lr.predict(Xte)
        acc_nb = accuracy_score(yte, yhat_nb)
        acc_lr = accuracy_score(yte, yhat_lr)
    except Exception as e:
        raise RuntimeError(f"Error during model training or prediction: {str(e)}")

    # Save trained models
    joblib.dump(nb, os.path.join(MODELS_DIR, 'nb_pipeline.joblib'))
    joblib.dump(lr, os.path.join(MODELS_DIR, 'lr_pipeline.joblib'))
    best = 'lr' if acc_lr >= acc_nb else 'nb'
    joblib.dump(lr if best == 'lr' else nb, os.path.join(MODELS_DIR, 'best_pipeline.joblib'))

    # Compile metrics dictionary, converting counts to int for JSON serialization
    metrics = {
        'cv': {
            'nb': {'accuracy_mean': float(cv_nb.mean()), 'accuracy_std': float(cv_nb.std())},
            'lr': {'accuracy_mean': float(cv_lr.mean()), 'accuracy_std': float(cv_lr.std())}
        },
        'heldout': {
            'nb': {'accuracy': float(acc_nb), 'report': classification_report(yte, yhat_nb, output_dict=True)},
            'lr': {'accuracy': float(acc_lr), 'report': classification_report(yte, yhat_lr, output_dict=True)},
            'best_model': best
        },
        'counts': {k: int(v) for k, v in df['category'].value_counts().items()}
    }

    # Save metrics to JSON, avoiding overwrite by generating unique filename if needed
    metrics_path = os.path.join(DATA_DIR, 'metrics.json')
    if os.path.exists(metrics_path):
        import time  # Import time for unique timestamp
        print(f"Warning: {metrics_path} already exists. Saving as metrics_{int(time.time())}.json")
        metrics_path = os.path.join(DATA_DIR, f'metrics_{int(time.time())}.json')
    with open(metrics_path, 'w', encoding='utf-8') as f:
        f.write(json.dumps(metrics, indent=2))

    print('[DONE] Saved models and metrics.')

if __name__ == '__main__':
    """
    Entry point of the script.
    """
    seed = int(os.getenv('RANDOM_SEED', 13))  # Get seed from env var or default to 13
    main(seed=seed)