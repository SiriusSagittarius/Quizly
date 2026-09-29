# Quizly – Backend

Django REST API for **Quizly**, an app that turns a YouTube video into a
multiple-choice quiz. The backend downloads the audio track of the video,
transcribes it with **Whisper AI** and lets `gpt-oss-120b` write a quiz with
10 questions and 4 answer options each. Both AI models run on **Groq**.

The frontend is provided separately and talks to this API via REST.
Authentication uses **JWT tokens in HttpOnly cookies**.

## Features

- Registration, login, logout and token refresh with JWT in HttpOnly cookies
- Logout puts the refresh **and** access token on a blacklist
- Create a quiz from a YouTube URL (`youtube.com/watch`, `youtu.be`, Shorts)
- List, read, rename and delete your own quizzes
- Admin panel to edit quizzes and single questions

## Tech stack

| Purpose | Tool |
|---|---|
| Web framework | Django, Django REST Framework |
| Authentication | djangorestframework-simplejwt (+ token blacklist) |
| CORS | django-cors-headers |
| YouTube download | yt-dlp |
| Audio conversion | FFmpeg |
| Transcription | Whisper AI (`whisper-large-v3-turbo`) via Groq API |
| Quiz generation | Groq API with `gpt-oss-120b` / `gpt-oss-20b` (`groq`) |

## Requirements

- **Python 3.12 or newer** (tested with 3.14)
- **FFmpeg, installed globally** – converts the audio for Whisper AI.
  The command `ffmpeg -version` must work in a new terminal.
  - Windows: `winget install Gyan.FFmpeg`
  - macOS: `brew install ffmpeg`
  - Linux (Debian/Ubuntu): `sudo apt install ffmpeg`
- **Deno** (recommended) – yt-dlp needs a JavaScript runtime for reliable
  YouTube downloads.
  - Windows: `winget install DenoLand.Deno`
  - macOS: `brew install deno`
  - Linux: `curl -fsSL https://deno.land/install.sh | sh`
- A free **Groq API key** from <https://console.groq.com/keys>
  (no credit card needed)

## Installation

```bash
git clone https://github.com/SiriusSagittarius/Quizly.git
cd Quizly

python -m venv env
# Windows
env\Scripts\activate
# macOS / Linux
source env/bin/activate

pip install -r requirements.txt
```

Copy `.env.example` to `.env` and fill in your values, at least
`DJANGO_SECRET_KEY` and `GROQ_API_KEY`:

```bash
cp .env.example .env
```

Create the database and an admin account, then start the server:

```bash
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

The API now runs at <http://127.0.0.1:8000/api/> and the admin panel at
<http://127.0.0.1:8000/admin/>.

## Using the frontend

Open the frontend folder with Live Server (VS Code) and use the address
**<http://127.0.0.1:5500>**, not `localhost:5500`. The auth cookies belong to
`127.0.0.1`. The browser only sends them to the API when the frontend runs
on the same host.

## API endpoints

| Method | Endpoint | Description | Auth |
|---|---|---|---|
| POST | `/api/register/` | Create a user account | – |
| POST | `/api/login/` | Log in, sets `access_token` and `refresh_token` cookies | – |
| POST | `/api/logout/` | Blacklist all tokens and delete the cookies | refresh cookie |
| POST | `/api/token/refresh/` | Set a new `access_token` cookie | refresh cookie |
| GET | `/api/quizzes/` | List your quizzes including questions | ✔ |
| POST | `/api/quizzes/` | Create a quiz from `{"url": "<YouTube URL>"}` | ✔ |
| GET | `/api/quizzes/{id}/` | Get one of your quizzes | ✔ |
| PATCH | `/api/quizzes/{id}/` | Change `title` and/or `description` | ✔ |
| DELETE | `/api/quizzes/{id}/` | Delete a quiz and its questions | ✔ |

Requests for a quiz of another user answer with `403`, unknown quizzes
with `404`.

## Configuration (`.env`)

| Variable | Meaning |
|---|---|
| `DJANGO_SECRET_KEY` | Secret key of the Django project |
| `DJANGO_DEBUG` | `True` for development |
| `DJANGO_ALLOWED_HOSTS` | Comma separated host names |
| `CORS_ALLOWED_ORIGINS` | Comma separated frontend origins |
| `JWT_COOKIE_SECURE` | `True` if the site runs on HTTPS |
| `GROQ_API_KEY` | Your Groq API key |
| `AI_MODELS` | Groq models, tried in this order |
| `TRANSCRIPTION_MODEL` | Whisper model on Groq |

## Good to know

- **Creating a quiz takes a moment.** The request waits for download,
  transcription and quiz generation, usually well under a minute.
- **Video length:** the audio is stored with 64 kbit/s, so videos up to
  about 50 minutes stay below the 25 MB upload limit of the Groq free tier.
- **Too little speech:** videos with fewer than 100 spoken words (music,
  noise) are rejected with `400`.
- **Groq free tier:** about 1,000 requests per day and 8,000 tokens per
  minute for each model. Transcripts are therefore cut after about
  16,000 characters (roughly 15 minutes of speech). For longer videos the
  quiz covers the first part of the video.
- **Fallback:** the backend tries the models from `AI_MODELS` one after
  another. If all of them fail, the API answers with `500` and an error
  message.

## Project structure

```
core/           Django settings and root URLs
auth_app/       Registration, login, logout, JWT cookie handling
  api/          Serializers, views, URLs, cookie authentication
quiz_app/       Quiz and question models, admin, quiz generation
  api/          Serializers, views, URLs, permissions, exceptions
  utils.py      YouTube -> audio -> transcript -> Groq AI -> database
```
