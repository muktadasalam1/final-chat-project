import psycopg2
from psycopg2.extras import RealDictCursor
import os

def get_connection():
    """الحصول على اتصال بقاعدة البيانات"""
    try:
        conn = psycopg2.connect(
            host=os.getenv('DB_HOST', 'localhost'),
            database=os.getenv('DB_NAME', 'chat_app'),
            user=os.getenv('DB_USER', 'postgres'),
            password=os.getenv('DB_PASSWORD', '5432'),
            port=os.getenv('DB_PORT', '5432')
        )
        return conn
    except Exception as e:
        print(f"Database connection error: {e}")
        raise

def init_database():
    """إنشاء جميع الجداول المطلوبة للتطبيق"""
    conn = get_connection()
    cur = conn.cursor()
    
    print("🔄 جاري تهيئة قاعدة البيانات...")
    
    # حذف الجداول القديمة (CASCADE لضمان حذف العلاقات)
    tables = [
        'message_reads', 'message_deletions', 'message_media', 
        'user_settings', 'user_connections', 'profiles', 
        'messages', 'users'
    ]
    
    for table in tables:
        try:
            cur.execute(f"DROP TABLE IF EXISTS {table} CASCADE")
            print(f"✓ تم حذف جدول {table} (إن وجد)")
        except Exception as e:
            print(f"⚠️ خطأ في حذف {table}: {e}")
    
    # 1. جدول المستخدمين
    cur.execute("""
        CREATE TABLE users (
            id SERIAL PRIMARY KEY,
            username VARCHAR(50) UNIQUE NOT NULL,
            password VARCHAR(255) NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_login TIMESTAMP,
            is_active BOOLEAN DEFAULT TRUE
        )
    """)
    print("✓ تم إنشاء جدول users")
    
    # 2. جدول الملفات الشخصية
    cur.execute("""
        CREATE TABLE profiles (
            id SERIAL PRIMARY KEY,
            user_id INTEGER UNIQUE NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            full_name VARCHAR(100),
            bio TEXT,
            avatar_path VARCHAR(500),
            phone_number VARCHAR(20),
            email VARCHAR(100),
            status_emoji VARCHAR(10) DEFAULT '👤',
            last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            avatar_updated_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    print("✓ تم إنشاء جدول profiles")
    
    # 3. جدول الرسائل
    cur.execute("""
        CREATE TABLE messages (
            id SERIAL PRIMARY KEY,
            chat_id INTEGER NOT NULL,
            sender_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            message TEXT,
            content_type VARCHAR(20) DEFAULT 'text',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            edited BOOLEAN DEFAULT FALSE,
            edited_at TIMESTAMP,
            is_deleted BOOLEAN DEFAULT FALSE,
            deleted_for_all BOOLEAN DEFAULT FALSE
        )
    """)
    print("✓ تم إنشاء جدول messages")
    
    # 4. جدول الوسائط للرسائل
    cur.execute("""
        CREATE TABLE message_media (
            id SERIAL PRIMARY KEY,
            message_id INTEGER NOT NULL REFERENCES messages(id) ON DELETE CASCADE,
            media_type VARCHAR(20) NOT NULL,
            media_path VARCHAR(500) NOT NULL,
            file_name VARCHAR(255),
            file_size INTEGER,
            duration INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    print("✓ تم إنشاء جدول message_media")
    
    # 5. جدول قراءة الرسائل
    cur.execute("""
        CREATE TABLE message_reads (
            id SERIAL PRIMARY KEY,
            message_id INTEGER NOT NULL REFERENCES messages(id) ON DELETE CASCADE,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            read_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(message_id, user_id)
        )
    """)
    print("✓ تم إنشاء جدول message_reads")
    
    # 6. جدول حذف الرسائل للمستخدمين
    cur.execute("""
        CREATE TABLE message_deletions (
            id SERIAL PRIMARY KEY,
            message_id INTEGER NOT NULL REFERENCES messages(id) ON DELETE CASCADE,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            deleted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(message_id, user_id)
        )
    """)
    print("✓ تم إنشاء جدول message_deletions")
    
    # 7. جدول إعدادات المستخدم
    cur.execute("""
        CREATE TABLE user_settings (
            id SERIAL PRIMARY KEY,
            user_id INTEGER UNIQUE NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            notifications_enabled BOOLEAN DEFAULT TRUE,
            sound_enabled BOOLEAN DEFAULT TRUE,
            message_preview_enabled BOOLEAN DEFAULT TRUE,
            language VARCHAR(10) DEFAULT 'ar',
            theme_preference VARCHAR(20) DEFAULT 'dark',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    print("✓ تم إنشاء جدول user_settings")
    
    # 8. جدول اتصالات المستخدمين
    cur.execute("""
        CREATE TABLE user_connections (
            id SERIAL PRIMARY KEY,
            user_id INTEGER UNIQUE NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            is_online BOOLEAN DEFAULT FALSE,
            last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            current_room VARCHAR(100)
        )
    """)
    print("✓ تم إنشاء جدول user_connections")
    
    # إنشاء بعض الفهارس لتحسين الأداء
    cur.execute("CREATE INDEX IF NOT EXISTS idx_messages_chat_id ON messages(chat_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_messages_sender_id ON messages(sender_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_messages_created_at ON messages(created_at)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_message_media_message_id ON message_media(message_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_message_reads_message_id ON message_reads(message_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_message_reads_user_id ON message_reads(user_id)")
    
    conn.commit()
    conn.close()
    
    print("✅ تم تهيئة قاعدة البيانات بنجاح!")
    print("📊 الجداول المنشأة:")
    print("   - users (المستخدمين)")
    print("   - profiles (الملفات الشخصية)")
    print("   - messages (الرسائل)")
    print("   - message_media (الوسائط)")
    print("   - message_reads (قراءة الرسائل)")
    print("   - message_deletions (حذف الرسائل)")
    print("   - user_settings (إعدادات المستخدم)")
    print("   - user_connections (اتصالات المستخدمين)")

def init_database_with_sample_data():
    """تهيئة قاعدة البيانات مع بعض البيانات التجريبية"""
    init_database()
    
    conn = get_connection()
    cur = conn.cursor()
    
    try:
        # إضافة مستخدم تجريبي
        cur.execute("""
            INSERT INTO users (username, password) 
            VALUES (%s, %s)
            ON CONFLICT (username) DO NOTHING
            RETURNING id
        """, ('demo', 'demo123'))
        
        demo_user = cur.fetchone()
        
        if demo_user:
            user_id = demo_user[0]
            
            # إضافة ملف شخصي للمستخدم التجريبي
            cur.execute("""
                INSERT INTO profiles (user_id, full_name, bio, status_emoji)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (user_id) DO NOTHING
            """, (user_id, 'مستخدم تجريبي', 'مرحباً! أنا أستخدم تطبيق الدردشة', '😊'))
            
            # إضافة إعدادات للمستخدم التجريبي
            cur.execute("""
                INSERT INTO user_settings (user_id)
                VALUES (%s)
                ON CONFLICT (user_id) DO NOTHING
            """, (user_id,))
            
            # إضافة اتصال للمستخدم التجريبي
            cur.execute("""
                INSERT INTO user_connections (user_id, is_online)
                VALUES (%s, %s)
                ON CONFLICT (user_id) DO NOTHING
            """, (user_id, True))
            
            print("✓ تم إضافة مستخدم تجريبي: demo / demo123")
        
        conn.commit()
        print("✅ تمت إضافة البيانات التجريبية بنجاح!")
        
    except Exception as e:
        print(f"⚠️ خطأ في إضافة البيانات التجريبية: {e}")
        conn.rollback()
    finally:
        conn.close()

def test_connection():
    """اختبار الاتصال بقاعدة البيانات"""
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT version();")
        version = cur.fetchone()
        print(f"✅ Database connected successfully!")
        print(f"📦 PostgreSQL version: {version[0][:50]}...")
        conn.close()
        return True
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False

if __name__ == "__main__":
    # إذا تم تشغيل الملف مباشرة، قم بتهيئة قاعدة البيانات
    import sys
    
    if test_connection():
        if len(sys.argv) > 1 and sys.argv[1] == '--with-sample':
            init_database_with_sample_data()
        else:
            init_database()
    else:
        print("⚠️ لا يمكن الاتصال بقاعدة البيانات. تأكد من:")
        print("   1. خادم PostgreSQL يعمل")
        print("   2. بيانات الاتصال صحيحة")
        print("   3. قاعدة البيانات 'chat_app' موجودة")