# PhotoLegal - Setup & Launch (Windows)

Prerequisites:
- Python 3.11+ on PATH
- PowerShell 7+

1) Setup (creates .venv and installs deps)
- PowerShell:
  - powershell -ExecutionPolicy Bypass -File .\setup_venv.ps1
- CMD:
  - setup_venv.bat

This creates .venv, installs from requirements.txt, and generates .env.
Set your OpenAI API key in .env:

OPENAI_API_KEY=sk-...

2) Launch the app
- PowerShell:
  - powershell -ExecutionPolicy Bypass -File .\start_app.ps1
- CMD:
  - start_app.bat

Streamlit URL: http://localhost:8501

Troubleshooting
- If text is garbled: scripts force UTF-8; messages are ASCII-only.
- If Python not found: install from https://www.python.org/ and rerun setup.
- If you see messages about C:\\Python313, ignore; scripts use venv python directly.

## Development

### Project Structure
```
photolegal/
├── app/
│   ├── main.py              # Streamlit UI and main application entry point
│   ├── models.py            # Pydantic models for data validation
│   ├── assess.py            # Legal assessment logic and analysis
│   ├── two_stage_analysis.py # Two-stage analysis implementation
│   ├── pdf.py               # PDF processing utilities
│   ├── utils.py             # General utility functions
│   ├── rules.yml            # Legal rules configuration
│   └── tests.py             # Test cases
├── requirements.txt         # Python dependencies
└── setup_venv.ps1          # Virtual environment setup script
```

### Key Features
- **Legal Photo Analysis**: Analyzes photos for potential legal violations
- **Two-Stage Analysis**: Combines rule-based and AI-based approaches
- **Comprehensive Legal Analysis**: Deep analysis of workplace compliance with Japanese laws and standards
- **PDF Processing**: Handles PDF document analysis
- **Streamlit UI**: Web-based user interface

### AI Coding Guidelines
- The system considers legal violations from both human operations and equipment aspects
- Combines rule-based and inference-based approaches for comprehensive analysis
- API keys are obtained from environment variables as a convention
- Software titles should be small and positioned slightly upwards for better balance in web design

