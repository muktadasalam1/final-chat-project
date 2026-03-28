from fastapi import FastAPI, WebSocket, Form, File, UploadFile, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from database import get_connection
from starlette.websockets import WebSocketDisconnect
import os
import json
import uuid
import shutil
from datetime import datetime
from pathlib import Path

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

# ربط مجلد الملفات المرفوعة والمجلدات الثابتة
app.mount("/uploads", StaticFiles(directory=str(UPLOAD_DIR)), name="uploads")
app.mount("/css", StaticFiles(directory=str(FRONTEND_DIR / "css")), name="css")
app.mount("/js", StaticFiles(directory=str(FRONTEND_DIR / "js")), name="js")

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
        
        cur.execute("INSERT INTO users (username, password) VALUES (%s,%s) RETURNING id", (username, password))
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
        notification_data = json.dumps({
            "type": "new_user",
            "user": {
                "id": new_user_id,
                "username": username
            }
        })
        
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
        cur.execute("SELECT id, username FROM users WHERE username=%s AND password=%s", (username, password))
        user = cur.fetchone()
        if user:
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
    """رفع صورة"""
    try:
        if not file.content_type.startswith('image/'):
            return JSONResponse(status_code=400, content={"status": "fail", "detail": "الملف ليس صورة"})
        
        file_extension = file.filename.split(".")[-1]
        unique_filename = f"{datetime.now().timestamp()}_{uuid.uuid4().hex}.{file_extension}"
        file_path = IMAGES_DIR / unique_filename
        
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
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
    """رفع ملف صوتي"""
    try:
        if not file.content_type.startswith('audio/'):
            return JSONResponse(status_code=400, content={"status": "fail", "detail": "الملف ليس صوتي"})
        
        file_extension = file.filename.split(".")[-1] if file.filename else "webm"
        unique_filename = f"{datetime.now().timestamp()}_{uuid.uuid4().hex}.{file_extension}"
        file_path = AUDIO_DIR / unique_filename
        
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        return {
            "status": "success",
            "media_path": f"/uploads/audio/{unique_filename}",
            "file_name": file.filename or "audio.webm",
            "file_size": file_path.stat().st_size,
            "duration": duration,
            "media_type": "audio"
        }
    except Exception as e:
        return {"status": "fail", "detail": str(e)}

@app.post("/upload-video")
async def upload_video(file: UploadFile = File(...)):
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
            query = """
                SELECT u.id, u.username, p.full_name, p.avatar_path, uc.is_online
                FROM users u
                LEFT JOIN profiles p ON u.id = p.user_id
                LEFT JOIN user_connections uc ON u.id = uc.user_id
                WHERE u.id != %s
                ORDER BY uc.is_online DESC, u.username
            """
            cur.execute(query, (user_id,))
        
        users = cur.fetchall()
        
        users_list = []
        for user in users:
            users_list.append({
                "id": user[0],
                "username": user[1],
                "full_name": user[2] or user[1],
                "avatar_path": user[3] or "/uploads/avatars/default-avatar.png",
                "is_online": user[4] or False
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
            message_data = {
                "id": msg[0],
                "sender": msg[1],
                "message": msg[2] or "",
                "content_type": msg[3] if msg[3] else "text",
                "created_at": msg[4].isoformat() if msg[4] else None,
            }
            
            if msg[5]:
                message_data["media_type"] = msg[5]
                message_data["media_path"] = msg[6]
                if msg[5] in ["audio", "video"] and msg[7]:
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
        message_count = cur.fetchone()[0]
        
        cur.execute("SELECT COUNT(DISTINCT chat_id) FROM messages WHERE sender_id = %s OR chat_id = %s", (user_id, user_id))
        chat_count = cur.fetchone()[0]
        
        cur.execute("SELECT COUNT(*) FROM messages WHERE sender_id = %s AND content_type IN ('image', 'audio', 'video')", (user_id,))
        media_count = cur.fetchone()[0]
        
        profile_data = {
            "id": profile[0],
            "username": profile[1],
            "joined_date": profile[2].isoformat() if profile[2] else None,
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
        
        return {"status": "success", "profile": profile_data}
        
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
        
        allowed_fields = ['full_name', 'bio', 'phone_number', 'email', 'status_emoji']
        
        for field in allowed_fields:
            if field in data and data[field] is not None:
                fields.append(f"{field} = %s")
                values.append(data[field])
        
        if fields:
            values.append(user_id)
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
        allowed_settings = ['notifications_enabled', 'sound_enabled', 'message_preview_enabled', 'language', 'theme_preference']
        
        for setting, value in data.items():
            if setting in allowed_settings:
                if isinstance(value, str):
                    if value.lower() == 'true':
                        value = True
                    elif value.lower() == 'false':
                        value = False
                
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
    await websocket.accept()
    if user_id not in active_notifications:
        active_notifications[user_id] = []
    active_notifications[user_id].append(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        if user_id in active_notifications and websocket in active_notifications[user_id]:
            active_notifications[user_id].remove(websocket)

@app.websocket("/ws/users-updates")
async def users_updates_endpoint(websocket: WebSocket):
    await websocket.accept()
    active_users_updates.append(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        if websocket in active_users_updates:
            active_users_updates.remove(websocket)

@app.websocket("/ws/{user_id}/{other_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: int, other_id: int):
    await websocket.accept()
    sender_name = get_username(user_id)
    
    if user_id not in active_notifications:
        active_notifications[user_id] = []
    active_notifications[user_id].append(websocket)
    
    try:
        while True:
            data = await websocket.receive_text()
            try:
                message_data = json.loads(data)
            except:
                message_data = {"type": "text", "message": data}
            
            conn = get_connection()
            cur = conn.cursor()
            
            content_type = message_data.get('type', 'text')
            message_text = message_data.get('message', '')
            
            if content_type in ['image', 'audio', 'video']:
                message_text = message_data.get('media_path', '')
            
            cur.execute("""
                INSERT INTO messages (chat_id, sender_id, message, content_type, created_at) 
                VALUES (%s, %s, %s, %s, CURRENT_TIMESTAMP) RETURNING id
            """, (other_id, user_id, message_text, content_type))
            msg_id = cur.fetchone()[0]
            
            if content_type in ['image', 'audio', 'video'] and message_data.get('media_path'):
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
            
            response_data = {
                'type': content_type,
                'id': msg_id,
                'sender': user_id,
                'sender_name': sender_name,
                'timestamp': datetime.utcnow().isoformat()
            }
            
            if content_type == 'text':
                response_data['message'] = message_data.get('message', '')
            else:
                response_data['media_path'] = message_data.get('media_path', '')
                if content_type in ['audio', 'video']:
                    response_data['duration'] = message_data.get('duration', 0)
            
            if message_data.get('tempId'):
                response_data['tempId'] = message_data.get('tempId')
            
            await websocket.send_text(json.dumps(response_data))
            
            if other_id in active_notifications:
                for notif_ws in active_notifications[other_id][:]:
                    try:
                        if notif_ws != websocket:
                            await notif_ws.send_text(json.dumps(response_data))
                    except:
                        if notif_ws in active_notifications[other_id]:
                            active_notifications[other_id].remove(notif_ws)
                            
    except WebSocketDisconnect:
        if user_id in active_notifications and websocket in active_notifications[user_id]:
            active_notifications[user_id].remove(websocket)
    except Exception as e:
        print(f"Error in websocket: {e}")