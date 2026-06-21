import os
import google.oauth2.credentials
import google_auth_oauthlib.flow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload
from google_auth_oauthlib.flow import InstalledAppFlow

# YouTube Data API scope for uploading videos
SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]


def get_authenticated_service(client_secrets_file="client_secrets.json", credentials_file="credentials.json"):
    """Handle OAuth2 authentication flow and return build object."""
    credentials = None
    
    # Load existing credentials if available
    if os.path.exists(credentials_file):
        try:
            from google.auth.transport.requests import Request
            import pickle
            with open(credentials_file, 'rb') as token:
                credentials = pickle.load(token)
            
            # Refresh token if expired
            if credentials and credentials.expired and credentials.refresh_token:
                credentials.refresh(Request())
        except Exception as e:
            print(f"Error loading saved credentials: {e}. Re-authenticating...")
            credentials = None

    # If credentials are not valid/available, perform OAuth flow
    if not credentials or not credentials.valid:
        if not os.path.exists(client_secrets_file):
            raise FileNotFoundError(
                f"🚨 Client secrets file not found at: {client_secrets_file}\n"
                "Please download OAuth Desktop credentials client JSON from Google Cloud Console "
                "and save it in the root folder."
            )
            
        flow = InstalledAppFlow.from_client_secrets_file(client_secrets_file, SCOPES)
        # Run local server to authenticate (requires browser interaction on the host machine)
        credentials = flow.run_local_server(port=0)
        
        # Save credentials for next runs
        import pickle
        with open(credentials_file, 'wb') as token:
            pickle.load = pickle.dump(credentials, token)

    return build("youtube", "v3", credentials=credentials)


def upload_video(video_path, title, description, tags, category_id="22", privacy_status="private", client_secrets_file="client_secrets.json", credentials_file="credentials.json"):
    """Upload a video to YouTube with metadata."""
    if not os.path.exists(video_path):
        raise FileNotFoundError(f"Video file not found at: {video_path}")
        
    print(f"📡 Connecting to YouTube Data API for upload: {title}...")
    youtube = get_authenticated_service(client_secrets_file, credentials_file)
    
    body = {
        "snippet": {
            "title": title[:100],  # Title limit is 100 characters
            "description": description,
            "tags": tags,
            "categoryId": category_id  # 22 is People & Blogs, 27 is Education, etc.
        },
        "status": {
            "privacyStatus": privacy_status,  # private, public, unlisted
            "selfDeclaredMadeForKids": False
        }
    }
    
    # Multi-part chunked upload setup
    media = MediaFileUpload(
        video_path,
        chunksize=1024*1024,
        mimetype="video/mp4",
        resumable=True
    )
    
    request = youtube.videos().insert(
        part="snippet,status",
        body=body,
        media_body=media
    )
    
    response = None
    print("🚀 Uploading video file...")
    while response is None:
        status, response = request.next_chunk()
        if status:
            print(f"Uploaded {int(status.progress() * 100)}%...")
            
    video_id = response.get("id")
    print(f"✅ Video Upload Completed! Video ID: {video_id}")
    print(f"🔗 Video URL: https://youtu.be/{video_id}")
    return video_id


def upload_thumbnail(video_id, thumbnail_path, client_secrets_file="client_secrets.json", credentials_file="credentials.json"):
    """Set custom thumbnail for the uploaded video ID."""
    if not os.path.exists(thumbnail_path):
        print(f"Thumbnail path not found: {thumbnail_path}. Skipping thumbnail upload.")
        return False
        
    print(f"🖼️ Uploading custom thumbnail for video: {video_id}...")
    youtube = get_authenticated_service(client_secrets_file, credentials_file)
    
    try:
        request = youtube.thumbnails().set(
            videoId=video_id,
            media_body=MediaFileUpload(thumbnail_path)
        )
        response = request.execute()
        print("✅ Custom Thumbnail Uploaded Successfully!")
        return True
    except HttpError as e:
        print(f"Error setting thumbnail: {e}")
        return False


if __name__ == "__main__":
    # Test script run
    print("YouTube Uploader script loaded. To run upload, import and execute upload_video().")
