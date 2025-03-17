## How to install
1. git clone -b rob-agents-sdk https://github.com/robrita/fsi-agent
2. copy sample.env to .env and update
3. python -m venv venv
4. .\venv\Scripts\activate
5. python -m pip install -r requirements.txt
6. chainlit run app.py --watch

## List of features
- Azure authentication
- Azure PostgreSQL DB
- Chat streaming
- Disable chat while waiting
- Chat with agents and llm models
