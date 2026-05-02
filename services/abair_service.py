import base64

import httpx

ABAIR_SYNTH_URL = "https://synthesis.abair.ie/api/synthesise"
DEFAULT_VOICE = "ga_CO_snc_piper"  # Sibéal — female Connemara (Connacht)


async def synthesise(text: str) -> bytes:
    """Call the ABAIR Irish TTS service and return raw WAV audio bytes.

    Uses the same endpoint as the abair.ie/synthesis web interface.
    Raises httpx.HTTPStatusError on a non-2xx response,
    and httpx.RequestError on network/timeout failures.
    """
    params = {"input": text, "voice": DEFAULT_VOICE, "normalise": "true"}
    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.get(ABAIR_SYNTH_URL, params=params)
        response.raise_for_status()
    return base64.b64decode(response.json()["audioContent"])
