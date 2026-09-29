# Quizly – Backend

Django REST API for **Quizly**, an app that turns a YouTube video into a
multiple-choice quiz. The backend downloads the audio track of the video,
transcribes it locally with **Whisper AI** and lets **Google Gemini Flash**
write a quiz with 10 questions and 4 answer options each.

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
| Transcription | Whisper AI (`openai-whisper`, runs locally) |
| Quiz generation | Google Gemini Flash (`google-genai`) |

## Requirements

- **Python 3.12 or newer** (tested with 3.14)
- **FFmpeg, installed globally** – required by Whisper AI and yt-dlp.
  The command `ffmpeg -version` must work in a new terminal.
  - Windows: `winget install Gyan.FFmpeg`
  - macOS: `brew install ffmpeg`
  - Linux (Debian/Ubuntu): `sudo apt install ffmpeg`
- **Deno** (recommended) – yt-dlp needs a JavaScript runtime for reliable
  YouTube downloads.
  - Windows: `winget install DenoLand.Deno`
  - macOS: `brew install deno`
  - Linux: `curl -fsSL https://deno.land/install.sh | sh`
- A free **Gemini API key** from <https://aistudio.google.com/apikey>
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
`DJANGO_SECRET_KEY` and `GEMINI_API_KEY`:

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
| `GEMINI_API_KEY` | Your Gemini API key |
| `GEMINI_MODELS` | Gemini Flash models, tried in this order |
| `WHISPER_MODEL` | Whisper model size (`tiny`, `base`, `small`, ...) |

## Good to know

- **Creating a quiz takes time.** The request waits for download,
  transcription and quiz generation. On a normal CPU a 5-minute video
  needs roughly one minute.
- **First quiz:** Whisper downloads its model once (about 140 MB for `base`).
- **One at a time:** transcriptions run one after another. A second quiz
  request waits until the first transcription is finished.
- **No speech:** videos without any spoken words are rejected with `400`.
- **Gemini free tier:** each model allows only about 20 requests per day
  and can be overloaded at peak times. The backend therefore tries the
  models from `GEMINI_MODELS` one after another. If all of them fail, the
  API answers with `500` and an error message.
- **Long videos:** transcripts are cut after 100,000 characters (about
  1.5 hours of speech).

## Project structure

```
core/           Django settings and root URLs
auth_app/       Registration, login, logout, JWT cookie handling
  api/          Serializers, views, URLs, cookie authentication
quiz_app/       Quiz and question models, admin, quiz generation
  api/          Serializers, views, URLs, permissions, exceptions
  utils.py      YouTube -> audio -> transcript -> Gemini -> database
```
