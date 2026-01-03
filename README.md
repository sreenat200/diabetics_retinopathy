# Diabetic Retinopathy Detection System

A comprehensive web application for detecting diabetic retinopathy using deep learning models. This system allows medical professionals to upload retinal images and receive automated analysis results to help in early detection and treatment of diabetic retinopathy.

## Features

- **User Authentication**: Secure signup, login, and password management with OTP verification
- **Patient Management**: Register and manage patient records with unique medical IDs
- **Image Analysis**: Upload retinal images for automated diabetic retinopathy detection
- **Batch Processing**: Analyze multiple images in a single session
- **AI-Powered Diagnosis**: Uses a trained deep learning model to classify retinopathy severity
- **Report Generation**: Generate PDF reports for individual and batch analyses
- **Analytics Dashboard**: Visualize patient data and diagnosis trends
- **AI Prescription Suggestions**: Integrate with AI models (OpenAI, Gemini, etc.) for treatment recommendations

## Technology Stack

- **Backend**: Python, Flask, SQLAlchemy
- **Frontend**: HTML, CSS, JavaScript, Tailwind CSS
- **AI/ML**: TensorFlow, Keras
- **Database**: SQLite (development), PostgreSQL (production ready)
- **Authentication**: Flask-Login, OTP-based verification
- **Image Processing**: OpenCV, Pillow
- **Reporting**: ReportLab for PDF generation

## Project Structure

```
diabetic_retinopathy_app/
├── app.py                 # Application entry point
├── __init__.py            # Flask application factory
├── config.py              # Configuration settings
├── models.py              # Database models
├── requirements.txt       # Python dependencies
├── README.md              # This file
├── .gitignore             # Git ignore rules
├── routes/                # Route handlers
│   ├── main_routes.py     # Main application routes
│   ├── auth_routes.py     # Authentication routes
│   ├── ai_model_routes.py # AI model management routes
│   └── report_routes.py   # Report generation routes
├── utils/                 # Utility functions
│   ├── model_handler.py   # AI model loading and prediction
│   ├── image_processing.py# Image processing functions
│   ├── email_service.py   # Email sending functionality
│   ├── ai_models.py       # AI model integration
│   └── report_generator.py# PDF report generation
├── templates/             # HTML templates
├── static/                # Static assets (CSS, JS, images)
├── model/                 # AI model files
└── instance/              # Database files
```

## Installation

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd diabetic_retinopathy_app
   ```

2. **Create a virtual environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables** (create a `.env` file):
   ```env
   SECRET_KEY=your-secret-key
   FLASK_DEBUG=True
   DATABASE_URL=sqlite:///diabetic_retinopathy.db
   SMTP_SERVER=your-smtp-server
   SMTP_PORT=587
   SMTP_USERNAME=your-email
   SMTP_PASSWORD=your-password
   ```

5. **Download the AI model**:
   - Place your trained diabetic retinopathy model file in the `model/` directory
   - Update the `MODEL_PATH` in `config.py` if needed

## Usage

1. **Start the application**:
   ```bash
   python app.py
   ```

2. **Access the application**:
   - Open your browser and navigate to `http://localhost:5000`
   - Register a new account or login with existing credentials

3. **Key Workflows**:
   - **Signup/Login**: Create an account with OTP verification
   - **Patient Registration**: Add patient details with unique medical IDs
   - **Image Analysis**: Upload retinal images for DR detection
   - **Batch Analysis**: Process multiple images for a patient
   - **Report Generation**: Download PDF reports of analyses
   - **Settings**: Manage account, password, and AI model configurations

## Database Models

- **User**: Medical professionals with authentication details
- **Patient**: Patient records with personal and medical information
- **Diagnosis**: Results of retinal image analyses
- **AiModelSettings**: Configuration for AI prescription suggestion models

## API Endpoints

### Authentication
- `POST /signup` - User registration with OTP
- `POST /login` - User login
- `POST /logout` - User logout
- `POST /forgot-password` - Password reset request

### Patient Management
- `GET /register-patient` - Patient registration page
- `POST /add-patient` - Add new patient
- `GET /patients` - List all patients
- `GET /patient/<id>` - View patient details

### Image Analysis
- `GET /analyze` - Image analysis page
- `POST /predict` - Single image analysis
- `POST /batch-predict` - Batch image analysis
- `GET /dr-onetime-analyse` - One-time analysis (no persistence)

### Reports
- `POST /download/report` - Generate and download reports
- `POST /download/batch-history-report` - Patient history report
- `POST /download/batch-session-report` - Batch session report

### AI Models
- `GET /ai-models` - List user's AI models
- `POST /ai-models` - Create new AI model
- `PUT /ai-models/<id>` - Update AI model
- `DELETE /ai-models/<id>` - Delete AI model

## Development

### Routes Organization
All route handlers are organized in the `routes/` directory:
- `main_routes.py`: Core application functionality
- `auth_routes.py`: User authentication and account management
- `ai_model_routes.py`: AI model configuration and management
- `report_routes.py`: Report generation functionality

### Contributing
1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- TensorFlow and Keras for deep learning framework
- Flask for web application framework
- Medical professionals and researchers in ophthalmology
- Open source community for various libraries and tools