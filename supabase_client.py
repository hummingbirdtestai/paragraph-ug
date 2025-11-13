# supabase_client.py
from supabase import create_client
import os
from dotenv import load_dotenv
from datetime import datetime

# ───────────────────────────────────────────────
# 🔹 Load environment variables
# ───────────────────────────────────────────────
load_dotenv()

# ───────────────────────────────────────────────
# 🔹 Initialize Supabase client
# ───────────────────────────────────────────────
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("❌ Missing SUPABASE_URL or SUPABASE_KEY in environment variables.")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# ───────────────────────────────────────────────
# 🔹 RPC Helper — Universal Caller
# ───────────────────────────────────────────────
def call_rpc(function_name: str, params: dict = None):
    """
    Generic helper to call Supabase RPC and handle responses safely (for supabase-py v2+).

    Example:
        call_rpc("start_orchestra", {"p_student_id": "<uuid>", "p_chapter_id": "<uuid>"})

    Notes:
    - Works seamlessly for NEET-UG schema (chapter-based)
    - Returns a dict if successful, None if empty or failed
    - Handles both `RETURNS jsonb` and `RETURNS TABLE(...)` SQL functions
    """
    try:
        if not function_name:
            print("⚠️ Missing function name in call_rpc()")
            return None

        # 🧩 Default empty params for optional RPCs
        params = params or {}

        # 🧾 Debug logging for traceability (toggle off in production)
        print(f"🧠 Calling RPC → {function_name} | Params: {params}")

        res = supabase.rpc(function_name, params).execute()
        data = getattr(res, "data", None)

        # 🔍 Validate and normalize return data
        if not data:
            print(f"⚠️ RPC {function_name} returned no data.")
            return None

        # Handle RPC returning a LIST of objects
        if isinstance(data, list):
            if len(data) == 0:
                print(f"⚠️ RPC {function_name} returned an empty list.")
                return None
            # Return the first element only if it’s a single-object response
            if len(data) == 1:
                return data[0]
            # Otherwise, return full list (for table-like responses)
            return data

        # Handle RPC returning a DICT
        elif isinstance(data, dict):
            return data

        # Handle unexpected return types
        else:
            print(f"⚠️ Unexpected RPC result type {type(data)} for {function_name}")
            return None

    except Exception as e:
        print(f"❌ RPC Exception in {function_name}: {e}")
        return None


# ───────────────────────────────────────────────
# 🔹 Utility Helper — Direct Table Access (Optional)
# ───────────────────────────────────────────────
def fetch_latest_pointer(student_id: str, chapter_id: str):
    """
    Fetches the most recent pointer for a student and chapter.
    Returns (pointer_id, conversation_log) or None.
    """
    try:
        res = (
            supabase.table("student_phase_pointer")
            .select("pointer_id, conversation_log, updated_at")
            .eq("student_id", student_id)
            .eq("chapter_id", chapter_id)
            .order("updated_at", desc=True)
            .limit(1)
            .execute()
        )
        if res.data and len(res.data) > 0:
            return res.data[0]
        else:
            print(f"⚠️ No pointer found for student {student_id}, chapter {chapter_id}")
            return None
    except Exception as e:
        print(f"⚠️ Error fetching latest pointer: {e}")
        return None


# ───────────────────────────────────────────────
# 🔹 Utility Helper — Bookmark Log
# ───────────────────────────────────────────────
def log_bookmark_action(student_id: str, chapter_id: str, pointer_id: int, is_bookmarked: bool):
    """
    Logs bookmark toggle action into 'student_phase_pointer' with updated timestamp.
    """
    try:
        supabase.table("student_phase_pointer") \
            .update({
                "is_bookmarked": is_bookmarked,
                "bookmark_updated_time": datetime.utcnow().isoformat() + "Z",
                "updated_at": datetime.utcnow().isoformat() + "Z",
            }) \
            .eq("student_id", student_id) \
            .eq("chapter_id", chapter_id) \
            .eq("pointer_id", pointer_id) \
            .execute()
        print(f"🔖 Bookmark updated → Student: {student_id}, Chapter: {chapter_id}, Pointer: {pointer_id}, State: {is_bookmarked}")
    except Exception as e:
        print(f"⚠️ Failed to update bookmark: {e}")


# ───────────────────────────────────────────────
# 🔹 Utility Helper — MCQ Submission Upsert
# ───────────────────────────────────────────────
def save_mcq_submission(student_id: str, chapter_id: str, react_order: int,
                         student_answer: str, correct_answer: str,
                         is_correct: bool, is_completed: bool = True):
    """
    Upserts an MCQ submission entry into 'student_mcq_submissions'.
    """
    try:
        payload = {
            "student_id": student_id,
            "chapter_id": chapter_id,
            "react_order": react_order,
            "student_answer": student_answer,
            "correct_answer": correct_answer,
            "is_correct": is_correct,
            "is_completed": is_completed,
            "submitted_at": datetime.utcnow().isoformat() + "Z",
        }

        supabase.table("student_mcq_submissions") \
            .upsert(payload, on_conflict=["student_id", "chapter_id", "react_order"]) \
            .execute()

        print(f"✅ MCQ saved → student {student_id}, chapter {chapter_id}, react_order {react_order}")
        return True

    except Exception as e:
        print(f"❌ Failed to save MCQ submission: {e}")
        return False
