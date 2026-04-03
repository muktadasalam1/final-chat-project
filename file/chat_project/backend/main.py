from fastapi import FastAPI, WebSocket, Form, File, UploadFile, Request
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.middleware.cors import CORSMiddleware
from starlette.staticfiles import StaticFiles
from starlette.websockets import WebSocketDisconnect
from starlette.datastructures import URLPath
from database import get_connection
from datetime import datetime
from pathlib import Path
import bcrypt
import shutil
import json
import uuid
import os

app = FastAPI()

# إعدادات CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# تحديد المسارات المطلقة
BASE_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIR = BASE_DIR / "frontend"
UPLOAD_DIR = BASE_DIR / "uploads"
IMAGES_DIR = UPLOAD_DIR / "images"
AUDIO_DIR = UPLOAD_DIR / "audio"
VIDEOS_DIR = UPLOAD_DIR / "videos"
AVATAR_DIR = UPLOAD_DIR / "avatars"

# إنشاء مجلدات للملفات
IMAGES_DIR.mkdir(parents=True, exist_ok=True)
AUDIO_DIR.mkdir(parents=True, exist_ok=True)
VIDEOS_DIR.mkdir(parents=True, exist_ok=True)
AVATAR_DIR.mkdir(parents=True, exist_ok=True)

class NoCacheStaticFiles(StaticFiles):
    async def get_response(self, path: str, scope: dict) -> Response:
        response = await super().get_response(path, scope)
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        return response

# ربط مجلد الملفات المرفوعة والمجلدات الثابتة
app.mount("/uploads", NoCacheStaticFiles(directory=str(UPLOAD_DIR)), name="uploads")
app.mount("/css", NoCacheStaticFiles(directory=str(FRONTEND_DIR / "css")), name="css")
app.mount("/js", NoCacheStaticFiles(directory=str(FRONTEND_DIR / "js")), name="js")

# متغيرات لتخزين الاتصالات النشطة
active_notifications = {}
active_users_updates = []

# ======================== تقديم الملفات الثابتة ========================
@app.get("/")
def root():
    """إرجاع صفحة index.html الرئيسية"""
    return FileResponse(FRONTEND_DIR / "index.html")

# ======================== المصادقة ========================
@app.post("/register")
async def register(username: str = Form(...), password: str = Form(...)):
    # تشفير كلمة المرور باستخدام bcrypt
    hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
    
    conn = get_connection()
    cur = conn.cursor()
    try:
        # التحقق من طول اسم المستخدم
        if len(username) < 3:
            return {"status": "fail", "detail": "اسم المستخدم يجب أن يكون 3 أحرف على الأقل"}
        
        # التحقق من عدم وجود الاسم
        cur.execute("SELECT id FROM users WHERE username = %s", (username,))
        if cur.fetchone():
            return {"status": "fail", "detail": "اسم المستخدم موجود بالفعل"}
        
        cur.execute("INSERT INTO users (username, password) VALUES (%s,%s) RETURNING id", (username, hashed_password.decode('utf-8')))
        new_user_id = cur.fetchone()[0]
        conn.commit()
        
        # إضافة سجل في جدول profiles
        cur.execute("""
            INSERT INTO profiles (user_id, full_name, last_seen)
            VALUES (%s, %s, CURRENT_TIMESTAMP)
        """, (new_user_id, username))
        
        # إضافة سجل في جدول user_settings
        cur.execute("""
            INSERT INTO user_settings (user_id)
            VALUES (%s)
        """, (new_user_id,))
        
        # إضافة سجل في جدول user_connections
        cur.execute("""
            INSERT INTO user_connections (user_id, is_online)
            VALUES (%s, %s)
        """, (new_user_id, False))
        
        conn.commit()
        
        # إرسال إشعار لجميع المستخدمين المتصلين عن المستخدم الجديد
        notification_data = json.dumps({ #the s in dumps stands for string
            "type": "new_user",#so it converts the Python object into a JSON string that can be sent over the WebSocket.
            "user": {
                "id": new_user_id,
                "username": username
            }
        })
        ####By using active_users_updates[:], 
        #the for loop processes each item in the copy (i will take each value from the copy), 
        #while any modifications (additions or removals) to the original list will not disrupt the iteration process.
        for ws in active_users_updates[:]:
            try:
                await ws.send_text(notification_data)
            except:
                if ws in active_users_updates:
                    active_users_updates.remove(ws)
        
        return {"status": "success", "user_id": new_user_id, "username": username}
    except Exception as e:
        conn.rollback()
        print(f"Error in register: {e}")
        return {"status": "fail", "detail": str(e)}
    finally:
        conn.close()

@app.post("/login")
def login(username: str = Form(...), password: str = Form(...)):
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("SELECT id, username, password FROM users WHERE username=%s", (username,))
        user = cur.fetchone() # fetchone() will return a single record as a tuple, 
                              #where user[0] is the user_id, user[1] is the username, 
                              # and user[2] is the hashed password.


        # verfiy the provided password against the stored hashed password using bcrypt's verify function.
        #the .checkpw method will handle the hashing and salting internally, 
        # ensuring that the password is securely checked without exposing the original password or the hash details.

        if user and bcrypt.checkpw(password.encode('utf-8'), user[2].encode('utf-8')):
            # تحديث آخر تسجيل دخول
            cur.execute("UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = %s", (user[0],))
            conn.commit()
            return {"status": "success", "user_id": user[0], "username": user[1]}
        return {"status": "fail", "detail": "اسم المستخدم أو كلمة المرور غير صحيحة"}
    except Exception as e:
        print(f"Error in login: {e}")
        return {"status": "fail", "detail": str(e)}
    finally:
        conn.close()

# ======================== رفع الملفات ========================
@app.post("/upload-image")
async def upload_image(file: UploadFile = File(...)):
#async defines an asynchronous function that can be awaited, 
#allowing for non-blocking operations, what it mean is that the method can perform other tasks while waiting for the file upload to complete, 
#improving the efficiency of handling multiple requests simultaneously.

##file: UploadFile is a class provided by FastAPI to handle file uploads.
# This is the type of input expected.
# It gives:1-file name 2-content type 3-file data (as a stream)
##=File(...) indicates that this parameter is required and should be treated as a file upload.

    """رفع صورة"""
    try:
        if not file.content_type.startswith('image/'): #validate the content type of the uploaded file to ensure it is an image.
            return JSONResponse(status_code=400, content={"status": "fail", "detail": "الملف ليس صورة"})
        
        file_extension = file.filename.split(".")[-1] #extract the file extension from the original filename.
        #we need a unique filename to avoid conflicts with existing files.
        #This line generates a unique filename by combining the current timestamp and a random UUID,
        #and appending the original file extension to maintain the correct format.
        unique_filename = f"{datetime.now().timestamp()}_{uuid.uuid4().hex}.{file_extension}" 
        
        file_path = IMAGES_DIR / unique_filename 
        
        with open(file_path, "wb") as buffer: #open the target file in binary write mode(required for images (not text!)) 
            #and use shutil.copyfileobj() to copy the contents of the uploaded file stream to the new file on disk.
            shutil.copyfileobj(file.file, buffer)
            #file is the fastapi wraper object that contains the uploaded file data, and file.file is the actual file stream that we can read from.
            #copyfileobj() needs streams(a stream is the actual file data piece by piece) as input taht way we used file.file which is the stream of the uploaded file, 
            #and buffer which is the stream of the new file we are creating on disk.
        return {
            "status": "success",
            "media_path": f"/uploads/images/{unique_filename}",
            "file_name": file.filename,
            "file_size": file_path.stat().st_size,
            "media_type": "image"
        }
    except Exception as e:
        return {"status": "fail", "detail": str(e)}

@app.post("/upload-audio")
async def upload_audio(file: UploadFile = File(...), duration: int = Form(0)):
    #same as upload-image but introduced duration for audio files, which is converting it to an int (Form(0)defualt value is 0)
    """رفع ملف صوتي"""
    try:
        if not file.content_type.startswith('audio/'):
            return JSONResponse(status_code=400, content={"status": "fail", "detail": "الملف ليس صوتي"})
        
        file_extension = file.filename.split(".")[-1] if file.filename else "webm"
        #if the filename exists, extract its extension the same way as upload-image.
        #if the filename is None (some browsers don't send it for recorded audio), default to "webm"
        #because recorded audio from the browser's MediaRecorder API is almost always in webm format.
        unique_filename = f"{datetime.now().timestamp()}_{uuid.uuid4().hex}.{file_extension}"
        file_path = AUDIO_DIR / unique_filename
        
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        return {
            "status": "success",
            "media_path": f"/uploads/audio/{unique_filename}",
            "file_name": file.filename or "audio.webm", #if the filename is None, default to "audio.webm" so the frontend always gets a readable name.
            "file_size": file_path.stat().st_size,
            "duration": duration, #include the duration in the response so the frontend can display the audio length without needing to load the file.
            "media_type": "audio"
        }
    except Exception as e:
        return {"status": "fail", "detail": str(e)}

@app.post("/upload-video")
async def upload_video(file: UploadFile = File(...)):
    #same as upload-image, but validates for video content type and saves to VIDEOS_DIR instead.
    #duration is not included here because video duration is typically handled by the frontend player directly.
    """رفع فيديو"""
    try:
        if not file.content_type.startswith('video/'):
            return JSONResponse(status_code=400, content={"status": "fail", "detail": "الملف ليس فيديو"})
        
        file_extension = file.filename.split(".")[-1]
        unique_filename = f"{datetime.now().timestamp()}_{uuid.uuid4().hex}.{file_extension}"
        file_path = VIDEOS_DIR / unique_filename
        
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        return {
            "status": "success",
            "media_path": f"/uploads/videos/{unique_filename}",
            "file_name": file.filename,
            "file_size": file_path.stat().st_size,
            "media_type": "video"
        }
    except Exception as e:
        return {"status": "fail", "detail": str(e)}

# ======================== المستخدمين ========================
@app.get("/users/{user_id}")
async def get_users(user_id: int, search: str = ""):
    """جلب المستخدمين مع إمكانية البحث"""
    conn = get_connection()
    cur = conn.cursor()
    try:
        if search:
            #if a search term is provided, filter users whose username OR full_name matches the search pattern.
            #ILIKE is a case-insensitive version of LIKE in PostgreSQL,
            #so searching for "ali" will also match "Ali" or "ALI".
            #the % around the search term act as wildcards, meaning the match can appear anywhere in the string.
            query = """
                SELECT u.id, u.username, p.full_name, p.avatar_path, uc.is_online
                FROM users u
                LEFT JOIN profiles p ON u.id = p.user_id
                LEFT JOIN user_connections uc ON u.id = uc.user_id
                WHERE u.id != %s
                AND (u.username ILIKE %s OR p.full_name ILIKE %s)
                ORDER BY uc.is_online DESC, u.username
            """
            search_pattern = f"%{search}%"
            cur.execute(query, (user_id, search_pattern, search_pattern))
        else:
            #if no search term is provided, return all users except the current user,
            #ordered so that online users appear first, then alphabetically by username.
            query = """
                SELECT u.id, u.username, p.full_name, p.avatar_path, uc.is_online
                FROM users u
                LEFT JOIN profiles p ON u.id = p.user_id
                LEFT JOIN user_connections uc ON u.id = uc.user_id
                WHERE u.id != %s
                ORDER BY uc.is_online DESC, u.username
            """
            cur.execute(query, (user_id,))
        
        users = cur.fetchall() #fetchall() returns all matching rows as a list of tuples.
        
        users_list = []
        for user in users:
            #build a clean dictionary for each user instead of returning raw tuples,
            #using "or" to provide fallback values when a field is NULL in the database.
            users_list.append({
                "id": user[0],
                "username": user[1],
                "full_name": user[2] or user[1], #if full_name is not set, fall back to username.
                "avatar_path": user[3] or "/uploads/avatars/default-avatar.png", #if no avatar is uploaded, use the default one.
                "is_online": user[4] or False #if the connection record is missing, treat the user as offline.
            })
        
        return {"users": users_list}
        
    except Exception as e:
        print(f"Error getting users: {e}")
        return {"users": []}
    finally:
        conn.close()

# ======================== الرسائل ========================
@app.get("/messages/{user_id}/{other_id}")
def get_messages(user_id: int, other_id: int):
    conn = get_connection()
    cur = conn.cursor()
    
    try:
        #fetch all messages exchanged between the two users in both directions:
        #either user_id sent to other_id, or other_id sent to user_id.
        #LEFT JOIN with message_media brings in any attached media info (image, audio, video) if it exists,
        #and returns NULL for media columns if the message has no attachment.
        #is_deleted = FALSE ensures soft-deleted messages are never shown to either user.
        #ORDER BY m.id ASC sorts messages from oldest to newest so the chat displays in the correct order.
        cur.execute("""
            SELECT m.id, m.sender_id, m.message, m.content_type, m.created_at,
                   mm.media_type, mm.media_path, mm.duration
            FROM messages m
            LEFT JOIN message_media mm ON m.id = mm.message_id
            WHERE (m.sender_id=%s AND m.chat_id=%s) OR (m.sender_id=%s AND m.chat_id=%s)
            AND m.is_deleted = FALSE
            ORDER BY m.id ASC
        """, (user_id, other_id, other_id, user_id))
        
        msgs = cur.fetchall()
        
        messages_list = []
        for msg in msgs:
            #build the base message dictionary from the messages table columns.
            message_data = {
                "id": msg[0],
                "sender": msg[1],
                "message": msg[2] or "", #if the message text is NULL (media-only message), return an empty string.
                "content_type": msg[3] if msg[3] else "text", #default to "text" if content_type is missing.
                "created_at": msg[4].isoformat() if msg[4] else None, #convert the datetime object to an ISO string so it can be serialized to JSON.
            }
            
            if msg[5]: #msg[5] is media_type — only add media fields if this message has an attachment.
                message_data["media_type"] = msg[5]
                message_data["media_path"] = msg[6]
                if msg[5] in ["audio", "video"] and msg[7]: #duration only makes sense for audio and video, not images.
                    message_data["duration"] = msg[7]
            
            messages_list.append(message_data)
        
        return {"messages": messages_list}
        
    except Exception as e:
        print(f"Error in get_messages: {e}")
        return {"messages": []}
    finally:
        conn.close()

# ======================== الملف الشخصي ========================
@app.get("/profile/{user_id}")
async def get_profile(user_id: int):
    """جلب الملف الشخصي للمستخدم"""
    conn = get_connection()
    cur = conn.cursor()
    try:
        #join three tables to get everything needed for the profile in a single query:
        #users: core account info (id, username, created_at, last_login)
        #profiles: personal details (full_name, bio, avatar, phone, email, last_seen, status_emoji)
        #user_connections: real-time online status (is_online)
        #LEFT JOIN is used so the query still returns the user even if their profile or connection record is missing.
        cur.execute("""
            SELECT u.id, u.username, u.created_at, u.last_login,
                   p.full_name, p.bio, p.avatar_path, p.phone_number, 
                   p.email, p.last_seen, p.status_emoji,
                   uc.is_online
            FROM users u
            LEFT JOIN profiles p ON u.id = p.user_id
            LEFT JOIN user_connections uc ON u.id = uc.user_id
            WHERE u.id = %s
        """, (user_id,))
        profile = cur.fetchone()
        
        if not profile:
            return JSONResponse(status_code=404, content={"status": "fail", "detail": "User not found"})
        
        # جلب الإعدادات
        cur.execute("SELECT * FROM user_settings WHERE user_id = %s", (user_id,))
        settings = cur.fetchone()
        
        # جلب الإحصائيات
        cur.execute("SELECT COUNT(*) FROM messages WHERE sender_id = %s", (user_id,))
        message_count = cur.fetchone()[0] #total number of messages sent by this user.
        
        cur.execute("""
            SELECT COUNT(DISTINCT user_id) FROM (
                SELECT chat_id AS user_id FROM messages WHERE sender_id = %s
                UNION
                SELECT sender_id AS user_id FROM messages WHERE chat_id = %s
            ) AS conversations
        """, (user_id, user_id))
        chat_count = cur.fetchone()[0] #number of unique conversations this user has participated in.
        #DISTINCT ensures each chat is counted once even if multiple messages were exchanged.
        
        cur.execute("SELECT COUNT(*) FROM messages WHERE sender_id = %s AND content_type IN ('image', 'audio', 'video')", (user_id,))
        media_count = cur.fetchone()[0] #total number of media messages (images, audio, video) sent by this user.
        
        #build the final profile dictionary using index-based access on the tuple returned by fetchone().
        #"or" is used as a fallback for any field that might be NULL in the database.
        profile_data = {
            "id": profile[0],
            "username": profile[1],
            "joined_date": profile[2].isoformat() if profile[2] else None, #convert datetime to ISO string for JSON serialization.
            "last_login": profile[3].isoformat() if profile[3] else None,
            "full_name": profile[4] or "",
            "bio": profile[5] or "",
            "avatar_path": profile[6] or "/uploads/avatars/default-avatar.png",
            "phone_number": profile[7] or "",
            "email": profile[8] or "",
            "last_seen": profile[9].isoformat() if profile[9] else None,
            "status_emoji": profile[10] or "👤",
            "is_online": profile[11] or False,
            "settings": {
                #settings are accessed by column index from the user_settings table.
                #if the settings record doesn't exist, fall back to safe default values.
                "notifications_enabled": settings[2] if settings else True,
                "sound_enabled": settings[3] if settings else True,
                "message_preview_enabled": settings[4] if settings else True,
                "language": settings[5] if settings else "ar",
                "theme_preference": settings[6] if settings else "dark"
            } if settings else {},
            "stats": {
                "messages": message_count,
                "chats": chat_count,
                "media": media_count
            }
        }
        
        return {"status": "success", "data": profile_data}
        
    except Exception as e:
        print(f"Error getting profile: {e}")
        return JSONResponse(status_code=500, content={"status": "fail", "detail": str(e)})
    finally:
        conn.close()

@app.post("/profile/update/{user_id}")
async def update_profile(user_id: int, request: Request):
    """تحديث الملف الشخصي"""
    data = await request.json()
    conn = get_connection()
    cur = conn.cursor()
    
    try:
        fields = []
        values = []
        
        #only allow updating specific fields to prevent the user from overwriting
        #sensitive columns like user_id or created_at by injecting unexpected keys.
        allowed_fields = ['full_name', 'bio', 'phone_number', 'email', 'status_emoji',"username"]
        
        for field in allowed_fields:
            if field in data and data[field] is not None:
                #dynamically build the SET clause by collecting only the fields
                #that were actually sent in the request and are not None.
                fields.append(f"{field} = %s")
                values.append(data[field])
        
        if fields:
            values.append(user_id)
            #use INSERT ... ON CONFLICT DO UPDATE (also known as "upsert") so that
            #if a profile row already exists for this user it gets updated,
            #and if it doesn't exist yet it gets created — all in a single query.
            query = f"""
                INSERT INTO profiles (user_id, {', '.join([f.split('=')[0] for f in fields])})
                VALUES (%s, {', '.join(['%s'] * len(fields))})
                ON CONFLICT (user_id) 
                DO UPDATE SET {', '.join(fields)}
            """
            final_values = [data[f.split('=')[0].strip()] for f in fields] + [user_id]
            cur.execute(query, final_values)
            conn.commit()
        
        return {"status": "success", "message": "Profile updated successfully"}
        
    except Exception as e:
        conn.rollback()
        print(f"Error updating profile: {e}")
        return JSONResponse(status_code=500, content={"status": "fail", "detail": str(e)})
    finally:
        conn.close()

@app.post("/settings/update/{user_id}")
async def update_settings(user_id: int, request: Request):
    """تحديث إعدادات المستخدم"""
    data = await request.json()
    conn = get_connection()
    cur = conn.cursor()
    
    try:
        #same allowed-list approach as update_profile — only recognized setting keys are processed,
        #anything else in the request body is silently ignored.
        allowed_settings = ['notifications_enabled', 'sound_enabled', 'message_preview_enabled', 'language', 'theme_preference']
        
        for setting, value in data.items():
            if setting in allowed_settings:
                if isinstance(value, str): #isinstance returns True if the value object is of the string type 
                    #boolean values coming from HTML forms or some frontends arrive as the strings "true"/"false"
                    #instead of actual Python booleans, so we convert them manually before saving to the DB.
                    if value.lower() == 'true':
                        value = True
                    elif value.lower() == 'false':
                        value = False
                
                #same upsert pattern as update_profile — insert a new settings row if one doesn't exist,
                #or update just the changed setting if it does.
                #updated_at is refreshed on every update so we can track when settings were last changed.
                query = f"""
                    INSERT INTO user_settings (user_id, {setting})
                    VALUES (%s, %s)
                    ON CONFLICT (user_id) 
                    DO UPDATE SET {setting} = %s, updated_at = CURRENT_TIMESTAMP
                """
                cur.execute(query, (user_id, value, value))
        
        conn.commit()
        return {"status": "success", "message": "Settings updated successfully"}
        
    except Exception as e:
        conn.rollback()
        print(f"Error updating settings: {e}")
        return JSONResponse(status_code=500, content={"status": "fail", "detail": str(e)})
    finally:
        conn.close()

# ======================== دوال مساعدة ========================
def get_username(user_id: int):
    #a simple helper function used internally by the WebSocket endpoint to get a sender's display name.
    #it returns "مستخدم"  as a safe fallback
    #if the user is not found or if any database error occurs.
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT username FROM users WHERE id = %s", (user_id,))
        result = cur.fetchone()
        conn.close()
        return result[0] if result else "مستخدم"
    except:
        return "مستخدم"

# ======================== WebSockets ========================
@app.websocket("/ws/notifications/{user_id}")
async def notifications_endpoint(websocket: WebSocket, user_id: int):
    #this endpoint is dedicated to receiving real-time notifications (friend requests, likes, etc.)
    #it does not send messages — it only listens and keeps the connection alive.
    await websocket.accept()
    if user_id not in active_notifications:
        active_notifications[user_id] = [] #initialize an empty list for this user if they have no active connections yet.
    active_notifications[user_id].append(websocket) #register this connection so the server can push notifications to it later.
    try:
        while True:
            await websocket.receive_text() #keep the connection alive by continuously waiting for any incoming data.
                                           #the client doesn't need to send anything useful here — this just prevents the connection from timing out.
    except WebSocketDisconnect:
        pass
    finally:
        #clean up by removing this specific WebSocket connection from the user's list when they disconnect.
        if user_id in active_notifications and websocket in active_notifications[user_id]:
            active_notifications[user_id].remove(websocket)

@app.websocket("/ws/users-updates")
async def users_updates_endpoint(websocket: WebSocket):
    #this endpoint broadcasts updates about users (like a new user registering) to all connected clients.
    #unlike notifications_endpoint which is per-user, this one is shared across everyone — 
    #any client connected here will receive events that affect the global user list.
    await websocket.accept()
    active_users_updates.append(websocket) #add this connection to the global broadcast list.
    try:
        while True:
            await websocket.receive_text() #same keep-alive pattern as notifications_endpoint.
    except WebSocketDisconnect:
        pass
    finally:
        if websocket in active_users_updates:
            active_users_updates.remove(websocket)

@app.websocket("/ws/{user_id}/{other_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: int, other_id: int):
    #this is the main chat WebSocket endpoint — it handles real-time message sending between two users.
    #user_id is the sender (the one connecting), other_id is the recipient.
    await websocket.accept()
    sender_name = get_username(user_id) #fetch the sender's username once at connection time so we don't query the DB on every message.
    
    if user_id not in active_notifications:
        active_notifications[user_id] = []
    active_notifications[user_id].append(websocket) #register the chat connection under the sender's notification list
                                                     #so they can also receive incoming notifications through the same connection.
    
    try:
        while True:
            data = await websocket.receive_text() #wait for the next message from the client.
            try:
                message_data = json.loads(data) #try to parse the incoming data as JSON.
            except:
                message_data = {"type": "text", "message": data} #if parsing fails (plain string sent), treat it as a plain text message.
            
            conn = get_connection()
            cur = conn.cursor()
            
            content_type = message_data.get('type', 'text') #get the message type (text, image, audio, video), defaulting to "text".
            message_text = message_data.get('message', '')
            
            if content_type in ['image', 'audio', 'video']:
                message_text = message_data.get('media_path', '') #for media messages, the "message" field holds the file path, not text.
            
            #save the message to the messages table and get back the generated message id using RETURNING id.
            #chat_id is set to other_id because the chat "belongs" to the conversation with the other user.
            cur.execute("""
                INSERT INTO messages (chat_id, sender_id, message, content_type, created_at) 
                VALUES (%s, %s, %s, %s, CURRENT_TIMESTAMP) RETURNING id
            """, (other_id, user_id, message_text, content_type))
            msg_id = cur.fetchone()[0]
            
            if content_type in ['image', 'audio', 'video'] and message_data.get('media_path'):
                #if the message contains a media file, save the extra media details
                #in the message_media table linked to the message by its id.
                cur.execute("""
                    INSERT INTO message_media (message_id, media_type, media_path, file_name, file_size, duration, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
                """, (
                    msg_id,
                    content_type,
                    message_data.get('media_path'),
                    message_data.get('file_name', ''),
                    message_data.get('file_size', 0),
                    message_data.get('duration', 0)
                ))
            
            conn.commit()
            conn.close()
            
            #build the response object that will be sent back to both the sender and the recipient.
            response_data = {
                'type': content_type,
                'id': msg_id,
                'sender': user_id,
                'sender_name': sender_name,
                'timestamp': datetime.utcnow().isoformat() #use UTC time so timestamps are consistent regardless of server timezone.
            }
            
            if content_type == 'text':
                response_data['message'] = message_data.get('message', '')
            else:
                response_data['media_path'] = message_data.get('media_path', '')
                if content_type in ['audio', 'video']:
                    response_data['duration'] = message_data.get('duration', 0)
            
            if message_data.get('tempId'):
                response_data['tempId'] = message_data.get('tempId') #echo back the temporary client-side id so the frontend
                                                                      #can replace the optimistic message with the confirmed one.
            
            await websocket.send_text(json.dumps(response_data)) #send the confirmed message back to the sender.
            
            if other_id in active_notifications:
                ####same copy-iteration pattern as in register — iterate over a copy of the list
                #so that removing a broken connection during the loop doesn't skip or crash the iteration.
                for notif_ws in active_notifications[other_id][:]:
                    try:
                        if notif_ws != websocket: #avoid sending the message back to the sender's own connection again.
                            await notif_ws.send_text(json.dumps(response_data)) #push the message to the recipient in real time.
                    except:
                        if notif_ws in active_notifications[other_id]:
                            active_notifications[other_id].remove(notif_ws) #remove the broken connection if sending fails.
                            
    except WebSocketDisconnect:
        if user_id in active_notifications and websocket in active_notifications[user_id]:
            active_notifications[user_id].remove(websocket)
    except Exception as e:
        print(f"Error in websocket: {e}")