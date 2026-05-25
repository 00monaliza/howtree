from __future__ import annotations

import json
import os
from typing import Optional

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")

SYSTEM_PROMPT = """Ты — AI-ассистент платформы HowTree, системы автоматического обнаружения и подсчёта деревьев на спутниковых снимках.

Твои задачи:
1. Объяснять результаты анализа — количество деревьев, площадь крон, уверенность модели
2. Отвечать на вопросы об экологии, городском озеленении, дистанционном зондировании
3. Общие вопросы о платформе и её возможностях

Технический контекст платформы:
- Нейросеть DeepForest (Faster R-CNN + ResNet-50), обучена на датасете NEON
- Спутниковые снимки: ESRI World Imagery (основной), Yandex, Mapbox
- Confidence > 0.7 — надёжная детекция; 0.4–0.7 — умеренная; < 0.4 — отфильтровывается
- Zoom=17 (~1.2 м/пиксель), оптимально для крон от 2 м диаметром
- Максимальная зона анализа: 50 км²

Отвечай кратко, по делу, на языке пользователя."""


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    messages: list[ChatMessage]
    analysis_context: Optional[dict] = None


@router.post("/chat")
async def chat(request: ChatRequest):
    if not ANTHROPIC_API_KEY:
        raise HTTPException(status_code=500, detail="ANTHROPIC_API_KEY not configured")

    system = SYSTEM_PROMPT
    if request.analysis_context:
        ctx = request.analysis_context
        system += "\n\nТекущий результат анализа пользователя:\n"
        if ctx.get("tree_count") is not None:
            system += f"- Обнаружено деревьев: {ctx['tree_count']}\n"
        if ctx.get("canopy_area_m2") is not None:
            system += f"- Площадь крон: {ctx['canopy_area_m2']:.0f} м²\n"
        if ctx.get("avg_confidence") is not None:
            system += f"- Средняя уверенность модели: {ctx['avg_confidence']:.2%}\n"
        if ctx.get("bbox_area_km2") is not None:
            system += f"- Площадь зоны анализа: {ctx['bbox_area_km2']:.3f} км²\n"

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": ANTHROPIC_API_KEY,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": "claude-haiku-4-5",
                "max_tokens": 1024,
                "system": system,
                "messages": [m.model_dump() for m in request.messages],
            },
        )

    if response.status_code != 200:
        raise HTTPException(
            status_code=response.status_code,
            detail=f"Anthropic API error: {response.text}",
        )

    data = response.json()
    text = data["content"][0]["text"]

    return {"content": text, "action": None}