from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import joblib
import pandas as pd
from uuid import uuid4
from prometheus_client import Counter, Gauge, generate_latest, CONTENT_TYPE_LATEST

app = Flask(__name__)
CORS(app)

# Configure SQLite database
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///predictions.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Load the trained model
model = joblib.load('trainmodel.h5')

# Prometheus metrics
predictions_total = Counter('predictions_total', 'Total number of predictions', ['category'])
correct_predictions = Counter('correct_predictions', 'Number of correct predictions', ['category'])
incorrect_predictions = Counter('incorrect_predictions', 'Number of incorrect predictions', ['category'])
prediction_confidence = Gauge('prediction_confidence', 'Average prediction confidence')
accuracy = Gauge('accuracy', 'Overall prediction accuracy')

# Initialize counters for each category
categories = ['bug', 'enhancement', 'question']
for category in categories:
    predictions_total.labels(category=category)
    correct_predictions.labels(category=category)
    incorrect_predictions.labels(category=category)

class Prediction(db.Model):
    __tablename__ = 'prediction'
    id = db.Column(db.String(36), primary_key=True)
    issue_body = db.Column(db.Text, nullable=False)
    predicted_label = db.Column(db.String(50), nullable=False)
    corrected_label = db.Column(db.String(50), nullable=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

def update_accuracy():
    total_correct = sum([correct_predictions.labels(category=c)._value.get() for c in categories])
    total_predictions = sum([predictions_total.labels(category=c)._value.get() for c in categories])
    if total_predictions > 0:
        accuracy.set(total_correct / total_predictions)

@app.route('/metrics')
def metrics():
    return generate_latest(), 200, {'Content-Type': CONTENT_TYPE_LATEST}

with app.app_context():
    db.drop_all()
    db.create_all()

@app.route('/api/predict', methods=['POST'])
def predict():
    try:
        data = request.get_json()
        if not data or 'issue_body' not in data:
            return jsonify({'error': 'issue_body is required'}), 400

        issue_body = data['issue_body']
        input_df = pd.DataFrame({'issue_body': [issue_body]})
        predicted_label = model.predict(input_df)[0]
        probabilities = model.predict_proba(input_df)[0]
        confidence_score = float(max(probabilities))

        # Update Prometheus metrics
        predictions_total.labels(category=predicted_label).inc()
        prediction_confidence.set(confidence_score)

        issue_id = str(uuid4())
        prediction = Prediction(
            id=issue_id,
            issue_body=issue_body,
            predicted_label=predicted_label
        )

        db.session.add(prediction)
        db.session.commit()

        return jsonify({
            'id': issue_id,
            'predicted_label': predicted_label,
            'confidence_score': confidence_score
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/correct', methods=['POST'])
def correct():
    try:
        data = request.get_json()
        if not data or 'id' not in data or 'corrected_label' not in data:
            return jsonify({'error': 'Both id and corrected_label are required'}), 400

        prediction = Prediction.query.get(data['id'])
        if not prediction:
            return jsonify({'error': 'Prediction not found'}), 404

        # Update Prometheus metrics
        if prediction.predicted_label != data['corrected_label']:
            incorrect_predictions.labels(category=prediction.predicted_label).inc()
        else:
            correct_predictions.labels(category=prediction.predicted_label).inc()
        update_accuracy()

        prediction.corrected_label = data['corrected_label']
        db.session.commit()

        return jsonify({
            'id': prediction.id,
            'original_label': prediction.predicted_label,
            'corrected_label': prediction.corrected_label
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True) # pragma: no cover