"""
╔══════════════════════════════════════════════════════════════════╗
║   STUDIO ANIMÉ ÉDUCATIF — Version 3 Professionnelle             ║
║   Streamlit + Groq API (GRATUIT)                                 ║
║   Clé API sidebar · Validation inline · 3 étapes épurées        ║
╚══════════════════════════════════════════════════════════════════╝
"""

import streamlit as st
import subprocess, sys, os, re, math, asyncio, json, tempfile
from dataclasses import dataclass
from typing import List
import warnings
warnings.filterwarnings("ignore")

@st.cache_resource
def install_deps():
    for pkg in ["groq","edge-tts","gtts","pydub","opencv-python-headless","pillow","numpy"]:
        subprocess.run([sys.executable,"-m","pip","install","-q",pkg],capture_output=True)
    return True
install_deps()

import cv2, numpy as np
from PIL import Image, ImageDraw, ImageFont
from gtts import gTTS
try:
    from groq import Groq as _GroqClient
    _GROQ_OK = True
except ImportError:
    _GROQ_OK = False
try:
    import edge_tts
    _EDGE_TTS_OK = True
except ImportError:
    _EDGE_TTS_OK = False

# ─────────────────────────────────────────
#  CONFIG
# ─────────────────────────────────────────
class Cfg:
    FPS=24; SIZE=512; CRF=23; EF=6
    FONT_DIR="/usr/share/fonts/truetype/dejavu/"
    FONT_B=FONT_DIR+"DejaVuSans-Bold.ttf"
    FONT_R=FONT_DIR+"DejaVuSans.ttf"
    VF="fr-FR-DeniseNeural"; VG="fr-FR-HenriNeural"
    VRATE="-20%"; VPITCH="+5Hz"
    MODEL="llama-3.1-8b-instant"

# ─────────────────────────────────────────
#  DATACLASSES
# ─────────────────────────────────────────
@dataclass
class Character:
    prenom:str; age:int; genre:str; hero:str="Par défaut"

@dataclass
class SongData:
    titre:str; intro:str; acte1:str; acte2:str
    refrain1:str; acte3:str; acte4:str; refrain2:str
    acte5:str; acte6:str; outro:str

@dataclass
class Scene:
    titre:str; decor:str; action:str
    emotion:str; dialogue:str; duree:int
    sky_mood:str="day"
    image_prompt:str=""
    emotion_text:str=""
    lieu_texte:str=""
    bg_img:Image.Image=None

# ─────────────────────────────────────────
#  THÈMES VISUELS
# ─────────────────────────────────────────
THEMES = {
    "electric":{"label":"⚡ Électricité","emoji":"⚡","color":"#6366f1",
        "sky_n":((100,140,255),(180,210,255)),"sky_d":((180,60,40),(120,40,30)),"sky_g":((255,160,40),(255,200,100)),
        "gnd":(60,160,60),"gnds":(40,120,40),"fx":(80,200,255),"wall":(240,240,255),
        "desc":"Maison moderne, prises électriques, éclairs bleus"},
    "kitchen":{"label":"🍳 Cuisine","emoji":"🍳","color":"#f97316",
        "sky_n":((255,220,150),(255,240,180)),"sky_d":((200,80,20),(140,50,10)),"sky_g":((255,180,60),(255,220,100)),
        "gnd":(100,70,40),"gnds":(70,50,25),"fx":(255,120,0),"wall":(255,230,200),
        "desc":"Grande cuisine familiale, couteaux, flammes orange"},
    "meds":{"label":"💊 Médicaments","emoji":"💊","color":"#a855f7",
        "sky_n":((200,180,255),(230,220,255)),"sky_d":((120,40,160),(80,20,120)),"sky_g":((220,180,255),(240,210,255)),
        "gnd":(80,160,80),"gnds":(55,120,55),"fx":(200,100,255),"wall":(240,230,255),
        "desc":"Salle de bain, armoire à pharmacie, lumière violette"},
    "pool":{"label":"🏊 Piscine","emoji":"🏊","color":"#0ea5e9",
        "sky_n":((60,160,255),(150,210,255)),"sky_d":((20,60,140),(10,40,100)),"sky_g":((255,200,80),(255,230,130)),
        "gnd":(0,120,200),"gnds":(0,90,160),"fx":(100,220,255),"wall":(200,240,255),
        "desc":"Piscine extérieure, eau bleue, carrelage blanc"},
    "road":{"label":"🚦 Route","emoji":"🚦","color":"#64748b",
        "sky_n":((140,180,230),(190,215,245)),"sky_d":((160,80,40),(120,60,30)),"sky_g":((255,180,60),(255,210,110)),
        "gnd":(80,80,80),"gnds":(55,55,55),"fx":(255,255,0),"wall":(200,200,210),
        "desc":"Rue de ville, passage piéton, véritable feu tricolore lumineux de circulation (traffic lights, NO FIRE FLAMES)"},
    "fire":{"label":"🔥 Feu / Gaz","emoji":"🔥","color":"#ef4444",
        "sky_n":((255,180,100),(255,210,150)),"sky_d":((200,50,0),(140,30,0)),"sky_g":((255,160,40),(255,200,90)),
        "gnd":(70,160,70),"gnds":(50,120,50),"fx":(255,80,0),"wall":(255,220,195),
        "desc":"Cuisine avec gaz, vraies flammes de feu ardentes (real fire flames)"},
    "behaviour":{"label":"🤝 Comportement","emoji":"🤝","color":"#f59e0b",
        "sky_n":((255,230,160),(255,245,200)),"sky_d":((200,100,30),(140,70,20)),"sky_g":((255,200,80),(255,230,120)),
        "gnd":(80,170,80),"gnds":(55,130,55),"fx":(255,190,0),"wall":(255,245,220),
        "desc":"Classe d'école ou cour de récréation, enfants qui jouent"},
    "general":{"label":"🌟 Général","emoji":"🌟","color":"#6366f1",
        "sky_n":((100,160,255),(200,230,255)),"sky_d":((220,80,50),(150,60,40)),"sky_g":((255,180,60),(255,220,120)),
        "gnd":(70,175,70),"gnds":(50,130,50),"fx":(255,200,0),"wall":(255,235,210),
        "desc":"Environnement général coloré et adapté"},
}

EXAMPLES = [
    {"icon":":material/electric_bolt:","label":"Prises","text":"Mon fils Adam, 5 ans, touche les prises électriques","theme":"electric"},
    {"icon":":material/restaurant:","label":"Couteaux","text":"Mon fils Youssef, 7 ans, joue avec les couteaux de cuisine","theme":"kitchen"},
    {"icon":":material/medication:","label":"Médicaments","text":"Ma fille Inès, 6 ans, mange des médicaments","theme":"meds"},
    {"icon":":material/pool:","label":"Piscine","text":"Ma fille Lina, 4 ans, s'approche seule du bord de la piscine","theme":"pool"},
    {"icon":":material/directions_car:","label":"Traverser","text":"Mon fils Rayan, 6 ans, traverse la rue sans regarder","theme":"road"},
    {"icon":":material/local_fire_department:","label":"Feu / Gaz","text":"Ma fille Sara, 5 ans, allume les boutons du gaz","theme":"fire"},
]

# ─────────────────────────────────────────
#  PROMPTS
# ─────────────────────────────────────────
VAL_PROMPT="""Tu es un modérateur d'application éducative pour enfants de 3 à 8 ans.
Analyse cette phrase parentale et réponds UNIQUEMENT en JSON valide sans markdown :
{
  "valide": true,
  "raison": "courte explication",
  "prenom": "prénom ou null",
  "age": "âge (nombre entier) ou null",
  "genre": "garçon ou fille",
  "danger": "type danger 3 mots",
  "theme": "electric|kitchen|meds|pool|road|fire|general",
  "comprehension": "En simple : ce que l'enfant fait exactement (1 phrase bienveillante)",
  "conseils": ["conseil court 1","conseil court 2","conseil court 3"],
  "message_parent": "message encourageant 1 phrase",
  "suggestions": ["phrase alternative 1","phrase alternative 2"]
}
Phrase : {betise}"""

SCN_PROMPT="""Tu es auteur de livres éducatifs pour enfants 3-8 ans. Génère une histoire narrative d'aventure.
INSTRUCTION DE STYLE : Les phrases de narration (scenes_narration) DOIVENT être racontées avec une voix de conteur très enthousiaste ! Utilise des exclamations, des onomatopées (Boïng, Oups, Aïe) et des questions pour captiver l'enfant !
Décor : {theme_desc}. Réponds UNIQUEMENT JSON valide sans markdown :
{{"prenom":"{prenom}","age":{age},"genre":"{genre}","hero":"{hero}","danger_court":"3 mots max",
"decor_principal":"8 mots max","ambiance_couleur":"couleur dominante",
"scenes_narration":[
  "Narration Scène 1 : Salutation directe et joyeuse au spectateur [{prenom}] et annonce fascinante de l'histoire qu'il va regarder sur son ami [{hero}] (invente un prénom aléatoire si 'Par défaut' -- JAMAIS le vrai prénom de l'enfant). Ne salue PAS le héros !",
  "Narration Scène 2 : Phrase créative décrivant ce que le héros [{hero}] est en train de faire.",
  "Narration Scène 3 : Autre phrase décrivant l'activité de [{hero}]. (Ne dis jamais 'l'enfant', utilise toujours son nom !) ",
  "Narration Scène 4 : [{hero}] découvre soudainement un nouvel objet (le danger).",
  "Narration Scène 5 : [{hero}] observe l'objet avec une grande curiosité.",
  "Narration Scène 6 : La tentation grandit, [{hero}] s'approche doucement...",
  "Narration Scène 7 : Un énorme suspense dramatique ! Est-ce que [{hero}] va le faire ?",
  "Narration Scène 8 : Le point de bascule ! [{hero}] commet l'interdit ! (Ton dramatique)",
  "Narration Scène 9 : Le contrecoup immédiat ! Très grosse frayeur ou accident réaliste pour [{hero}].",
  "Narration Scène 10 : [{hero}] réalise sa terrible erreur avec beaucoup d'émotion.",
  "Narration Scène 11 : [{hero}] appelle à l'aide ou panique totale.",
  "Narration Scène 12 : Le conteur explique à [{hero}] POURQUOI c'est interdit (belle leçon créative).",
  "Narration Scène 13 : [{hero}] écoute et comprend avec tristesse son erreur.",
  "Narration Scène 14 : [{hero}] fait la promesse solennelle de ne jamais recommencer.",
  "Narration Scène 15 : Adresse-toi directement au spectateur [{prenom}] pour récapituler la bêtise de [{hero}], et conclus positivement. (ATTENTION: NE LUI RE-DIS PAS BONJOUR ICI, juste un message de conclusion !)"
],
"image_prompts":[
  "Describe scene 1 background in English. IMPORTANT: Show the main hero [{hero}] looking DIRECTLY at the camera lens, making direct eye contact with the viewer, and waving happily.",
  "Describe scene 2 background in English. Include [{hero}]. Include friends ONLY IF relevant to this scene's story.",
  "Describe scene 3 background in English. Include [{hero}]. Include friends ONLY IF relevant to this scene's story.",
  "Describe scene 4 background in English. Include [{hero}]. Include friends ONLY IF relevant to this scene's story.",
  "Describe scene 5 background in English. Include [{hero}]. Include friends ONLY IF relevant to this scene's story.",
  "Describe scene 6 background in English. Include [{hero}]. Include friends ONLY IF relevant to this scene's story.",
  "Describe scene 7 background in English. Include [{hero}]. Include friends ONLY IF relevant to this scene's story.",
  "Describe scene 8 background in English. Include [{hero}]. Include friends ONLY IF relevant to this scene's story.",
  "Describe scene 9 background in English. Include [{hero}]. Include friends ONLY IF relevant to this scene's story.",
  "Describe scene 10 background in English. Include [{hero}]. Include friends ONLY IF relevant to this scene's story.",
  "Describe scene 11 background in English. Include [{hero}]. Include friends ONLY IF relevant to this scene's story.",
  "Describe scene 12 background in English. Include [{hero}]. Include friends ONLY IF relevant to this scene's story.",
  "Describe scene 13 background in English. Include [{hero}]. Include friends ONLY IF relevant to this scene's story.",
  "Describe scene 14 background in English. Include [{hero}]. Include friends ONLY IF relevant to this scene's story.",
  "Describe scene 15 background in English. IMPORTANT: Show the main hero [{hero}] looking DIRECTLY into the camera, making direct eye contact with the child viewer, waving goodbye or giving a thumbs up."
],
"lieux_scenes":[
  "phrase courte (1-3 mots max) SANS AUCUN EMOJI pour indiquer le lieu (ex: Dans la cuisine)",
  "phrase courte lieu scène 2 sans emoji",
  "phrase courte lieu scène 3 sans emoji",
  "phrase courte lieu scène 4 sans emoji",
  "phrase courte lieu scène 5 sans emoji",
  "phrase courte lieu scène 6 sans emoji",
  "phrase courte lieu scène 7 sans emoji",
  "phrase courte lieu scène 8 sans emoji",
  "phrase courte lieu scène 9 sans emoji",
  "phrase courte lieu scène 10 sans emoji",
  "phrase courte lieu scène 11 sans emoji",
  "phrase courte lieu scène 12 sans emoji",
  "phrase courte lieu scène 13 sans emoji",
  "phrase courte lieu scène 14 sans emoji",
  "phrase courte lieu scène 15 sans emoji"
],
"emotions_personnage":[
  "état émotionnel très court, ex: 'Dora heureuse' ou 'Spiderman triste'. NE JAMAIS ÉCRIRE le mot 'Humeur', juste l'état.",
  "état émotionnel scène 2, direct et court",
  "état émotionnel scène 3",
  "état émotionnel scène 4",
  "état émotionnel scène 5",
  "état émotionnel scène 6",
  "état émotionnel scène 7",
  "état émotionnel scène 8",
  "état émotionnel scène 9",
  "état émotionnel scène 10",
  "état émotionnel scène 11",
  "état émotionnel scène 12",
  "état émotionnel scène 13",
  "état émotionnel scène 14",
  "état émotionnel scène 15"
],
"song":{{"titre":"L'Histoire de {prenom} et [danger] (style {hero})",
"intro":"2-3 phrases d'accroche rimées","acte1":"vie normale 3-4 phrases rimées",
"acte2":"découverte objet dangereux 3-4 phrases rimées",
"refrain1":"avertissement NON NON NON 3-4 phrases rimées",
"acte3":"le héros fait EXPLICITEMENT la bêtise 2-3 phrases dramatiques",
"acte4":"la conséquence effrayante (se fait mal/peur) 3-4 phrases rimées",
"refrain2":"l'explication pédagogique : voilà pourquoi c'est interdit",
"acte5":"comprend son erreur et regrette 3-4 phrases émouvantes",
"acte6":"promesse de ne plus recommencer 3-4 phrases rimées",
"outro":"message direct au spectateur pour qu'il ne fasse pas la bêtise"}}}}
Phrase : {betise}"""

# ─────────────────────────────────────────
#  IA — GROQ
# ─────────────────────────────────────────
def _extract_json(raw: str) -> str:
    """Extrait le JSON même si du texte entoure le bloc."""
    # 1. Retirer les blocs markdown ```json ... ```
    raw = re.sub(r"```(?:json)?\s*", "", raw).strip()
    raw = re.sub(r"```", "", raw).strip()
    # 2. Trouver le premier { et le dernier }
    start = raw.find("{")
    end   = raw.rfind("}")
    if start != -1 and end != -1 and end > start:
        return raw[start:end+1]
    return raw

def _call(api_key: str, prompt: str, max_tok: int = 800) -> dict:
    """Appelle Groq et retourne un dict JSON parsé."""
    c = _GroqClient(api_key=api_key)
    m = c.chat.completions.create(
        model=Cfg.MODEL,
        max_tokens=max_tok,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system",
             "content": "Tu es un assistant qui répond UNIQUEMENT en JSON valide."},
            {"role": "user", "content": prompt}
        ]
    )
    raw = m.choices[0].message.content.strip()
    cleaned = _extract_json(raw)
    return json.loads(cleaned)

def validate_ai(betise: str, api_key: str) -> dict:
    return _call(api_key, VAL_PROMPT.replace("{betise}", betise), 900)

# ─────────────────────────────────────────
#  CHAT PROMPT — conversation libre + détection scénario
# ─────────────────────────────────────────
CHAT_PROMPT = """
Tu es un assistant pédagogique chaleureux et compréhensif. Tu parles UNIQUEMENT français.
Tu aides les PARENTS avec l'éducation de leur enfant.

Règle 1 — CONVERSATION GÉNÉRALE :
Si le parent salue, pose une question, ou demande une explication, réponds TOUJOURS avec un ton adapté aux enfants, simple et éducatif. 
Exemples : "Un danger, c'est quelque chose qui peut nous faire du mal...", "Bonjour ! Comment allez-vous aujourd'hui ?"
Pas de limite de mots stricte, sois naturel et utile. Informe le parent que tu es là pour l'aider.

Règle 2 — DÉTECTION (MODE SCÉNARIO) :
Dès que le parent décrit N'IMPORTE QUELLE situation inquiétante, bêtise, ou comportement dangereux, ou demande de l'aide sur une action spécifique :
Exemples : "Mon fils fait des bêtises avec...", "Ma fille n'arrête pas de...", "Mon enfant touche à...", "Que faire quand mon enfant...", "Aide-moi, mon petit..."
  → ACTIVE IMMÉDIATEMENT le mode scénario.
  → Prénom et âge sont OPTIONNELS (utilise "l'enfant" et null pour l'âge si absents).
  → Ta réponse : phrase de confirmation empathique courte.

Règle 3 — MISES À JOUR ET CORRECTIONS (CRUCIAL) :
Le message du parent peut contenir la balise "[CORRECTION DU PARENT]". 
Ce qui suit cette balise est la NOUVELLE consigne absolue. Tu DOIS écraser et remplacer l'ancien prénom, l'ancien âge, l'ancien genre ou l'ancien comportement par ce qui est dit dans la correction.
Exemple : "... [CORRECTION DU PARENT] : Salma 8 ans" -> Renvoyer prénom "Salma" et âge 8. Oublier tout prénom ou âge précédent.
Exemple : "... [CORRECTION DU PARENT] : c'est un garçon" -> Renvoyer genre "garçon".

SUGGESTIONS D'ENRICHISSEMENT (Mode Scénario) : 
Si le scénario manque de détails contextuels, génère 1 à 3 suggestions COURTES (ex: "dès que j'ai le dos tourné").
IMPORTANT : Si l'histoire du parent est DÉJÀ très complète, ou si rajouter des détails serait répétitif et inutile, renvoie strictement une liste VIDE []. Ne génère jamais de suggestions artificielles juste pour remplir.

Réponds UNIQUEMENT en JSON valide sans markdown :

Pour comportement inquiétant/corrigible :
{{"type":"scenario","response":"",
"valide":true,"raison":"(Doit toujours être true)",
"prenom":"prénom (ou 'Votre enfant')","age":null,"genre":"garçon ou fille",
"hero":"nom du héros (ex: Spiderman, Dora, ou 'Par défaut')",
"danger":"description courte du comportement",
"theme":"general", // CHOISIS UN SEUL MOT EXACT PARMI : electric, kitchen, meds, pool, road, fire, behaviour, general
"comprehension":"Il fait [comportement].",
"conseils":["conseil 1","conseil 2","conseil 3"],
"message_educatif":"Phrase courte pour l'enfant (SANS AUCUN GUILLEMET POUR NE PAS CASSER LE JSON)",
"scenes":["scène 1 (action)","scène 2 (bêtise)","scène 3 (conséquence)","scène 4 (leçon)"],
"message_parent":"Ne vous inquiétez pas, on va corriger ça ensemble !",
"suggestions":["suggestion 1"]}}

Pour conversation générale :
{{"type":"general","response":"ta réponse naturelle, simple, éducative et adaptée."}}

Pour hors sujet :
{{"type":"invalid","response":"Je suis spécialisé dans les comportements des enfants.",
"suggestions":["Mon enfant frappe ses amis","Ma fille touche les prises"]}}

Message du parent : {message}
"""

def chat_ai(message: str, api_key: str, current_state: dict = None) -> dict:
    """Analyse le message et retourne type general/scenario/invalid + réponse."""
    prompt = CHAT_PROMPT.replace("{message}", message)
    if current_state and current_state.get("type") == "scenario":
        prompt += f"\n\nÉTAT ACTUEL : Prénom='{current_state.get('prenom')}', Âge={current_state.get('age')}, Genre={current_state.get('genre')}"
        prompt += "\n⚠️ INSTRUCTION SPECIALE : Tu dois utiliser ces valeurs de l'état actuel SAUF SI la balise [CORRECTION DU PARENT] vient les contredire. Dans ce cas, modifie l'état actuel et remplace-le obligatoirement par la correction."
        
    res = _call(api_key, prompt, 1500)
    if res.get("type") == "scenario":
        pre = res.get("prenom") or "Votre enfant"
        age = res.get("age")
        hero = res.get("hero", "Par défaut")
        
        hero_str = f" (Héros: {hero})" if hero and hero != "Par défaut" else ""
        enfant_info = f"{pre}, {age} ans{hero_str}" if age else f"{pre}{hero_str}"
        
        danger = res.get("danger", "ce comportement")
        msg_edu = res.get("message_educatif", "On va apprendre à corriger cela.")
        scenes = res.get("scenes", ["[Scène 1]", "[Scène 2]", "[Scène 3]", "[Scène 4]"])
        scenes_str = "\n".join(f"- {s}" for s in scenes)
        res["response"] = (
            f"✅ J'ai bien compris la situation !\n\n"
            f"Voici ce que je vais mettre dans la vidéo :\n\n"
            f"👤 ENFANT : {enfant_info}\n"
            f"⚠️ DANGER : {danger}\n"
            f"📖 MESSAGE ÉDUCATIF : \"{msg_edu}\"\n\n"
            f"🎨 IMAGES DANS LA VIDÉO :\n{scenes_str}"
        )
    return res

def scenario_ai(betise: str, val: dict, api_key: str) -> dict:
    theme_val = val.get("theme") or "general"
    t = THEMES.get(theme_val, THEMES["general"])
    p = SCN_PROMPT.replace("{betise}", betise).replace("{theme_desc}", t["desc"])
    prenom = val.get("prenom") or "l'enfant"
    age = val.get("age") or 5
    genre = val.get("genre") or "garçon"
    hero = val.get("hero") or "Par défaut"
    p = p.replace("{prenom}", str(prenom))
    p = p.replace("{age}", str(age))
    p = p.replace("{genre}", str(genre))
    p = p.replace("{hero}", str(hero))
    
    if hero and hero != "Par défaut":
        p += f"\n\n🚨 INSTRUCTION ABSOLUE : Le parent a choisi le héros '{hero}'. Ce héros ({hero}) DOIT ÊTRE LE PERSONNAGE PRINCIPAL de l'histoire et de la narration ! C'est {hero} qui fait la bêtise et qui apprend la leçon, PAS un personnage secondaire qui vient l'aider !"
        
    return _call(api_key, p, 3000)

def parse_scenario(d: dict) -> tuple:
    prenom = d.get("prenom") or ""
    age = d.get("age") or 5
    genre = d.get("genre") or "garçon"
    hero = d.get("hero") or "Par défaut"
    char = Character(prenom=str(prenom), age=int(age), genre=str(genre), hero=str(hero))
    s = d.get("song", {})
    song = SongData(titre=s.get("titre",f"Histoire de {char.prenom}"), intro=s.get("intro","..."), acte1=s.get("acte1","..."),
        acte2=s.get("acte2","..."), refrain1=s.get("refrain1","..."), acte3=s.get("acte3","..."),
        acte4=s.get("acte4","..."), refrain2=s.get("refrain2","..."), acte5=s.get("acte5","..."),
        acte6=s.get("acte6","..."), outro=s.get("outro","..."))
    # Récupère les 15 narrations générées par l'IA
    raw_narr = d.get("scenes_narration", [])
    # Nettoie les narrations (retire le préfixe "Scène X : " si présent)
    narrations = []
    for n in raw_narr:
        txt = str(n)
        if ":" in txt:
            txt = txt.split(":", 1)[-1].strip()
        narrations.append(txt)
    # Complète si l'IA donne moins de 15 narrations
    defaults = [
        f"Voici {char.prenom}.",
        f"{char.prenom} joue joyeusement aujourd'hui.",
        "Oh, regarde ce qu'il y a là !",
        "Il s'approche, c'est très tentant.",
        "Est-ce qu'il doit toucher ?",
        "Attention, c'est dangereux !",
        "Mais il n'écoute pas...",
        "Oh non, il fait la bêtise !",
        "Aïe ! Ça s'est très mal passé !",
        "Il a mal et demande de l'aide !",
        "Voilà pourquoi il ne fallait pas le faire.",
        "C'est très dangereux !",
        f"Maintenant, {char.prenom} a bien compris le danger.",
        "Il promet de ne plus jamais recommencer.",
        "Et toi aussi, sois très prudent !",
    ]
    while len(narrations) < 15:
        narrations.append(defaults[len(narrations)])
        
    img_prompts = d.get("image_prompts", [])
    while len(img_prompts) < 15:
        img_prompts.append("beautiful landscape, children book illustration style, detailed scene")
        
    ep = d.get("emotions_personnage", [])
    while len(ep) < 15:
        ep.append("détendu")
        
    ls = d.get("lieux_scenes", [])
    while len(ls) < 15:
        ls.append("📍 Quelque part")
        
    return char, song, narrations[:15], img_prompts[:15], ep[:15], ls[:15]

# L'ancien dictionnaire DECOR_LABELS a été entièrement retiré car les lieux sont générés 100% par l'IA.

def build_scenes(char: Character, song: SongData, tk: str, narrations: list, img_prompts: list, ep: list, ls: list, dframes: list) -> List[Scene]:
    p = char.hero if char.hero and char.hero != "Par défaut" else char.prenom
    f = Cfg.FPS
    dm = {"electric": ["maison","parc","maison","maison","maison","danger"]+["parc"]*9,
          "kitchen":  ["maison","parc","maison","maison","maison","danger"]+["parc"]*9,
          "pool":     ["parc"]*3+["danger"]*3+["parc"]*9,
          "road":     ["parc"]*3+["danger"]*3+["parc"]*9}
    d = dm.get(tk, ["parc"]*15)
    # Utilise les narrations IA comme dialogue de chaque scène
    n = narrations  # alias court
    ip = img_prompts
    return [
        Scene("Introduction",    d[0],  "saute_joie",       "heureux",   n[0],  dframes[0],  "day",    ip[0], ep[0], ls[0]),
        Scene(f"La vie de {p}", d[1],  "court_vite",       "heureux",   n[1],  dframes[1],  "day",    ip[1], ep[1], ls[1]),
        Scene("Belle journée",  d[2],  "marche_content",   "heureux",   n[2],  dframes[2],  "golden", ip[2], ep[2], ls[2]),
        Scene("Qu'est-ce?",     d[3],  "decouvre_surpris", "curieux",   n[3],  dframes[3],  "golden", ip[3], ep[3], ls[3]),
        Scene("Une idée...",    d[4],  "hesite_balance",   "penseur",   n[4],  dframes[4],  "golden", ip[4], ep[4], ls[4]),
        Scene("⚠️ ATTENTION!",  d[5],  "appelle_gestes",   "effraye",   n[5],  dframes[5],  "day",    ip[5], ep[5], ls[5]),
        Scene("NON NON NON!",   d[6],  "saute_peur",       "effraye",   n[6],  dframes[6],  "day",    ip[6], ep[6], ls[6]),
        Scene("La bêtise!",     d[7],  "fait_betise_saute","curieux",   n[7],  dframes[7],  "dusk",   ip[7], ep[7], ls[7]),
        Scene("Conséquences!",  d[8],  "court_panique",    "effraye",   n[8],  dframes[8],  "dusk",   ip[8], ep[8], ls[8]),
        Scene("AU SECOURS!",    d[9],  "appelle_gestes",   "effraye",   n[9],  dframes[9],  "dusk",   ip[9], ep[9], ls[9]),
        Scene("La leçon",       d[10], "ecoute_hoche",     "desole",    n[10], dframes[10],  "day",    ip[10], ep[10], ls[10]),
        Scene(f"{p} comprend",  d[11], "pleure_assise",    "triste",    n[11], dframes[11],  "day",    ip[11], ep[11], ls[11]),
        Scene("La promesse",    d[12], "saute_promesse",   "determine", n[12], dframes[12],  "day",    ip[12], ep[12], ls[12]),
        Scene("Et toi?",        d[13], "pointe_enfant",    "heureux",   n[13], dframes[13],  "day",    ip[13], ep[13], ls[13]),
        Scene("À bientôt!",     d[14], "salue_saute",      "fier",      n[14], dframes[14],  "day",    ip[14], ep[14], ls[14]),
    ]

# ─────────────────────────────────────────
#  PALETTE
# ─────────────────────────────────────────
class P:
    SKIN=(255,232,205);CHEEK=(255,175,165);HAIR_B=(55,38,18);HAIR_G=(195,135,70)
    SHIRT_B=(135,206,235);SHIRT_G=(255,20,147);PANTS=(45,85,195);SHOE=(175,48,48)
    EYE_B=(80,160,255);EYE_G=(255,100,195);WHITE=(255,255,255);OUTLINE=(30,20,10)
    SUN=(255,245,100);TEAR=(90,195,255);FLAME_C=(255,230,80)
    ROOF=(185,80,60);DOOR=(110,65,35);WINDOW=(180,220,255)
    TREE_T=(85,52,28);TREE_L=(60,185,60)
    UI_BG=(245,247,252);UI_TFG=(30,30,80);UI_DFG=(60,60,140)
    SONG_BG=(245,245,255);SONG_FG=(80,60,180);UI_BAR=(99,102,241)

def lerp(a,b,t):return a+(b-a)*t
def lc(c1,c2,t):return tuple(int(lerp(a,b,t))for a,b in zip(c1,c2))
def grad(draw,x0,y0,x1,y1,tc,bc):
    for y in range(y0,y1):
        t=(y-y0)/max(1,y1-y0); draw.line([(x0,y),(x1,y)],fill=lc(tc,bc,t))

def get_sky(td,mood):
    if mood=="dusk": return td["sky_d"]
    if mood=="golden": return td["sky_g"]
    return td["sky_n"]

def draw_bg(draw,decor,mood,frame,td):
    S=Cfg.SIZE; tc,bc=get_sky(td,mood)
    grad(draw,0,0,S,int(S*.64),tc,bc)
    if mood!="dusk":
        sx,sy=int(S*.85),int(S*.09)
        draw.ellipse([sx-22,sy-22,sx+22,sy+22],fill=P.SUN)
        for ang in range(0,360,45):
            rx=sx+int(30*math.cos(math.radians(ang+frame*.3)))
            ry=sy+int(30*math.sin(math.radians(ang+frame*.3)))
            draw.line([(sx,sy),(rx,ry)],fill=P.SUN,width=2)
    gnd=td["gnds"]if mood=="dusk"else td["gnd"]
    draw.rectangle([0,int(S*.64),S,S],fill=gnd)
    if mood!="dusk":
        for i in range(4):
            cx2=(50+i*int(S/4)+int(3*math.sin(frame*.015+i*1.2)))%S
            cy2=int(S*.12)+i%2*int(S*.06)
            for dx in[-16,0,16]:
                draw.ellipse([cx2+dx-14,cy2-12,cx2+dx+14,cy2+12],fill=P.WHITE)
    tx,ty=int(S*.83),int(S*.64)
    draw.rectangle([tx-8,ty-int(S*.22),tx+8,ty],fill=P.TREE_T)
    draw.ellipse([tx-int(S*.09),ty-int(S*.32),tx+int(S*.09),ty-int(S*.16)],fill=P.TREE_L)
    if decor in("maison","danger"):
        wc=td.get("wall",P.WHITE); mx,my=28,int(S*.62); mw,mh=int(S*.30),int(S*.22)
        draw.rectangle([mx,my-mh,mx+mw,my],fill=wc,outline=P.OUTLINE,width=2)
        draw.polygon([mx-10,my-mh,mx+mw//2,my-mh-int(S*.10),mx+mw+10,my-mh],fill=P.ROOF,outline=P.OUTLINE,width=2)
        draw.rectangle([mx+mw//2-15,my-int(S*.10),mx+mw//2+15,my],fill=P.DOOR,outline=P.OUTLINE,width=2)
        wl=(255,255,180)if mood=="dusk"else P.WINDOW
        for wx2 in[mx+8,mx+mw-38]:
            draw.rectangle([wx2,my-int(S*.17),wx2+30,my-int(S*.10)],fill=wl,outline=P.OUTLINE,width=2)
        fx=td["fx"]
        if mood=="dusk":
            for fi in range(5):
                fh=28+int(16*math.sin(frame*.22+fi*.8)); fx2=mx+10+fi*int(mw/5)
                draw.ellipse([fx2-8,my-mh-fh,fx2+8,my-mh],fill=fx)
                draw.ellipse([fx2-4,my-mh-fh-8,fx2+4,my-mh-6],fill=P.FLAME_C)
    if decor=="danger":
        fx=td["fx"]
        for i in range(6):
            angle=math.radians(i*60+frame*3)
            ex=int(S*.5)+int(80*math.cos(angle)); ey=int(S*.45)+int(50*math.sin(angle))
            r=6+int(4*math.sin(frame*.18+i))
            draw.ellipse([ex-r,ey-r,ex+r,ey+r],fill=fx)

def anim_off(action,frame):
    if action in("saute_joie","saute_promesse","salue_saute","fait_betise_saute"):
        return 0,-abs(int(30*math.sin(frame*.16)))
    if action=="saute_peur": return int(4*math.sin(frame*.45)),-abs(int(18*math.sin(frame*.32)))
    if action in("court_vite","marche_content","court_panique"):
        return int(5*math.sin(frame*.12)),int(5*math.sin(frame*.22))
    if action=="pleure_assise": return 0,int(Cfg.SIZE*.04)
    return 0,int(3*math.sin(frame*.07))

def draw_char(draw,cx,cy,action,emotion,frame,genre,hero="Par défaut",is_narrating=True):
    S=int(Cfg.SIZE * 0.60); dx,dy=anim_off(action,frame); x,y=cx+dx,cy+dy
    shirt=P.SHIRT_G if genre=="fille" else P.SHIRT_B
    hair=P.HAIR_G if genre=="fille" else P.HAIR_B
    eye_c=P.EYE_G if genre=="fille" else P.EYE_B
    pants=P.PANTS
    shoe=P.SHOE
    skin=P.SKIN
    
    # -- GESTION DES HÉROS SPÉCIFIQUES --
    h = str(hero).lower()
    if "spider" in h:
        shirt=(220,30,30); pants=(40,60,180); shoe=(220,30,30); hair=(220,30,30); skin=(220,30,30)
    elif "super" in h:
        shirt=(40,60,200); pants=(220,30,30); hair=(20,20,20)
    elif "masha" in h:
        shirt=(200,50,150); pants=(200,50,150); hair=(200,50,150)
    elif "dora" in h:
        shirt=(240,100,180); pants=(250,140,40); hair=(60,30,10)
    elif "elsa" in h or "neige" in h:
        shirt=(120,220,255); pants=(120,220,255); hair=(255,250,210)
    elif "batman" in h:
        shirt=(50,50,50); pants=(30,30,30); shoe=(20,20,20); hair=(30,30,30)
    elif "jerry" in h:
        skin=(140,90,50); shirt=(140,90,50); pants=(140,90,50); hair=(140,90,50)
    elif "tom" in h:
        skin=(120,130,150); shirt=(120,130,150); pants=(120,130,150); hair=(120,130,150)

    draw.ellipse([cx-int(S*.06),cy+int(S*.015),cx+int(S*.06),cy+int(S*.03)],fill=(30,30,30))
    if emotion=="triste": shirt=lc(shirt,(130,130,160),.4)
    elif emotion=="effraye": shirt=lc(shirt,(180,180,190),.35)
    draw.ellipse([x-int(S*.05),y-int(S*.04),x+int(S*.05),y+int(S*.075)],fill=shirt,outline=P.OUTLINE,width=2)
    if action=="pleure_assise":
        draw.ellipse([x-int(S*.06),y+int(S*.07),x+int(S*.01),y+int(S*.13)],fill=pants,outline=P.OUTLINE,width=2)
        draw.ellipse([x+int(S*.01),y+int(S*.07),x+int(S*.06),y+int(S*.13)],fill=pants,outline=P.OUTLINE,width=2)
    else:
        sw=int(20*math.sin(frame*.2))if action in("court_vite","marche_content","court_panique")else 3
        draw.line([x-int(S*.02),y+int(S*.065),x-int(S*.03)-sw,y+int(S*.12)],fill=pants,width=int(S*.022))
        draw.line([x+int(S*.02),y+int(S*.065),x+int(S*.03)+sw,y+int(S*.12)],fill=pants,width=int(S*.022))
        draw.ellipse([x-int(S*.05)-sw,y+int(S*.11),x-int(S*.01)-sw,y+int(S*.135)],fill=shoe,outline=P.OUTLINE,width=2)
        draw.ellipse([x+int(S*.01)+sw,y+int(S*.11),x+int(S*.05)+sw,y+int(S*.135)],fill=shoe,outline=P.OUTLINE,width=2)
    
    def arm(x1,y1,x2,y2):
        draw.line([x1,y1,x2,y2],fill=skin,width=int(S*.018))
        draw.ellipse([x2-5,y2-5,x2+5,y2+5],fill=skin,outline=P.OUTLINE,width=1)
    sw2=int(22*math.sin(frame*.18))
    if action=="saute_joie":
        arm(x-int(S*.046),y-int(S*.008),x-int(S*.084),y-int(S*.078))
        arm(x+int(S*.046),y-int(S*.008),x+int(S*.084),y-int(S*.078))
    elif action in("court_vite","marche_content","court_panique"):
        arm(x-int(S*.046),y,x-int(S*.07)+sw2,y+int(S*.022))
        arm(x+int(S*.046),y,x+int(S*.07)-sw2,y+int(S*.022))
    elif action=="appelle_gestes":
        gh=int(30*math.sin(frame*.16))
        arm(x-int(S*.046),y,x-int(S*.09),y-int(S*.062)-gh)
        arm(x+int(S*.046),y,x+int(S*.09),y-int(S*.062)+gh)
    elif action=="saute_peur":
        t2=int(6*math.sin(frame*.45))
        arm(x-int(S*.046),y+t2,x-int(S*.075),y-int(S*.05)+t2)
        arm(x+int(S*.046),y-t2,x+int(S*.075),y-int(S*.05)-t2)
    elif action=="pointe_enfant":
        arm(x-int(S*.046),y,x-int(S*.06),y+int(S*.022))
        draw.line([x+int(S*.046),y,x+int(S*.1),y-int(S*.02)],fill=skin,width=int(S*.018))
        draw.ellipse([x+int(S*.094),y-int(S*.035),x+int(S*.116),y-int(S*.013)],fill=skin,outline=P.OUTLINE,width=1)
    elif action in("saute_promesse","salue_saute"):
        arm(x-int(S*.046),y,x-int(S*.06),y+int(S*.025))
        arm(x+int(S*.046),y,x+int(S*.08),y-int(S*.086))
    elif action=="fait_betise_saute":
        arm(x-int(S*.046),y,x-int(S*.07),y-int(S*.03))
        arm(x+int(S*.046),y,x+int(S*.086),y-int(S*.04))
    elif action=="pleure_assise":
        arm(x-int(S*.046),y+int(S*.034),x-int(S*.025),y+int(S*.066))
        arm(x+int(S*.046),y+int(S*.034),x+int(S*.025),y+int(S*.066))
    elif action=="decouvre_surpris":
        arm(x+int(S*.046),y,x+int(S*.084),y+int(S*.005))
        arm(x-int(S*.046),y,x-int(S*.06),y+int(S*.025))
    else:
        arm(x-int(S*.046),y,x-int(S*.062),y+int(S*.022))
        arm(x+int(S*.046),y,x+int(S*.062),y+int(S*.022))
    hy=y-int(S*.13)
    draw.ellipse([x-int(S*.066),hy,x+int(S*.066),hy+int(S*.136)],fill=skin,outline=P.OUTLINE,width=2)
    draw.arc([x-int(S*.064),hy,x+int(S*.064),hy+int(S*.07)],180,0,fill=hair,width=10)
    if genre=="fille":
        draw.rectangle([x-int(S*.07),hy+int(S*.012),x-int(S*.042),hy+int(S*.094)],fill=hair)
        draw.rectangle([x+int(S*.042),hy+int(S*.012),x+int(S*.07),hy+int(S*.094)],fill=hair)
    ey=hy+int(S*.054); ew,eh=14,12
    if emotion in("surpris","effraye"): eh=16
    elif emotion in("heureux","fier"): eh=10
    cligne=(frame%75)<3
    for side in(-1,1):
        ox=x+side*int(S*.034)
        if cligne:
            draw.arc([ox-ew,ey-3,ox+ew,ey+5],0,180,fill=P.OUTLINE,width=2)
        else:
            draw.ellipse([ox-ew,ey-eh,ox+ew,ey+eh],fill=P.WHITE,outline=P.OUTLINE,width=2)
            draw.ellipse([ox-6,ey-5,ox+6,ey+5],fill=eye_c)
            draw.ellipse([ox-4,ey-3,ox+4,ey+3],fill=(8,8,18))
            draw.ellipse([ox-10,ey-8,ox-3,ey-2],fill=P.WHITE)
    draw.ellipse([x-int(S*.076),ey+5,x-int(S*.044),ey+20],fill=P.CHEEK)
    draw.ellipse([x+int(S*.044),ey+5,x+int(S*.076),ey+20],fill=P.CHEEK)
    my2=hy+int(S*.096)
    is_talking = is_narrating and ((frame % 20) < 10)
    mouth_h = 4 + int(6 * abs(math.sin(frame * 0.5))) if is_talking else 2
    if is_talking: draw.ellipse([x-4, my2-2, x+4, my2+mouth_h], fill=(80,10,10))
    elif emotion in("heureux","fier","determine"): draw.arc([x-10,my2-5,x+10,my2+8],0,180,fill=(185,65,65),width=3)
    elif emotion in("triste","desole"): draw.arc([x-10,my2+5,x+10,my2+14],180,0,fill=(178,65,65),width=3)
    elif emotion in("surpris","effraye"): draw.ellipse([x-9,my2-2,x+9,my2+14],fill=(135,48,48))
    else: draw.line([x-7,my2+6,x+7,my2+6],fill=(168,68,68),width=2)
    if emotion=="triste":
        for s2 in(-1,1):
            lx=x+s2*int(S*.056); ly=ey+int(S*.025)+int(5*math.sin(frame*.22+s2))
            draw.polygon([lx-4,ly,lx+4,ly,lx,ly+14],fill=P.TEAR)
    if action in("court_vite","court_panique"):
        for li in range(4):
            lx2=x-int(S*.12)-li*10; ly2=y+li*6
            draw.line([lx2,ly2,lx2+int(S*.044),ly2],fill=(160,165,190),width=2)

_FONTS=None
def get_fonts():
    global _FONTS
    if _FONTS: return _FONTS
    S=Cfg.SIZE
    try:
        _FONTS={"big":ImageFont.truetype(Cfg.FONT_B,max(16,S//20)),
                "med":ImageFont.truetype(Cfg.FONT_B,max(13,S//28)),
                "small":ImageFont.truetype(Cfg.FONT_R,max(12,S//32))}
    except:
        d=ImageFont.load_default(); _FONTS={"big":d,"med":d,"small":d}
    return _FONTS



def wrap_text(text: str, max_chars: int) -> list:
    """Coupe le texte en lignes de max_chars caractères."""
    words = text.split()
    lines, cur = [], ""
    for w in words:
        if len(cur) + len(w) + 1 <= max_chars:
            cur = (cur + " " + w).strip()
        else:
            if cur: lines.append(cur)
            cur = w
    if cur: lines.append(cur)
    return lines


def draw_ui(img, scene, f_in, song, genre):
    draw = ImageDraw.Draw(img)
    F = get_fonts()
    S = Cfg.SIZE

    # ════════════════════════════════
    # BARRE HAUTE — fond blanc semi-transparent
    # ════════════════════════════════
    top_h = 58
    ov = Image.new("RGBA", (S, top_h), (0, 0, 0, 0))
    d2 = ImageDraw.Draw(ov)
    for yy in range(top_h):
        alpha = int(200 * (1 - yy / top_h) ** 0.6)
        d2.line([(0, yy), (S, yy)], fill=(255, 255, 255, alpha))
    img.paste(Image.alpha_composite(
        img.crop((0, 0, S, top_h)).convert("RGBA"), ov), (0, 0))
    draw = ImageDraw.Draw(img)

    # Acte label retiré pour un affichage plus propre. Titre scène recentré.
    # Titre scène — gauche, gras (centré verticalement dans la barre)
    draw.text((10, 16), scene.titre[:32], fill=(20, 20, 60), font=F["med"])

    # 📍 Lieu — droite, fond pill arrondi généré par l'IA
    lieu_raw = scene.lieu_texte
    if isinstance(lieu_raw, list):
        lieu_raw = lieu_raw[0] if lieu_raw else "Inconnu"
    lieu = str(lieu_raw) if lieu_raw else "Inconnu"
    import re
    # Supprime tous les émojis et caractères non-textuels pour éviter le bug d'affichage PIL
    lieu = re.sub(r'[^\w\s.,\'!-]', '', lieu, flags=re.UNICODE).strip()
    try:
        lw = draw.textlength(lieu, font=F["small"])
    except:
        lw = len(lieu) * 7
    lx = S - int(lw) - 18
    draw.rounded_rectangle([lx - 6, 6, S - 8, 26], radius=8, fill=(240, 220, 255))
    draw.text((lx, 8), lieu, fill=(80, 30, 160), font=F["small"])

    # ════════════════════════════════
    # BARRE BASSE — fond noir cinématique
    # ════════════════════════════════
    bot_h = int(S * 0.33)
    ov2 = Image.new("RGBA", (S, bot_h), (0, 0, 0, 0))
    d3 = ImageDraw.Draw(ov2)
    for yy in range(bot_h):
        # fondu progressif du transparent vers noir opaque
        t = (yy / bot_h) ** 0.5
        alpha = int(230 * t)
        d3.line([(0, yy), (S, yy)], fill=(8, 5, 30, alpha))
    img.paste(Image.alpha_composite(
        img.crop((0, S - bot_h, S, S)).convert("RGBA"), ov2), (0, S - bot_h))
    draw = ImageDraw.Draw(img)

    y0 = S - bot_h + 6

    # ✨ L'émotion IA du personnage principal — italique violet clair
    # L'IA génère maintenant toute la phrase (ex: "Humeur de Spiderman : joyeux")
    petit_texte = f"* {scene.emotion_text}"
    draw.text((12, y0), petit_texte, fill=(180, 155, 255), font=F["small"])
    y0 += 20

    # Ligne séparatrice
    draw.line([(12, y0), (S - 12, y0)], fill=(80, 60, 160), width=1)
    y0 += 7

    # 💬 Narration IA — grand texte blanc cassé, multi-lignes
    narr = scene.dialogue
    # Retire le préfixe [Dans...] si présent dans le texte
    if narr.startswith("["):
        end_bracket = narr.find("]")
        if end_bracket != -1:
            narr = narr[end_bracket + 1:].strip()
    
    # Garder la largeur à 36 pour que le texte n'écrase pas le personnage animé Python superposé à droite
    lines = wrap_text(narr, 36)[:4]
    for i, line in enumerate(lines):
        # Première ligne un peu plus grande
        font = F["med"] if i == 0 else F["small"]
        color = (255, 252, 220) if i == 0 else (210, 200, 240)
        draw.text((12, y0), line, fill=color, font=font)
        y0 += 22 if i == 0 else 18

    # Barre de progression — tout en bas
    prog = f_in / max(1, scene.duree)
    draw.rounded_rectangle([10, S - 9, S - 10, S - 3], radius=3, fill=(40, 30, 90))
    fw = int((S - 20) * prog) + 10
    if fw > 20:
        draw.rounded_rectangle([10, S - 9, fw, S - 3], radius=3, fill=P.UI_BAR)

def easing(t): return 3*t**2-2*t**3
def blend(f1,f2,t): return np.clip(f1*(1-t)+f2*t,0,255).astype(np.uint8)

def render_scene(scene, genre, song, gframe, td):
    frames = []
    S = Cfg.SIZE
    # Le personnage se tient en bas à droite au premier plan
    char_x = int(S * 0.85)
    char_y = int(S * 0.84)
    for f in range(scene.duree):
        img = Image.new("RGBA", (S, S))
        draw = ImageDraw.Draw(img)
        # 1. Image de fond générée si disponible, sinon repli
        if getattr(scene, "bg_img", None) is not None:
            img.paste(scene.bg_img, (0, 0))
        else:
            draw_bg(draw, scene.decor, scene.sky_mood, gframe + f, td)
        
        # 2. Barre d'interface texte
        draw_ui(img, scene, f, song, genre)

        # 3. Personnage au premier plan (par dessus l'image et l'interface)
        # La narration audio a ~500ms de silence à la fin, soit environ 12 frames
        is_narrating_now = f < (scene.duree - 12)
        draw_char(draw, char_x, char_y, scene.action, scene.emotion, gframe + f, genre, hero="Par défaut", is_narrating=is_narrating_now)
        
        frames.append(cv2.cvtColor(np.array(img.convert("RGB")), cv2.COLOR_RGB2BGR))
    return frames

def render_all(scenes, genre, song, td, pb):
    all_f = []; gf = 0; EF = Cfg.EF; total = len(scenes)
    for i, scene in enumerate(scenes):
        pb.progress((i+1)/total, text=f"🎨 Scène {i+1}/{total} — {scene.titre}")
        sf = render_scene(scene, genre, song, gf, td)
        if all_f and EF > 0:
            prev = all_f[-EF:]; nxt = sf[:EF]
            bl = [blend(prev[j], nxt[j], easing(j/EF)) for j in range(min(EF,len(prev),len(nxt)))]
            all_f[-len(bl):] = bl
        all_f.extend(sf); gf += scene.duree
    pb.progress(1.0, text="✅ Rendu terminé!")
    return all_f

async def _edge_gen(text,voice,rate,pitch,out):
    comm=edge_tts.Communicate(text=text,voice=voice,rate=rate,pitch=pitch)
    await comm.save(out)

def gen_audio(char, narrations, theme_name, folder, ph) -> tuple:
    voice=Cfg.VF if char.genre=="fille" else Cfg.VG
    vrate=Cfg.VRATE
    vpitch=Cfg.VPITCH
    
    chosen_narr = st.session_state.get("narrator", "Par défaut")
    if "Femme" in chosen_narr:
        voice = "fr-FR-DeniseNeural"
    elif "Homme" in chosen_narr:
        voice = "fr-FR-HenriNeural"
        vpitch = "-5Hz"
    elif "Fille" in chosen_narr:
        voice = "fr-FR-EloiseNeural"
        vpitch = "+15Hz"
    elif "Garçon" in chosen_narr:
        voice = "fr-FR-HenriNeural"
        vpitch = "+35Hz"
        
    from pydub import AudioSegment
    import os, time
    
    combined_voix = AudioSegment.silent(duration=0)
    durees_frames = []
    vp=os.path.join(folder,"voix.mp3")
    
    ph.info("🎙️ Génération voix et synchro scène par scène...")
    for idx, text in enumerate(narrations):
        # Nettoyer texte des préfixes
        if "]" in text: text = text.split("]", 1)[-1].strip()
        if ":" in text: text = text.split(":", 1)[-1].strip()
        
        part_path = os.path.join(folder, f"part_{idx}.mp3")
        ok = False
        if _EDGE_TTS_OK:
            try:
                import edge_tts, asyncio
                asyncio.run(_edge_gen(text,voice,vrate,vpitch,part_path))
                ok = True
            except: pass
        if not ok:
            from gtts import gTTS
            gTTS(text=text,lang="fr",slow=False).save(part_path)
            
        seg = AudioSegment.from_file(part_path)
        # 500ms pause
        seg = seg + AudioSegment.silent(duration=500)
        combined_voix += seg
        
        dframes = int((len(seg) / 1000.0) * Cfg.FPS)
        durees_frames.append(dframes)
        
    combined_voix.export(vp, format="mp3")
    
    try:
        ph.info("🎵 Mixage de l'ambiance musicale adaptée...")
        import urllib.request, hashlib
        seed_str = f"{char.hero}_{theme_name}"
        music_id = int(hashlib.md5(seed_str.encode()).hexdigest(), 16) % 17 + 1
        bgm_url = f"https://www.soundhelix.com/examples/mp3/SoundHelix-Song-{music_id}.mp3"
        bgm_path = os.path.join(folder, "bgm.mp3")
        req = urllib.request.Request(bgm_url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=15) as resp, open(bgm_path, 'wb') as f:
            f.write(resp.read())
            
        music_audio = AudioSegment.from_file(bgm_path) - 15
        while len(music_audio) < len(combined_voix): music_audio += music_audio
        music_audio = music_audio[:len(combined_voix)]
        mix = combined_voix.overlay(music_audio)
        vp_mix = os.path.join(folder, "voix_mix.mp3")
        mix.export(vp_mix, format="mp3")
        return vp_mix, durees_frames
    except Exception as e:
        return vp, durees_frames

def encode_video(frames,audio,folder,prenom)->str:
    silent=os.path.join(folder,"_s.mp4"); final=os.path.join(folder,f"ANIME_{prenom.upper()}.mp4")
    h,w=frames[0].shape[:2]
    wr=cv2.VideoWriter(silent,cv2.VideoWriter_fourcc(*"mp4v"),Cfg.FPS,(w,h))
    for fr in frames: wr.write(fr)
    wr.release()
    subprocess.run(["ffmpeg","-y","-i",silent,"-i",audio,"-c:v","libx264","-preset","fast",
        "-crf",str(Cfg.CRF),"-c:a","aac","-b:a","128k","-movflags","+faststart","-shortest",final],
        capture_output=True,text=True)
    if os.path.exists(silent): os.remove(silent)
    return final

# ─────────────────────────────────────────
#  CSS PROFESSIONNEL
# ─────────────────────────────────────────
CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=Outfit:wght@500;700;800&display=swap');

html,body,.stApp,[data-testid="stAppViewContainer"]{
    background:#ffffff!important;
    font-family:'Inter',system-ui,sans-serif;
}
[data-testid="stHeader"]{background:transparent!important;}
[data-testid="stSidebar"]{background:#ffffff!important;border-right:1px solid #f0f0f0;padding-top:2rem;}
.block-container{background:transparent!important;padding-top:2rem!important;max-width:840px!important;}

/* Typography */
h1,h2,h3{color:#0f172a!important;font-family:'Outfit',sans-serif; letter-spacing:-0.02em;}
p,div,label{font-family:'Inter',sans-serif;}
.material-icons, .material-symbols-rounded, .material-symbols-outlined, i[class*="icon"], span[class*="icon"], span[class*="material"], span[class*="stIcon"] {
    font-family: "Material Symbols Rounded", "Material Icons" !important;
}
:not(.ds-bubble-user):not(.ds-bubble-user *):not(.ds-bubble-ai):not(.ds-bubble-ai *) {
    color: inherit;
}
.block-container p, .block-container label,
.block-container span:not(.ds-time),
.stMarkdown p { color:#334155; }

/* Hero — Retour de la couleur vibrante pour ancrer le design ! */
.hero{
    background:linear-gradient(135deg, #4f46e5 0%, #db2777 100%);
    border: none;
    border-radius:24px;
    padding:2.5rem 2rem;
    text-align:center;
    margin-bottom:2.5rem;
    box-shadow: 0 10px 30px rgba(79, 70, 229, 0.25);
}
.hero h1{
    color:#ffffff!important;
    font-size:2.4rem;
    font-weight:800;
    margin:0 0 10px!important;
    background: none;
    -webkit-background-clip: initial;
    -webkit-text-fill-color: initial;
}
.hero p{
    color:rgba(255,255,255,0.9)!important;
    font-size:1.05rem;
    font-weight: 500;
    margin:0!important;
}

/* Cards */
.card{
    background:#ffffff;
    border:1px solid rgba(255,255,255,0.8);
    border-radius:20px;
    padding:1.75rem;
    margin-bottom:1.5rem;
    box-shadow:0 8px 25px rgba(0,0,0,0.06);
    backdrop-filter: blur(10px);
}

/* Step indicator - Soft styling */
.steps-row{display:flex;align-items:center;justify-content:center;
    gap:0;margin-bottom:2.5rem;}
.step-dot{width:42px;height:42px;border-radius:50%;display:flex;
    align-items:center;justify-content:center;font-weight:800;font-size:14px;
    border:2px solid #e2e8f0;background:#ffffff;color:#94a3b8;z-index:1;
    transition: all 0.3s ease;}
.step-dot.active{background:#4f46e5;border-color:#4f46e5;color:#ffffff;
    box-shadow:0 0 0 6px rgba(79,70,229,.12); transform:scale(1.1);}
.step-dot.done{background:#10b981;border-color:#10b981;color:#ffffff;}
.step-line{width:70px;height:3px;background:#e2e8f0;margin-bottom:22px; transition: all 0.3s ease;}
.step-line.done{background:#10b981;}
.step-lbl{font-size:11px;font-weight:700;width:80px;text-align:center;
    color:#94a3b8!important;margin-top:6px; letter-spacing:0.04em; text-transform:uppercase;}
.step-lbl.active{color:#4f46e5!important;}
.step-lbl.done{color:#10b981!important;}
.step-col{display:flex;flex-direction:column;align-items:center;}

/* ══════════════════════════════════════
   CHAT DEEPSEEK — Design épuré
   ══════════════════════════════════════ */
[data-testid="stMarkdownContainer"],
[data-testid="stMarkdownContainer"] > div { width: 100% !important; }

/* — Bulle IA (gauche) — */
.ds-msg-ai {
    display: flex; align-items: flex-start; gap: 12px; margin: 12px 0;
}
.ds-avatar-ai {
    width: 34px; height: 34px; border-radius: 50%; flex-shrink: 0;
    background: linear-gradient(135deg, #6366f1, #8b5cf6);
    display: flex; align-items: center; justify-content: center;
    font-size: 1rem; margin-top: 2px; color: white;
    box-shadow: 0 4px 10px rgba(99,102,241,0.25);
}
.ds-bubble-ai {
    background: #ffffff;
    border: 1px solid #f1f5f9;
    border-radius: 4px 20px 20px 20px;
    padding: 12px 18px;
    font-size: 0.94rem; line-height: 1.6;
    max-width: 88%; word-break: break-word;
    box-shadow: 0 8px 24px rgba(149,157,165,0.06);
}
.ds-bubble-ai, .ds-bubble-ai * { color: #334155 !important; }

/* — Bulle Parent (droite) — */
.ds-user-wrap {
    display: flex; flex-direction: column; align-items: flex-end; width: 100%;
    margin: 12px 0;
}
.ds-bubble-user {
    background: linear-gradient(135deg,#3b82f6,#4f46e5) !important;
    border-radius: 20px 4px 20px 20px !important;
    padding: 12px 18px !important;
    font-size: 0.94rem !important; line-height: 1.6 !important;
    max-width: 90% !important;
    box-shadow: 0 8px 24px rgba(79,70,229,0.15) !important;
    word-break: break-word !important; display: inline-block !important;
}
.ds-bubble-user, .ds-bubble-user * {
    color: #ffffff !important; font-family: 'Inter', sans-serif !important;
}
.ds-time {
    font-size: 0.65rem; opacity: 0.5; margin-top: 6px;
    display: block; color: #94a3b8 !important; font-weight:500;
}
.ds-user-wrap .ds-time { text-align: right; }

/* — Cadre principal du chat — premium style */
[data-testid="stVerticalBlockBorderWrapper"] {
    border: 1px solid #f1f5f9 !important;
    border-radius: 20px !important;
    background: #ffffff !important;
    box-shadow: 0 12px 40px rgba(0,0,0,0.04) !important;
    padding: 0 !important;
    overflow: hidden !important;
}
[data-testid="stVerticalBlockBorderWrapper"] [data-testid="stVerticalBlockBorderWrapper"] {
    border: none !important;
    box-shadow: none !important;
    border-radius: 0 !important;
    background: transparent !important;
}
.chat-frame-inner {
    padding: 20px 24px 10px;
}
.chat-input-wrap {
    background: #f8fafc;
    padding: 14px 20px 16px;
    border-top: 1px solid #f1f5f9;
}

/* En-tête chat — refined */
.chat-section-header {
    display: flex; align-items: center; gap: 14px;
    border-bottom: 1px solid #f1f5f9;
    padding-bottom: 16px; margin-bottom: 8px;
}
.chat-section-header .csh-icon {
    width: 42px; height: 42px; border-radius: 12px;
    background: #eef2ff;
    color: #4f46e5;
    display: flex; align-items: center; justify-content: center;
    font-size: 1.3rem; flex-shrink: 0;
}
.chat-section-header .csh-title {
    font-size: 1.05rem; font-weight: 800; font-family:'Outfit',sans-serif; color: #0f172a !important; margin: 0 !important;
}
.chat-section-header .csh-sub {
    font-size: 0.8rem; color: #64748b !important; margin-top: 2px;
}

/* Sidebar */
.sb-title{font-family:'Outfit',sans-serif; font-size:1.1rem;font-weight:700;color:#0f172a;margin-bottom:1rem;
    display:flex;align-items:center;gap:8px;}
.sb-step{font-size:.82rem;color:#475569;padding:6px 0;display:flex;
    align-items:flex-start;gap:8px; border-bottom: 1px solid #f1f5f9;}

/* Buttons — Beautiful and tactile */
.stButton>button{
    border-radius:99px!important;
    font-weight:600!important;
    font-size:.9rem!important;
    padding: 0.4rem 1rem!important;
    transition:all .25s cubic-bezier(0.4, 0, 0.2, 1)!important;
    background:#ffffff!important;
    border:1px solid #cbd5e1!important;
    color:#475569!important;
    box-shadow: 0 2px 4px rgba(0,0,0,0.02)!important;
}
.stButton>button:hover{
    background:#f8fafc!important;
    border-color:#94a3b8!important;
    transform:translateY(-1px)!important;
    box-shadow: 0 4px 6px rgba(0,0,0,0.04)!important;
}
.stButton>button[kind="primary"]{
    background:linear-gradient(135deg,#4f46e5,#7c3aed)!important;
    color:#ffffff!important;border:none!important;
    box-shadow:0 6px 15px rgba(79,70,229,.25)!important;
}
.stButton>button[kind="primary"]:hover{
    transform:translateY(-3px)!important;
    box-shadow:0 10px 25px rgba(79,70,229,.4)!important;
}

/* Inputs — Pill shapes and soft focus */
.stTextArea>div>div>textarea,.stTextInput>div>div>input, .stSelectbox>div>div>div {
    background:#ffffff!important;
    border:1.5px solid #e2e8f0!important;
    border-radius:14px!important;
    font-size:.95rem!important;
    color:#1e293b!important;
    transition: all 0.2s ease!important;
    box-shadow: 0 1px 2px rgba(0,0,0,0.01)!important;
}
.stTextArea>div>div>textarea:focus,.stTextInput>div>div>input:focus, .stSelectbox>div>div>div:focus-within{
    border-color:#4f46e5!important;
    box-shadow:0 0 0 4px rgba(79,70,229,.1)!important;
}

/* Progress */
.stProgress>div>div>div{
    background:linear-gradient(90deg,#4f46e5,#db2777)!important;
    border-radius: 99px!important;
}
.stProgress>div>div {
    border-radius: 99px!important;
    background:#f1f5f9!important;
}

/* Misc */
hr{border-color:#f1f5f9!important;}
.stAlert{border-radius:16px!important; border:none!important;}
[data-testid="stExpander"]{
    background: #ffffff!important;
    border-radius: 16px!important;
    border: 1px solid #f1f5f9!important;
    box-shadow: 0 4px 12px rgba(0,0,0,0.02)!important;
}
#MainMenu,footer{visibility:hidden;}
</style>
"""

# ─────────────────────────────────────────
#  HELPERS UI
# ─────────────────────────────────────────
def stepper(cur:int)->str:
    labels=["La bêtise","Scénario","Vidéo"]
    icons=["<span class='material-symbols-rounded' style='font-size:18px;'>edit_document</span>",
           "<span class='material-symbols-rounded' style='font-size:18px;'>movie</span>",
           "<span class='material-symbols-rounded' style='font-size:18px;'>celebration</span>"]
    parts=[]
    for i in range(1,4):
        if i<cur:     dc,lc2,nt="done","done","<span class='material-symbols-rounded' style='font-size:18px;'>check</span>"
        elif i==cur:  dc,lc2,nt="active","active",icons[i-1]
        else:         dc,lc2,nt="","",str(i)
        parts.append(f'<div class="step-col"><div class="step-dot {dc}">{nt}</div>'
                     f'<div class="step-lbl {lc2}">{labels[i-1]}</div></div>')
        if i<3:
            ld="done"if i<cur else ""
            parts.append(f'<div class="step-line {ld}"></div>')
    return f'<div class="steps-row">{".".join(parts)}</div>'


# ─────────────────────────────────────────
#  MAIN
# ─────────────────────────────────────────
def main():
    st.set_page_config(page_title="Studio Animé Éducatif",page_icon="🎬",
                       layout="centered",initial_sidebar_state="expanded")
    st.markdown(CSS,unsafe_allow_html=True)

    # ── SESSION ──
    defaults={"step":1,"api_key":"","betise":"","val":None,
              "scenario":None,"char":None,"song":None,"narrations":[],"img_prompts":[],
              "theme":"general","analyzing":False,"show_key":False,
              "confirmed_yes":False,"confirmed_no":False,
              "chat_history":[],"editing_index":None,"editing_content":""}
    for k,v in defaults.items():
        if k not in st.session_state: st.session_state[k]=v

    # ══════════════════════════════════════
    #  SIDEBAR
    # ══════════════════════════════════════
    with st.sidebar:
        # — Clé API —
        st.markdown(
            "<div style='background:linear-gradient(135deg,#f5f3ff,#ede9fe);"
            "border:1px solid #c4b5fd;border-radius:12px;padding:10px 14px;"
            "margin-bottom:12px;display:flex;align-items:center;gap:8px;'>"
            "<span class='material-symbols-rounded' style='color:#7c3aed;font-size:1.2rem;'>key</span>"
            "<span style='font-size:0.95rem;font-weight:700;color:#1e293b;'>Clé API Groq</span>"
            "</div>",
            unsafe_allow_html=True
        )
        key = st.text_input("Clé", value=st.session_state.api_key, type="password",
            placeholder="gsk_...", label_visibility="collapsed")
        st.session_state.api_key = key
        valid_key = bool(key and key.strip().startswith("gsk_"))
        if valid_key: st.success("Clé valide", icon=":material/check_circle:")
        else: st.warning("Clé manquante", icon=":material/warning:")

        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown(
            "<div style='background:linear-gradient(135deg,#ecfdf5,#d1fae5);"
            "border:1px solid #6ee7b7;border-radius:12px;padding:10px 14px;"
            "margin-bottom:12px;display:flex;align-items:center;gap:8px;'>"
            "<span class='material-symbols-rounded' style='color:#059669;font-size:1.2rem;'>info</span>"
            "<span style='font-size:0.95rem;font-weight:700;color:#1e293b;'>Comment ça marche ?</span>"
            "</div>",
            unsafe_allow_html=True
        )
        for ic, txt in [
            ("<span class='material-symbols-rounded' style='font-size:1.1rem;vertical-align:middle;color:#7c3aed;'>looks_one</span>","<b>Racontez</b> la bêtise de l'enfant dans le chat"),
            ("<span class='material-symbols-rounded' style='font-size:1.1rem;vertical-align:middle;color:#7c3aed;'>looks_two</span>","<b>L'IA analyse</b> et propose un scénario"),
            ("<span class='material-symbols-rounded' style='font-size:1.1rem;vertical-align:middle;color:#7c3aed;'>looks_3</span>","<b>Personnalisez</b> (Héros, Musique...)"),
            ("<span class='material-symbols-rounded' style='font-size:1.1rem;vertical-align:middle;color:#7c3aed;'>looks_4</span>","<b>Téléchargez</b> le dessin animé !"),
        ]:
            st.markdown(f'<div class="sb-step">{ic} <span style="line-height:1.5;">{txt}</span></div>', unsafe_allow_html=True)

        if st.session_state.step > 1:
            st.markdown("---")
            if st.button(":material/refresh: Recommencer", use_container_width=True):
                for k in ["step","betise","val","scenario","char","song","narrations","img_prompts","theme","confirmed_yes","confirmed_no","chat_history","editing_index","editing_content"]:
                    st.session_state[k]=1 if k=="step" else "general" if k=="theme" else [] if k in ["narrations","img_prompts","chat_history"] else "" if k=="betise" else False if k in ["confirmed_yes","confirmed_no"] else None
                st.rerun()

    # ── HÉRÔ ──
    st.markdown("""<div class="hero">
        <h1><span class="material-symbols-rounded" style="font-size: 2.2rem; vertical-align: bottom;">movie</span> Studio Animé Éducatif</h1>
        <p>Transforme la bêtise de ton enfant en dessin animé éducatif personnalisé <span class="material-symbols-rounded" style="font-size: 1.1rem; vertical-align: middle;">auto_awesome</span></p>
    </div>""",unsafe_allow_html=True)

    st.markdown(stepper(st.session_state.step),unsafe_allow_html=True)

    # ══════════════════════════════════════
    #  ÉTAPE 1 — CHAT PÉDAGOGIQUE
    # ══════════════════════════════════════
    if st.session_state.step == 1:
        import datetime as _dt
        import html as _html
        import streamlit.components.v1 as _cmp

        def _ts():
            return _dt.datetime.now().strftime("%H:%M")

        def ds_ai_bubble(content, ts=""):
            return (
                '<div class="ds-msg-ai">'
                '<div class="ds-avatar-ai"><span class="material-symbols-rounded" style="color:white;font-size:1.1rem;">smart_toy</span></div>'
                '<div>'
                f'<div class="ds-bubble-ai">{content}</div>'
                + (f'<span class="ds-time">{ts}</span>' if ts else '') +
                '</div></div>'
            )

        # ─ EN-TÊTE (hors cadre) ─
        st.markdown(
            '<div class="chat-section-header">'
            '<div class="csh-icon"><span class="material-symbols-rounded" style="color:white;font-size:1.4rem;">school</span></div>'
            '<div>'
            '<div class="csh-title">Assistant Pédagogique</div>'
            '<div class="csh-sub">Discutez librement · Détection automatique des situations de danger</div>'
            '</div></div>',
            unsafe_allow_html=True
        )

        # ══════════════════════════════════════════════════
        # CADRE DU CHAT (messages + input)
        # ══════════════════════════════════════════════════
        _ei         = st.session_state.get("editing_index", None)
        _input_key  = f"chat_input_{len(st.session_state.chat_history)}"
        send_clicked = False

        with st.container(border=True):

            # — Messages scrollables —
            with st.container(height=280, border=False):
                # — Bienvenue (déplacé dans la zone scrollable) —
                st.markdown(
                    '<div class="chat-frame-inner" style="padding-top:0;">'
                    + ds_ai_bubble(
                        "<b>Bonjour ! 👋 Je suis votre Assistant Pédagogique.</b><br>"
                        "<span style='font-size:0.87rem;'>"
                        "Décrivez le comportement de votre enfant — je comprends la situation "
                        "et je génère automatiquement un dessin animé éducatif ✨</span>"
                    )
                    + '</div>',
                    unsafe_allow_html=True
                )
                
                for i, msg in enumerate(st.session_state.chat_history):
                    txt = _html.escape(msg["content"]).replace("\n", "<br>")
                    ts  = msg.get("ts", "")

                    if msg["role"] == "ai":
                        st.markdown(ds_ai_bubble(txt, ts), unsafe_allow_html=True)
                    else:
                        if _ei == i:
                            # Mode édition inline
                            _, _ez = st.columns([1, 5])
                            with _ez:
                                edited = st.text_area(
                                    "Modifier",
                                    value=st.session_state.editing_content,
                                    height=80, label_visibility="collapsed",
                                    key=f"inline_edit_{i}"
                                )
                                st.session_state.editing_content = edited
                                _ca, _cc = st.columns([1, 1])
                                with _cc:
                                    if st.button("✓ Confirmer", key=f"confirm_{i}",
                                                 type="primary", use_container_width=True):
                                        new_txt = st.session_state.editing_content.strip()
                                        if new_txt:
                                            st.session_state.chat_history[i]["content"] = new_txt
                                            st.session_state.chat_history = \
                                                st.session_state.chat_history[:i+1]
                                            st.session_state.editing_index = None
                                            st.session_state.editing_content = ""
                                            st.session_state.val = None
                                            st.session_state.betise = new_txt
                                            with st.spinner("🤖 Analyse en cours…"):
                                                import time; time.sleep(1)
                                                try:
                                                    res = chat_ai(new_txt, st.session_state.api_key, st.session_state.val)
                                                    reply = res.get("response", "Bien reçu !")
                                                    st.session_state.chat_history.append({"role":"ai","content":reply,"ts":_ts()})
                                                    st.session_state.val = res if res.get("type")=="scenario" else None
                                                    if res.get("theme") in THEMES:
                                                        st.session_state.theme = res["theme"]
                                                except Exception as e:
                                                    st.error(f"Erreur : {e}")
                                            st.rerun()
                                with _ca:
                                    if st.button("✕ Annuler", key=f"cancel_{i}",
                                                 use_container_width=True):
                                        st.session_state.editing_index = None
                                        st.session_state.editing_content = ""
                                        st.rerun()
                        else:
                            # Bulle parent à droite
                            _, _bc = st.columns([2, 5])
                            with _bc:
                                st.markdown(
                                    f'<div class="ds-user-wrap">'
                                    f'<div class="ds-bubble-user">{txt}</div>'
                                    + (f'<span class="ds-time">{ts}</span>' if ts else '') +
                                    '</div>',
                                    unsafe_allow_html=True
                                )
                            _, _mc = st.columns([5, 2])
                            with _mc:
                                if st.button("✏️", key=f"mod_{i}",
                                             help="Modifier ce message"):
                                    st.session_state.editing_index = i
                                    st.session_state.editing_content = msg["content"]
                                    st.rerun()

                # — Enrichissements Actionnables (Minimaliste Pro) —
                _lv = st.session_state.val
                if _lv and _lv.get("type") == "scenario" and _lv.get("valide"):
                    _sugg = _lv.get("suggestions", [])
                    if _sugg:
                        st.markdown(
                            "<div style='margin: 4px 0 6px 45px;'>"
                            "<span style='font-size:0.68rem; font-weight:700; color:#4f46e5; text-transform:uppercase; letter-spacing:0.06em;'>"
                            "↳ Suggestions rapides"
                            "</span>"
                            "</div>",
                            unsafe_allow_html=True
                        )
                        _jc, _kc = st.columns([0.9, 10])
                        with _kc:
                            _sugg_to_show = _sugg[:3]
                            for _sid, _s in enumerate(_sugg_to_show):
                                if st.button(_s, key=f"enrich_{_sid}",
                                             use_container_width=True):
                                        import html as _html
                                        _s_clean = _html.unescape(_s)
                                        # Seulement afficher la suggestion propre dans la petite bulle (pas tout l'historique)
                                        st.session_state.chat_history.append(
                                            {"role": "user", "content": _s_clean, "ts": _ts()})
                                        
                                        # Construire la consigne de fond pour l'IA
                                        _nm = f"{st.session_state.betise.rstrip('.,!? ')}\n[CORRECTION DU PARENT] : {_s_clean}"
                                        st.session_state.betise = _nm
                                        
                                        with st.spinner("🤖 Mise à jour du scénario…"):
                                            import time; time.sleep(1)
                                            try:
                                                _r2 = chat_ai(_nm, st.session_state.api_key, st.session_state.val)
                                                reply2 = _r2.get("response","")
                                                st.session_state.chat_history.append({"role":"ai","content":reply2,"ts":_ts()})
                                                if _r2.get("type") == "scenario":
                                                    st.session_state.val = _r2
                                                    if _r2.get("theme") in THEMES:
                                                        st.session_state.theme = _r2["theme"]
                                            except Exception as _e:
                                                st.error(f"Erreur : {_e}")
                                        st.rerun()

                # Auto-scroll en temps réel
                import time
                _cmp.html(f"""<script>
                function forceScroll() {{
                    try {{
                        var ws = window.parent.document.querySelectorAll(
                            '[data-testid="stVerticalBlockBorderWrapper"], [data-testid="stVerticalBlock"]');
                        if (ws.length > 0) {{
                            for(var i=0; i<ws.length; i++) {{
                                if(ws[i].scrollHeight > ws[i].clientHeight) {{
                                    ws[i].scrollTop = ws[i].scrollHeight;
                                }}
                            }}
                        }}
                    }} catch(e) {{}}
                }}
                forceScroll();
                setTimeout(forceScroll, 100);
                setTimeout(forceScroll, 300);
                setTimeout(forceScroll, 600);
                </script><div style='display:none;'>{len(st.session_state.chat_history)}</div>""", height=0)

            # — Champ de saisie (Enter = envoyer) —
            st.markdown('<div class="chat-input-wrap">', unsafe_allow_html=True)
            with st.form(key="chat_form", enter_to_submit=True, border=False):
                _fc, _fb = st.columns([11, 1])
                with _fc:
                    st.text_area("msg",
                        placeholder="Décrivez la bêtise de votre enfant… (Entrée pour envoyer)",
                        height=72, label_visibility="collapsed", key=_input_key)
                with _fb:
                    st.markdown("<div style='margin-top:36px;'></div>", unsafe_allow_html=True)
                    send_clicked = st.form_submit_button("↑", type="primary",
                                                         use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)

        # ══════════════════════════════════════════════════
        # LOGIQUE D'ENVOI
        # ══════════════════════════════════════════════════
        if send_clicked:
            _msg = st.session_state.get(_input_key, "").strip()
            if not st.session_state.api_key.strip():
                st.error("⚠️ Clé API Groq manquante (barre latérale).")
            elif not _msg:
                st.error("⚠️ Écris ton message.")
            elif not _GROQ_OK:
                st.error("La bibliothèque `groq` n'est pas installée.")
            else:
                if st.session_state.val and st.session_state.val.get("type") == "scenario":
                    full_msg = f"{st.session_state.betise.rstrip('.,!? ')}\n[CORRECTION DU PARENT] : {_msg}"
                else:
                    full_msg = _msg
                    
                st.session_state.betise = full_msg
                
                st.session_state.chat_history.append(
                    {"role": "user", "content": _msg, "ts": _ts()})
                with st.spinner("🤖 Je comprends la situation…"):
                    import time; time.sleep(1)
                    try:
                        res = chat_ai(full_msg, st.session_state.api_key, st.session_state.val)
                        reply = res.get("response", "Je suis là !")
                        st.session_state.chat_history.append({"role": "ai", "content": reply, "ts": _ts()})
                            
                        # Comme pour l'enrichissement : on garde l'ancien val si c'est pas un scénario
                        if res.get("type") == "scenario":
                            st.session_state.val = res
                            if res.get("theme") in THEMES:
                                st.session_state.theme = res["theme"]
                        st.rerun()
                    except Exception as e:
                        st.session_state.chat_history.pop()
                        st.error(f"Erreur API Groq : {e}")

        # ══════════════════════════════════════════════════
        # ZONE DE DÉCISION — Toujours visible sous le chat
        # ══════════════════════════════════════════════════
        _lv = st.session_state.val
        _ok = bool(_lv and _lv.get("type") == "scenario" and _lv.get("valide"))

        if _ok:
            _v = _lv
            _age_str = f" · {_v.get('age')} ans" if _v.get("age") else ""
            # ── Carte de validation ──
            st.markdown(
                "<div style='background:linear-gradient(135deg,#f0fdf4,#dcfce7);"
                "border:1.5px solid #4ade80;border-radius:14px;"
                "padding:14px 18px;margin-top:14px;'>"
                "<div style='font-size:0.9rem;font-weight:700;color:#15803d;margin-bottom:6px;'>"
                f"📌 Scénario prêt : {_v.get('prenom','Votre enfant')}{_age_str} • {_v.get('danger','')}</div>"
                f"<div style='font-size:0.88rem;color:#166534;opacity:0.85;'>"
                f"{_v.get('comprehension','')}</div>"
                "</div>",
                unsafe_allow_html=True
            )

            # ── Boutons Actions ──
            st.markdown("<div style='margin-top:12px;'></div>", unsafe_allow_html=True)
            _bg1, _bg2 = st.columns([3, 1])
            with _bg1:
                if st.button(
                    ":material/movie: GÉNÉRER LE DESSIN ANIMÉ ÉDUCATIF !",
                    type="primary", use_container_width=True, key="btn_gen_video"
                ):
                    with st.spinner("Création du scénario animé…"):
                        try:
                            _data = scenario_ai(
                                st.session_state.betise, _v, st.session_state.api_key)
                            st.session_state.scenario = _data
                            _ch, _sg, _nar, _ipr, _ep, _ls = parse_scenario(_data)
                            st.session_state.char  = _ch
                            st.session_state.song  = _sg
                            st.session_state.narrations  = _nar
                            st.session_state.img_prompts = _ipr
                            st.session_state.emotions_personnage = _ep
                            st.session_state.lieux_scenes = _ls
                            st.session_state.step = 2
                            st.rerun()
                        except json.JSONDecodeError:
                            st.error("Format JSON invalide.")
                        except Exception as _e:
                            st.error(f"Erreur : {_e}")
            with _bg2:
                if st.button(":material/refresh: Réinterpréter", use_container_width=True, key="btn_reinterp"):
                    with st.spinner("Nouvelle réflexion…"):
                        import time; time.sleep(1)
                        try:
                            _r3 = chat_ai(st.session_state.betise, st.session_state.api_key, st.session_state.val)
                            reply3 = _r3.get("response", "")
                            st.session_state.chat_history.append({"role": "ai", "content": reply3, "ts": _ts()})
                            st.session_state.val = _r3 if _r3.get("type")=="scenario" else None
                            if _r3.get("theme") in THEMES:
                                st.session_state.theme = _r3["theme"]
                            st.rerun()
                        except Exception as _e:
                            st.error(f"Erreur : {_e}")
        else:
            # Pas encore de scénario détecté : invite + bouton grisé
            st.markdown(
                "<div style='background:#f8fafc;border:1.5px solid #e2e8f0;"
                "border-radius:14px;padding:14px 18px;margin-top:14px;"
                "text-align:center;color:#94a3b8;font-size:0.84rem;'>"
                "💬 Décrivez le comportement de votre enfant pour débloquer la génération vidéo"
                "</div>",
                unsafe_allow_html=True
            )
            st.button(":material/movie: Générer le dessin animé éducatif",
                      type="secondary", use_container_width=True,
                      key="btn_gen_video", disabled=True)

        # ══ SUGGESTIONS RAPIDES ══
        st.markdown("<div style='margin-top:24px;'></div>", unsafe_allow_html=True)
        st.markdown(
            "<style>[data-testid='stVerticalBlockBorderWrapper']:has(button[data-testid^='stBaseButton']) "
            "{ border-color:#c4b5fd !important; border-radius:16px !important; }</style>",
            unsafe_allow_html=True
        )
        with st.container(border=True):
            st.markdown(
                "<div style='background:linear-gradient(135deg,#7c3aed,#a855f7);"
                "border-radius:8px;padding:12px 16px;margin:-16px -16px 14px -16px;'>"
                "<span class='material-symbols-rounded' style='color:#fff;font-size:1.1rem;vertical-align:middle;margin-right:6px;'>lightbulb</span>"
                "<span style='font-size:0.9rem;font-weight:700;color:#fff;'>Exemples rapides</span>"
                "<span style='font-size:0.75rem;color:rgba(255,255,255,0.8);margin-left:8px;'>— cliquez pour démarrer</span>"
                "</div>",
                unsafe_allow_html=True
            )
            def set_example(txt, thm):
                st.session_state[_input_key] = txt
                st.session_state.theme = thm
            for i in range(0, len(EXAMPLES), 3):
                cols = st.columns(3)
                for j in range(3):
                    idx = i + j
                    if idx < len(EXAMPLES):
                        ex = EXAMPLES[idx]
                        with cols[j]:
                            st.button(
                                f"{ex['icon']} {ex['label']}", key=f"ex_{idx}",
                                use_container_width=True, help=ex["text"],
                                on_click=set_example, args=(ex["text"], ex["theme"])
                            )





        # ══ CHOIX DU PERSONNAGE ══
        st.markdown("<div style='margin-top:16px;'></div>", unsafe_allow_html=True)
        with st.container(border=True):
            st.markdown(
                "<div style='background:linear-gradient(135deg,#2563eb,#3b82f6);"
                "border-radius:8px;padding:12px 16px;margin:-16px -16px 14px -16px;'>"
                "<span class='material-symbols-rounded' style='color:#fff;font-size:1.1rem;vertical-align:middle;margin-right:6px;'>sports_martial_arts</span>"
                "<span style='font-size:0.9rem;font-weight:700;color:#fff;'>Personnage de la vidéo</span>"
                "<span style='font-size:0.75rem;color:rgba(255,255,255,0.8);margin-left:8px;'>— l'IA ou votre choix</span>"
                "</div>",
                unsafe_allow_html=True
            )
            HEROES = [
                {"icon": ":material/smart_toy:", "label": "Par défaut (L'IA choisit)"},
                {"icon": ":material/face_3:", "label": "Petite fille"},
                {"icon": ":material/face_6:", "label": "Petit garçon"},
                {"icon": ":material/bug_report:", "label": "Spiderman"},
                {"icon": ":material/flight:", "label": "Superman"},
                {"icon": ":material/pest_control_rodent:", "label": "Tom & Jerry"},
                {"icon": ":material/child_care:", "label": "Masha"},
                {"icon": ":material/backpack:", "label": "Dora"},
                {"icon": ":material/ac_unit:", "label": "Elsa"},
            ]
            def append_hero(hero_name):
                current = st.session_state.get(_input_key, "")
                if "Par défaut" in hero_name:
                    addon = "Laissez l'IA choisir le personnage."
                else:
                    addon = f"Le héros de l'histoire sera {hero_name}."
                if current:
                    if not current.endswith(" "): current += " "
                    st.session_state[_input_key] = current + addon
                else:
                    st.session_state[_input_key] = addon
            for i in range(0, len(HEROES), 3):
                cols = st.columns(3)
                for j in range(3):
                    idx = i + j
                    if idx < len(HEROES):
                        h = HEROES[idx]
                        with cols[j]:
                            st.button(
                                f"{h['icon']} {h['label']}", key=f"hero_{idx}",
                                use_container_width=True, on_click=append_hero, args=(h["label"],)
                            )

        # ══ CHOIX DU NARRATEUR ══
        st.markdown("<div style='margin-top:16px;'></div>", unsafe_allow_html=True)
        with st.container(border=True):
            st.markdown(
                "<div style='background:linear-gradient(135deg,#db2777,#ec4899);"
                "border-radius:8px;padding:12px 16px;margin:-16px -16px 14px -16px;'>"
                "<span class='material-symbols-rounded' style='color:#fff;font-size:1.1rem;vertical-align:middle;margin-right:6px;'>mic</span>"
                "<span style='font-size:0.9rem;font-weight:700;color:#fff;'>Voix du Narrateur</span>"
                "<span style='font-size:0.75rem;color:rgba(255,255,255,0.8);margin-left:8px;'>— qui raconte l'histoire</span>"
                "</div>",
                unsafe_allow_html=True
            )
            VOICES = ["Par défaut (selon l'enfant)", "Femme (Douce)", "Homme (Chaleureux)", "Petite Fille", "Petit Garçon"]
            if "narrator" not in st.session_state:
                st.session_state.narrator = VOICES[0]
            st.session_state.narrator = st.selectbox("Voix du narrateur", VOICES,
                index=VOICES.index(st.session_state.narrator) if st.session_state.narrator in VOICES else 0,
                label_visibility="collapsed")

    # ══════════════════════════════════════
    #  ÉTAPE 2 — SCÉNARIO
    # ══════════════════════════════════════
    elif st.session_state.step==2:
        char=st.session_state.char; song=st.session_state.song
        data=st.session_state.scenario
        t=THEMES.get(st.session_state.theme,THEMES["general"])
        if not char or not song:
            st.error("Données manquantes."); st.session_state.step=1; st.rerun()

        # En-tête professionnel (Cadre haut)
        st.markdown(f"""
        <div style="background:linear-gradient(135deg, #0f172a 0%, #1e293b 100%); 
                    border-radius: 16px; padding: 24px; color: white; display: flex; 
                    align-items: center; gap: 20px; box-shadow: 0 10px 25px rgba(0,0,0,0.15); margin-bottom: 24px;">
            <div style="width:80px;height:80px;border-radius:50%;
                 background:linear-gradient(135deg,{t['color']},#ec4899);
                 display:flex;align-items:center;justify-content:center;
                 font-size:2.5rem;flex-shrink:0; border: 3px solid rgba(255,255,255,0.2);">
                 {'👧'if char.genre=='fille'else'👦'}</div>
            <div style="flex:1;">
                <div style="font-size:0.85rem; text-transform:uppercase; letter-spacing:0.1em; color:#94a3b8; font-weight:700;">Protagoniste & Cadre</div>
                <div style="font-size:1.8rem;font-weight:800;color:#f8fafc; margin-bottom: 4px;">{char.prenom} <span style="font-size:1.1rem; color:#cbd5e1; font-weight:500;">({char.age} ans)</span></div>
                <div style="display: flex; gap: 10px; flex-wrap: wrap; margin-top: 8px;">
                    <span style="background: rgba(239,68,68,0.2); border: 1px solid rgba(239,68,68,0.5); border-radius: 99px; padding: 4px 12px; font-size: 0.8rem; font-weight: 600; color: #fca5a5;">⚠️ Danger : {data.get('danger_court','')}</span>
                    <span style="background: rgba(99,102,241,0.2); border: 1px solid rgba(99,102,241,0.5); border-radius: 99px; padding: 4px 12px; font-size: 0.8rem; font-weight: 600; color: #a5b4fc;">🦸‍♂️ Héros : {char.hero if char.hero and char.hero != "Par défaut" else "Choix libre de l'IA"}</span>
                </div>
            </div>
            <div style="flex:1; min-width: 200px; background: rgba(255,255,255,0.05); border-radius: 12px; padding: 16px; border: 1px solid rgba(255,255,255,0.1);">
                <div style="font-size: 0.8rem; font-weight: 700; color: #94a3b8; text-transform: uppercase;">🎵 Thème Musical</div>
                <div style="font-size: 1rem; font-weight: 600; color: #e2e8f0; margin-top: 4px;">{song.titre}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # Storyboard visuel complet
        with st.expander("🎬 Démarche du scénario (Aperçu des scènes)", expanded=True):
            scenes_titles = ["1. Introduction", "2. La vie normale", "3. Découverte", "4. Tentation", "5. Hésitation",
                             "6. ⚠️ DANGER", "7. Suspense...", "8. 💥 L'ACTION", "9. Aïe aïe aïe!", "10. Peur",
                             "11. Pourquoi?", "12. Explication", "13. Compréhension", "14. Promesse", "15. Conclusion"]
            
            narrations = st.session_state.narrations
            
            timeline_html = "<div style='display:flex; flex-direction:column; gap: 10px; margin-bottom: 10px;'>"
            for idx in range(min(15, len(narrations))):
                scene_tit = scenes_titles[idx] if idx < len(scenes_titles) else f"Scène {idx+1}"
                narr_text = narrations[idx]
                
                # Couleurs dynamiques selon l'intensité narrative
                if idx in [5, 7, 8]:
                    border_color = "#ef4444" # Rouge (Action/Danger)
                    bg_color = "#fef2f2"
                elif idx in [10, 11, 12]:
                    border_color = "#22c55e" # Vert (Leçon/Compréhension)
                    bg_color = "#f0fdf4"
                else:
                    border_color = "#6366f1" # Bleu (Normal)
                    bg_color = "#f8fafc"
                    
                timeline_html += f"""<div style="border: 1px solid #e2e8f0; border-left: 5px solid {border_color}; background: {bg_color}; border-radius: 8px; padding: 12px 16px; box-shadow: 0 1px 3px rgba(0,0,0,0.05); display: flex; flex-direction: column; gap: 4px;">
<div style="font-size: 0.75rem; font-weight: 800; color: #64748b; text-transform: uppercase;">{scene_tit}</div>
<div style="font-size: 0.95rem; font-weight: 500; color: #1e293b; font-style: italic;">💬 "{narr_text}"</div>
</div>"""
            timeline_html += "</div>"
            
            st.markdown(timeline_html, unsafe_allow_html=True)

        st.markdown("<br>",unsafe_allow_html=True)
        cb,cg=st.columns([1,2])
        with cb:
            if st.button(":material/arrow_back: Modifier",use_container_width=True):
                st.session_state.step=1; st.session_state.val=None; st.rerun()
        with cg:
            if st.button(":material/movie: Générer la vidéo maintenant!",type="primary",use_container_width=True):
                st.session_state.step=3; st.rerun()

    # ══════════════════════════════════════
    #  ÉTAPE 3 — GÉNÉRATION VIDÉO
    # ══════════════════════════════════════
    elif st.session_state.step==3:
        char=st.session_state.char; song=st.session_state.song
        data=st.session_state.scenario
        td=THEMES.get(st.session_state.theme,THEMES["general"])
        if not char or not song:
            st.error("Données manquantes."); st.session_state.step=1; st.rerun()

        st.markdown(f"""<div class="card" style="display:flex;align-items:center;gap:14px;
            padding:1rem 1.25rem;">
            <div style="font-size:2.2rem;">{'👧'if char.genre=='fille'else'👦'}</div>
            <div>
                <div style="font-weight:800;font-size:1.1rem;color:#0f172a;">
                    {char.prenom} · {char.age} ans</div>
                <div style="font-size:.84rem;color:#64748b;">🎵 {song.titre}</div>
            </div>
        </div>""",unsafe_allow_html=True)

        with st.status("⚙️ Génération en cours...",expanded=True) as status:
            info_txt = st.empty()
            aph = st.empty()
            with tempfile.TemporaryDirectory() as tmpdir:
                audio_path, durees_frames = gen_audio(char, st.session_state.narrations, st.session_state.theme, tmpdir, aph)
                aph.empty()
                
                # Check list is complete for safety
                if not durees_frames or len(durees_frames) < 15:
                    durees_frames = [int(Cfg.FPS*5)] * 15
                    
                scenes=build_scenes(char,song,st.session_state.theme,st.session_state.narrations,st.session_state.img_prompts, st.session_state.emotions_personnage, st.session_state.lieux_scenes, durees_frames)
                
                info_txt.write("🖼️ Génération des décors avec l'IA...")
                import urllib.request, urllib.parse, time
                pb_bg = st.progress(0, text="Téléchargement des images IA…")
                for i, scene in enumerate(scenes):
                    image_recue = False
                    for tentatives in range(10):
                        try:
                            prompt = f"{scene.image_prompt}, completely exact same character design, highly consistent character, 2d flat vector illustration, colorful children book style, cute, no text"
                            url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(prompt)}?width={Cfg.SIZE}&height={Cfg.SIZE}&nologo=true&seed={42+i}"
                            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
                            with urllib.request.urlopen(req, timeout=10) as resp:
                                scene.bg_img = Image.open(resp).convert("RGBA").resize((Cfg.SIZE, Cfg.SIZE))
                                image_recue = True
                                break
                        except Exception as e:
                            time.sleep(1.5)
                    if not image_recue: scene.bg_img = None
                    pb_bg.progress((i+1)/len(scenes), text=f"Décor IA {i+1}/{len(scenes)}")

                pb_bg.empty()
                info_txt.write("🎨 Rendu vidéo frame par frame...")
                pb=st.progress(0,text="Démarrage…")
                frames=render_all(scenes,char.genre,song,td,pb)

                pb.empty()
                info_txt.write("⚙️ Encodage MP4…")
                fp=encode_video(frames,audio_path,tmpdir,char.prenom)
                if not os.path.exists(fp):
                    st.error("❌ Erreur encodage. Vérifie que ffmpeg est installé."); st.stop()
                with open(fp,"rb")as fv: vb=fv.read()
            info_txt.empty()
            status.update(label="✅ Vidéo prête!",state="complete",expanded=False)

        st.success(f"La vidéo de **{char.prenom}** est prête!", icon=":material/celebration:")
        st.video(vb)
        danger_slug=data.get("danger_court","").replace(" ","_")
        st.download_button(
            label=f":material/save: Télécharger la vidéo — {char.prenom}.mp4",
            data=vb,
            file_name=f"anime_{char.prenom.lower()}_{danger_slug}.mp4",
            mime="video/mp4",use_container_width=True,type="primary")

        st.markdown("---")
        c1, c2 = st.columns(2)
        with c1:
            # Relancer avec les mêmes données (Générera de nouvelles images avec l'IA)
            if st.button(":material/refresh: Regénérer la vidéo", use_container_width=True, type="primary"):
                st.rerun()
        with c2:
            # Retour à l'étape 2 (modifier le scénario)
            if st.button(":material/arrow_back: Retour au scénario", use_container_width=True):
                st.session_state.step = 2
                st.rerun()
                
        st.markdown("<br>", unsafe_allow_html=True)
        # Revenir complètement au début pour une toute nouvelle bêtise
        if st.button(":material/home: Créer une toute nouvelle histoire (Accueil)", use_container_width=True):
            for k in["step","betise","val","scenario","char","song","narrations","img_prompts","theme","confirmed_yes","confirmed_no","chat_history","editing_index","editing_content"]:
                st.session_state[k]=1 if k=="step" else "general" if k=="theme" else [] if k in["narrations","img_prompts","chat_history"] else "" if k=="betise" else False if k in["confirmed_yes","confirmed_no"] else None
            st.rerun()
    # ── Footer ──
    st.markdown("---")
    st.markdown("<p style='text-align:center;font-size:.76rem;color:#94a3b8;'>"
        "Studio Animé Éducatif v3 · Groq AI · "
        "Pour les enfants de 3 à 8 ans · Bienveillant &amp; Éducatif</p>",
        unsafe_allow_html=True)


if __name__=="__main__":
    main()
    
