from dotenv import load_dotenv
from requests import post, get
import os
import base64
import json
import secrets
import string
from flask import (
    Flask,
    render_template,
    request,
    make_response,
    redirect,
    session,
    url_for,
)
from urllib.parse import urlencode

AUTH_URL = "https://accounts.spotify.com/authorize"
TOKEN_URL = "https://accounts.spotify.com/api/token"
BASE_URL = "https://api.spotify.com/v1/me"

load_dotenv()

REDIRECT_URI = os.getenv("REDIRECT_URI")
CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")

auth_string = f"{CLIENT_ID}:{CLIENT_SECRET}"
auth_bytes = auth_string.encode("utf-8")
auth_base64 = str(base64.b64encode(auth_bytes), "utf-8")
AUTHORIZATION_HEADER = {
    "Authorization": "Basic " + auth_base64,
    "Content-Type": "application/x-www-form-urlencoded",
}

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY")


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/login")
def login():
    state = "".join(
        secrets.choice(string.ascii_uppercase + string.digits) for _ in range(16)
    )
    scope = "user-top-read"
    payload = {
        "client_id": CLIENT_ID,
        "response_type": "code",
        "redirect_uri": REDIRECT_URI,
        "state": state,
        "scope": scope,
    }

    r = make_response(redirect(f"{AUTH_URL}/?{urlencode(payload)}"))
    r.set_cookie("auth_state", state)
    return r


@app.route("/callback")
def callback():
    code = request.args.get("code")
    state = request.args.get("state")
    stored_state = request.cookies.get("auth_state")

    payload = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": REDIRECT_URI,
    }

    r = post(TOKEN_URL, headers=AUTHORIZATION_HEADER, data=payload)
    r_data = json.loads(r.content)

    session["tokens"] = {
        "access_token": r_data.get("access_token"),
        "refresh_token": r_data.get("refresh_token"),
    }

    return redirect(url_for("user"))


@app.route("/refresh")
def refresh():
    headers = {
        "Authorization": AUTHORIZATION_HEADER,
        "Content-Type": "application/x-www-form-urlencoded",
    }
    payload = {
        "grant_type": "refresh_token",
        "refresh_token": session["tokens"].get("refresh_token"),
    }

    r = post(TOKEN_URL, headers=headers, data=payload)
    r_data = json.loads(r.content)

    session["tokens"]["access_token"] = r_data.get("access_token")

    return json.dumps(session["tokens"])


@app.route("/user")
def user():
    headers = {"Authorization": f"Bearer {session['tokens'].get('access_token')}"}

    r = get(BASE_URL, headers=headers)
    r_data = json.loads(r.content)

    return render_template("user.html", data=r_data, tokens=session.get("tokens"))


@app.route("/<top_items>")
def top(top_items):
    top_type = ""
    if top_items == "top_artists":
        top_type = "artists"
    elif top_items == "top_tracks":
        top_type = "tracks"

    headers = {"Authorization": f"Bearer {session['tokens'].get('access_token')}"}

    r = get(url=f"{BASE_URL}/top/{top_type}", headers=headers)
    r_data = json.loads(r.content)
    return render_template("top_items.html", data=r_data, tokens=session.get("tokens"))


if __name__ == "__main__":
    app.run()
