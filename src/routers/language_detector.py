"""
Language Detection Module
Detects user query language (PT/EN/ES) with intelligent fallbacks
"""

from typing import Optional
from transformers import pipeline


# ============================================================================
# GLOBAL STATE
# ============================================================================

_language_detector = None


# ============================================================================
# PUBLIC API
# ============================================================================

def get_language_detector():
    """
    Get or create language detector pipeline (lazy loading).
    Uses xlm-roberta-base-language-detection for fast, accurate language ID.
    
    Returns:
        Transformers pipeline for language detection
    """
    global _language_detector
    
    if _language_detector is None:
        from ..core.config import config

        print(f"🌍 Loading language detector: {config.LANGUAGE_MODEL}")
        _language_detector = pipeline(
            "text-classification",
            model=config.LANGUAGE_MODEL,
            device=-1  # CPU (use 0 for GPU)
        )
        print("✅ Language detector loaded")
    
    return _language_detector


def detect_language(text: str, default_lang: str = 'pt') -> str:
    """
    Detect language from text with intelligent fallback.
    
    Strategy:
    1. Use ML model for detection
    2. If unsupported language → check for Portuguese/Spanish patterns
    3. If very short query (<5 chars) → use default
    4. If low confidence on short query → use default
    
    Args:
        text: Text to detect language from
        default_lang: Default language if detection is uncertain (default: 'pt' for Brazil)
    
    Returns:
        Language code: 'pt', 'en', or 'es'
    
    Examples:
        >>> detect_language("como faço pra investir?")
        'pt'
        
        >>> detect_language("pix")  # Short, ambiguous
        'pt'  # Falls back to default
        
        >>> detect_language("how do I invest?")
        'en'
    """
    detector = get_language_detector()
    result = detector(text[:512])  # Limit to 512 chars for speed
    
    lang_code = result[0]['label']  # e.g., 'pt', 'en', 'es'
    confidence = result[0]['score']
    
    supported_langs = ['pt', 'en', 'es']
    
    # If unsupported language detected, use intelligent fallback
    if lang_code not in supported_langs:
        # For very short queries (< 5 chars), use default
        if len(text.strip()) < 5:
            print(f"⚠️  Short query '{text}', using default language '{default_lang}'")
            return default_lang
        
        # For longer queries, check for language-specific patterns
        text_lower = text.lower()
        
        # Portuguese patterns
        pt_patterns = ['como', 'qual', 'por', 'para', 'com', 'de', 'que', 'não', 'sim', 'pix', 'fatura', 'cartão', 'cartao', 'conta']
        if any(word in text_lower.split() for word in pt_patterns):
            print(f"⚠️  Detected Portuguese patterns in '{text[:30]}...', using 'pt'")
            return 'pt'
        
        # Spanish patterns (different from Portuguese)
        es_patterns = ['cómo', 'cuál', 'qué', 'sí', '¿', '¡']
        if any(pattern in text_lower for pattern in es_patterns):
            print(f"⚠️  Detected Spanish patterns in '{text[:30]}...', using 'es'")
            return 'es'
        
        # English patterns
        en_patterns = ['how', 'what', 'why', 'when', 'where', 'the', 'a', 'is']
        if any(word in text_lower.split() for word in en_patterns):
            print(f"⚠️  Detected English patterns in '{text[:30]}...', using 'en'")
            return 'en'
        
        # No patterns matched, use default
        print(f"⚠️  Unsupported language '{lang_code}', using default '{default_lang}'")
        return default_lang
    
    # If low confidence on short queries, use default
    if confidence < 0.7 and len(text.strip()) < 10:
        print(f"⚠️  Low confidence ({confidence:.2%}) on short query, using default '{default_lang}'")
        return default_lang
    
    return lang_code

