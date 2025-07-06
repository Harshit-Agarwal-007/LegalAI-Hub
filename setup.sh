#!/bin/bash

# Legal AI Hub Setup Script
echo "🚀 Setting up Legal AI Hub..."

# Create project structure
echo "📁 Creating project structure..."
mkdir -p static templates tmp uploads

# Create virtual environment
echo "🐍 Creating virtual environment..."
python3 -m venv venv
source venv/bin/activate

# Install dependencies
echo "📦 Installing dependencies..."
pip install --upgrade pip
pip install -r complete_requirements.txt

# Copy static files
echo "📄 Setting up static files..."
cp static_styles.css static/style.css
cp legal_ai_interface.html templates/index.html

# Create environment file
echo "⚙️  Creating environment file..."
cat > .env << EOL
# Azure Document Intelligence
AZURE_DOC_ENDPOINT=your_document_intelligence_endpoint
AZURE_DOC_KEY=your_document_intelligence_key

# Azure Translator
AZURE_TRANSLATOR_KEY=your_translator_key
AZURE_TRANSLATOR_ENDPOINT=https://api.cognitive.microsofttranslator.com
AZURE_TRANSLATOR_REGION=your_region

# Azure AI Inference
AZURE_INFERENCE_SDK_ENDPOINT=your_inference_endpoint
AZURE_INFERENCE_SDK_KEY=your_inference_key
DEPLOYMENT_NAME=your_model_name

# Application settings
DEBUG=True
MAX_FILE_SIZE=10485760
UPLOAD_DIR=uploads
EOL

echo "✅ Setup complete!"
echo ""
echo "Next steps:"
echo "1. Update the .env file with your Azure credentials"
echo "2. Run: python enhanced_main.py"
echo "3. Open: http://localhost:8000"
echo ""
echo "For production deployment:"
echo "• Use gunicorn: gunicorn enhanced_main:app -w 4 -k uvicorn.workers.UvicornWorker"
echo "• Set up reverse proxy (nginx/caddy)"
echo "• Use environment variables for secrets"
echo "• Set up monitoring and logging"
