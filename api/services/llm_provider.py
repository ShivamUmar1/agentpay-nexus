import asyncio
from enum import Enum
import json
import logging
import random
import re
import time
from typing import Dict, Any, Optional, List
import httpx
from api.config import settings

logger = logging.getLogger(__name__)

AI_CUMULATIVE_DEADLINE: float = 18.0


class ProviderHealthState(str, Enum):
    NOT_CONFIGURED = "not_configured"
    NOT_CHECKED = "not_checked"
    CONFIGURED = "configured"
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    QUOTA_EXHAUSTED = "quota_exhausted"


class AIErrorKind(str, Enum):
    QUOTA_EXHAUSTED = "QUOTA_EXHAUSTED"
    RATE_LIMIT_TRANSIENT = "RATE_LIMIT_TRANSIENT"
    AUTH_ERROR = "AUTH_ERROR"
    MODEL_NOT_FOUND = "MODEL_NOT_FOUND"
    SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"
    TIMEOUT = "TIMEOUT"
    BAD_REQUEST = "BAD_REQUEST"
    MALFORMED_RESPONSE = "MALFORMED_RESPONSE"
    PROVIDER_UNAVAILABLE = "PROVIDER_UNAVAILABLE"


class AIError(Exception):
    """Structured AI provider error with classification, user-safe messaging, and retry metadata."""

    def __init__(
        self,
        kind: AIErrorKind,
        message: str,
        user_message: str,
        status_code: Optional[int] = None,
        retry_after: Optional[float] = None,
        model: Optional[str] = None
    ):
        super().__init__(message)
        self.kind = kind
        self.message = message
        self.user_message = user_message
        self.status_code = status_code
        self.retry_after = retry_after
        self.model = model

    def to_dict(self) -> Dict[str, Any]:
        return {
            "error_kind": self.kind.value,
            "message": self.message,
            "user_message": self.user_message,
            "status_code": self.status_code,
            "retry_after": self.retry_after,
            "model": self.model
        }


def parse_retry_delay(text: str, headers: Optional[Dict[str, str]] = None) -> Optional[float]:
    """Extracts retry delay in seconds from Gemini response body or HTTP headers."""
    if headers:
        for k, v in headers.items():
            if k.lower() == "retry-after":
                try:
                    return float(v)
                except (ValueError, TypeError):
                    pass

    match = re.search(r'"retryDelay":\s*"(\d+(?:\.\d+)?)s"', text)
    if match:
        try:
            return float(match.group(1))
        except (ValueError, TypeError):
            pass
    return None


def classify_gemini_error(
    status_code: int,
    response_text: str,
    headers: Optional[Dict[str, str]] = None,
    model: Optional[str] = None
) -> AIError:
    """Classifies raw Gemini HTTP errors into structured, user-safe AIError instances."""
    retry_after = parse_retry_delay(response_text, headers)
    lower_text = response_text.lower()

    if status_code in (401, 403):
        return AIError(
            kind=AIErrorKind.AUTH_ERROR,
            message=f"Gemini authentication failed (HTTP {status_code}): {response_text[:180]}",
            user_message="AI provider authentication failed. Please verify API key configuration and permissions.",
            status_code=status_code,
            model=model
        )

    if status_code == 404:
        return AIError(
            kind=AIErrorKind.MODEL_NOT_FOUND,
            message=f"Gemini model not found (HTTP 404): {response_text[:180]}",
            user_message=f"Configured AI model '{model}' was not found or is no longer supported by the provider.",
            status_code=status_code,
            model=model
        )

    if status_code == 503:
        return AIError(
            kind=AIErrorKind.SERVICE_UNAVAILABLE,
            message=f"Gemini service unavailable (HTTP 503): {response_text[:180]}",
            user_message="AI provider is temporarily overloaded or unavailable. Please retry shortly.",
            status_code=status_code,
            retry_after=retry_after or 2.0,
            model=model
        )

    if status_code == 429:
        has_transient_delay = bool(retry_after is not None)
        has_daily_or_billing_keywords = any(kw in lower_text for kw in [
            "per day", "daily limit", "daily quota", "billing", "free tier", "spend limit", "project quota", "exceeded your current quota"
        ])
        has_rpm_keywords = any(kw in lower_text for kw in [
            "per minute", "requests per minute", "tokens per minute", "rpm", "tpm", "rate limit"
        ])

        if has_daily_or_billing_keywords:
            is_transient = False
        elif has_transient_delay or has_rpm_keywords:
            is_transient = True
        else:
            is_transient = False

        if is_transient:
            return AIError(
                kind=AIErrorKind.RATE_LIMIT_TRANSIENT,
                message=f"Gemini transient rate limit reached (HTTP 429): {response_text[:180]}",
                user_message="AI service request rate limit reached. Please wait a moment and retry.",
                status_code=status_code,
                retry_after=retry_after,
                model=model
            )
        else:
            return AIError(
                kind=AIErrorKind.QUOTA_EXHAUSTED,
                message=f"Gemini quota exhausted (HTTP 429): {response_text[:180]}",
                user_message="AI research is temporarily unavailable because the configured AI provider has reached a usage limit. Your task has been preserved. Please retry when AI service availability is restored. No payment has been captured.",
                status_code=status_code,
                retry_after=retry_after,
                model=model
            )

    return AIError(
        kind=AIErrorKind.SERVICE_UNAVAILABLE,
        message=f"Gemini HTTP error {status_code}: {response_text[:180]}",
        user_message="AI provider encountered an unexpected error. Please retry.",
        status_code=status_code,
        model=model
    )


def extract_topic_title(prompt: str) -> str:
    """Extracts clean topic/title from prompt text."""
    lines = prompt.strip().split("\n")
    for line in lines:
        cleaned = line.strip().lstrip("#").strip()
        lower = cleaned.lower()
        if lower.startswith("title:"):
            return cleaned.split(":", 1)[1].strip()
        if lower.startswith("task title:"):
            return cleaned.split(":", 1)[1].strip()
        if lower.startswith("analyze the research data for:"):
            return cleaned.split(":", 1)[1].strip()
        if lower.startswith("generate an executive report on:"):
            return cleaned.split(":", 1)[1].strip()
        if lower.startswith("audit the final deliverable for task:"):
            return cleaned.split(":", 1)[1].strip()
        if lower.startswith("conduct rigorous market research on:"):
            continue
    first = lines[0].strip().lstrip("#").strip()
    return first[:60] if first else "Market Intelligence Objective"


def extract_json(text: str) -> Dict[str, Any]:
    """Extracts JSON object from LLM response text, handling markdown fences and formatting."""
    text = text.strip()
    match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
    if match:
        text = match.group(1).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        brace_match = re.search(r"(\{[\s\S]*\})", text)
        if brace_match:
            try:
                return json.loads(brace_match.group(1))
            except Exception:
                pass
        raise ValueError(f"Could not parse valid JSON from text: {text[:200]}")


class LLMProvider:
    """Central provider abstraction supporting Gemini, OpenAI, and truthful status semantics."""

    def __init__(self):
        self._health_state: ProviderHealthState = ProviderHealthState.NOT_CHECKED
        self._last_health_check_time: Optional[float] = None
        self._last_error_message: Optional[str] = None

    @property
    def gemini_key(self) -> Optional[str]:
        return settings.GEMINI_API_KEY

    @property
    def openai_key(self) -> Optional[str]:
        return settings.OPENAI_API_KEY

    @property
    def gemini_model(self) -> str:
        return settings.GEMINI_MODEL

    @property
    def openai_model(self) -> str:
        return settings.OPENAI_MODEL

    @property
    def provider_name(self) -> str:
        if self.gemini_key:
            return "gemini"
        if self.openai_key:
            return "openai"
        return "offline_scaffold"

    def get_status(self) -> Dict[str, Any]:
        """Instantaneous diagnostics endpoint reporting truthful configuration without external network overhead."""
        has_creds = bool(self.gemini_key or self.openai_key)

        if not has_creds:
            status_val = ProviderHealthState.NOT_CONFIGURED.value
        elif self._health_state == ProviderHealthState.NOT_CHECKED:
            status_val = ProviderHealthState.CONFIGURED.value  # Truthful: Credentials present, unverified
        else:
            status_val = self._health_state.value

        return {
            "provider": self.provider_name,
            "configured_model": self.gemini_model if self.gemini_key else (self.openai_model if self.openai_key else "none"),
            "fallback_model": settings.GEMINI_FALLBACK_MODEL if self.gemini_key else None,
            "has_credentials": has_creds,
            "status": status_val,
            "health_state": self._health_state.value,
            "last_checked_timestamp": self._last_health_check_time,
            "last_error": self._last_error_message,
            "timeout_seconds": settings.AI_REQUEST_TIMEOUT,
            "max_budget_seconds": settings.AI_REQUEST_TIMEOUT * 2
        }

    async def generate_text(self, prompt: str, system_instruction: Optional[str] = None) -> str:
        """Generates text from configured provider or raises AIError if live provider fails."""
        if self.gemini_key:
            return await self._call_gemini(prompt, system_instruction, as_json=False)
        elif self.openai_key:
            try:
                return await self._call_openai(prompt, system_instruction)
            except Exception as e:
                self._health_state = ProviderHealthState.DEGRADED
                raise AIError(
                    kind=AIErrorKind.SERVICE_UNAVAILABLE,
                    message=f"OpenAI error: {str(e)[:180]}",
                    user_message="OpenAI service is temporarily unavailable."
                )
        return self._generate_fallback_text(prompt, system_instruction)

    async def generate_json(self, prompt: str, system_instruction: Optional[str] = None) -> Dict[str, Any]:
        """Generates structured JSON from configured provider or raises AIError if live provider fails."""
        full_system = (system_instruction or "") + "\n\nCRITICAL: Respond ONLY with a valid JSON object. Do not include introductory or concluding conversational prose."
        
        if self.gemini_key:
            text = await self._call_gemini(prompt, full_system, as_json=True)
            return extract_json(text)
        elif self.openai_key:
            try:
                text = await self._call_openai(prompt, full_system)
                return extract_json(text)
            except Exception as e:
                self._health_state = ProviderHealthState.DEGRADED
                raise AIError(
                    kind=AIErrorKind.SERVICE_UNAVAILABLE,
                    message=f"OpenAI error: {str(e)[:180]}",
                    user_message="OpenAI service is temporarily unavailable."
                )

        return self._generate_fallback_json(prompt, system_instruction)

    async def _call_gemini(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        as_json: bool = False
    ) -> str:
        key = self.gemini_key
        if not key:
            self._health_state = ProviderHealthState.NOT_CONFIGURED
            raise AIError(
                kind=AIErrorKind.PROVIDER_UNAVAILABLE,
                message="GEMINI_API_KEY is not configured.",
                user_message="AI service is not configured."
            )

        primary_model = self.gemini_model
        fallback_model = settings.GEMINI_FALLBACK_MODEL
        models_to_try = [primary_model]
        if fallback_model and fallback_model != primary_model:
            models_to_try.append(fallback_model)

        contents = [{"role": "user", "parts": [{"text": prompt}]}]
        payload: Dict[str, Any] = {
            "contents": contents,
            "generationConfig": {
                "temperature": 0.2,
                "maxOutputTokens": 4096
            }
        }
        if system_instruction:
            payload["system_instruction"] = {
                "parts": [{"text": system_instruction}]
            }
        if as_json:
            payload["generationConfig"]["responseMimeType"] = "application/json"

        last_error: Optional[AIError] = None
        timeout_val = settings.AI_REQUEST_TIMEOUT
        start_time = time.monotonic()

        async with httpx.AsyncClient() as client:
            for idx, model in enumerate(models_to_try):
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"
                elapsed = time.monotonic() - start_time
                remaining = max(0.0, AI_CUMULATIVE_DEADLINE - elapsed)
                if remaining <= 0.5:
                    if last_error:
                        raise last_error
                    raise AIError(
                        kind=AIErrorKind.TIMEOUT,
                        message=f"Gemini cumulative deadline of {AI_CUMULATIVE_DEADLINE}s reached before attempting {model}.",
                        user_message="AI provider request timed out. Please retry.",
                        model=model
                    )

                req_timeout = min(timeout_val, remaining)

                try:
                    response = await asyncio.wait_for(
                        client.post(url, json=payload, timeout=req_timeout),
                        timeout=req_timeout
                    )
                    if response.status_code == 200:
                        data = response.json()
                        candidates = data.get("candidates", [])
                        if candidates and "content" in candidates[0]:
                            parts = candidates[0]["content"].get("parts", [])
                            if parts and "text" in parts[0]:
                                self._health_state = ProviderHealthState.HEALTHY
                                self._last_health_check_time = time.time()
                                return parts[0]["text"]
                        raise AIError(
                            kind=AIErrorKind.MALFORMED_RESPONSE,
                            message=f"Gemini model {model} returned unexpected structure: {str(data)[:200]}",
                            user_message="AI provider returned an unparseable response structure.",
                            status_code=200,
                            model=model
                        )

                    # Classify error
                    err = classify_gemini_error(
                        status_code=response.status_code,
                        response_text=response.text,
                        headers=dict(response.headers),
                        model=model
                    )

                    # Update internal health state
                    self._last_health_check_time = time.time()
                    self._last_error_message = err.user_message

                    if err.kind == AIErrorKind.QUOTA_EXHAUSTED:
                        self._health_state = ProviderHealthState.QUOTA_EXHAUSTED
                        logger.warning(f"Gemini QUOTA_EXHAUSTED on model {model}. Halting without cascading.")
                        raise err

                    if err.kind == AIErrorKind.AUTH_ERROR:
                        self._health_state = ProviderHealthState.DEGRADED
                        logger.warning(f"Gemini AUTH_ERROR on model {model}. Halting.")
                        raise err

                    # Transient RPM rate limit: if retry_after <= 2.0s and on primary model, wait and retry once
                    if err.kind == AIErrorKind.RATE_LIMIT_TRANSIENT and err.retry_after and err.retry_after <= 2.0 and idx == 0:
                        elapsed_before_sleep = time.monotonic() - start_time
                        rem_before_sleep = max(0.0, AI_CUMULATIVE_DEADLINE - elapsed_before_sleep)
                        if rem_before_sleep > (err.retry_after + 0.5):
                            logger.info(f"Transient rate limit on {model}; waiting {err.retry_after}s before retry (remaining budget: {rem_before_sleep:.1f}s)...")
                            try:
                                await asyncio.wait_for(
                                    asyncio.sleep(err.retry_after),
                                    timeout=rem_before_sleep
                                )
                            except (asyncio.TimeoutError, TimeoutError):
                                logger.warning(f"Gemini cumulative deadline of {AI_CUMULATIVE_DEADLINE}s reached during RPM retry delay on {model}.")
                                err = AIError(
                                    kind=AIErrorKind.TIMEOUT,
                                    message=f"Gemini cumulative deadline of {AI_CUMULATIVE_DEADLINE}s reached during RPM retry delay on {model}.",
                                    user_message="AI provider request timed out. Please retry.",
                                    model=model
                                )
                                self._health_state = ProviderHealthState.DEGRADED
                                last_error = err
                                continue
                        else:
                            logger.warning(f"Insufficient remaining time ({rem_before_sleep:.2f}s) for RPM retry on {model} within {AI_CUMULATIVE_DEADLINE}s deadline.")

                        rem_after_sleep = max(0.0, AI_CUMULATIVE_DEADLINE - (time.monotonic() - start_time))
                        if rem_after_sleep > 0.5:
                            retry_timeout = min(timeout_val, rem_after_sleep)
                            try:
                                retry_resp = await asyncio.wait_for(
                                    client.post(url, json=payload, timeout=retry_timeout),
                                    timeout=retry_timeout
                                )
                                if retry_resp.status_code == 200:
                                    data = retry_resp.json()
                                    candidates = data.get("candidates", [])
                                    if candidates and "content" in candidates[0]:
                                        parts = candidates[0]["content"].get("parts", [])
                                        if parts and "text" in parts[0]:
                                            self._health_state = ProviderHealthState.HEALTHY
                                            return parts[0]["text"]
                                err = classify_gemini_error(
                                    status_code=retry_resp.status_code,
                                    response_text=retry_resp.text,
                                    headers=dict(retry_resp.headers),
                                    model=model
                                )
                            except (httpx.TimeoutException, asyncio.TimeoutError, TimeoutError):
                                err = AIError(
                                    kind=AIErrorKind.TIMEOUT,
                                    message=f"Gemini model {model} retry timed out within deadline.",
                                    user_message="AI provider request timed out. Please retry.",
                                    model=model
                                )
                        else:
                            logger.warning(f"Insufficient remaining time for RPM retry on {model} within {AI_CUMULATIVE_DEADLINE}s deadline.")

                    # Transient 503 Service Unavailable: exactly 1 bounded retry with jitter and cumulative deadline
                    elif err.kind == AIErrorKind.SERVICE_UNAVAILABLE and response.status_code == 503 and idx == 0:
                        delay = min(err.retry_after or 1.5, 2.5)
                        delay += random.uniform(0.1, 0.4)
                        elapsed_before_sleep = time.monotonic() - start_time
                        rem_before_sleep = max(0.0, AI_CUMULATIVE_DEADLINE - elapsed_before_sleep)

                        if rem_before_sleep > (delay + 0.5):
                            logger.info(f"Transient 503 on {model}; waiting {delay:.2f}s before bounded retry (remaining budget: {rem_before_sleep:.1f}s)...")
                            try:
                                await asyncio.wait_for(
                                    asyncio.sleep(delay),
                                    timeout=rem_before_sleep
                                )
                            except (asyncio.TimeoutError, TimeoutError):
                                logger.warning(f"Gemini cumulative deadline of {AI_CUMULATIVE_DEADLINE}s reached during 503 retry delay on {model}.")
                                self._health_state = ProviderHealthState.DEGRADED
                                raise AIError(
                                    kind=AIErrorKind.TIMEOUT,
                                    message=f"Gemini cumulative deadline of {AI_CUMULATIVE_DEADLINE}s reached during 503 retry delay on {model}.",
                                    user_message="AI provider request timed out. Please retry.",
                                    model=model
                                )

                            rem_after_sleep = max(0.0, AI_CUMULATIVE_DEADLINE - (time.monotonic() - start_time))
                            if rem_after_sleep > 0.5:
                                retry_timeout = min(timeout_val, rem_after_sleep)
                                try:
                                    retry_resp = await asyncio.wait_for(
                                        client.post(url, json=payload, timeout=retry_timeout),
                                        timeout=retry_timeout
                                    )
                                    if retry_resp.status_code == 200:
                                        data = retry_resp.json()
                                        candidates = data.get("candidates", [])
                                        if candidates and "content" in candidates[0]:
                                            parts = candidates[0]["content"].get("parts", [])
                                            if parts and "text" in parts[0]:
                                                self._health_state = ProviderHealthState.HEALTHY
                                                self._last_health_check_time = time.time()
                                                return parts[0]["text"]
                                        self._health_state = ProviderHealthState.DEGRADED
                                        raise AIError(
                                            kind=AIErrorKind.MALFORMED_RESPONSE,
                                            message=f"Gemini model {model} returned unexpected structure on retry: {str(data)[:200]}",
                                            user_message="AI provider returned an unparseable response structure.",
                                            status_code=200,
                                            model=model
                                        )
                                    err = classify_gemini_error(
                                        status_code=retry_resp.status_code,
                                        response_text=retry_resp.text,
                                        headers=dict(retry_resp.headers),
                                        model=model
                                    )
                                    self._health_state = ProviderHealthState.DEGRADED
                                    raise err
                                except (httpx.TimeoutException, asyncio.TimeoutError, TimeoutError):
                                    logger.warning(f"Gemini model {model} retry timed out within deadline.")
                                    self._health_state = ProviderHealthState.DEGRADED
                                    raise AIError(
                                        kind=AIErrorKind.TIMEOUT,
                                        message=f"Gemini model {model} retry timed out within deadline.",
                                        user_message="AI provider request timed out. Please retry.",
                                        model=model
                                    )
                            else:
                                logger.warning(f"Insufficient remaining time ({rem_after_sleep:.2f}s) after sleep for 503 retry on {model}; aborting retry.")
                                self._health_state = ProviderHealthState.DEGRADED
                                raise err
                        else:
                            logger.warning(f"Insufficient remaining time ({rem_before_sleep:.2f}s) for 503 retry delay {delay:.2f}s within {AI_CUMULATIVE_DEADLINE}s budget; aborting retry.")
                            self._health_state = ProviderHealthState.DEGRADED
                            raise err

                    self._health_state = ProviderHealthState.DEGRADED
                    logger.warning(f"Gemini model {model} failed with {err.kind.value}; checking fallback model...")
                    last_error = err
                    continue

                except (httpx.TimeoutException, asyncio.TimeoutError, TimeoutError):
                    self._health_state = ProviderHealthState.DEGRADED
                    self._last_health_check_time = time.time()
                    logger.warning(f"Gemini model {model} timed out after {req_timeout:.1f}s.")
                    last_error = AIError(
                        kind=AIErrorKind.TIMEOUT,
                        message=f"Gemini model {model} timed out after {req_timeout:.1f}s.",
                        user_message="AI provider request timed out. Please retry.",
                        model=model
                    )
                    continue

                except AIError:
                    raise

                except Exception as ex:
                    self._health_state = ProviderHealthState.DEGRADED
                    logger.error(f"Unexpected error calling Gemini on {model}: {ex}")
                    last_error = AIError(
                        kind=AIErrorKind.SERVICE_UNAVAILABLE,
                        message=f"Unexpected error: {str(ex)[:180]}",
                        user_message="AI service encountered an unexpected error.",
                        model=model
                    )
                    continue

        if last_error:
            raise last_error
        raise AIError(
            kind=AIErrorKind.SERVICE_UNAVAILABLE,
            message="All configured Gemini models failed.",
            user_message="AI service is currently unavailable. Please retry later."
        )

    async def _call_openai(self, prompt: str, system_instruction: Optional[str] = None) -> str:
        url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.openai_key}",
            "Content-Type": "application/json"
        }
        messages = []
        if system_instruction:
            messages.append({"role": "system", "content": system_instruction})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": self.openai_model,
            "messages": messages,
            "temperature": 0.2,
            "max_tokens": 4096
        }

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
            self._health_state = ProviderHealthState.HEALTHY
            return data["choices"][0]["message"]["content"]

    async def test_connection(self) -> Dict[str, Any]:
        """Bounded single-ping live inference test with a maximum 3.0s timeout."""
        if not self.gemini_key and not self.openai_key:
            self._health_state = ProviderHealthState.NOT_CONFIGURED
            return {
                "status": ProviderHealthState.NOT_CONFIGURED.value,
                "provider": "offline_scaffold",
                "model": "none",
                "message": "No external AI credentials configured; using offline structural scaffold."
            }
        
        provider = self.provider_name
        model = self.gemini_model if provider == "gemini" else self.openai_model
        t0 = time.time()
        try:
            if provider == "gemini":
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={self.gemini_key}"
                payload = {
                    "contents": [{"role": "user", "parts": [{"text": "Respond with OK only."}]}],
                    "generationConfig": {"temperature": 0.0, "maxOutputTokens": 10}
                }
                async with httpx.AsyncClient(timeout=3.0) as client:
                    resp = await client.post(url, json=payload)
                    self._last_health_check_time = time.time()
                    if resp.status_code != 200:
                        err = classify_gemini_error(resp.status_code, resp.text, dict(resp.headers), model)
                        self._health_state = ProviderHealthState.QUOTA_EXHAUSTED if err.kind == AIErrorKind.QUOTA_EXHAUSTED else ProviderHealthState.DEGRADED
                        self._last_error_message = err.user_message
                        return {
                            "status": self._health_state.value,
                            "provider": provider,
                            "model": model,
                            "error_kind": err.kind.value,
                            "error": err.user_message
                        }
                    res = resp.json()["candidates"][0]["content"]["parts"][0]["text"]
                    self._health_state = ProviderHealthState.HEALTHY
            elif provider == "openai":
                res = await self._call_openai("Respond with 'OK' only.", system_instruction="Output 'OK' only.")
                self._health_state = ProviderHealthState.HEALTHY
            else:
                return self.get_status()

            latency = round((time.time() - t0) * 1000, 1)
            return {
                "status": ProviderHealthState.HEALTHY.value,
                "provider": provider,
                "model": model,
                "latency_ms": latency,
                "sample_response": res.strip()[:60]
            }
        except Exception as e:
            self._health_state = ProviderHealthState.DEGRADED
            self._last_health_check_time = time.time()
            self._last_error_message = str(e)[:180]
            return {
                "status": ProviderHealthState.DEGRADED.value,
                "provider": provider,
                "model": model,
                "error": str(e)[:180]
            }

    def _generate_fallback_text(self, prompt: str, system_instruction: Optional[str] = None) -> str:
        """Deterministic structural fallback text with zero fabricated figures."""
        topic = extract_topic_title(prompt)
        return (
            f"# Executive Intelligence Report: {topic}\n\n"
            "> **Notice**: Generated via AgentPay Nexus Offline Structural Scaffold. Requires active AI credentials for live external generation.\n\n"
            f"### Primary Domain Outline for: {topic}\n\n"
            "This structural scaffold establishes domain categories, macro analytical frameworks, "
            "and governance checklists. Quantitative metrics and empirical projections are unavailable in offline mode."
        )

    def _generate_fallback_json(self, prompt: str, system_instruction: Optional[str] = None) -> Dict[str, Any]:
        """Topic-aware structural JSON fallback with ZERO fabricated numbers, market shares, or charts."""
        lower_prompt = prompt.lower()
        topic = extract_topic_title(prompt)
        
        # Subtask planning
        if "plan" in lower_prompt or "subtask" in lower_prompt or "orchestrat" in lower_prompt:
            return {
                "objective_summary": f"Execution pipeline for '{topic[:60]}' covering deep research, analytics, synthesis, and QA auditing.",
                "complexity_tier": "Standard",
                "estimated_total_cost": 8.00,
                "execution_mode": "offline_scaffold",
                "subtasks": [
                    {
                        "step_name": "research",
                        "assigned_agent_id": "agent_research_01",
                        "agent_category": "Research",
                        "objective": f"Gather domain fundamentals and key players for {topic[:40]}.",
                        "dependencies": ["planning"],
                        "estimated_cost": 2.00
                    },
                    {
                        "step_name": "data_analysis",
                        "assigned_agent_id": "agent_analysis_02",
                        "agent_category": "Analytics",
                        "objective": f"Audit quantitative metrics and evaluate CAGR feasibility for {topic[:40]}.",
                        "dependencies": ["research"],
                        "estimated_cost": 3.00
                    },
                    {
                        "step_name": "content_generation",
                        "assigned_agent_id": "agent_content_03",
                        "agent_category": "Content",
                        "objective": f"Synthesize findings into an executive Markdown deliverable for {topic[:40]}.",
                        "dependencies": ["data_analysis"],
                        "estimated_cost": 2.00
                    },
                    {
                        "step_name": "quality_assurance",
                        "assigned_agent_id": "agent_qa_04",
                        "agent_category": "Verification",
                        "objective": f"Audit deliverable completeness and compliance for {topic[:40]}.",
                        "dependencies": ["content_generation"],
                        "estimated_cost": 1.00
                    }
                ],
                "_disclosure": "Generated via AgentPay Nexus Offline Structural Scaffold. Requires active AI credentials for live external generation."
            }

        # Market research
        if "research" in lower_prompt or "market size" in lower_prompt:
            return {
                "market_overview": f"Domain landscape outline for '{topic}'. Evaluation identifies emerging technology patterns and regulatory standards.",
                "market_size_current": "Unavailable (Requires Live Research)",
                "market_size_forecast": "Unavailable (Requires Live Research)",
                "cagr_projected": None,
                "major_competitors": [],
                "growth_drivers": [
                    f"Structural domain integration in {topic[:30]}",
                    "Enterprise demand for process reliability and automation",
                    "Compliance and governance operational standards"
                ],
                "challenges": [
                    "Empirical data verification constraints",
                    "Regulatory harmonization across jurisdictions"
                ],
                "sources": [
                    {"source": "Structural Scaffold Framework (Offline Mode)", "reliability": "Scaffold"}
                ],
                "_disclosure": "Generated via AgentPay Nexus Offline Structural Scaffold. Requires active AI credentials for live external generation.",
                "execution_mode": "offline_scaffold"
            }

        # Data analysis
        if "analysis" in lower_prompt or "cagr" in lower_prompt or "quantitative" in lower_prompt:
            return {
                "computed_metrics": {
                    "base_year_revenue_usd_bn": None,
                    "target_year_revenue_usd_bn": None,
                    "cagr_percent": None,
                    "status": "unavailable",
                    "message": "Quantitative metrics unavailable in offline scaffold mode. Live AI research is required for empirical calculations."
                },
                "market_share_breakdown": [],
                "chart_revenue_projections": [],
                "key_findings": [
                    f"Quantitative baseline metrics unavailable for '{topic[:30]}' in offline scaffold mode.",
                    "Empirical financial projections deferred until verified research data is supplied."
                ],
                "_disclosure": "Generated via AgentPay Nexus Offline Structural Scaffold.",
                "execution_mode": "offline_scaffold"
            }

        # QA
        if "quality" in lower_prompt or "qa" in lower_prompt or "audit" in lower_prompt:
            return {
                "audit_status": "OFFLINE_SCAFFOLD",
                "completeness_score": 0,
                "factual_coherence_score": 0,
                "constraint_compliance": False,
                "budget_compliance": True,
                "feedback": "Offline structural scaffold generated without live AI models. Not eligible for payment or production deliverable approval.",
                "corrections_required": True,
                "is_payment_eligible": False,
                "_disclosure": "Generated via AgentPay Nexus Offline Structural Scaffold."
            }

        # Default fallback JSON
        return {
            "status": "offline_scaffold",
            "message": f"Processed through AgentPay Nexus Structural Scaffold for '{topic[:40]}'",
            "data": {"topic": topic[:80]},
            "_disclosure": "Generated via AgentPay Nexus Offline Structural Scaffold.",
            "execution_mode": "offline_scaffold"
        }


llm_provider = LLMProvider()
