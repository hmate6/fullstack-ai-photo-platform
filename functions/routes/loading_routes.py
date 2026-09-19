from markupsafe import Markup
from sqlalchemy.exc import SQLAlchemyError
from random import choice
from flask import send_file, make_response, flash, send_from_directory
from bleach import clean
from functions.auth_functions import *
from sqlalchemy import desc
from functions.kep_generalasa import MAXLENGTH
from functions.emailsendzoho import *
from functions.regisztralas import email_verification_url
from app_init import *

with open("styles.txt", mode="r", encoding="utf-8") as f:
    styles = f.readlines()
    styles = [x.strip() for x in styles]

@app.route("/upgrade")
def upgrade_redirect():
    return redirect("/low-credits")

@app.route("/low-credits")
def low_credits():
    return render_template("codes/low_credit.html")

@app.route("/continue-as-guest")
def continue_as_guest():
    if logged_in():
        return redirect("/")
    if request.args.get("csrf_token", None) != session.get("csrf_token", None):
        return "CSRF TOKEN ERROR"

    email = GUEST_EMAIL
    accquery = UserAccount.query.filter_by(email=email).first()

    accquery.last_login = datetime.now()
    db.session.commit()

    dbitem = accquery
    lastpwreset = accquery.last_pw_reset_unix

    if not r.exists(email):
        r.set(email, accquery.last_pw_reset_unix)

    session["user"] = email
    session["userid"] = dbitem.id
    session["emailregex"] = regex_email(email)
    session["last_pw_reset_unix"] = lastpwreset
    session["email"] = email.lower()
    session["profile_picture"] = dbitem.profile_picture

    return redirect(session.get("reqpath", "/generate"))

@app.route("/random")
def randomimg():
    queried_image = Images.query.filter_by(public=True).all()

    if queried_image == []:
        return render_template("showcase_shrug.html")

    filename = choice(queried_image).name.replace(".jpeg", "")
    return redirect("/photo/" + filename)

@app.route("/")
def redirect_home():
    return redirect("/generate")

@app.route("/photo/<name>")
def showcase(name):
    name += ".jpeg"
    queried = Images.query.filter_by(name=name).first()
    if queried is None:
        return abort(404)
    prompt = queried.prompt
    style = queried.stilus

    title = "".join(f"{x} " for x in prompt.split(" ")[0:10])
    kw = "".join(f"{x.strip()}, " for x in prompt.split(" ")[1:40:12])
    return render_template("showcase.html", name=name, prompt=prompt, style=style, prompt_kw=kw, prompt_title=title)

@app.route("/randomprompt")
def randomprompt():
    return choice(prompt_examples)

@app.route("/login")
def belepes_load():
    response = make_response(render_template("auth/login.html"))
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '-1'
    return response

@app.route("/generate")
def fiok_load():
    if not logged_in():
        return redirect("/login")

    userid = session.get("userid")

    imagelist = []
    prompts = []
    dbquery = db.session.query(Images.name, Images.prompt).filter(Images.user_id == userid, Images.deleted == False).order_by(
        Images.id.desc()).limit(12).all()

    for x in dbquery:
        imagelist.append(x[0])
        prompts.append(x[1])

    height = "400px"

    selectedstyle = request.args.get("style")
    if selectedstyle:
        selectedstyle = styles_url_pairs.get(clean(selectedstyle), "None")
        session["style"] = selectedstyle

    render_template_response = render_template("generate.html", lof=len(imagelist), imagelist=imagelist[0:12],
                           height=height, prompts=prompts, maxlength=MAXLENGTH, styles=styles, selectedstyle=selectedstyle, example_prompt=choice(prompt_examples))

    response = make_response(render_template_response)
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '-1'

    return response

@app.route("/logout")
def logout():
    if not logged_in():
        return redirect("/login")

    csrf_token = request.args.get("csrf-token")
    if csrf_token is None or not csrf_token:
        flash("No csrf token sent, for security reasons you must log out using the Log Out button at the bottom of this page.")
        return redirect("/settings")
    if csrf_token != session.get("csrf_token"):
        flash("Incorrect csrf token was sent, for security reasons you must log out using the Log Out button at the bottom of this page.")
        return redirect("/settings")

    session.clear()
    return redirect("/login")

@app.route("/logout-from-every-place")
def logout_from_every_place():
    if not logged_in():
        return redirect("/login")
    csrf_token = request.args.get("csrf-token")
    if csrf_token is None or not csrf_token:
        flash(
            "No csrf token sent, for security reasons you must log out using the Log Out button at the bottom of this page.")
        return redirect("/settings")
    if csrf_token != session.get("csrf_token"):
        flash(
            "Incorrect csrf token was sent, for security reasons you must log out using the Log Out button at the bottom of this page.")
        return redirect("/settings")

    timenow = int(time())
    UserAccount.query.filter_by(id=session.get("userid")).first().last_pw_reset_unix = timenow
    r.set(session.get("email"), timenow)

    session.clear()
    return redirect("/logout")

@app.route("/background-remover")
def bgremove():
    if not logged_in():
        return redirect("/login")
    return render_template("bgedit.html")

@app.route("/3d-generate")
def fiok3d_load():
    if not logged_in():
        return redirect("/login")
    return render_template("fiok3d-generation.html", maxlength=1000, example_prompt=choice(prompts3d))

@app.route("/load3dshowcase")
def load_3d_showcase():
    return jsonify(choice(showcase_3d_prompts))

@app.route("/random3dprompt")
def random_3d_prompt():
    return choice(prompts3d)

@app.route("/image-to-text")
def ocr_load():
    if not logged_in():
        return redirect("/login")
    return render_template("imagetotext.html")

@app.route("/enhance")
def enhance_load():
    if not logged_in():
        return redirect("/login")
    return render_template("enhance.html")

@app.route("/frame-extractor")
def frame_extractor_load():
    return render_template("frame_extractor.html")

@app.route('/share_image', methods=['POST'])
def share_image():
    if not logged_in():
        return jsonify({"message": "You are not logged in!"})

    data = request.get_json()
    image_id = data.get('image_id')
    db.session.expire_all()
    query = Images.query.filter_by(user_id=session.get("userid"), name=image_id).first()

    if query is None:
        log("share_images_to_explore", "ERROR", f"We couldnt find the specified image: userid={session.get('userid')}, imageid={image_id}")
        return jsonify({"status": "notfound", "message": "We couldn't find the specified imagee."})

    if not query.public:
        query.published_at = datetime.now()
        query.public = True
        db.session.commit()
    else:
        return jsonify({"status": "success",
                    "message": "You have already shared that image!"})
    return jsonify({"status": "success", "message": "Image share success"})

@app.route("/sitemap.xml")
def sitemap():
    return send_from_directory("static", "sitemap.xml")

@app.route("/robots.txt")
def robots():
    return send_from_directory("static", "robots.txt")

@app.route("/contact")
def visszajelzes():
    return render_template("visszajelzes.html", current_page="visszajelzes")

@app.route("/verify-your-email")
def verify_your_email():
    if not logged_in():
        return redirect("/login")
    if user_status(session.get("userid")): # If verified email
        return redirect("/generate")

    if not r.exists(f"verify_email:{session.get('userid')}"):
        email = session.get("email")
        url = email_verification_url()
        db.session.add(EmailVerification(email=email, url=url, expire=datetime.now() + timedelta(hours=72)))
        db.session.commit()

        send_email_new(email, "Confirm Your E-mail Address!", email_message_for("email_verification", url, mode))

    r.set(f"verify_email:{session.get('userid')}", "", ex=20)
    return render_template("auth/verify_email.html")


@app.route("/settings")
def beallitasok_load():
    if "user" not in session:
        return redirect(url_for("belepes_load"))
    sub_status = "Unsubscribed"
    end_date = ""

    render_template_response = render_template("beallitasok.html", emailregex=session.get("email"), sub_status=sub_status, end_date=end_date)
    response = make_response(render_template_response)
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '-1'

    return response

styles_url_pairs = {'realistic': 'Realistic', 'comic': 'Comic', 'cyberpunk': 'Cyberpunk', 'retro': 'Retro', 'fantasy': 'Fantasy', 'cyberpunk-noir': 'Cyberpunk Noir', 'retro-futurism': 'Retro Futurism', 'steampunk-fantasy': 'Steampunk Fantasy', 'surreal-dreamscape': 'Surreal Dreamscape', 'apocalyptic-realism': 'Apocalyptic Realism', 'digital-impressionism': 'Digital Impressionism', 'bio-punk': 'Bio-Punk', 'dark-fantasy': 'Dark Fantasy', 'minimalist-zen': 'Minimalist Zen', 'art-deco-elegance': 'Art Deco Elegance', 'fantasy-realism': 'Fantasy Realism', 'post-internet-art': 'Post-Internet Art', 'dark-surrealism': 'Dark Surrealism', 'neon-dystopia': 'Neon Dystopia', 'gritty-realism': 'Gritty Realism', 'whimsical-fantasy': 'Whimsical Fantasy', 'high-fantasy': 'High Fantasy', 'kawaii-aesthetic': 'Kawaii Aesthetic', 'cosmic-horror': 'Cosmic Horror', 'geometric-abstraction': 'Geometric Abstraction', 'color-field-painting': 'Color Field Painting', 'psychedelic-art': 'Psychedelic Art', 'nature-inspired': 'Nature-Inspired', 'urban-sketching': 'Urban Sketching', 'futuristic-industrial': 'Futuristic Industrial', 'dystopian-realism': 'Dystopian Realism', 'vintage-collage': 'Vintage Collage', 'lofi-aesthetic': 'Lofi Aesthetic', 'abstract-expressionism': 'Abstract Expressionism', 'augmented-reality': 'Augmented Reality', 'manga-style': 'Manga Style', 'classic-portraiture': 'Classic Portraiture', 'cinematic-style': 'Cinematic Style', 'vaporwave': 'Vaporwave', 'impressionist-landscapes': 'Impressionist Landscapes', 'fantasy-illustration': 'Fantasy Illustration', 'realistic-wildlife': 'Realistic Wildlife', 'experimental-photography': 'Experimental Photography', 'street-art': 'Street Art', 'gothic-architecture': 'Gothic Architecture', 'sculptural-design': 'Sculptural Design', 'monochrome-minimalism': 'Monochrome Minimalism', 'folk-art': 'Folk Art', 'celestial-themes': 'Celestial Themes', 'art-nouveau': 'Art Nouveau', 'conceptual-art': 'Conceptual Art', 'mystical-realism': 'Mystical Realism', 'horror-art': 'Horror Art', 'architectural-photography': 'Architectural Photography', 'futuristic-nature': 'Futuristic Nature', 'kinetic-art': 'Kinetic Art', 'mythological-themes': 'Mythological Themes', 'digital-collage': 'Digital Collage', 'cultural-heritage': 'Cultural Heritage', 'nature-photography': 'Nature Photography', 'sculptural-illustration': 'Sculptural Illustration', 'abstract-landscape': 'Abstract Landscape', 'theatrical-design': 'Theatrical Design', 'renaissance-influence': 'Renaissance Influence', 'street-photography': 'Street Photography', 'cybernetic-aesthetics': 'Cybernetic Aesthetics', 'chibi-style': 'Chibi Style', 'constructivism': 'Constructivism', 'lush-tropical': 'Lush Tropical', 'modernist-architecture': 'Modernist Architecture', 'ethereal-portraiture': 'Ethereal Portraiture', 'brutalist-architecture': 'Brutalist Architecture', 'photorealism': 'Photorealism', 'cyberpunk-fantasy': 'Cyberpunk Fantasy', 'neo-classical': 'Neo-Classical', 'ambient-light': 'Ambient Light', 'digital-surrealism': 'Digital Surrealism', 'rural-charm': 'Rural Charm', 'intergalactic-exploration': 'Intergalactic Exploration', 'visual-poetry': 'Visual Poetry', 'glamour-photography': 'Glamour Photography', 'artistic-collaboration': 'Artistic Collaboration', 'emotionally-charged': 'Emotionally Charged', 'hyperrealism': 'Hyperrealism', 'elegant-minimalism': 'Elegant Minimalism', 'psycho-realism': 'Psycho-Realism', 'neoclassical-revival': 'Neoclassical Revival', 'pop-surrealism': 'Pop Surrealism', 'anime-futurism': 'Anime Futurism', 'baroque-fantasy': 'Baroque Fantasy', 'retro-sci-fi': 'Retro Sci-Fi', 'urban-dystopia': 'Urban Dystopia', 'hypercolor-pop-art': 'Hypercolor Pop Art', 'photographic-abstraction': 'Photographic Abstraction', 'new-gothic': 'New Gothic', 'deconstructivism': 'Deconstructivism', 'organic-architecture': 'Organic Architecture', 'symbolist-art': 'Symbolist Art', 'sci-fi-minimalism': 'Sci-Fi Minimalism', 'expressionist-urbanism': 'Expressionist Urbanism', 'botanical-art': 'Botanical Art', 'ancient-mythology': 'Ancient Mythology', 'anime-slice-of-life': 'Anime Slice of Life', '3d-pixel-art': '3D Pixel Art', 'metaphysical-realism': 'Metaphysical Realism', 'alien-landscape': 'Alien Landscape', 'rococo-glamour': 'Rococo Glamour', 'art-brut': 'Art Brut', 'futuristic-gothic': 'Futuristic Gothic', 'dreamlike-fantasy': 'Dreamlike Fantasy', 'magical-realism': 'Magical Realism', 'post-apocalyptic-fantasy': 'Post-Apocalyptic Fantasy', 'geometric-surrealism': 'Geometric Surrealism', 'afrofuturism': 'Afrofuturism', 'brutalist-sci-fi': 'Brutalist Sci-Fi', 'punk-rock-aesthetic': 'Punk Rock Aesthetic', 'futuristic-pastel': 'Futuristic Pastel', 'minimalist-sci-fi': 'Minimalist Sci-Fi', 'anime-fantasy': 'Anime Fantasy', 'organic-abstraction': 'Organic Abstraction', 'surrealist-portrait': 'Surrealist Portrait', 'grunge-aesthetic': 'Grunge Aesthetic', 'dynamic-expressionism': 'Dynamic Expressionism', 'alien-gothic': 'Alien Gothic', 'watercolor-fantasy': 'Watercolor Fantasy', 'retro-futuristic-pop': 'Retro Futuristic Pop', 'neo-baroque': 'Neo-Baroque', 'ethereal-sci-fi': 'Ethereal Sci-Fi', 'sci-fi-horror': 'Sci-Fi Horror', 'retro-dystopia': 'Retro Dystopia', 'elemental-magic': 'Elemental Magic', 'hyper-real-sci-fi': 'Hyper-Real Sci-Fi', 'neo-impressionism': 'Neo-Impressionism', 'steampunk-fantasy-noir': 'Steampunk Fantasy Noir', 'nostalgic-futurism': 'Nostalgic Futurism', 'bio-luminescent-landscape': 'Bio-Luminescent Landscape', 'zen-sci-fi': 'Zen Sci-Fi', 'crystalline-structures': 'Crystalline Structures', 'street-noir': 'Street Noir', 'ancient-civilization-fantasy': 'Ancient Civilization Fantasy', 'surreal-nature': 'Surreal Nature', 'mechanical-fantasy': 'Mechanical Fantasy', 'gothic-fantasy': 'Gothic Fantasy', 'dark-botanical': 'Dark Botanical', 'retro-glamour': 'Retro Glamour', 'steam-fantasy': 'Steam Fantasy', 'color-splash-urbanism': 'Color Splash Urbanism', 'post-surrealism': 'Post-Surrealism', 'conceptual-sci-fi': 'Conceptual Sci-Fi', 'ambient-nature': 'Ambient Nature', 'mechanical-abstraction': 'Mechanical Abstraction', 'cyber-art-deco': 'Cyber-Art Deco', 'dynamic-fantasy-portraits': 'Dynamic Fantasy Portraits', 'cinematic-urban-nature': 'Cinematic Urban Nature', 'conceptual-wildlife-art': 'Conceptual Wildlife Art', 'psychedelic-urban-landscapes': 'Psychedelic Urban Landscapes', 'whimsical-wildlife-illustrations': 'Whimsical Wildlife Illustrations', 'psycho-dynamic-fantasy': 'Psycho-Dynamic Fantasy', 'cinematic-whimsical-art': 'Cinematic Whimsical Art', 'ethereal-fantasy-portraiture': 'Ethereal Fantasy Portraiture', 'dynamic-nature-landscapes': 'Dynamic Nature Landscapes', 'conceptual-surreal-landscapes': 'Conceptual Surreal Landscapes', 'abstract-fantasy-art': 'Abstract Fantasy Art', 'cinematic-retro-fantasy': 'Cinematic Retro Fantasy', 'dynamic-urban-fantasy-portraits': 'Dynamic Urban Fantasy Portraits', 'psychedelic-nature-art': 'Psychedelic Nature Art', 'conceptual-surreal-portraits': 'Conceptual Surreal Portraits', 'ethereal-nature-art': 'Ethereal Nature Art', 'dynamic-whimsical-landscapes': 'Dynamic Whimsical Landscapes', 'ethereal-urban-wildlife': 'Ethereal Urban Wildlife', 'conceptual-abstract-wildlife': 'Conceptual Abstract Wildlife', 'dynamic-surreal-nature-art': 'Dynamic Surreal Nature Art', 'kaleidoscopic-urban-portraits': 'Kaleidoscopic Urban Portraits', 'ethereal-urban-art': 'Ethereal Urban Art', 'dynamic-fantasy-wildlife-portraits': 'Dynamic Fantasy Wildlife Portraits', 'psychedelic-fantasy-nature': 'Psychedelic Fantasy Nature', 'whimsical-urban-fantasy-landscapes': 'Whimsical Urban Fantasy Landscapes', 'dynamic-wildlife-art': 'Dynamic Wildlife Art', 'ethereal-wildlife-landscapes': 'Ethereal Wildlife Landscapes', 'retro-sci-fi-fantasy': 'Retro Sci-Fi Fantasy', 'vibrant-abstract-art': 'Vibrant Abstract Art', 'dreamlike-kinetic-landscapes': 'Dreamlike Kinetic Landscapes', 'futuristic-urban-jungle': 'Futuristic Urban Jungle', 'mythological-modernism': 'Mythological Modernism', 'neo-classicist-fantasy': 'Neo-Classicist Fantasy', 'geometric-fantasy-landscapes': 'Geometric Fantasy Landscapes', 'industrial-surrealism': 'Industrial Surrealism', 'artistic-cultural-fusion': 'Artistic Cultural Fusion', 'romantic-steampunk-fantasy': 'Romantic Steampunk Fantasy', 'cosmic-dreamscape': 'Cosmic Dreamscape', 'metaphysical-urban-landscapes': 'Metaphysical Urban Landscapes', 'retro-futuristic-fantasy': 'Retro-Futuristic Fantasy', 'nature-inspired-abstract-art': 'Nature-Inspired Abstract Art', 'transcendent-animal-portraits': 'Transcendent Animal Portraits', 'harmonious-urban-landscapes': 'Harmonious Urban Landscapes', 'symbolic-nature-art': 'Symbolic Nature Art', 'energetic-abstract-portraits': 'Energetic Abstract Portraits', 'ethereal-magical-landscapes': 'Ethereal Magical Landscapes', 'cinematic-nature-narratives': 'Cinematic Nature Narratives', 'urban-noir-fantasy': 'Urban Noir Fantasy', 'futuristic-eco-design': 'Futuristic Eco-Design'}

prompt_examples = [
    "A futuristic city skyline at sunset with neon lights reflecting off glass buildings.",
    "A fantasy forest with glowing mushrooms and mystical creatures in the background.",
    "A medieval knight in shining armor standing in a misty forest with a sword raised.",
    "A cyberpunk street scene with flying cars and holographic advertisements.",
    "A peaceful mountain landscape with a serene lake reflecting the snow-capped peaks.",
    "A detailed steampunk airship flying over a city made of brass and copper.",
    "A group of astronauts exploring the surface of a distant exoplanet with a dramatic sky.",
    "A vibrant coral reef teeming with colorful fish and aquatic plants.",
    "A post-apocalyptic wasteland with a lone survivor walking through ruins.",
    "A majestic dragon perched on a mountain peak, looking down on a valley below.",
    "A magical unicorn galloping through a field of tall grass under a rainbow.",
    "A bustling market street in a Middle Eastern city during the golden hour.",
    "A high-tech robot standing in front of a futuristic skyscraper.",
    "An ancient Egyptian temple with towering statues and hieroglyphs on the walls.",
    "A peaceful Japanese garden with koi fish swimming in a pond surrounded by cherry blossoms.",
    "A fierce lion walking through the African savannah at dawn.",
    "A vintage 1920s art deco building with intricate geometric designs.",
    "A close-up of a galaxy with vibrant nebulae and swirling stars.",
    "A serene beach with turquoise waters, white sand, and palm trees.",
    "A powerful wizard casting a spell in an enchanted forest filled with glowing creatures.",
    "A sleek sports car speeding down an empty highway at night.",
    "A group of penguins waddling on an icy tundra with snowflakes falling around them.",
    "A mystical tree with glowing leaves standing in the center of a foggy meadow.",
    "A futuristic space station orbiting a distant planet with a view of the stars.",
    "A peaceful village in the Swiss Alps with snow-covered houses and a bright blue sky.",
    "A Victorian mansion with intricate architecture and a foggy garden.",
    "A vibrant street art mural on the side of a brick building in an urban area.",
    "A large, majestic eagle soaring through a mountain valley.",
    "A spaceship traveling through a colorful wormhole in space.",
    "A bustling Tokyo street with a mix of traditional and modern architecture.",
    "A haunted mansion with spooky lights shining through the windows and fog surrounding it.",
    "A surreal dreamscape with floating islands and glowing plants.",
    "A futuristic robot interacting with humans in a high-tech city.",
    "A large, detailed clock tower in the center of a busy European city square.",
    "A snowy winter landscape with a cabin surrounded by tall pine trees.",
    "A group of robots working together to build a large, futuristic structure.",
    "A colorful hot air balloon floating over a vast desert landscape.",
    "A majestic whale swimming gracefully through the deep blue ocean.",
    "A cyberpunk hacker's workspace filled with glowing screens and digital maps.",
    "A fiery volcano erupting with lava flowing down the sides and ash in the air.",
    "A medieval castle surrounded by a moat and guarded by knights on horseback.",
    "A mystical glowing portal opening in the middle of a forest at night.",
    "A fantasy elf archer standing on a cliff overlooking a magical valley.",
    "A futuristic skyscraper covered in greenery with solar panels and wind turbines.",
    "A tranquil forest with rays of sunlight shining through the trees.",
    "A robotic dog running through a futuristic park with lush green grass.",
    "A large dragonfly with metallic wings perched on a blade of grass.",
    "A tropical rainforest filled with colorful parrots and exotic wildlife.",
    "A frozen wasteland with icebergs and a lone ship navigating through the water.",
    "A futuristic city street with neon signs, robots, and flying vehicles.",
    "A classic 1960s convertible car driving along a scenic coastal highway.",
    "A samurai warrior standing in a bamboo forest with a katana in hand.",
    "A glowing jellyfish floating in the dark depths of the ocean.",
    "A futuristic underwater research station with scientists studying marine life.",
    "A medieval wizard’s tower with arcane symbols glowing on the walls.",
    "A serene sunset over a desert with giant, rocky formations in the background.",
    "A futuristic hoverboard race through a neon-lit city at night.",
    "A giant mechanical spider roaming through an abandoned industrial site.",
    "A mythical creature with the body of a lion and wings of an eagle.",
    "A luxury yacht cruising through the crystal-clear waters of the Mediterranean.",
    "A floating castle surrounded by clouds and glowing with soft, ethereal light.",
    "A high-tech laboratory with advanced scientific equipment and holographic displays.",
    "A peaceful pond with a wooden bridge and lotus flowers floating on the surface.",
    "A fast-paced chase scene with a futuristic motorcycle speeding through a city.",
    "A giant robot battling a monstrous creature in a ruined city.",
    "A dark forest filled with glowing fireflies and ancient trees.",
    "A steampunk inventor’s workshop with intricate gears and machines.",
    "A large, detailed dragon circling a volcano with smoke and ash billowing from the top.",
    "A peaceful countryside with a small cottage surrounded by fields of flowers.",
    "A giant, futuristic spaceship landing on a barren moon with distant stars in the sky.",
    "A medieval tavern filled with adventurers and magical creatures.",
    "A winter wonderland with snow-covered trees, ice sculptures, and a frozen lake.",
    "A space explorer standing on the surface of Mars, looking up at the stars.",
    "A group of mystical creatures gathered around a glowing crystal in an enchanted cave.",
    "A desert oasis with palm trees, a sparkling pool of water, and a distant sandstorm.",
    "A dragonfly made of glass flying through a field of tall grasses.",
    "A futuristic drone delivering a package in a busy urban environment.",
    "A lush green jungle with a waterfall cascading down into a clear pool of water.",
    "A highly detailed, mechanical owl perched on a branch in a dark forest.",
    "A magical library filled with floating books and enchanted artifacts.",
    "A surreal scene of a giant clock with melting gears and twisting time.",
    "A spaceship with a sleek design flying through the asteroid belt.",
    "A tropical island with crystal-clear waters, white sand beaches, and palm trees.",
    "A city covered in snow with festive holiday decorations on the streets.",
    "A robot exploring an abandoned city overrun with nature.",
    "A lush garden with colorful butterflies and blooming flowers.",
    "A glowing crystal cave with shimmering blue and purple stones embedded in the walls.",
    "A medieval marketplace with vendors selling goods under colorful tents.",
    "A space exploration rover driving across the rocky surface of a distant moon.",
    "A fire-breathing dragon soaring above a castle in a fantasy world.",
    "A futuristic spaceport with ships coming and going in a bustling intergalactic hub.",
    "A lone wolf standing on a rocky outcrop with a full moon in the background.",
    "A surreal dream world where gravity seems to bend and objects float in mid-air.",
    "A crowded cyberpunk alley with neon lights and futuristic technology.",
    "A bustling city square in the morning with pedestrians and coffee carts.",
    "A sleek, futuristic yacht cruising through the skies over a city.",
    "A magical phoenix rising from the ashes with fiery wings and bright orange feathers.",
    "A serene lake surrounded by autumn trees with colorful foliage reflecting on the water.",
    "A mysterious cave entrance hidden behind a waterfall in a dense jungle.",
    "A futuristic sports arena with holographic fans and high-tech stadium seating.",
    "A large, ornate chandelier hanging in the center of a grand ballroom.",
    "A dramatic sunset over a cliff with an ancient stone temple overlooking the ocean.",
    "A group of adventurers exploring a deep, dark cave filled with treasure.",
    "A massive waterfall cascading down into a river surrounded by lush greenery.",
    "A futuristic, clean city with solar panels on every building and flying cars.",
    "A fantastical underwater kingdom with coral castles and schools of fish.",
    "A giant, mechanical clockwork bird soaring through a cloudy sky.",
    "A robot exploring a futuristic, alien landscape with towering, bizarre plants.",
    "A glowing dragonfly flying over a field of glowing flowers at night.",
    "A magical, snow-covered forest with a frozen waterfall and glowing lights.",
    "A majestic ship sailing through the clouds with wings and glowing sails.",
    "A serene mountain pass with a lone traveler crossing a bridge over a river.",
    "A surreal art installation with floating geometric shapes and soft lighting.",
    "A vibrant carnival with colorful rides, food stalls, and excited visitors.",
    "A tranquil lake with a small wooden boat drifting under a starry sky.",
    "A futuristic cityscape with holograms, flying vehicles, and neon signs.",
    "A cyberpunk city at night, illuminated by neon signs in various languages, with rain-slicked streets reflecting the vibrant lights. Flying cars hover above while shadowy figures in futuristic attire walk the sidewalks. The scene is dense with mist and has a cinematic, sci-fi aesthetic.",

    "A majestic medieval castle perched on a rocky cliff, surrounded by dense fog. The castle has tall towers with glowing windows, and a wooden drawbridge extends over a deep chasm. The background features a dark forest, and lightning flashes in the sky, creating a dramatic, fantasy-style atmosphere.",

    "A serene Japanese Zen garden at sunset, featuring a koi pond with colorful fish, neatly raked gravel patterns, and a red torii gate in the background. Cherry blossoms gently fall from the trees, and a stone lantern emits a soft glow. The setting evokes peace and tranquility.",

    "An astronaut exploring an alien planet with towering rock formations and bioluminescent plants. The landscape is bathed in a mysterious purple and blue glow, and two moons are visible in the sky. Strange floating creatures glide through the air, adding to the otherworldly atmosphere.",

    "A post-apocalyptic wasteland with ruined skyscrapers covered in ivy and nature reclaiming the land. A lone survivor wearing rugged armor walks through the overgrown streets, accompanied by a robotic dog. The sky is an eerie orange, and remnants of old civilization, like broken street signs, litter the ground.",

    "An ancient library filled with towering bookshelves, golden candlelight flickering in the dimly lit hall. Dust particles float in the air, and enchanted books levitate between shelves. A wise old wizard with a long beard sits at a wooden desk, studying an ancient tome with glowing runes.",

    "A steampunk city with massive airships floating above, gears and cogs turning in the machinery around. The streets are filled with people in Victorian-style clothing with mechanical enhancements. Steam billows from pipes, and a large clock tower dominates the skyline, evoking a sense of industrial-era fantasy.",

    "A tropical island with crystal-clear waters, palm trees swaying in the breeze, and a hidden pirate cove. A wooden shipwreck rests on the shore, with treasure chests spilling gold coins onto the sand. The sky is bright blue with fluffy white clouds, creating a paradise-like setting.",

    "A futuristic metropolis with skyscrapers made of glass and metal, massive digital billboards, and flying drones navigating the skyline. The streets below are filled with autonomous vehicles, humanoid robots, and citizens wearing augmented reality headsets. The cityscape glows with neon lights, blending cyberpunk and utopian aesthetics.",

    "A magical underwater kingdom with glowing coral reefs, mermaids swimming gracefully among schools of fish, and sunken ruins of an ancient civilization. Bioluminescent sea creatures illuminate the deep ocean, and a majestic sea dragon weaves between the ruins, exuding an aura of mystery and wonder.",

    "A grand Viking village nestled between towering snow-capped mountains, with wooden longhouses decorated with carved dragon heads. The village square has a large bonfire where warriors gather, clad in fur-lined armor, while the northern lights dance in the sky above.",

    "An abandoned space station orbiting a distant planet, its metallic corridors dimly lit by flickering emergency lights. Floating debris drifts in zero gravity, and control panels display cryptic messages. A lone astronaut investigates the eerie silence, evoking a sense of mystery and suspense.",

    "A vast desert with rolling dunes, where an ancient, half-buried temple stands. Mysterious symbols are carved into the stone, glowing faintly under the scorching sun. A lone traveler in a flowing cloak approaches the entrance, seeking lost secrets of a forgotten civilization.",

    "A mystical enchanted forest with towering bioluminescent trees and glowing mushrooms. Small fairies with translucent wings hover around, leaving trails of golden light. A wise old owl wearing tiny spectacles perches on a branch, observing the magical realm with keen interest.",

    "A colossal dragon perched atop a mountain peak, its shimmering scales reflecting the sunlight. Smoke curls from its nostrils as it watches over the valley below. A brave knight stands at the foot of the mountain, sword drawn, preparing for an epic battle.",

    "A cozy winter cabin deep in a snow-covered forest, smoke curling from the chimney. Golden light spills from the windows, illuminating the snowy surroundings. Inside, a fireplace crackles warmly, with a stack of books and a mug of hot cocoa resting on a wooden table.",

    "An ancient Greek city on a hill, with marble temples dedicated to the gods. The Acropolis gleams under the midday sun, and toga-clad philosophers debate in the agora. Statues of gods and goddesses stand tall, overlooking the blue Aegean Sea in the distance.",

    "A high-tech laboratory with robotic arms assembling futuristic devices. Holographic screens display scientific formulas and blueprints. A scientist in a sleek lab coat examines a glowing, pulsating orb of energy, while android assistants assist with complex calculations.",

    "A gothic vampire castle under a blood-red moon, with towering spires and dark stone walls. Bats swarm around the highest tower, and eerie blue torches flicker in the night. A shadowy figure in a long cloak stands at the entrance, eyes glowing crimson.",

    "A massive treehouse village hidden deep within a jungle, connected by wooden rope bridges. Lanterns dangle from the branches, casting a warm glow on the lush surroundings. Exotic birds with colorful feathers perch on the wooden railings, adding to the tropical wonder.",

    "A medieval blacksmith’s forge, glowing with the intense heat of molten metal. Sparks fly as the blacksmith hammers a glowing sword on an anvil. Shelves lined with finely crafted weapons and armor glisten in the dim firelight, creating an immersive, historical atmosphere.",

    "A surreal dreamscape where floating islands drift in the sky, connected by glowing vines. Waterfalls cascade from their edges, disappearing into the clouds below. In the distance, a giant moon with a human-like face watches over the whimsical landscape.",

    "A massive ancient robot, overgrown with moss and vines, sitting dormant in a dense jungle. Its eyes are dim, but faint traces of energy pulse through its core. Archaeologists in futuristic suits study the relic, wondering if it will awaken after centuries of slumber.",

    "A samurai duel at dawn, with two warriors facing off in a misty bamboo forest. Their katanas glisten in the morning light, and cherry blossoms swirl around them. The air is tense with honor and tradition as they prepare for a legendary battle.",

    "A cosmic nebula swirling with vibrant purples, blues, and oranges, filled with distant galaxies and glowing stars. A lone spaceship soars through the celestial wonder, leaving a trail of shimmering light as it journeys into the unknown depths of space.",

    "An elegant ballroom in a grand Victorian mansion, with guests in extravagant dresses and suits dancing under a golden chandelier. A masked figure in a deep red cloak stands in the shadows, watching the festivities with a mysterious air of intrigue.",

    "A peaceful countryside cottage surrounded by fields of blooming lavender. A small wooden fence encloses a vegetable garden, and a fluffy orange cat lounges on the front porch. The distant mountains provide a stunning backdrop to the idyllic rural scene.",

    "A colossal floating fortress in the sky, suspended by massive propellers and balloons. The castle-like structure is home to airship pirates who navigate the skies in search of treasure. Below, clouds swirl around, revealing glimpses of the ocean far beneath.",

]

prompts3d = [
    "A detailed 3D model of a futuristic spaceship with intricate mechanical parts.",
    "A medieval castle complete with towers, drawbridges, and a moat.",
    "A realistic human figure with fully articulated joints and detailed facial features.",
    "A fantasy creature with dragon wings, a lion’s body, and a serpent’s tail.",
    "A highly detailed 3D model of a modern smartphone with visible ports and buttons.",
    "A cyberpunk-style building with neon lights and holographic billboards.",
    "A vintage typewriter with every key and lever modeled in detail.",
    "A detailed model of a sports car with realistic textures and a fully designed interior.",
    "A steampunk-inspired airship with brass details and rotating propellers.",
    "A fully textured 3D model of a tropical palm tree with coconuts.",
    "A modular set of medieval weapons, including swords, shields, and axes.",
    "A futuristic robot with articulated arms and glowing eyes.",
    "A realistic 3D model of a wooden treasure chest with gold coins inside.",
    "A modern high-rise building with glass windows and a rooftop garden.",
    "A 3D model of a detailed kitchen set with appliances, cabinets, and utensils.",
    "A mystical altar with glowing runes and a floating crystal centerpiece.",
    "A realistic 3D model of a wild tiger in a walking pose.",
    "A vintage clock tower with gears and a functioning clock face.",
    "A modular sci-fi corridor system with glowing panels and pipes.",
    "A realistic airplane cockpit with detailed controls and screens.",
    "A 3D model of a mythical phoenix with flames trailing from its wings.",
    "A detailed dinosaur skeleton model for a museum exhibit.",
    "A set of fantasy-style potion bottles with intricate engravings.",
    "A realistic 3D model of a camping tent with poles and fabric textures.",
    "A modular medieval marketplace with stalls, goods, and merchants.",
    "A detailed 3D model of a coffee shop interior with tables, chairs, and a counter.",
    "A futuristic hovercar with rotating wheels and glowing undercarriage.",
    "A realistic 3D model of a chessboard with intricately designed chess pieces.",
    "A sci-fi space station with docking ports and solar panels.",
    "A medieval blacksmith’s workshop with tools, an anvil, and a furnace.",
    "A fantasy dragon perched on a rock with scales and glowing eyes.",
    "A 3D model of a realistic houseplant in a ceramic pot.",
    "A high-tech drone with detailed propellers and a sleek design.",
    "A modular set of realistic rocks and boulders for a natural environment.",
    "A fully textured 3D model of a pirate ship with sails and cannons.",
    "A medieval knight’s armor set displayed on a mannequin.",
    "A detailed 3D model of a realistic lion in a roaring pose.",
    "A modern living room with furniture, decor, and lighting fixtures.",
    "A futuristic mech robot with weapons and articulated joints.",
    "A 3D model of a cozy campsite with a tent, campfire, and logs.",
    "A detailed ancient Greek temple with columns and statues.",
    "A realistic 3D model of a bicycle with functional parts.",
    "A modular sci-fi vehicle with customizable parts and textures.",
    "A fantasy treehouse with rope bridges and lanterns.",
    "A realistic model of a classic grand piano with detailed keys.",
    "A detailed underwater submarine with visible propellers and windows.",
    "A fully articulated 3D humanoid robot with realistic movement capabilities.",
    "A modular medieval village with houses, fences, and wells.",
    "A 3D model of a futuristic energy weapon with glowing effects.",
    "A realistic mountain range with textures for snow and rocky terrain.",
    "A fantasy wizard’s tower with a spiral staircase and glowing crystals.",
    "A 3D model of a fully equipped modern gym with exercise machines.",
    "A modular sci-fi spaceship cockpit with seats and control panels.",
    "A realistic tree model with autumn leaves and bark textures.",
    "A medieval tavern with barrels, tables, and a fireplace.",
    "A futuristic motorbike with glowing lights and sleek aerodynamics.",
    "A detailed model of a modern office desk with a computer and stationery.",
    "A fantasy-style throne with ornate carvings and a velvet cushion.",
    "A realistic 3D model of a wild deer in a grazing pose.",
    "A modular set of stone ruins with moss and cracks for texture.",
    "A fully detailed 3D model of a city park with trees, benches, and paths.",
    "A sci-fi battle tank with energy shields and rotating turrets.",
    "A realistic bird model with detailed feathers and flight animation potential.",
    "A modular spaceship hangar with landing pads and maintenance equipment.",
    "A detailed 3D model of a historic lighthouse with functioning lights.",
    "A modern kitchen island with a sink, stovetop, and bar stools.",
    "A detailed model of a sports stadium with seating and a playing field.",
    "A fantasy-style sword with glowing runes and a jeweled hilt.",
    "A 3D model of a realistic fish with detailed scales and fins.",
    "A modular dungeon set with traps, treasure chests, and enemies.",
    "A realistic 3D model of a fully loaded picnic basket.",
    "A futuristic humanoid exosuit with weapon mounts and glowing panels.",
    "A detailed medieval chapel with stained glass windows and wooden pews.",
    "A modern SUV with a fully designed interior and exterior.",
    "A modular jungle environment with vines, trees, and rocks.",
    "A detailed 3D model of a giant mech standing in a battle-ready pose.",
    "A sci-fi research lab with holographic screens and robotic arms.",
    "A fantasy creature resembling a hybrid of a wolf and an eagle.",
    "A realistic model of a fully furnished bedroom with a cozy aesthetic.",
    "A futuristic spaceship interior with detailed corridors and a control room.",
    "A detailed 3D model of a realistic horse in a galloping pose.",
    "A modular set of desert structures for a small settlement.",
    "A high-tech command center with large screens and holographic displays.",
    "A medieval blacksmith’s anvil with tools and glowing coals.",
    "A realistic model of a chef’s kitchen with professional equipment.",
    "A modular sci-fi outpost with antennas, solar panels, and equipment crates.",
    "A fully detailed 3D model of a fire-breathing dragon in flight.",
    "A futuristic cargo drone with robotic arms and a cargo compartment.",
    "A detailed model of a classic clockwork mechanism with gears and levers.",
    "A modular fantasy tavern interior with tables, a bar, and lighting.",
    "A realistic 3D model of a wild bear standing on its hind legs.",
    "A high-tech futuristic laboratory with advanced scientific instruments.",
    "A modular fantasy village with glowing lanterns and cobblestone paths.",
    "A realistic 3D model of a sailing boat with visible ropes and sails.",
    "A detailed alien landscape with bizarre rock formations and glowing plants.",
    "A modular set of snowy terrain with trees and icy patches.",
    "A futuristic motorcycle with glowing wheels and aerodynamic design.",
    "A fully textured 3D model of a treasure chest with gems and gold coins."
]

showcase_3d_prompts = [
  {
    "prompt": "An ancient fantasy wizard staff, carved wooden shaft with glowing crystal at the top, ornate runes, symmetrical design, solid silhouette, photorealistic textures, studio lighting, isolated on dark background, high detail",
    "location": "8bde4d72-5d3b-4cf0-814b-fae09eef398d"
  },
  {
    "prompt": "A medieval treasure chest, reinforced wooden panels with iron bands, metal lock, worn but solid geometry, symmetrical design, realistic textures, studio lighting, isolated object on neutral background",
    "location": "c5f56440-0c9f-41be-87d6-84a11051ba1d"
  },
  {
    "prompt": "A cute stylized robot character, rounded shapes, simple mechanical joints, glossy plastic materials, symmetrical body, clear silhouette, studio lighting, isolated on white background, Pixar-style 3D reference",
    "location": "ca5cca00-a09d-464e-8b54-4ad849b0e922"
  },
  {
    "prompt": "An ancient stone idol statue, carved geometric shapes, symmetrical proportions, weathered stone texture, solid form, neutral pose, studio lighting, isolated object, realistic archaeology style",
    "location": "fc0bbc95-d032-4b49-a9f2-e5a772571b7d"
  },
  {
    "prompt": "A fantasy potion bottle, glass container with cork, glowing liquid inside, ornate metal details, symmetrical shape, solid geometry, studio lighting, isolated on dark background, ultra-detailed",
    "location": "b5cfbed0-ea2d-49c6-91c2-9f3e5b700c27"
  },
  {
    "prompt": "A futuristic sci-fi drone, compact mechanical design, hard-surface geometry, symmetrical arms, metallic materials, realistic textures, studio lighting, isolated object, high-resolution product render",
    "location": "9546ee8b-720b-4635-82fa-a0b5b5b82da8"
  },
  {
    "prompt": "A legendary ancient sword, straight blade, detailed hilt with gemstone, symmetrical design, realistic metal reflections, solid silhouette, studio lighting, isolated object on neutral background",
    "location": "102e11f2-2902-4d03-b5f6-b973f1a4c5d2"
  }
]
