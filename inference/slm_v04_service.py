"""Service HTTP d'inférence pour les modèles compacts LIDAL SLM V0.4.

Lancer sur la station GPU :
    uvicorn inference.slm_v04_service:app --host 0.0.0.0 --port 8010
"""

from __future__ import annotations

import hmac
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Any

from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, Field

app = FastAPI(title="LIDAL SLM V0.4", version="0.4.0")


class AnalysisRequest(BaseModel):
    text: str = Field(min_length=1, max_length=10_000)
    context: dict[str, Any] = Field(default_factory=dict)


class AnalysisResponse(BaseModel):
    raw_model_output: str
    model_version: str
    inference_ms: int
    created_at: str


class _Runtime:
    def __init__(self) -> None:
        self.model = None
        self.tokenizer = None
        self.lock = Lock()
        self.model_path = Path(
            os.getenv(
                "LIDAL_SLM_MODEL_PATH",
                str(Path.home() / "lidal-slm-compact" / "runs" / "answer_only_s1"),
            )
        )

    @property
    def model_version(self) -> str:
        return os.getenv("LIDAL_SLM_MODEL_VERSION", self.model_path.name)

    def load(self) -> None:
        if self.model is not None and self.tokenizer is not None:
            return
        with self.lock:
            if self.model is not None and self.tokenizer is not None:
                return
            import torch
            from transformers import AutoModelForCausalLM, AutoTokenizer

            tokenizer = AutoTokenizer.from_pretrained(self.model_path)
            if tokenizer.pad_token_id is None:
                tokenizer.pad_token_id = tokenizer.eos_token_id
            dtype: object = torch.bfloat16 if torch.cuda.is_available() else "auto"
            model = AutoModelForCausalLM.from_pretrained(
                self.model_path,
                device_map="auto",
                dtype=dtype,
            ).eval()
            self.tokenizer = tokenizer
            self.model = model

    def generate(self, prompt: str) -> str:
        self.load()
        import torch

        assert self.model is not None
        assert self.tokenizer is not None
        inputs = self.tokenizer(
            prompt,
            return_tensors="pt",
            truncation=True,
            max_length=int(os.getenv("LIDAL_SLM_INPUT_TOKENS", "1024")),
        ).to(self.model.device)
        with self.lock, torch.inference_mode():
            output = self.model.generate(
                **inputs,
                max_new_tokens=int(os.getenv("LIDAL_SLM_MAX_NEW_TOKENS", "768")),
                do_sample=False,
                eos_token_id=self.tokenizer.eos_token_id,
                pad_token_id=self.tokenizer.eos_token_id,
            )
        generated = output[0, inputs["input_ids"].shape[1] :]
        return self.tokenizer.decode(generated, skip_special_tokens=True)


runtime = _Runtime()


def _authorize(provided_key: str | None) -> None:
    expected_key = os.getenv("LIDAL_SLM_API_KEY", "").strip()
    if expected_key and not hmac.compare_digest(provided_key or "", expected_key):
        raise HTTPException(status_code=401, detail="invalid service key")


def _build_prompt(text: str, context: dict[str, Any]) -> str:
    target = context.get("monitoring_target") or {}
    header = f"scope={target.get('scope')}"
    if target.get("entity_name"):
        header += f" entite={target['entity_name']}"
    if context.get("topic"):
        header += f" secteur={context['topic']}"
    return (
        f"### Contexte ###\n{header}\n\n"
        f"### Commentaire ###\n{text}\n\n"
        "### Reponse compacte ###\n"
    )


@app.get("/health")
def health() -> dict[str, object]:
    return {
        "status": "ready" if runtime.model_path.exists() else "model_missing",
        "model_loaded": runtime.model is not None,
        "model_version": runtime.model_version,
    }


@app.post("/v1/analyze", response_model=AnalysisResponse)
def analyze(
    request: AnalysisRequest,
    x_lidal_slm_key: str | None = Header(default=None),
) -> AnalysisResponse:
    _authorize(x_lidal_slm_key)
    started = time.perf_counter()
    raw_output = runtime.generate(_build_prompt(request.text.strip(), request.context))
    return AnalysisResponse(
        raw_model_output=raw_output,
        model_version=runtime.model_version,
        inference_ms=round((time.perf_counter() - started) * 1000),
        created_at=datetime.now(timezone.utc).isoformat(),
    )
