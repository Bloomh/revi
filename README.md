# Revi

Aggregated, AI-generated reviews to help you make good purchases in seconds.

## Setup

1. Create a virtual environment (recommended):
```bash
python -m venv venv
source venv/bin/activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up environment variables:
   1. Copy `.env.template` to a new file named `.env`:
   ```bash
   cp .env.template .env
   ```
   2. Fill in your API keys in the `.env` file:
      - `YOUTUBE_API_KEY`: Get from [Google Cloud Console](https://console.cloud.google.com)
      - `OPENAI_API_KEY`: Get from [OpenAI](https://platform.openai.com/api-keys)
      - `OXYLABS_USER`, `OXYLABS_PASS`: Get from [Oxylabs](https://oxylabs.io)
      - `ENSEMBLEDDATA_API_KEY`: Get from [EnsembleData](https://ensembledata.com)
      - `PERPLEXITY_API_KEY`: Get from [Perplexity](https://perplexity.ai)

   All these APIs are required for full functionality.

4. Run the application:
```bash
python app.py
```

5. Open your browser and visit: `http://localhost:5000`
