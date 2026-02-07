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


class AIResponse(BaseModel):
    action: str  # "create", "complete", "delete", "chat"
    target_id: Optional[int] = None
    title: Optional[str] = None
    deadline: Optional[str] = None
    priority: Optional[str] = None
    reply_text: Optional[str] = None


@retry(stop=stop_after_attempt(3), wait=wait_fixed(2), retry=retry_if_exception_type(Exception))
def generate_content_with_retry(prompt_parts: list):
    return client.models.generate_content(
        model='gemini-2.5-flash',
        contents=[types.Content(parts=prompt_parts)],  # Enviamos una lista de partes (Texto + Audio)
        config=types.GenerateContentConfig(
            response_mime_type='application/json',
            temperature=0.1
        )
    )


def _build_prompt_text(active_tasks: List[str]) -> str:
    today_iso = datetime.now().isoformat()
    tasks_context = "\n".join(active_tasks) if active_tasks else "No hay tareas pendientes."

    return f"""
    Eres un gestor de tareas inteligente (GTD). Hoy es {today_iso}.

    TUS TAREAS ACTIVAS (ID: Título):
    {tasks_context}

    Instrucciones:
    1. Escucha/Lee el input del usuario.
    2. Decide la ACCIÓN:
       - "complete": Si dice que terminó algo. Devuelve 'target_id'.
       - "delete": Si quiere borrar. Devuelve 'target_id'.
       - "create": Si es nueva tarea. Genera 'title' (max 5 palabras), 'deadline' y 'priority'.
       - "chat": Si es saludo. Genera 'reply_text'.

    3. REGLAS DE CREACIÓN:
       - Si no hay fecha, deadline = HOY 23:59.
       - Título ultra corto.

    Responde SOLO JSON:
    {{
        "action": "create/complete/delete/chat",
        "target_id": 123,
        "title": "...",
        "deadline": "YYYY-MM-DDTHH:MM:SS",
        "priority": "alta/media/baja",
        "reply_text": "..."
    }}
    """


def analyze_intent(text: str, active_tasks: List[str]) -> AIResponse:
    prompt_text = _build_prompt_text(active_tasks)
    full_prompt = f"{prompt_text}\n\nINPUT DEL USUARIO (TEXTO): \"{text}\""

    # Enviamos solo texto
    return _execute_ai([types.Part.from_text(text=full_prompt)])


def analyze_audio_intent(audio_bytes: bytes, active_tasks: List[str]) -> AIResponse:
    prompt_text = _build_prompt_text(active_tasks)
    full_prompt = f"{prompt_text}\n\nINPUT DEL USUARIO (AUDIO): (Analiza el audio adjunto)"

    # Enviamos Texto + Blob de Audio
    parts = [
        types.Part.from_text(text=full_prompt),
        types.Part.from_bytes(data=audio_bytes, mime_type="audio/ogg")  # Telegram usa OGG
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
        return AIResponse(action="chat", reply_text="Lo siento, no entendí eso.")


# Adaptador Legacy
def parse_task_with_ai(text: str) -> TaskCreate:
    ai_response = analyze_intent(text, active_tasks=[])
    deadline_dt = datetime.now()
    if ai_response.deadline:
        try:
            deadline_dt = datetime.fromisoformat(ai_response.deadline)
        except ValueError:
            pass
    return TaskCreate(
        title=ai_response.title or text[:50],
        subject="API",
        deadline=deadline_dt,
        priority=ai_response.priority or "media"
    )