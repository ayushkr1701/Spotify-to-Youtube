# Spotify to YouTube Playlist Converter

A website that converts your spotify playlist to youtube playlist. The tech stack being used for this website is Flask. Spotify Developer account and basic knowledge is required for spotify oauth and setting the authentication from spotify side.
Apart from spotify, Google Console is also used for setting up YouTube Data API V3 and oauth.

## Setting Up Spotify Credentials

First of all, create a .env file in the root directory and create variables like SPOTIFYCLIENTID , SPOTIFYCLIENTSECRET , SPOTIFYREDIRECTURI. Now open spotify developers account https://developer.spotify.com/ and now go to your dashboard and click create app.
Give an app name, a basic description, and in redirect URIs add http://localhost:5000/callback and select web API and web playback one and click save. An app will be created, now click on settings and copy the client ID, client secret and redirect URI and paste it in the variables created previously in .env, the spotify credentials is all good to go.

## Setting up Google Cloud Platform for Oauth and youtube API 

Visit the Google cloud console website, create a new project, give it a name, organization and location. Once the project is created, select that project, click on APIs and Services, then click on enable APIs and Services and search for YouTube Data API v3 and enable that API. Now click on Oauth Consent Screen and select external, and then fill the basic details and in the scopes select .../auth/userinfo.email ,
.../auth/userinfo.profile, openid and then select the YouTube Data API v3 scopes. Now add a test user, and click save. Now go to credentials, click on create credentials and select the application type as web application and under add authorized URIs, click add URI and add http://localhost:5000/callback/google and once done, download the JSON and name it as client_secret_web.json , copy this file in the root directory of the project.

#Running the project
Open the terminal and run 'py app.py'. You will see that the development server is running on localhost 5000 port, open that in browser, click on authenticate with spotify, login with your spotify account and then you will be redirected to select one of your playlist, select the one you want to convert and then click on convert playlist, now you'll be redirected to authenticate with google account, select the one you added as test user, give permissions and your playlist will be created. Go to your linked youtube account and you'll see that there is a playlist with the same name and videos of all the songs that are there in your spotify playlist.

