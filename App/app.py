import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import streamlit as st
import pandas as pd
import pickle
from sqlalchemy import create_engine


# Set up Spotify credentials
sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(client_id="", client_secret="", requests_timeout=1000))

# Function to get track info
def get_track_info(query):
    results = sp.search(q=query, type='track', limit=1)
    if results['tracks']['items']:
        track_info = results['tracks']['items'][0]
        return track_info
    return None

# Function to get recommendations based on track name
def get_recommendations(track_name):
    query = f"track:{track_name}"
    results = sp.search(q=query, type='track')
    
    if results['tracks']['items']:
        seed_track_uri = results['tracks']['items'][0]['uri']
        recommendations = sp.recommendations(seed_tracks=[seed_track_uri])['tracks']
        return recommendations
    else:
        return []
    
# Custom CSS styles
custom_css = """
<style>
    body {
        background-color: #0E1117;
        color: #FAFAFA;
        font-family: Monospace;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        height: 100vh;
        margin: 0;
    }
    .stButton>button {
        background-color: #62E65B;
        color: #FAFAFA;
        transition: background-color 0.3s, color 0.3s;  /* Smooth transition */
    }
    .stButton>button:hover,
    .stButton>button:focus,
    .stButton>button:active {
        background-color: #62E65B;
        color: black;  /* Change font color to black when button is interacted */
    }
    .stTextInput>div>input {
        background-color: #262730;
        color: #FAFAFA;
    }
    .stButton {
        display: flex;
        justify-content: flex-end;
    }
</style>
"""

    
def tracks_items_to_df(tracks_items) :
    result = pd.DataFrame(columns=["track_id","track_name","track_preview_url","track_popularity","track_duration","artists_id","artists_name","album_id","album_name","album_ release_date"])

    traks_fields = {"track_id":"id","track_name":"name","track_preview_url":"preview_url","track_duration":"duration_ms","track_explicit":"explicit","track_popularity":"popularity"}
    artist_fields = {"artist_id":"id","artist_name":"name"}
    album_fields = {"album_id":"id","album_name":"name","album_release_date":"release_date"}

    dicts_list = []

    for item in tracks_items :
        row = {} 
        for field in traks_fields.items() : 
            row[field[0]] = item[field[1]]

        for artist in item["artists"]: # Comment c'est géré quand il y a plusieurs artistes ?
            for field in artist_fields.items() : 
                row[field[0]] = artist[field[1]]

        for field in album_fields.items() : 
            row[field[0]] = item["album"][field[1]]
       
        dicts_list.append(row)

    return pd.DataFrame(dicts_list)

def load(file_name):
    try:
        with open(file_name, "rb") as f:
            return pickle.load(f)
    except FileNotFoundError:
        print("File not found!")


# Apply custom CSS
st.markdown(custom_css, unsafe_allow_html=True)
st.markdown(
    """
    <style>
    /* Sélecteur pour la partie de la page que vous voulez cibler */
    div[data-testid="stHorizontalBlock"].css-ocqkz7  {
        align-items: end;
    }
    </style>
    """,
    unsafe_allow_html=True  # Permet l'exécution du code HTML
)

# -- Display on web page --

st.title("Music Recommendation & Player")

col1, col2 = st.columns([0.6, 0.4], gap="small")  

with col1:
    track_name = st.text_input(label="", placeholder="Enter a song name")

with col2:
    bouton = st.button("Get Recommendations", key="get_rec_button")


## -- When user have enter a song and pressed button --

if bouton and track_name:
    search_results = sp.search(q= track_name, type= "track")
    search_results_df = tracks_items_to_df(search_results["tracks"]["items"])
    song_choice = search_results_df.iloc[0,:]
    audio_features = sp.audio_features(song_choice["track_id"])
    audio_features = pd.DataFrame(audio_features)
    audio_features = audio_features.iloc[:,0:11]

    scaler  = load("scaler.pickle")
    model  = load("model.pickle")
    X_scaled_new = scaler.transform(audio_features)
    X_scaled_df= pd.DataFrame(X_scaled_new, columns = audio_features.columns)
    cluster = model.predict(X_scaled_df)[0]

    pw = "password1999"
    connection_string = 'mysql+pymysql://root:' + pw + '@localhost:3306/'
    engine = create_engine(connection_string, pool_pre_ping = False)
    
    X = pd.read_sql("SELECT * FROM spotify.df_feat_final", con = engine)

    reco_id = X[X['cluster'] == cluster].sample()["track_id"].values[0]
    reco_API_response = sp.track(reco_id)

    reco_track_name = reco_API_response["name"]
    reco_track_artist = reco_API_response["artists"][0]["name"]
    reco_preview_url = reco_API_response["preview_url"]
    reco_album_image_url = reco_API_response['album']['images'][0]['url']


    # -- Original music--
    col1, col2 = st.columns(2, gap = "medium")

    with col1:
        track_info = get_track_info(track_name)
        st.write("#### Original track")
        st.image(track_info['album']['images'][0]['url'], width=300)  # Image centrée

        original_audio_preview_url = track_info['preview_url']
        if original_audio_preview_url:
            st.audio(original_audio_preview_url, format='audio/mp3')
        else:
            st.write("No audio preview available for the original track.")

        st.write(track_info['name'], "-", track_info["artists"][0]["name"])  # Titre centré


    # -- Recommandation --
    with col2:
        st.write("#### Your recommendation")
        st.image(reco_album_image_url, width=300)  # Image centrée

        if reco_preview_url:
            st.audio(reco_preview_url, format='audio/mp3')
        else:
            st.write("No audio preview available for this recommended track.")

        st.write(reco_track_name, "-", reco_track_artist)