import os
import uvicorn
from src.settings.server import app

if __name__ == '__main__':
    uvicorn.run(app,
                host=os.environ.get('NEURAL_HOST', '0.0.0.0'),
                port=int(os.environ.get('NEURAL_PORT', 8501)))