import pytest
from app import app, db
import json
from unittest.mock import patch


@pytest.fixture(autouse=True)
def mock_model():
    """Mock the model to avoid loading the actual model file"""
    with patch('joblib.load') as mock:
        class MockModel:
            def predict(self, X):
                return ['bug']
        mock.return_value = MockModel()
        yield mock


@pytest.fixture
def client():
    """Test client fixture"""
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['TESTING'] = True

    with app.test_client() as client:
        with app.app_context():
            db.create_all()
            yield client
            db.session.remove()
            db.drop_all()


def test_predict_endpoint(client):
    """Test the prediction endpoint"""
    response = client.post(
        '/api/predict',
        json={'issue_body': 'There is a bug in the login system'}
    )

    assert response.status_code == 200
    data = json.loads(response.data)
    assert 'id' in data
    assert 'predicted_label' in data
    assert isinstance(data['predicted_label'], str)


def test_predict_endpoint_missing_body(client):
    """Test prediction endpoint with missing body"""
    response = client.post('/api/predict', json={})
    assert response.status_code == 400
    data = json.loads(response.data)
    assert data['error'] == 'issue_body is required'


def test_predict_endpoint_error(client):
    """Test prediction endpoint with error condition"""
    with patch('pandas.DataFrame') as mock_df:
        mock_df.side_effect = Exception("Test error")
        response = client.post(
            '/api/predict',
            json={'issue_body': 'Test issue'}
        )

        assert response.status_code == 500
        data = json.loads(response.data)
        assert 'error' in data


def test_correct_endpoint(client):
    """Test the correction endpoint"""
    # First make a prediction
    pred_response = client.post(
        '/api/predict',
        json={'issue_body': 'Test issue'}
    )
    pred_data = json.loads(pred_response.data)

    # Then correct it
    response = client.post(
        '/api/correct',
        json={
            'id': pred_data['id'],
            'corrected_label': 'bug'
        }
    )

    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['corrected_label'] == 'bug'
    assert 'original_label' in data


def test_correct_endpoint_invalid_id(client):
    """Test correction endpoint with invalid ID"""
    response = client.post(
        '/api/correct',
        json={
            'id': 'invalid-id',
            'corrected_label': 'bug'
        }
    )

    assert response.status_code == 404
    data = json.loads(response.data)
    assert data['error'] == 'Prediction not found'


def test_correct_missing_fields(client):
    """Test correction with missing required fields"""
    response = client.post('/api/correct', json={})
    assert response.status_code == 400
    data = json.loads(response.data)
    assert data['error'] == 'Both id and corrected_label are required'


def test_predict_invalid_request(client):
    """Test prediction with invalid request format"""
    response = client.post('/api/predict', data='not json')
    assert response.status_code == 500
    data = json.loads(response.data)
    assert 'error' in data
