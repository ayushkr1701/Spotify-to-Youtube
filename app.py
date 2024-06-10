from urllib.error import HTTPError
from flask import Flask, render_template, request, redirect, url_for, session
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials
import googleapiclient.discovery
import googleapiclient.errors
import os
import time
import socket

socket.setdefaulttimeout(300000)

video_cache = {}


app = Flask(__name__)
app.secret_key = os.urandom(24)  
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1' #"to solve the http error occuring during oauth as it does not allow on http but on https"

#Spotify API credentials
SPOTIFY_CLIENT_ID = os.getenv("SPOTIFYCLIENTID")
print(SPOTIFY_CLIENT_ID)
SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIFYCLIENTSECRET")
SPOTIFY_REDIRECT_URI = os.getenv("SPOTIFYREDIRECTURI")

#YouTube API credentials
CLIENT_SECRETS_FILE = "client_secret_web_2.json"
SCOPES = ["https://www.googleapis.com/auth/youtube.force-ssl"]
API_SERVICE_NAME = "youtube"
API_VERSION = "v3"

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/authenticate-spotify')
def authenticate_spotify():
    sp_oauth = SpotifyOAuth(client_id=SPOTIFY_CLIENT_ID, client_secret=SPOTIFY_CLIENT_SECRET,
                            redirect_uri=SPOTIFY_REDIRECT_URI, scope='playlist-read-private')
    auth_url = sp_oauth.get_authorize_url()
    return redirect(auth_url)

@app.route('/callback')
def callback_spotify():
    code = request.args.get('code')
    state = request.args.get('state')
    sp_oauth = SpotifyOAuth(client_id=SPOTIFY_CLIENT_ID, client_secret=SPOTIFY_CLIENT_SECRET,
                            redirect_uri=SPOTIFY_REDIRECT_URI, scope='playlist-read-private')
    token_info = sp_oauth.get_access_token(code)
    session['spotify_token_info'] = token_info
    return redirect(url_for('select_playlist'))

@app.route('/select-playlist')
def select_playlist():
    token_info = session.get('spotify_token_info', None)
    if not token_info:
        return redirect(url_for('authenticate_spotify'))
    
    spotify = spotipy.Spotify(auth=token_info['access_token'])
    playlists = spotify.current_user_playlists()
    return render_template('select_playlist.html', playlists=playlists['items'])

@app.route('/authenticate-google')
def authenticate_google():
    flow = InstalledAppFlow.from_client_secrets_file(
        CLIENT_SECRETS_FILE, SCOPES)
    flow.redirect_uri = url_for('callback_google', _external=True)
    authorization_url, state = flow.authorization_url(
        access_type='offline',
        prompt='select_account')
    session['state'] = state
    print(authorization_url)
    return redirect(authorization_url)

@app.route('/callback/google')
def callback_google():
    state = request.args.get('state')
    if state != session.get('state'):
        raise Exception('Invalid state')
    
    flow = InstalledAppFlow.from_client_secrets_file(
        CLIENT_SECRETS_FILE, SCOPES, state=state)
    flow.redirect_uri = url_for('callback_google', _external=True)
    authorization_response = request.url
    flow.fetch_token(authorization_response=authorization_response)
    credentials = flow.credentials
    session['credentials'] = credentials_to_dict(credentials)
    return redirect(url_for('convert_playlist'))

def credentials_to_dict(credentials):
    return {
        'token': credentials.token,
        'refresh_token': credentials.refresh_token,
        'token_uri': credentials.token_uri,
        'client_id': credentials.client_id,
        'client_secret': credentials.client_secret,
        'scopes': credentials.scopes
    }

@app.route('/convert-playlist', methods=['POST'])
def convert_playlist():
    playlist_id = request.form.get('playlist_id')

    def get_authenticated_youtube():
        credentials_dict = session.get('credentials')
        if not credentials_dict:
            print("No credentials found in session. Redirecting to authenticate with Google.")
            return None
        
        credentials = Credentials(**credentials_dict)
        try:
            youtube = googleapiclient.discovery.build(
                API_SERVICE_NAME, API_VERSION, credentials=credentials)
            return youtube
        except Exception as e:
            print("An error occurred while creating the YouTube API client:", e)
            return None

    youtube = get_authenticated_youtube()
    if not youtube:
        return redirect(url_for('authenticate_google'))
    def create_playlist(youtube, title, description):
        try:
            request = youtube.playlists().insert(
                part="snippet,status",
                body={
                    "snippet": {
                        "title": title,
                        "description": description,
                    },
                    "status": {
                        "privacyStatus": "private"
                    }
                }
            )
            response = request.execute()
            print(f"Playlist {title} created!!")
            return response["id"]
        except Exception as e:
            print("An error occurred while creating the youtube playlist:", e)
            return None   

    def search_video(youtube, query):
        if query in video_cache:
            return video_cache[query]
        else:
            try:
                request = youtube.search().list(
                    part="snippet",
                    q=query,
                    type="video",
                    maxResults=1,
                )
                response = request.execute()
                if response['items']:
                    video_id = response['items'][0]['id']['videoId']
                    video_cache[query] = video_id
                    return video_id
                else:
                    return None
            except HTTPError as e:
                print("An error occurred:", e)
                return None

    def add_video_to_playlist(youtube, playlist_id, video_id):
        max_retries = 5
        retry_count = 0
        backoff_time = 1
        while retry_count < max_retries:
            try:
                request = youtube.playlistItems().insert(
                    part="snippet",
                    body={
                        "snippet": {
                            "playlistId": playlist_id,
                            "position": 0,
                            "resourceId": {
                                "kind": "youtube#video",
                                "videoId": video_id
                            }
                        }
                    },
                )
                response = request.execute()
                print(f"{video_id} added!")
                return response
            except HTTPError as e:
                print(e)
                if e.resp.status == 409:
                    print(f"Song '{video_id}' already exists in the playlist. skippin")
                    return None
                elif 'SERVICE_UNAVAILABLE' in str(e):
                    retry_count += 1
                    print(f"Attempt {retry_count} failed. Retrying in {backoff_time} sec")
                    time.sleep(backoff_time)
                    backoff_time *= 2
                else:
                    raise Exception("Failed to add the song to the playlist after n retries.")

        raise Exception("Failed to add the song to the playlist after n retries.")


    token_info = session.get('spotify_token_info', None)
    if not token_info:
        return redirect(url_for('authenticate_spotify'))
    
    spotify = spotipy.Spotify(auth=token_info['access_token'])
    playlist = spotify.playlist(playlist_id)
    title = playlist['name']
    description = playlist['description']
    youtube_playlist_id = create_playlist(youtube, title, description)

    if not youtube_playlist_id:
        return "Failed to create YouTube playlist."

    tracks = spotify.playlist_tracks(playlist_id)
    for item in tracks['items']:
        track = item['track']
        query = f"{track['name']} by {', '.join([artist['name'] for artist in track['artists']])}"
        video_id = search_video(youtube, query)
        if video_id:
            add_video_to_playlist(youtube, youtube_playlist_id, video_id)
        else:
            print('Video not found!')

    return "Playlist converted successfully yeeeeeeee!!!!"

if __name__ == '__main__':
    app.run(debug=True)
