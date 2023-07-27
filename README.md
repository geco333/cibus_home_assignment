## Overview

Sets up a local RESTFul API server using the *FastApi* framework and a
local SQLite database to create messages and vote for them.

## Setup
### Locally
1. `python -m pip install -r requirements.txt` to install all dependencies.
2. `python -m alembic upgrade head` to setup a local SQLite database file.
3. `python main.py` to start the *FastAPI* server locally in port 8000

### Using Docker
1. Build the image using `docker build -t message_board .`
2. Run the server in a container on local port 8000 using `docker run -d -p 8000:8000 message_board`


Once the server is online all API endpoints documentation can be found in:
http://localhost:8000/docs