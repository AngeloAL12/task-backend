import json
from datetime import datetime
from typing import List, Optional
from google import genai
from google.genai import types
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_exception_type
from pydantic import BaseModel

from app.core.config import settings
from app.schemas.task import TaskCreate

client = genai.Client(api_key=settings.GEMINI_API_KEY)


# --- 1. MODELO DE RESPUESTA ACTUALIZADO ---
class AIResponse(BaseModel):
    action: str
    target_id: Optional[int] = None
    title: Optional[str] = None
    subject: Optional[str] = None
    deadline: Optional[str] = None
    priority: Optional[str] = None
    reply_text: Optional[str] = None


@retry(stop=stop_after_attempt(3), wait=wait_fixed(2), retry=retry_if_exception_type(Exception))
def generate_content_with_retry(prompt_parts: list):
    return client.models.generate_content(
        model='gemini-2.5-flash',
        contents=[types.Content(parts=prompt_parts)],
        config=types.GenerateContentConfig(
            response_mime_type='application/json',
            temperature=0.1
        )
    )

def _build_prompt_text(active_tasks: List[str], user_schedule: str) -> str:
    now = datetime.now()
    today_iso = now.strftime("%Y-%m-%d %H:%M:%S")
    day_name = now.strftime("%A")  # Ej: Monday, Tuesday...

    tasks_context = "\n".join(active_tasks) if active_tasks else "No hay tareas pendientes."

    schedule_context = user_schedule if user_schedule else "El usuario no ha definido su horario."

    return f"""
    Eres un gestor de tareas inteligente (GTD). 
    FECHA Y HORA ACTUAL: {today_iso} (Día: {day_name})

    HORARIO DE CLASES DEL USUARIO:
    {schedule_context}

    TAREAS ACTIVAS (ID: Título):
    {tasks_context}

    Instrucciones:
    1. Escucha/Lee el input del usuario.
    2. Decide la ACCIÓN:
       - "complete": Si dice que terminó algo. Devuelve 'target_id'.
       - "delete": Si quiere borrar. Devuelve 'target_id'.
       - "create": Si es nueva tarea.
       - "chat": Si es saludo.

    3. REGLAS PARA "CREATE":
       - Subject (Materia): 
         A) IMPORTANTE: Compara la HORA ACTUAL con el HORARIO DE CLASES. Si coincide, ASIGNA ESA MATERIA.
         B) Si no coincide, intenta deducirla por el contexto del texto.
         C) Si no sabes, pon "General".
       - Title: Resumen corto (max 5 palabras).
       - Deadline: Si no se dice, HOY 23:59.
       - Priority: Alta/Media/Baja.

    Responde SOLO JSON:
    {{
        "action": "create/complete/delete/chat",
        "target_id": 123,
        "title": "...",
        "subject": "Materia Detectada",
        "deadline": "YYYY-MM-DDTHH:MM:SS",
        "priority": "alta/media/baja",
        "reply_text": "..."
    }}
    """

def analyze_intent(text: str, active_tasks: List[str], user_schedule: str = "") -> AIResponse:
    prompt_text = _build_prompt_text(active_tasks, user_schedule)
    full_prompt = f"{prompt_text}\n\nINPUT DEL USUARIO (TEXTO): \"{text}\""

    return _execute_ai([types.Part.from_text(text=full_prompt)])


def analyze_audio_intent(audio_bytes: bytes, active_tasks: List[str], user_schedule: str = "") -> AIResponse:
    prompt_text = _build_prompt_text(active_tasks, user_schedule)
    full_prompt = f"{prompt_text}\n\nINPUT DEL USUARIO (AUDIO): (Analiza el audio adjunto)"

    parts = [
        types.Part.from_text(text=full_prompt),
        types.Part.from_bytes(data=audio_bytes, mime_type="audio/ogg")
    ]
    return _execute_ai(parts)


def _execute_ai(parts: list) -> AIResponse:
    try:
        response = generate_content_with_retry(parts)
        clean = response.text.replace("```json", "").replace("```", "").strip()
        data = json.loads(clean)

        if data.get("action") == "create" and not data.get("deadline"):
            data["deadline"] = datetime.now().replace(hour=23, minute=59).isoformat()

        return AIResponse(**data)
    except Exception as e:
        print(f"🔴 AI Error: {e}")
        return AIResponse(action="chat", reply_text="Lo siento, hubo un error procesando eso.")

def parse_task_with_ai(text: str) -> TaskCreate:
    ai_response = analyze_intent(text, active_tasks=[], user_schedule="")

    deadline_dt = datetime.now()
    if ai_response.deadline:
        try:
            deadline_dt = datetime.fromisoformat(ai_response.deadline)
        except ValueError:
            pass

    return TaskCreate(
        title=ai_response.title or text[:50],
        subject=ai_response.subject or "API",  # Usamos lo que diga la IA o default
        deadline=deadline_dt,
        priority=ai_response.priority or "media"
    )