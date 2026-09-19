from markupsafe import Markup
from sqlalchemy import desc
from app_init import *
from sqlalchemy.exc import SQLAlchemyError
from functions.auth_functions import log

# Like rendszer
@app.route('/toggle-like', methods=['POST'])
@limiter.limit("20 per minute")
def toggle_like():
    user_id = session.get("userid", None)

    if not logged_in(): return "not_logged_in", 401

    location = request.form.get("location")
    if not location:
        return jsonify({"error": "Location not provided"}), 400

    try:
        location = location.split("/")
        image_creator_id, image_name = location[0], location[1]
        image_creator_id = int(image_creator_id)
    except (ValueError, AttributeError) as e:
        print(e)
        return jsonify({"error": "Invalid location format"}), 400

    try:
        with db.session.begin_nested():
            queried_image = (
                Images.query
                .filter_by(user_id=image_creator_id, name=image_name)
                .with_for_update()
                .first()
            )

            if queried_image is None:
                return jsonify({"error": "Image does not exist"}), 404

            queried_likedimage = LikedImage.query.filter_by(user_id=user_id, image_creator_id=image_creator_id, name=image_name).with_for_update().first()

            if queried_likedimage is None:
                new_liked_image = LikedImage(user_id=user_id, image_creator_id=image_creator_id, name=image_name, liked=True)
                queried_image.likes += 1  # Increment likes count
                db.session.add(new_liked_image)
            else:
                qliked = queried_likedimage.liked

                if qliked:
                    queried_image.likes -= 1
                else:
                    queried_image.likes += 1

                queried_likedimage.liked = not queried_likedimage.liked

        db.session.commit()

        return jsonify({'status': 'success', 'likes': queried_image.likes}), 200

    except SQLAlchemyError:
        db.session.rollback()
        log("explore_liking", "ERROR", str(SQLAlchemyError) + str(SQLAlchemyError.args))
        return jsonify({"error": "Database error occurred"}), 500

# Route to explore load
@app.route("/explore")
def explore_load():
    sorted_by = request.args.get("sorted_by")
    sorted_by_argument = "?sorted_by=most_liked" if sorted_by == "most_liked" else ""

    user_id = session.get("userid", 0)  # Replace with actual user_id from session or request

    column = getattr(Images, 'likes') if sorted_by == "most_liked" else getattr(Images, "published_at")
    rows = Images.query.filter_by(public=True).order_by(desc(column)).limit(12).all()

    images = []
    liked_image_ids = [f"{liked.image_creator_id}/{liked.name}" for liked in LikedImage.query.filter_by(user_id=user_id).all() if liked.liked == True]

    for row in rows:
        ago = int((datetime.now() - row.published_at).total_seconds() / 60)
        agoprint = get_how_much_times_ago(ago)
        images.append({"ago": agoprint, "style": row.stilus, "location_without": row.name, "location": f"{row.user_id}/{row.name}", "location_w_id": f"{row.user_id}/{row.name}", "prompt": row.prompt, "aspect_ratio": row.arany, "likes": row.likes, "liked": row.id in liked_image_ids})  # Check if the image is liked by the user })

    return render_template("explore.html", images=images, length_of_images_list=len(images), liked_image_ids=Markup(liked_image_ids), sorted_by_argument=sorted_by_argument)
