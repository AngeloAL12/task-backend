import json
from datetime import datetime
from typing import List, Optional
from google import genai
from google.genai import types
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_exception_type
from pydantic import BaseModel

from app.core.config import settings
from app.schemas.task import TaskCreate  # <--- IMPORTANTE: Esto arregla el error de esquema

client = genai.Client(api_key=settings.GEMINI_API_KEY)

class AIResponse(BaseModel):
    action: str  # "create", "complete", "delete", "chat"
    target_id: Optional[int] = None
    title: Optional[str] = None
    deadline: Optional[str] = None
    priority: Optional[str] = None
    reply_text: Optional[str] = None

@retry(stop=stop_after_attempt(3), wait=wait_fixed(2), retry=retry_if_exception_type(Exception))
def generate_content_with_retry(prompt: str):
    return client.models.generate_content(
        model='gemini-2.5-flash',
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type='application/json',
            temperature=0.1
        )
    )

def analyze_intent(text: str, active_tasks: List[str]) -> AIResponse:
    today_iso = datetime.now().isoformat()
    tasks_context = "\n".join(active_tasks) if active_tasks else "No hay tareas pendientes."

    prompt = f"""
    Eres un gestor de tareas inteligente (GTD). Hoy es {today_iso}.

    TUS TAREAS ACTIVAS (ID: Título):
    {tasks_context}

    INPUT DEL USUARIO: "{text}"

    Instrucciones:
    1. Decide la ACCIÓN basándote en el input y las tareas activas:
       - "complete": Si el usuario dice que terminó algo ("ya hice X", "listo X"). DEBES devolver el 'target_id' correcto.
       - "delete": Si quiere borrar/cancelar ("borra X", "quita X"). DEBES devolver el 'target_id'.
       - "create": Si es una nueva tarea ("hacer X", "recordar Y"). Genera 'title' (max 5 palabras), 'deadline' y 'priority'.
       - "chat": Si es saludo o pregunta general ("hola", "gracias"). Genera 'reply_text'.

    2. REGLAS DE CREACIÓN:
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

    try:
        response = generate_content_with_retry(prompt)
        clean = response.text.replace("```json", "").replace("```", "").strip()
        data = json.loads(clean)

        # Corrección de seguridad para fechas
        if data.get("action") == "create" and not data.get("deadline"):
            data["deadline"] = datetime.now().replace(hour=23, minute=59).isoformat()

        return AIResponse(**data)
    except Exception as e:
        print(f"🔴 AI Error: {e}")
        # Fallback seguro
        return AIResponse(action="create", title=text[:20], priority="media")


# --- 2. ADAPTADOR DE COMPATIBILIDAD (Para que no falle tasks.py) ---
def parse_task_with_ai(text: str) -> TaskCreate:
    """
    Esta función engaña al router 'tasks.py' usando el nuevo cerebro
    pero devolviendo el formato antiguo que espera.
    """
    # Usamos la IA sin contexto de tareas (lista vacía)
    ai_response = analyze_intent(text, active_tasks=[])

    # Convertimos la fecha de string a datetime
    deadline_dt = datetime.now()
    if ai_response.deadline:
        try:
            deadline_dt = datetime.fromisoformat(ai_response.deadline)
        except ValueError:
            pass

    # Devolvemos el objeto TaskCreate que el router necesita
    return TaskCreate(
        title=ai_response.title or text[:50],
        subject="API",
        deadline=deadline_dt,
        priority=ai_response.priority or "media"
    )