# Final Chat Project

A real-time web-based messaging application with an Arabic-first (RTL) UI. Built with FastAPI (Python) backend and vanilla HTML/CSS/JS frontend, using WebSockets for instant communication.

## Features

- **Authentication** -- Register and login with JWT-based sessions
- **Real-time Messaging** -- Instant text messages via WebSockets
- **Media Sharing** -- Upload and send images, videos, and audio recordings
- **User Profiles** -- View and edit username, full name, bio, phone, email
- **Online Status** -- See who is online in real-time
- **Notifications** -- Real-time in-app notifications for new messages
- **Dark/Light Themes** -- Toggle between dark, light, and auto (system preference)
- **Responsive Design** -- Mobile-friendly with hamburger menu and resizable sidebar
- **QR Code Access** -- Generate QR codes for easy mobile access
- **Cloudflare Tunnel** -- Optional public URL for remote access without port forwarding

## Tech Stack

| Layer | Technology |
|-------|------------|
| Backend | FastAPI, Uvicorn |
| Database | PostgreSQL |
| Auth | JWT (python-jose), bcrypt |
| Rate Limiting | slowapi |
| Frontend | Vanilla HTML5, CSS3, JavaScript (ES6+) |
| Real-time | Native WebSockets |
| Icons | Font Awesome 6.5.1 |
| Tunneling | Cloudflare Tunnel (cloudflared) |

## Prerequisites

- Python 3.10+
- PostgreSQL
- `cloudflared` CLI (optional, for public tunneling)

## Installation

### 1. Clone the repository

```bash
git clone <repository-url>
cd final-chat-project
```

### 2. Install Python dependencies

```bash
pip install fastapi uvicorn psycopg2-binary "python-jose[cryptography]" bcrypt slowapi python-dotenv pyperclip qrcode pillow
```

### 3. Set up PostgreSQL

Create a database:

```sql
CREATE DATABASE chat_app;
```

### 4. Configure environment variables

Create a `.env` file in `file/chat_project/backend/`:

```env
SECOND_KEY=your-secret-jwt-key
DB_HOST=localhost
DB_NAME=chat_app
DB_USER=postgres
DB_PASSWORD=your-password
DB_PORT=5432
```

### 5. Initialize the database

```bash
cd file/chat_project/backend

# Create tables only
python database.py

# Create tables + demo user (demo/demo123)
python database.py --with-sample
```

## Running the Application

### Option A: Using the launcher script (recommended)

```bash
cd file
python run_app.py
```

This starts the server, optionally launches a Cloudflare Tunnel, generates QR codes, and opens the browser.

### Option B: Running the server directly

```bash
cd file/chat_project/backend
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

Access the app at [http://localhost:8000](http://localhost:8000).

## Project Structure

```
final-chat-project/
├── .gitignore
└── file/
    ├── run_app.py                    # Launcher (server + tunnel + QR codes)
    └── chat_project/
        ├── backend/
        │   ├── main.py               # FastAPI app, routes, WebSocket handlers
        │   ├── database.py           # PostgreSQL connection & schema init
        │   └── DEVELOPMENT.env       # Dev environment variables
        └── frontend/
            ├── index.html            # Single-page application
            ├── css/
            │   ├── main.css          # Root variables, layout, animations
            │   ├── auth.css          # Login/register screens
            │   ├── chat.css          # Chat area & messages
            │   ├── components.css    # Reusable UI components
            │   ├── media.css         # Image/video styles
            │   ├── modal.css         # Image modal overlay
            │   ├── profile.css       # Profile screen
            │   ├── responsive.css    # Mobile breakpoints
            │   └── theme.css         # Light mode overrides
            └── js/
                ├── main.js           # Global vars, sidebar resize
                ├── auth.js           # Session, login, register, logout
                ├── chat.js           # Chat open/close, send messages
                ├── websocket.js      # WebSocket connections
                ├── messages.js       # Message rendering, date separators
                ├── media.js          # Media upload & preview
                ├── audio.js          # Audio recording & playback
                ├── profile.js        # Profile editing, settings, theme
                ├── ui.js             # Toasts, screen switching, mobile
                └── utils.js          # HTML escaping, user list, modals
```

## API Endpoints

### REST

| Method | Endpoint | Rate Limit | Description |
|--------|----------|------------|-------------|
| `POST` | `/register` | 20/10s | Create account |
| `POST` | `/login` | 20/10s | Login, returns JWT |
| `GET` | `/users/{user_id}` | 20/10s | List users (search supported) |
| `GET` | `/messages/{user_id}/{other_id}` | -- | Conversation history |
| `GET` | `/profile/{user_id}` | -- | Get user profile |
| `POST` | `/profile/update/{user_id}` | 20/10s | Update profile (JWT required) |
| `POST` | `/settings/update/{user_id}` | 20/10s | Update settings (JWT required) |
| `POST` | `/upload-image` | -- | Upload image |
| `POST` | `/upload-audio` | -- | Upload audio |
| `POST` | `/upload-video` | -- | Upload video |

### WebSocket

| Endpoint | Description |
|----------|-------------|
| `/ws/{user_id}/{other_id}` | Real-time chat messages |
| `/ws/notifications/{user_id}` | Per-user notifications |
| `/ws/users-updates` | Global user list updates |

## Database Schema

8 tables: `users`, `profiles`, `messages`, `message_media`, `message_reads`, `message_deletions`, `user_settings`, `user_connections`.

Tables are created automatically by `database.py`.

## Configuration

### User Settings

| Setting | Default | Options |
|---------|---------|---------|
| Notifications | enabled | `true` / `false` |
| Sounds | enabled | `true` / `false` |
| Message previews | enabled | `true` / `false` |
| Language | Arabic | `ar` / `en` |
| Theme | Dark | `dark` / `light` / `auto` |

## License

No license specified.
