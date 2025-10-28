import json
import time
from pathlib import Path
from datetime import datetime

NOTIFICATIONS_FILE = "pending_notifications.json"

def create_notification(request_id, caller_id, answer):
    """Create a notification for the agent to process"""
    notifications = load_notifications()
    
    notification = {
        "id": f"NOTIF_{int(time.time())}_{len(notifications)}",
        "request_id": request_id,
        "caller_id": caller_id,
        "answer": answer,
        "created_at": datetime.now().isoformat(),
        "processed": False,
        "processed_at": None
    }
    
    notifications.append(notification)
    save_notifications(notifications)
    
    print(f"📢 NOTIFICATION CREATED: {notification['id']}")
    print(f"   For caller: {caller_id}")
    print(f"   Request: {request_id}")
    
    return notification

def load_notifications():
    """Load notifications from file"""
    try:
        if Path(NOTIFICATIONS_FILE).exists():
            file_path = Path(NOTIFICATIONS_FILE)
            # Check if file is empty
            if file_path.stat().st_size == 0:
                print("ℹ️ Notifications file is empty, initializing with empty list")
                return []
            
            with open(NOTIFICATIONS_FILE, 'r') as f:
                content = f.read().strip()
                # Double-check content isn't empty string
                if not content:
                    return []
                return json.loads(content)
    except json.JSONDecodeError as e:
        print(f"⚠️ JSON decode error in notifications: {e}")
        print("ℹ️ Initializing with empty notifications list")
        return []
    except Exception as e:
        print(f"⚠️ Error loading notifications: {e}")
    return []

def save_notifications(notifications):
    """Save notifications to file"""
    try:
        with open(NOTIFICATIONS_FILE, 'w') as f:
            json.dump(notifications, f, indent=2)
        return True
    except Exception as e:
        print(f"⚠️ Error saving notifications: {e}")
        return False

def get_pending_notifications():
    """Get all unprocessed notifications"""
    notifications = load_notifications()
    return [n for n in notifications if not n['processed']]

def mark_notification_processed(notification_id):
    """Mark a notification as processed"""
    notifications = load_notifications()
    
    for n in notifications:
        if n['id'] == notification_id:
            n['processed'] = True
            n['processed_at'] = datetime.now().isoformat()
    
    save_notifications(notifications)
    print(f"✅ Notification {notification_id} marked as processed")
    return True

def clear_old_notifications(days=7):
    """Clean up old processed notifications"""
    from datetime import timedelta
    
    notifications = load_notifications()
    cutoff = datetime.now() - timedelta(days=days)
    
    filtered = [
        n for n in notifications
        if not n['processed'] or 
        datetime.fromisoformat(n['processed_at']) > cutoff
    ]
    
    removed = len(notifications) - len(filtered)
    if removed > 0:
        save_notifications(filtered)
        print(f"🗑️ Cleaned up {removed} old notifications")
    
    return removed