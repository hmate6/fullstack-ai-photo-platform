from datetime import datetime
from pathlib import Path

from authlib.integrations.flask_client import OAuth
from flask import Flask, request
from flask_sqlalchemy import SQLAlchemy
from flask import url_for, session, redirect, render_template
from os import environ, getenv
from flask_session import Session
import redis
from flask_limiter import Limiter
from dotenv import load_dotenv
from flask import jsonify
import socket
from time import time
from datetime import timedelta
from flask import abort

import builtins
import inspect
import os
TEMPFOLDER = "./static/t/"

if environ.get("WERKZEUG_RUN_MAIN") == "true":
    print("Don't forget to change the 'running' module to disable the testing environment!")

load_dotenv(dotenv_path=".env.example")
GUEST_EMAIL = "guestmail@hmate6_on_github.net"

if getenv("DEBUG_PRINT") == "True":
    _original_print = builtins.print
    def traced_print(*args, **kwargs):
        stack = inspect.stack()

        # stack[0] = traced_print
        # stack[1] = actual print()
        # stack[2] = function containing print
        # stack[3] = caller of that function

        def frame_info(frame):
            return f"{os.path.basename(frame.filename)}:{frame.lineno} in {frame.function}"

        lines = ["\nPRINT called at:"]

        if len(stack) > 1:
            lines.append(f" ├─ print()        → {frame_info(stack[1])}")
        if len(stack) > 2:
            lines.append(f" ├─ function body  → {frame_info(stack[2])}")
        if len(stack) > 3:
            lines.append(f" └─ function call  → {frame_info(stack[3])}")

        _original_print("\n".join(lines))
        _original_print(" Message:", *args, **kwargs)


    builtins.print = traced_print

with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
    s.connect(("8.8.8.8", 80))  # Google's public DNS server
    localip = s.getsockname()[0]

if environ.get("WERKZEUG_RUN_MAIN") == "true":  # CHANGED: lasd a fenti magyarazatot -- ne irjuk ki duplan
    print("Local ip: ", localip)

HOST = getenv("HOST")
test_environment = True if getenv("TEST_ENVIRONMENT") == "True" else False
test = test_environment

app = Flask(__name__)

app.secret_key = getenv("APP_SECRET_KEY")
@app.before_request
def setheader():
    if test_environment:
        request.environ['X-Forwarded-For'] = "127.0.0.1"
        request.environ['HTTP_X_FORWARDED_FOR'] = "127.0.0.1"

if not test_environment:
    app.config['SQLALCHEMY_DATABASE_URI'] = environ.get("DATABASE_URL")
    app.config['SESSION_COOKIE_DOMAIN'] = environ.get("HOST")
    app.config['SESSION_COOKIE_SECURE'] = True
    app.config['SESSION_COOKIE_HTTPONLY'] = True
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
    app.config['SESSION_USE_SIGNER'] = True
else:
    app.config['SQLALCHEMY_DATABASE_URI'] = "sqlite:///app.db"

r = redis.StrictRedis(host='localhost', port=6379, db=0)

app.config['SESSION_TYPE'] = 'redis'
app.config['SESSION_REDIS'] = redis.StrictRedis(host='localhost', port=6379, db=0)
app.config['MAX_CONTENT_LENGTH'] = 60 * 1024 * 1024  # 100MB
Session(app)

Path("./static/t").mkdir(exist_ok=True)
Path("./static/photo").mkdir(exist_ok=True)
Path("./static/photo-hd").mkdir(exist_ok=True)

# Google OAUTH
oauth = OAuth(app)
google_auth = oauth.register(
    name='google',
    client_id=environ.get('GAUTH_CLIENT_ID'),
    client_secret=environ.get('GAUTH_SECRET_KEY'),
    access_token_url='https://oauth2.googleapis.com/token',
    authorize_url='https://accounts.google.com/o/oauth2/auth',
    api_base_url='https://www.googleapis.com/oauth2/v1/',
    client_kwargs={'scope': 'openid email profile'},
    server_metadata_url= 'https://accounts.google.com/.well-known/openid-configuration'
)

db = SQLAlchemy(app)

class LikedImage(db.Model):
    __tablename__ = 'liked_image'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=False)
    image_creator_id = db.Column(db.Integer, nullable=False)
    name = db.Column(db.String(500), nullable=False)
    liked = db.Column(db.Boolean, nullable=False)

class UserAccount(db.Model):
    __tablename__ = 'accounts'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(400), unique=True, nullable=False)
    password = db.Column(db.String(80), nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), default=datetime.now(), nullable=False)
    last_login = db.Column(db.DateTime)
    unlock_time = db.Column(db.DateTime)
    login_attempts = db.Column(db.Integer, nullable=False, default=0)
    resetpw_attempts = db.Column(db.Integer, nullable=False, default=0)
    pw_reset_link_sent = db.Column(db.Boolean, nullable=True)
    username = db.Column(db.String(100), nullable=True)
    is_generating = db.Column(db.Boolean, default=False)
    credits = db.Column("tool_uses", db.Integer, default=0)
    last_pw_reset = db.Column(db.DateTime)
    last_pw_reset_unix = db.Column(db.BigInteger, default=0)
    api_key = db.Column(db.String(200), nullable=True)
    email_verified = db.Column(db.Boolean, default=False)
    wants_email_promotions = db.Column(db.Boolean, default=False)
    deleted = db.Column(db.Boolean, default=False)
    verification_limit = db.Column(db.Integer, default=0)
    plan = db.Column(db.String(40), default="pro")
    subscription_expire_int = db.Column(db.Integer, default=None)
    tool_uses_in_plan = db.Column(db.Integer, default=100)
    acc_version = db.Column(db.String(40), nullable=True)
    profile_picture = db.Column(db.String(500), nullable=True)

class Pwr(db.Model):
    __tablename__ = "pwr"
    id = db.Column(db.Integer, primary_key=True, nullable=False)
    user_id = db.Column(db.Integer, nullable=False)
    url = db.Column(db.String(100), nullable=False)
    expire = db.Column(db.DateTime, nullable=False)

class EmailVerification(db.Model):
    __tablename__ = "emailverification"
    id = db.Column(db.Integer, primary_key=True, nullable=False)
    email = db.Column(db.String(400), nullable=False)
    url = db.Column(db.String(90), nullable=False)
    expire = db.Column(db.DateTime, nullable=False)
    is_expired = db.Column(db.Boolean, default=False)

class Images(db.Model):
    __tablename__ = "images"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer)
    width = db.Column(db.Integer)
    height = db.Column(db.Integer)
    steps = db.Column(db.Integer)
    cfg_scale = db.Column(db.Integer)
    created_at = db.Column(db.DateTime, default=datetime.now(), nullable=False)
    prompt = db.Column(db.String(10000))
    negative_prompt = db.Column(db.String(10000))
    cost = db.Column(db.Float)
    name = db.Column(db.String(500))
    arany = db.Column(db.String(10))
    stilus = db.Column(db.String(100))
    modell = db.Column(db.String(10))
    stilus_url = db.Column(db.String(100))
    public = db.Column(db.Boolean, default=False)
    likes = db.Column(db.Integer, default=0)
    username = db.Column(db.String(100), nullable=True)
    published_at = db.Column(db.DateTime, nullable=True)
    deleted = db.Column(db.Boolean, default=False)
    to_accept = db.Column(db.Boolean, default=False)

class Feedbacks(db.Model):
    __tablename__ = "feedbacks"
    id = db.Column(db.Integer, primary_key=True)
    userid = db.Column(db.Integer)
    feedback = db.Column(db.String(5000))
    rating = db.Column(db.Integer)
    date = db.Column(db.DateTime)
    email = db.Column(db.String(700))
    subject = db.Column(db.String(120))

class Transactions(db.Model): # logolja minden user generálásnak típusát
    __tablename__ = "transactions"
    id = db.Column(db.Integer, primary_key=True, nullable=False)
    user_id = db.Column(db.Integer, nullable=False)
    text = db.Column(db.String(10000), nullable=False)
    credits_cost = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False)
    type = db.Column(db.String(100), nullable=False)

with app.app_context():  # CHANGED: korábban ez a rész két külön app_context() blokk volt, most egybe van vonva
    db.create_all()
    queried = UserAccount.query.filter_by(email=GUEST_EMAIL).first()
    if queried is None:
        email = GUEST_EMAIL
        profile_picture = "/static/img/userimg.webp"
        timenow = int(time())
        db.session.add(UserAccount(email=email, created_at=datetime.now(),
                                   acc_version="google", credits=500,
                                   email_verified=True, profile_picture=profile_picture, last_pw_reset_unix=timenow))
        db.session.commit()
        """session["user"] = email
        session["email"] = email
        user = UserAccount.query.filter_by(email=email).first()
        session["userid"] = user.id
        session["profile_picture"] = profile_picture
        session["last_pw_reset_unix"] = timenow

        r.set(email, timenow)"""

def getip():
    return request.headers['X-Forwarded-For'].split(",")[0]

limiter = Limiter(getip, storage_uri="redis://localhost:6379",app=app) # Use client's ip address, global limits

def logged_in():
    "logged_in() checks in the session if the user is logged in, returns True or False"
    # not to confuse with its base "user" cookie which contains the username of the logged in user
    if "user" not in session:
        session.pop("user", None)
        session.pop("status", None)
        session.pop("last_pw_reset_unix", None)
        session.pop("userid", None)
        session.pop("email", None)
        session.pop("plan", None)
        return False
    return True

def current_page(url):
    return url_for(url)

def get_how_much_times_ago(minutes):
    if minutes < 60:
        return f"{minutes} minutes ago"
    elif minutes < 1440:
        return f"{minutes // 60} hours ago"
    else:
        return f"{minutes // 1440} days ago"



# stilusok: ha a user kiválaszt egy stílust a képgeneráláshoz, akkor a prompthoz hozzá lesz adva a stílusnak megfelelő szöveg
stilusok = {
    "None": "",
    "Realistic": "8k, high quality, ultra resolution, masterpiece, stunning, ultra-HD",
    "Comic": "comic, graphic novel, cartoon, comic book style",
    "Realisztikus": "8k, high quality, ultra resolution, masterpiece, stunning, ultra-HD",
    "Cyberpunk": "cyberpunk, futuristic, dystopian, cityscape, high-tech, dark, neon-lit, urban",
    "Retro": "retro, vintage, classic, nostalgic",
    "Fantasy": "fantasy, magical, mystical, enchanted, otherworldly, mythical, epic, fairytale",
    "Cyberpunk Noir": "futuristic cityscapes, neon lights, rain-soaked streets, high contrast shadows, gritty urban aesthetics, advanced technology, dystopian vibes, dark and moody atmosphere",
    "Retro Futurism": "vintage sci-fi aesthetics, pastel colors, sleek curves, 1950s design elements, optimistic technology, surreal landscapes, nostalgic elements, whimsical imagination",
    "Steampunk Fantasy": "Victorian-era design, intricate machinery, brass and copper tones, whimsical inventions, gears and cogs, fantasy elements, historical influences, lush details",
    "Surreal Dreamscape": "unreal landscapes, distorted reality, ethereal colors, dream-like quality, imaginative compositions, bizarre imagery, fluid forms, enchanting atmospheres",
    "Apocalyptic Realism": "post-apocalyptic environments, decaying urban landscapes, muted color palettes, harsh textures, survival themes, emotional depth, stark contrasts, haunting beauty",
    "Digital Impressionism": "pixelated brush strokes, vibrant color splashes, modern artistic techniques, emotional landscapes, blending of reality and abstraction, digital canvas, atmospheric depth, expressive forms",
    "Bio-Punk": "biotechnology, genetic manipulation, organic aesthetics, mutated flora and fauna, futuristic medicine, intricate biological designs, ecological themes, vibrant ecosystems",
    "Dark Fantasy": "ominous landscapes, mythical creatures, gothic elements, shadowy atmospheres, epic quests, rich storytelling, magical realism, foreboding settings",
    "Minimalist Zen": "simple compositions, monochromatic palettes, natural elements, tranquility, balance, clean lines, spacious layouts, meditative quality",
    "Art Deco Elegance": "geometric shapes, rich colors, luxurious materials, intricate patterns, 1920s glamour, bold design, opulence, vintage sophistication",
    "Fantasy Realism": "mythical beings, enchanting landscapes, realistic detail, immersive storytelling, rich textures, vibrant colors, otherworldly elements, compelling narratives",
    "Post-Internet Art": "digital culture critique, glitch aesthetics, internet iconography, mixed media, contemporary issues, ironic humor, virtual identities, vibrant color schemes",
    "Dark Surrealism": "unsettling imagery, bizarre juxtapositions, dream-like sequences, psychological depth, haunting figures, surreal narratives, emotional intensity, shadowy undertones",
    "Neon Dystopia": "glowing neon signs, urban decay, technological ruins, vibrant yet grim settings, reflections in rain, cyberpunk elements, oppressive atmosphere, high-energy visuals",
    "Gritty Realism": "unfiltered perspectives, raw emotions, everyday struggles, harsh environments, authentic storytelling, strong character focus, textured imagery, socio-political themes",
    "Whimsical Fantasy": "playful characters, colorful landscapes, imaginative storytelling, magical creatures, lighthearted narratives, charming details, bright palettes, joyful atmospheres",
    "High Fantasy": "epic quests, intricate world-building, legendary heroes, magical realms, elaborate costumes, mythical creatures, immersive storytelling, grand adventures",
    "Kawaii Aesthetic": "cute characters, pastel colors, playful themes, adorable designs, cheerful motifs, Japanese pop culture influences, whimsical elements, lighthearted vibes",
    "Cosmic Horror": "existential dread, unfathomable entities, dark cosmic themes, nightmarish landscapes, psychological terror, atmospheric tension, eldritch imagery, eerie aesthetics",
    "Geometric Abstraction": "bold shapes, vibrant colors, minimalistic forms, symmetry and asymmetry, dynamic compositions, modern aesthetics, mathematical precision, artistic expression",
    "Color Field Painting": "large expanses of color, emotive palettes, simple forms, minimalist approach, expressive use of color, abstract landscapes, visual meditation, tranquil compositions",
    "Psychedelic Art": "vibrant colors, mind-bending patterns, surreal visuals, hallucinogenic themes, kaleidoscopic imagery, dream-like sequences, spiritual exploration, playful shapes",
    "Nature-Inspired": "organic forms, earthy color palettes, natural textures, botanical elements, harmonious compositions, eco-conscious themes, lush landscapes, serene beauty",
    "Urban Sketching": "loose linework, spontaneous compositions, dynamic cityscapes, candid moments, observational drawing, lively characters, architectural details, everyday life",
    "Futuristic Industrial": "sleek designs, advanced materials, urban environments, cutting-edge technology, mechanical aesthetics, bold structures, innovation themes, metallic color schemes",
    "Dystopian Realism": "bleak environments, societal decay, everyday struggles, authentic narratives, emotional depth, raw imagery, gritty textures, unsettling atmospheres",
    "Vintage Collage": "layered imagery, retro aesthetics, mixed media, nostalgic themes, playful combinations, historical references, creative storytelling, vibrant visuals",
    "Lofi Aesthetic": "soft color palettes, vintage vibes, nostalgic imagery, relaxed atmospheres, muted tones, urban landscapes, hand-drawn elements, chill vibes",
    "Abstract Expressionism": "emotional intensity, gestural brushwork, bold colors, spontaneous compositions, individual expression, psychological exploration, dynamic energy, layered textures",
    "Augmented Reality": "interactive elements, digital overlays, merging real and virtual worlds, immersive experiences, technological integration, futuristic aesthetics, playful innovation",
    "Manga Style": "distinctive character designs, dynamic action, expressive emotions, dramatic compositions, Japanese comic influences, vibrant storytelling, detailed backgrounds, visual narrative",
    "Classic Portraiture": "realistic representations, dramatic lighting, rich textures, historical influences, emotional depth, traditional techniques, timeless elegance, compelling storytelling",
    "Cinematic Style": "dramatic compositions, high contrast lighting, immersive storytelling, strong character focus, atmospheric depth, vivid colors, visual narratives, emotional impact",
    "Vaporwave": "retro aesthetics, nostalgic visuals, surreal imagery, bright colors, 80s and 90s influences, glitch art, internet culture, playful irony",
    "Impressionist Landscapes": "loose brushwork, soft color palettes, capturing light, atmospheric effects, natural beauty, emotional resonance, dynamic compositions, tranquil scenes",
    "Fantasy Illustration": "epic characters, vivid worlds, imaginative storytelling, detailed environments, magical elements, rich colors, captivating narratives, illustrative quality",
    "Realistic Wildlife": "natural habitats, intricate details, vibrant colors, emotional connection to nature, dynamic compositions, authenticity, ecological themes, stunning imagery",
    "Experimental Photography": "unconventional techniques, creative compositions, abstract visuals, blending mediums, exploring perceptions, innovative approaches, emotive storytelling, thought-provoking images",
    "Street Art": "urban expressions, graffiti influences, vibrant colors, social commentary, cultural themes, large-scale murals, bold graphics, dynamic storytelling",
    "Gothic Architecture": "intricate details, dark elegance, towering structures, historical influences, dramatic lighting, romanticism, rich textures, enchanting environments",
    "Sculptural Design": "three-dimensional forms, innovative materials, organic shapes, structural integrity, balance and harmony, modern aesthetics, tactile quality, creative exploration",
    "Monochrome Minimalism": "black and white palettes, simplicity in form, emphasis on contrast, clean lines, focused compositions, meditative quality, refined aesthetics, timeless elegance",
    "Folk Art": "cultural motifs, traditional craftsmanship, vibrant colors, storytelling elements, community influence, handmade quality, rustic charm, rich symbolism",
    "Celestial Themes": "cosmic landscapes, starry skies, ethereal colors, spiritual exploration, otherworldly imagery, dreamy atmospheres, expansive compositions, wonder and mystery",
    "Art Nouveau": "flowing lines, organic forms, floral motifs, elegant designs, decorative arts, intricate patterns, historical influences, graceful aesthetics",
    "Conceptual Art": "idea-driven visuals, innovative approaches, thought-provoking themes, interdisciplinary practices, modern aesthetics, challenging perceptions, creative exploration",
    "Mystical Realism": "blending reality and fantasy, enchanting environments, magical elements, immersive storytelling, rich symbolism, ethereal quality, emotional depth, surreal narratives",
    "Horror Art": "dark themes, unsettling imagery, psychological tension, grotesque elements, nightmarish visuals, eerie atmospheres, emotional intensity, captivating narratives",
    "Architectural Photography": "capturing structures, dramatic perspectives, emphasis on lines, light and shadow play, urban environments, artistic framing, visual storytelling, intricate details",
    "Futuristic Nature": "blending technology and ecology, innovative designs, organic forms, sustainable aesthetics, vibrant colors, ecological themes, imaginative landscapes, harmonious coexistence",
    "Kinetic Art": "movement and motion, interactive elements, engaging experiences, dynamic compositions, vibrant colors, playful designs, innovative techniques, visual storytelling",
    "Mythological Themes": "inspired by legends, mythical creatures, epic narratives, rich symbolism, ancient cultures, imaginative storytelling, enchanting visuals, timeless tales",
    "Digital Collage": "layered imagery, blending traditional and digital techniques, playful combinations, modern aesthetics, vibrant colors, creative storytelling, innovative design",
    "Cultural Heritage": "traditional motifs, historical influences, storytelling elements, vibrant colors, craftsmanship, community values, rich symbolism, emotional resonance",
    "Nature Photography": "capturing landscapes, intricate details, vibrant colors, emotional connection to nature, dynamic compositions, authenticity, ecological themes, stunning imagery",
    "Sculptural Illustration": "three-dimensional forms, creative storytelling, dynamic compositions, modern aesthetics, tactile quality, innovative approaches, organic shapes, artistic expression",
    "Abstract Landscape": "imaginative environments, bold colors, emotional resonance, dynamic compositions, surreal elements, expressive forms, layered textures, vibrant visuals",
    "Theatrical Design": "dramatic compositions, emotional storytelling, bold visuals, immersive experiences, thematic depth, innovative designs, rich colors, engaging narratives",
    "Renaissance Influence": "classical techniques, realistic representations, intricate details, historical themes, emotional depth, rich colors, timeless elegance, artistic exploration",
    "Street Photography": "candid moments, urban environments, authentic storytelling, dynamic compositions, capturing everyday life, cultural diversity, emotional connection, gritty realism",
    "Cybernetic Aesthetics": "merging technology and biology, futuristic designs, intricate patterns, organic forms, advanced materials, imaginative landscapes, vibrant colors, innovative narratives",
    "Chibi Style": "cute characters, exaggerated proportions, playful expressions, vibrant colors, lighthearted themes, Japanese pop culture influences, whimsical elements, joyful atmospheres",
    "Constructivism": "geometric forms, bold colors, social themes, abstract designs, visual clarity, innovative aesthetics, dynamic compositions, artistic expression",
    "Lush Tropical": "vibrant flora, exotic landscapes, rich colors, immersive environments, natural beauty, harmonious compositions, tropical themes, emotional connection to nature",
    "Modernist Architecture": "clean lines, functional designs, innovative materials, minimalist aesthetics, urban environments, structural integrity, dynamic compositions, contemporary influences",
    "Ethereal Portraiture": "soft lighting, mystical atmospheres, dream-like quality, glowing effects, serene expressions, delicate details, spiritual undertones, otherworldly beauty",
    "Brutalist Architecture": "raw concrete textures, monolithic structures, bold forms, functional design, stark aesthetics, urban environments, strong geometry, minimalist decoration",
    "Photorealism": "hyper-detailed imagery, life-like accuracy, realistic textures, clear focal points, meticulous attention to detail, emotional resonance, compelling narratives, high-resolution visuals",
    "Cyberpunk Fantasy": "dystopian futures, neon-lit environments, advanced technology, societal collapse, cybernetic enhancements, complex characters, urban grit, vibrant storytelling",
    "Neo-Classical": "grandeur and elegance, classical elements, dramatic compositions, rich textures, historical themes, timeless beauty, emotional depth, artistic mastery",
    "Ambient Light": "soft glow, atmospheric effects, tranquility, muted colors, serene environments, minimal distractions, emotional depth, visual comfort",
    "Digital Surrealism": "imaginative worlds, digital manipulation, dream-like sequences, unexpected juxtapositions, vibrant color palettes, visual storytelling, psychological exploration, modern aesthetics",
    "Rural Charm": "pastoral landscapes, rustic elements, warm color palettes, intimate scenes, emotional connections, traditional craftsmanship, natural beauty, simplicity",
    "Intergalactic Exploration": "vast cosmic landscapes, alien worlds, futuristic technology, vibrant colors, imaginative storytelling, epic journeys, deep space aesthetics, awe and wonder",
    "Visual Poetry": "artistic expression, emotional resonance, layered meanings, abstract visuals, poignant imagery, creative narratives, innovative compositions, conceptual depth",
    "Glamour Photography": "high fashion, dramatic lighting, stunning visuals, bold colors, sophisticated styling, captivating poses, emotional storytelling, luxurious aesthetics",
    "Artistic Collaboration": "interdisciplinary approaches, diverse mediums, collective creativity, innovative ideas, shared visions, unique narratives, collaborative storytelling, dynamic outcomes",
    "Emotionally Charged": "intense feelings, powerful imagery, evocative compositions, depth of storytelling, vibrant colors, raw emotions, relatable experiences, impactful visuals",
    "Hyperrealism": "exaggerated detail, meticulous techniques, life-like quality, visual intensity, emotional depth, unexpected perspectives, engaging narratives, striking realism",
    "Elegant Minimalism": "simplicity in design, muted colors, uncluttered spaces, refined aesthetics, clear focus, harmonious compositions, tranquility, emotional connection",
    "Képregény": " comic, graphic novel, cartoon, comic book style",
    'Psycho-Realism': "Craft a scene that blends stark realism with psychological depth, featuring subtle, eerie distortions that reflect inner emotions.",
    'Neoclassical Revival': "Illustrate an opulent architectural landscape adorned with classical columns, intricate sculptures, and a sense of grandeur inspired by ancient civilizations.",
    'Pop Surrealism': "Depict an imaginative world filled with whimsical characters interacting in bizarre and dreamlike settings, characterized by vibrant colors.",
    'Anime Futurism': "Visualize a cutting-edge cityscape inhabited by anime-inspired characters, robots, and advanced technologies, all immersed in neon lights and rich hues.",
    'Baroque Fantasy': "Create a richly detailed and dramatic tableau with flowing textiles, regal figures, and lush backdrops that evoke the splendor of the Baroque period.",
    'Retro Sci-Fi': "Illustrate a futuristic vision as imagined in the 1950s, showcasing retro-futuristic elements like ray guns and flying saucers amidst a vivid color palette.",
    'Urban Dystopia': "Portray a deteriorating metropolis overwhelmed by urban decay, revealing the struggles of its inhabitants through oppressive architecture and somber expressions.",
    'Hypercolor Pop Art': "Craft a lively and colorful composition featuring bold outlines and exaggerated forms, inspired by pop art aesthetics infused with neon colors and digital textures.",
    'Photographic Abstraction': "Merge photographic realism with abstract forms and textures, creating a visual experience that oscillates between clarity and abstraction.",
    'New Gothic': "Illustrate a contemporary gothic scene filled with dark, atmospheric architecture and enigmatic figures that evoke a sense of mystery and horror.",
    'Deconstructivism': "Visualize a chaotic and fragmented landscape where architectural elements and objects are deconstructed and reassembled, conveying a sense of disarray.",
    'Organic Architecture': "Depict architecture inspired by natural forms, featuring flowing designs that integrate harmoniously with the environment using organic materials.",
    'Symbolist Art': "Create a dreamlike composition rich with symbolism and mystical imagery, evoking deep emotional resonance and spiritual significance.",
    'Sci-Fi Minimalism': "Visualize a sleek, minimalist futuristic space that emphasizes geometric simplicity and metallic textures in its design.",
    'Expressionist Urbanism': "Illustrate an emotionally charged urban environment where the architecture and setting distort to reflect the intensity of human experiences.",
    'Botanical Art': "Create a vibrant and detailed illustration of flora, capturing the essence and beauty of nature with a scientific approach.",
    'Ancient Mythology': "Depict a grand scene inspired by ancient mythological tales, featuring gods, legendary heroes, and mythical beasts in a magnificent landscape.",
    'Anime Slice of Life': "Illustrate a cozy, everyday moment in an anime style, showcasing characters engaged in casual interactions within a serene, contemporary backdrop.",
    '3D Pixel Art': "Create a nostalgic voxel-based 3D scene utilizing blocky, pixelated forms to represent characters, landscapes, or objects in a retro gaming aesthetic.",
    'Metaphysical Realism': "Visualize a scene where ordinary objects possess profound symbolic meaning, inviting viewers to engage in introspection and reflection.",
    'Alien Landscape': "Depict an extraterrestrial environment filled with bizarre vegetation and alien fauna, complemented by a surreal sky that evokes wonder.",
    'Rococo Glamour': "Create an opulent scene adorned with intricate details and soft pastel colors, reflecting the lavishness of the Rococo artistic movement.",
    'Art Brut': "Illustrate raw, unrefined imagery that channels deep emotion through simplistic forms and vivid color contrasts, celebrating primal creativity.",
    'Futuristic Gothic': "Visualize a towering metropolis that fuses gothic architecture with cutting-edge technology, showcasing sharp spires and luminous interfaces.",
    'Dreamlike Fantasy': "Craft a magical realm where fantasy and reality intertwine, featuring glowing elements, levitating landscapes, and ethereal beings.",
    'Magical Realism': "Illustrate a believable setting imbued with enchanting details, such as floating objects and mystical creatures that hint at the extraordinary.",
    'Post-Apocalyptic Fantasy': "Depict a world where elements of fantasy persist amid a post-apocalyptic backdrop, featuring ruined landscapes and enigmatic magical beings.",
    'Geometric Surrealism': "Create a surreal composition filled with abstract geometric shapes that merge with dreamlike environments, challenging perceptions of reality.",
    'Afrofuturism': "Visualize a vibrant futuristic world that integrates African cultural themes with advanced technological elements, showcasing bold designs.",
    'Brutalist Sci-Fi': "Depict a stark, futuristic landscape dominated by heavy concrete structures, merging brutalist architectural aesthetics with sci-fi influences.",
    'Punk Rock Aesthetic': "Illustrate a dynamic urban scene characterized by rebellion and energy, featuring vivid colors, rough textures, and edgy punk-inspired figures.",
    'Futuristic Pastel': "Craft a sleek and modern environment using soft pastel colors, where technological elements merge seamlessly with a soothing atmosphere.",
    'Minimalist Sci-Fi': "Portray a pristine, minimalist futuristic space that emphasizes simplicity with geometric shapes and a neutral color palette.",
    'Anime Fantasy': "Illustrate a vivid fantasy realm populated by magical creatures and heroic characters, showcasing intricate anime-inspired art styles.",
    'Organic Abstraction': "Visualize an abstract composition influenced by natural forms, characterized by flowing lines, soft hues, and fluid dynamics.",
    'Surrealist Portrait': "Create a captivating and dreamlike portrait that distorts reality through surreal elements like floating objects and shifting facial features.",
    'Grunge Aesthetic': "Depict a raw and gritty scene filled with dark tones, distressed textures, and an underground atmosphere that embodies rebellion.",
    'Dynamic Expressionism': "Illustrate an abstract composition brimming with energy and movement, employing expressive brushstrokes and vivid colors.",
    'Alien Gothic': "Create a mysterious and dark atmosphere combining gothic architectural elements with alien forms and surreal lighting.",
    'Watercolor Fantasy': "Depict a soft, fantastical landscape using gentle watercolor techniques, merging delicate colors with fluid, dreamlike shapes.",
    'Retro Futuristic Pop': "Illustrate a playful scene that blends retro-futuristic elements with pop art, combining bold graphic shapes with nostalgic designs.",
    'Neo-Baroque': "Craft a lavish and ornate scene filled with intricate details, rich tones, and extravagant characters reminiscent of Baroque elegance.",
    'Ethereal Sci-Fi': "Visualize a soft and otherworldly sci-fi landscape filled with luminous light, futuristic innovations, and dreamlike vistas.",
    'Sci-Fi Horror': "Illustrate a chilling futuristic setting where advanced technology intersects with terrifying creatures and eerie high-tech environments.",
    'Retro Dystopia': "Depict a dark, dystopian world infused with retro design elements like vintage technology and subdued color palettes.",
    'Elemental Magic': "Create a vibrant scene showcasing powerful magic associated with natural elements—fire, water, earth, and air—surrounding mystical characters.",
    'Hyper-Real Sci-Fi': "Visualize an incredibly detailed futuristic cityscape where textures and lighting create an immersive, realistic environment.",
    'Neo-Impressionism': "Illustrate a modern interpretation of impressionism, focusing on the interplay of light, color, and abstract shapes in a contemporary context.",
    'Steampunk Fantasy Noir': "Create a dark, atmospheric scene where Victorian steampunk aesthetics intertwine with elements of fantasy and noir, featuring smoky streets.",
    'Nostalgic Futurism': "Depict a futuristic vision infused with retro influences, blending old-fashioned technologies with modern designs for a nostalgic effect.",
    'Bio-Luminescent Landscape': "Visualize an alien world brimming with bioluminescent flora and fauna, creating a vibrant, surreal atmosphere filled with glowing elements.",
    'Zen Sci-Fi': "Illustrate a tranquil, minimalist futuristic scene where technology harmonizes with nature, characterized by clean lines and soft hues.",
    'Crystalline Structures': "Depict an abstract landscape filled with shimmering geometric forms and crystals that evoke a sense of alien beauty.",
    'Street Noir': "Visualize a gritty urban environment at night, filled with deep shadows, harsh neon lighting, and mysterious figures lurking in the darkness.",
    'Ancient Civilization Fantasy': "Illustrate a grand depiction of an ancient civilization filled with towering temples, mythical creatures, and an atmosphere of awe-inspiring power.",
    'Surreal Nature': "Create a dreamlike landscape where natural elements blend with fantastical forms, challenging the viewer's perception of the environment.",
    'Mechanical Fantasy': "Illustrate a fantastical world where intricate machinery powers the environment, merging fantasy elements with mechanical design.",
    'Gothic Fantasy': "Craft a dark, atmospheric scene rich with gothic castles, mythical beings, and an eerie, haunting ambiance.",
    'Dark Botanical': "Depict a moody botanical scene where plants and flowers seem animated, set within a mysterious and shadowy environment.",
    'Retro Glamour': "Illustrate a glamorous, vintage-inspired scene reminiscent of classic Hollywood, showcasing elegant fashion and luxurious, soft lighting.",
    'Steam Fantasy': "Create a fantastical universe powered by steam technology, where characters engage with advanced mechanical inventions and grand airships.",
    'Color Splash Urbanism': "Visualize a vibrant urban environment, splashed with bright colors that contrast sharply with a gritty, industrial backdrop.",
    'Post-Surrealism': "Illustrate a contemporary surreal composition that incorporates modern themes and digital elements into a dreamlike narrative.",
    'Conceptual Sci-Fi': "Depict a futuristic realm where abstract concepts converge with advanced technology, exploring innovative ideas through visual artistry.",
    'Ambient Nature': "Create a serene natural scene with gentle lighting and subtle textures, evoking a sense of calm and peacefulness.",
    'Mechanical Abstraction': "Illustrate an abstract composition influenced by mechanical",
    'Dynamic Fantasy Portraits': "Create fantasy portraits that embody movement and energy through design, emphasizing vibrant colors and imaginative themes, while capturing the essence of characters in dynamic poses and fantastical settings.",
    'Cinematic Urban Nature': "Illustrate urban scenes that capture the beauty of nature within city environments, blending architectural elements with organic forms, creating a harmonious coexistence between urban life and the natural world.",
    'Conceptual Wildlife Art': "Create wildlife pieces that explore conceptual themes and narratives, inviting viewers to reflect on the relationship between nature and humanity, emphasizing the significance of wildlife conservation and environmental awareness.",
    'Psychedelic Urban Landscapes': "Create urban landscapes using psychedelic colors and patterns, producing a visually intriguing experience that challenges perception and reality, merging fantasy elements with familiar cityscapes to spark imagination.",
    'Whimsical Wildlife Illustrations': "Illustrate whimsical representations of wildlife filled with playful elements and surreal characteristics, evoking a sense of joy and wonder, and encouraging viewers to see the magic in everyday creatures and their habitats.",
    'Psycho-Dynamic Fantasy': "Illustrate dynamic fantasy scenes that explore psychological themes and emotional landscapes, utilizing dramatic color contrasts and complex compositions to delve into the depths of the human psyche and fantasy worlds.",
    'Cinematic Whimsical Art': "Illustrate whimsical scenes that feel cinematic and rich in detail, featuring enchanting characters and imaginative settings that capture the viewer's imagination, transporting them into a delightful and fantastical narrative.",
    'Ethereal Fantasy Portraiture': "Create portraits that capture ethereal qualities and magical elements, merging fantasy aesthetics with soft, dreamlike visuals to evoke emotions and create a sense of otherworldliness in the depicted subjects.",
    'Dynamic Nature Landscapes': "Depict landscapes that emphasize movement and energy through natural elements, showcasing the dynamic aspects of the environment and weather, and capturing the vibrancy and life inherent in natural settings.",
    'Conceptual Surreal Landscapes': "Illustrate surreal landscapes that explore conceptual themes and ideas, challenging viewers to interpret the deeper meanings behind the imagery, merging reality with imagination in unexpected and thought-provoking ways.",
    'Abstract Fantasy Art': "Create fantasy pieces that employ abstract forms and vibrant colors, inviting viewers to engage with the art on an emotional and intellectual level, encouraging interpretation beyond the literal and into the realm of imagination.",
    'Cinematic Retro Fantasy': "Depict fantasy scenes that feel cinematic and inspired by retro aesthetics, blending vintage styles with modern storytelling elements to create a nostalgic yet fresh visual narrative that resonates with viewers.",
    'Dynamic Urban Fantasy Portraits': "Illustrate urban portraits filled with dynamic movement and fantasy elements, capturing the energy of city life infused with imaginative themes, showcasing characters in vibrant, bustling settings that bring stories to life.",
    'Psychedelic Nature Art': "Create vibrant and surreal nature scenes using psychedelic colors and forms, emphasizing the extraordinary beauty of the natural world, inviting viewers to experience nature in a bold and transformative way that inspires awe.",
    'Conceptual Surreal Portraits': "Illustrate surreal portraits that explore conceptual themes and ideas, pushing the boundaries of traditional portraiture with imaginative elements, inviting viewers to question identity and reality through artistic expression.",
    'Ethereal Nature Art': "Create artistic representations of nature that embody ethereal qualities, blending organic forms with dreamlike colors and textures to evoke a sense of peace and connection to the natural world, enhancing its beauty.",
    'Dynamic Whimsical Landscapes': "Illustrate whimsical landscapes that emphasize movement and energy through playful elements, capturing the joyful essence of a fantasy world where imagination knows no bounds, and creativity flourishes in vibrant colors.",
    'Ethereal Urban Wildlife': "Create urban wildlife scenes that embody ethereal qualities and magical elements, portraying the coexistence of wildlife in city settings and infusing ordinary environments with a sense of wonder and enchantment.",
    'Conceptual Abstract Wildlife': "Create abstract wildlife pieces that explore conceptual themes and narratives, pushing the viewer to engage with the art on a deeper level, provoking thoughts about the role of wildlife in the ecosystem and our connection to it.",
    'Dynamic Surreal Nature Art': "Create nature art that embodies movement and energy through surreal elements, transforming natural scenes into dreamlike landscapes where the lines between reality and imagination blur, evoking a sense of wonder and exploration.",
    'Kaleidoscopic Urban Portraits': "Create urban portraits using kaleidoscopic patterns and vibrant colors, blending modern city life with abstract artistic expressions, resulting in captivating visuals that challenge conventional portraiture while celebrating diversity.",
    'Ethereal Urban Art': "Create urban scenes that embody ethereal qualities and magical elements, merging the vibrancy of city life with dreamlike aesthetics, inviting viewers to explore the unseen beauty within everyday urban environments.",
    'Dynamic Fantasy Wildlife Portraits': "Depict wildlife in fantasy settings that emphasize movement and energy, showcasing animals in imaginative scenarios that highlight their grace and power, while integrating elements of fantasy to enrich the narrative.",
    'Psychedelic Fantasy Nature': "Create vibrant and surreal nature scenes using psychedelic colors and forms, aiming to inspire awe and reflection on the beauty and complexity of the natural world while encouraging viewers to explore their creativity.",
    'Whimsical Urban Fantasy Landscapes': "Illustrate whimsical urban landscapes filled with enchanting elements, merging the charm of city life with fantastical features, creating a visual narrative that sparks curiosity and invites exploration.",
    'Dynamic Wildlife Art': "Depict wildlife in dynamic manners, emphasizing movement and energy, and capturing the vitality of animals in their natural habitats, showcasing their interactions with the environment in compelling visual storytelling.",
    'Ethereal Wildlife Landscapes': "Illustrate landscapes that capture the beauty of wildlife in ethereal settings, combining soft, dreamlike qualities with vibrant elements to create serene environments that evoke tranquility and admiration for nature's wonders.",
    'Retro Sci-Fi Fantasy': "Create retro-inspired sci-fi fantasy scenes, blending classic design elements with imaginative narratives that transport viewers to alternative realities filled with unique characters and technology.",
    'Vibrant Abstract Art': "Create vibrant abstract art pieces that use color and form to convey emotions and ideas, inviting viewers to interpret the artwork through their unique perspectives and experiences.",
    'Dreamlike Kinetic Landscapes': "Illustrate landscapes that feel alive with motion, utilizing dreamlike elements to evoke a sense of wonder and curiosity, creating immersive scenes that invite exploration.",
    'Futuristic Urban Jungle': "Depict futuristic cities overrun by nature, blending advanced technology with lush greenery, highlighting the balance between urban development and environmental preservation.",
    'Mythological Modernism': "Create modern interpretations of mythological themes, blending contemporary aesthetics with timeless stories to explore the relevance of ancient tales in today's world.",
    'Neo-Classicist Fantasy': "Illustrate fantasy scenes that draw inspiration from classical art, merging historical techniques with imaginative elements to create a unique visual narrative that transcends time.",
    'Geometric Fantasy Landscapes': "Create fantasy landscapes defined by geometric shapes and patterns, merging the organic with the structured, producing a visually striking environment that challenges traditional perceptions of nature.",
    'Industrial Surrealism': "Depict surreal scenes that blend industrial elements with imaginative landscapes, creating a visual dialogue about the relationship between technology and nature in modern society.",
    'Artistic Cultural Fusion': "Illustrate art that blends elements from diverse cultures, creating a harmonious and vibrant visual experience that celebrates the beauty of global traditions and artistic expressions.",
    'Romantic Steampunk Fantasy': "Create steampunk-inspired fantasy scenes filled with romance and adventure, highlighting intricate designs and imaginative storytelling that transports viewers to a bygone era with a twist.",
    'Cosmic Dreamscape': "Illustrate dreamlike landscapes set in cosmic environments, utilizing vibrant colors and surreal elements to evoke a sense of wonder and exploration of the universe's mysteries.",
    'Metaphysical Urban Landscapes': "Create urban landscapes that explore metaphysical themes, challenging perceptions of reality and inviting viewers to engage with the deeper meanings hidden within the scenes.",
    'Retro-Futuristic Fantasy': "Depict fantasy scenes inspired by retro-futuristic aesthetics, merging nostalgic design elements with imaginative narratives that transport viewers to alternate realities filled with adventure.",
    'Nature-Inspired Abstract Art': "Create abstract pieces inspired by the beauty of nature, utilizing organic forms and earthy colors to evoke a sense of calm and connection to the natural world.",
    'Transcendent Animal Portraits': "Illustrate animal portraits that transcend realism, capturing the spirit and essence of each creature through imaginative and expressive techniques that celebrate their individuality.",
    'Harmonious Urban Landscapes': "Create urban landscapes that emphasize harmony between human structures and natural elements, showcasing the beauty of coexistence and the importance of sustainability in city planning.",
    'Symbolic Nature Art': "Illustrate nature scenes that incorporate symbolic elements to convey deeper meanings about the environment and humanity's connection to it, inviting reflection and awareness.",
    'Energetic Abstract Portraits': "Create abstract portraits that capture the energy and emotion of the subjects, using vibrant colors and dynamic shapes to express the complexities of human experience.",
    'Ethereal Magical Landscapes': "Depict landscapes that embody magical and ethereal qualities, blending natural beauty with fantastical elements to create enchanting environments that inspire wonder and imagination.",
    'Cinematic Nature Narratives': "Illustrate nature scenes that tell compelling narratives, combining cinematic techniques with rich detail to create immersive environments that engage viewers in storytelling.",
    'Urban Noir Fantasy': "Create dark and moody urban fantasy scenes filled with intrigue and mystery, utilizing chiaroscuro lighting and atmospheric elements to evoke a sense of suspense and allure.",
    'Futuristic Eco-Design': "Depict futuristic designs that prioritize sustainability and environmental harmony, merging advanced technology with eco-friendly practices to envision a brighter, greener future."
}


# REMOVED: itt egy teljesen kikommentelt, nem használt 'debug_print' segédfüggvény-vázlat volt (sys import,
# print felülírás traceback kiírással) -- sosem volt bekapcsolva, csak kód-szemét volt.
