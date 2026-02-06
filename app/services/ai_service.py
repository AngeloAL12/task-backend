import json
import re
from datetime import datetime
from google import genai
from google.genai import types
from app.core.config import settings
from app.schemas.task import TaskCreate

# Inicializamos cliente
client = genai.Client(api_key=settings.GEMINI_API_KEY)


def parse_task_with_ai(text: str) -> TaskCreate:
    today_iso = datetime.now().isoformat()

    prompt = f"""
    Eres un parser de tareas. Hoy es {today_iso}.
    Analiza: "{text}"

    Responde SOLO con este JSON:
    {{
        "title": "string",
        "subject": "string (o 'General')",
        "deadline": "YYYY-MM-DDTHH:MM:SS" (o null),
        "priority": "alta/media/baja"
    }}
    """

    try:
        # Usamos el nombre completo del modelo para evitar 404s
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type='application/json',
                temperature=0.1  # Bajamos temperatura para que sea más "robot"
            )
        )

        clean_text = response.text
        if "```" in clean_text:
            clean_text = clean_text.replace("```json", "").replace("```", "")

        clean_text = clean_text.strip()

        data = json.loads(clean_text)
        return TaskCreate(**data)

    except Exception as e:
        # IMPORTANTE: Esto imprimirá el error real en tu terminal para que sepamos qué pasó
        print(f"\n🔴 ERROR REAL DE IA: {type(e).__name__}: {e}\n")
        return TaskCreate(title=text, priority="media")