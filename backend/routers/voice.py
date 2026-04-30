import logging

from fastapi import APIRouter, HTTPException, Request

from schemas.voice import VoiceDesignParams, VoiceDesignRequest, VoiceDesignResponse, VoiceSpeakRequest, VoiceSpeakResponse

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/voice", tags=["voice"])


@router.post("/design")
async def design(request: Request, body: VoiceDesignRequest) -> VoiceDesignResponse:
    message = body.message.strip()
    if not message:
        raise HTTPException(status_code=400, detail="message is required")

    try:
        params = await request.app.state.inference.voice_design_params(message)
    except Exception:
        logger.exception("voice_design_params failed")
        raise HTTPException(status_code=503, detail="Voice design (Gemini) unavailable")

    try:
        audio_b64, mime = await request.app.state.speech.design_voice(
            voice_description=params["voice_description"],
            text=params["sample_text"],
        )
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception:
        logger.exception("design_voice failed")
        raise HTTPException(status_code=502, detail="ElevenLabs voice generation failed")

    return VoiceDesignResponse(
        params=VoiceDesignParams(
            voice_description=params["voice_description"],
            display_label=params["display_label"],
            tags=params["tags"],
        ),
        sample_text=params["sample_text"],
        audio_base64=audio_b64,
        audio_mime=mime or "audio/mpeg",
    )


@router.post("/speak")
async def speak(request: Request, body: VoiceSpeakRequest) -> VoiceSpeakResponse:
    if not body.voice_description.strip() or not body.text.strip():
        raise HTTPException(status_code=400, detail="voice_description and text are required")

    try:
        audio_b64, mime = await request.app.state.speech.speak_designed_voice(
            voice_description=body.voice_description,
            text=body.text,
        )
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception:
        logger.exception("speak_designed_voice failed")
        raise HTTPException(status_code=502, detail="ElevenLabs voice generation failed")

    return VoiceSpeakResponse(audio_base64=audio_b64, audio_mime=mime or "audio/mpeg")
