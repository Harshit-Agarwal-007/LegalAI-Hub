# LegalAI-Hub
Legal AI Hub - README
A comprehensive AI-powered contract analysis platform that combines OCR, translation, and advanced AI to analyze legal documents and provide risk assessments with interactive chat capabilities.

🚀 Features
PDF Contract Processing: Upload PDF contracts for automated analysis

OCR Technology: Extract text from scanned documents using Azure Document Intelligence

Multi-language Support: Automatic translation to English for analysis

AI Risk Assessment: Identify risky clauses and get improved contract versions

Interactive Chat: Ask follow-up questions about your contract analysis

Web Interface: User-friendly web application with modern UI

REST API: Full API access for integration with other systems

📋 Prerequisites
Python 3.8 or higher

Azure Account with the following services:

Azure Document Intelligence (for OCR)

Azure Translator (for translation)

Azure AI Inference (for AI analysis)

🛠️ Installation
1. Clone the Repository
bash
git clone <your-repository-url>
cd legal-ai-hub
2. Install Dependencies
bash
pip install -r requirements.txt
3. Set Up Environment Variables
Create a .env file in the project root:

bash
# Azure Document Intelligence (OCR)
AZURE_DOC_ENDPOINT=https://your-resource.cognitiveservices.azure.com/
AZURE_DOC_KEY=your_document_intelligence_key

# Azure Translator
AZURE_TRANSLATOR_KEY=your_translator_key
AZURE_TRANSLATOR_ENDPOINT=https://api.cognitive.microsofttranslator.com
AZURE_TRANSLATOR_REGION=your_region

# Azure AI Inference
AZURE_INFERENCE_SDK_ENDPOINT=https://your-model-endpoint.services.ai.azure.com/models/
AZURE_INFERENCE_SDK_KEY=your_inference_key
DEPLOYMENT_NAME=Phi-4-mini-instruct
