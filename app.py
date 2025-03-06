from flask import Flask, request, jsonify, Response
from markupsafe import escape
from utils import (
    getCompanyProfile,
    getGroupedUrls,
    getPromotionalUrlGroups,
    getJavascriptRenderedPage,
    parse_html_page
)
import os
from optimizedBlogGeneration import (
    generateBaseBlogUsingKeyword,
    TONES,
    addPromotionalUrlsToBlog,
    addImagesToBlog,
)
from supabase import create_client, Client
from onedrive import upload_file, download_file
from PIL import Image
import io
import mimetypes

supabase_url: str = os.environ.get("SUPABASE_URL")
supabase_key: str = os.environ.get("SUPABASE_KEY")


app = Flask(__name__)

@app.route("/")
def index():
    return jsonify({"status": "Server is up and running"}), 200


@app.route("/save-company-data", methods=["POST"])
def saveCompanyProfile():
    supabase: Client = create_client(supabase_url, supabase_key)
    supabase.postgrest.auth(request.authorization.token)
    url = request.form.get("url")
    if not url:
        return jsonify({"error": "No url provided"}), 400
    userId = request.form.get("userId")
    if not userId:
        return jsonify({"error": "No userId provided"}), 401
    groupedUrls = getGroupedUrls(url)
    promotionalUrlGroups = getPromotionalUrlGroups(groupedUrls)
    companyProfile = getCompanyProfile(url)
    try:
        response = (
            supabase.table("Company Data")
            .insert(
                {
                    "company_name": companyProfile["CompanyName"],
                    "company_profile": companyProfile,
                    "grouped_urls": groupedUrls,
                    "promotional_url_groups": promotionalUrlGroups,
                    "user_id": userId,
                }
            )
            .execute()
        )
        return Response(response.json(), mimetype="application/json")
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/image/<path:name>", methods=["GET"])
def getImage(name):
    app.logger.info(request.path)
    # Retrieve query parameters.
    width = request.args.get("width", type=int)
    height = request.args.get("height", type=int)
    out_type = request.args.get("type", default=None, type=str)

    try:
        file_data = download_file(request.path)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    # Attempt to open the file as an image.
    try:
        image = Image.open(io.BytesIO(file_data))
    except Exception:
        return jsonify({"error": str(e)}), 500

    original_width, original_height = image.size

    # Determine new dimensions if any resizing parameters are provided.
    if width or height:
        if width and height:
            new_width, new_height = width, height
        elif width:
            new_width = width
            new_height = int((width / original_width) * original_height)
        elif height:
            new_height = height
            new_width = int((height / original_height) * original_width)
        image = image.resize((new_width, new_height))

    # Determine output format.
    if out_type:
        out_format = out_type.upper()
        if out_format == "JPG":
            out_format = "JPEG"
        mime_type = f"image/{out_format.lower()}"
    else:
        out_format = image.format if image.format else "PNG"
        if out_format.upper() == "JPG":
            out_format = "JPEG"
        mime_type = f"image/{out_format.lower()}"

    # Save the (potentially modified) image to a BytesIO stream.
    output = io.BytesIO()
    image.save(output, format=out_format)
    output.seek(0)
    response = Response(output.getvalue(), mimetype=mime_type)
    # Set cache policy: cache for 1 hour (3600 seconds)
    response.headers["Cache-Control"] = "public, max-age=3600"
    return response


@app.route("/files/<path:name>", methods=["GET"])
def getFile(name):
    try:
        file_data = download_file(request.path)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    # For non-image files, ignore query parameters.
    mime_type = mimetypes.guess_type(name)[0] or "application/octet-stream"
    response = Response(file_data, mimetype=mime_type)
    # Set cache policy: cache for 1 hour (3600 seconds)
    response.headers["Cache-Control"] = "public, max-age=3600"
    return response


@app.route("/upload", methods=["PUT"])
def upload():
    # Assuming the client uses a key like "file" for the uploaded file.
    if "file" not in request.files:
        return jsonify({"error": "No file part"}), 400
    file = request.files["file"]
    file_name = file.filename
    binary_data = file.read()
    if "image" in file.mimetype:
        onedrive_path = "image/"
    else:
        onedrive_path = "files/"

    path = request.form.get("path")
    if path:
        onedrive_path += path

    if onedrive_path.startswith("/"):
        onedrive_path = onedrive_path[1:]
    if onedrive_path.endswith("/"):
        onedrive_path = onedrive_path[:-1]

    file_name = file_name.replace("/", "")

    uploaded_url = upload_file(binary_data, onedrive_path, file_name)
    if uploaded_url:
        return jsonify({"url": uploaded_url}), 200
    else:
        return jsonify({"error": "Upload failed"}), 500


@app.route("/generate-base-blog", methods=["GET"])
def generateBaseBlog():
    access_token = request.authorization.token
    app.logger.info(access_token)
    data: dict = request.json
    supabase: Client = create_client(supabase_url, supabase_key)
    supabase.postgrest.auth(access_token)
    keyword = data.get("keyword")
    userId = data.get("userId")
    if not userId:
        return jsonify({"error": "No Use ID Provided."}), 401
    if supabase.auth.get_user(access_token).user.id != userId:
        return jsonify({"error": "Authentication error"}), 401

    companyId = data.get("companyId")
    if not companyId:
        return jsonify({"error": "No company ID Provided."}), 400
    structure = data.get("structure")
    companyUrl = data.get("companyUrl")
    companyProfile = data.get("companyProfile")
    tone = data.get("tone", TONES.Casual)
    if companyUrl:
        if not companyProfile:
            return jsonify({"error": "No company profile Provided."}), 400
    if not keyword:
        return jsonify({"error": "No Keyword Provided."}), 400
    supabase.table("Blogs").insert(
        {
            "markdown": blog,
            "status": "STRUCTURE",
            "user_id": userId,
            "company": companyId,
        }
    ).execute()
    blog = generateBaseBlogUsingKeyword(
        keyword, companyUrl, companyProfile, structure, tone
    )
    return Response(blog, mimetype="text/plain")


@app.route("/add-urls-to-blog", methods=["GET"])
def addUrls():
    access_token = request.authorization.token
    data: dict = request.json
    supabase: Client = create_client(supabase_url, supabase_key)
    supabase.postgrest.auth(access_token)
    keyword = data.get("keyword")
    userId = data.get("userId")
    blogId = data.get("blogId")
    blog = ""
    if not blogId:
        return jsonify({"error": "No blog ID Provided."}), 400
    else:
        response = supabase.table("Blogs").select("markdown").eq("id", blogId).execute()
        if not response.data:
            return jsonify({"error": "No blog not found Provided."}), 404
        blog = response.data["markdown"]
    if not userId:
        return jsonify({"error": "No Use ID Provided."}), 401
    if supabase.auth.get_user(access_token).user.id != userId:
        return jsonify({"error": "Authentication error"}), 401

    companyId = data.get("companyId")
    if not companyId:
        return jsonify({"error": "No company ID Provided."}), 400
    groupedUrls = data.get("groupedUrls")
    promotionalGroups = data.get("promotionalGroups")

    blog = addPromotionalUrlsToBlog(blog, keyword, groupedUrls, promotionalGroups)
    response = (
        supabase.table("Blogs")
        .update({"markdown": blog, "status": "URL"})
        .eq("id", blogId)
        .execute()
    )
    return Response(response.data, mimetype="application/json")


@app.route("/add-images-to-blog", methods=["GET"])
def addImagesToBlog1():
    access_token = request.authorization.token
    data: dict = request.json
    supabase: Client = create_client(supabase_url, supabase_key)
    supabase.postgrest.auth(access_token)
    userId = data.get("userId")
    if not userId:
        return jsonify({"error": "No Use ID Provided."}), 401
    if supabase.auth.get_user(access_token).user.id != userId:
        return jsonify({"error": "Authentication error"}), 401

    companyId = data.get("companyId")
    if not companyId:
        return jsonify({"error": "No company ID Provided."}), 400
    blogId = data.get("blogId")
    blog = ""
    if not blogId:
        return jsonify({"error": "No blog ID Provided."}), 400
    else:
        response = supabase.table("Blogs").select("markdown").eq("id", blogId).execute()
        if not response.data:
            return jsonify({"error": "No blog not found Provided."}), 404
        blog = response.data["markdown"]
    blog = addImagesToBlog(blog)
    response = (
        supabase.table("Blogs")
        .update(
            {
                "markdown": blog,
                "status": "DONE",
            }
        )
        .eq("id", blogId)
        .execute()
    )
    return Response(response.data, mimetype="application/json")


@app.route("/generate-blog", methods=["GET"])
def generateBlog():
    access_token = request.authorization.token
    data: dict = request.json
    supabase: Client = create_client(supabase_url, supabase_key)
    supabase.postgrest.auth(access_token)
    keyword = data.get("keyword")
    userId = data.get("userId")
    if not userId:
        return jsonify({"error": "No Use ID Provided."}), 401
    if supabase.auth.get_user(access_token).user.id != userId:
        return jsonify({"error": "Authentication error"}), 401

    companyId = data.get("companyId")
    if not companyId:
        return jsonify({"error": "No company ID Provided."}), 400
    structure = data.get("structure")
    companyUrl = data.get("companyUrl")
    companyProfile = data.get("companyProfile")
    groupedUrls = data.get("groupedUrls")
    promotionalGroups = data.get("promotionalGroups")
    tone = data.get("tone", TONES.Casual)
    if companyUrl:
        if not companyProfile:
            return jsonify({"error": "No company profile Provided."}), 400
        if not groupedUrls:
            return jsonify({"error": "Grouped Sitemap urls not Provided."}), 400
        if not promotionalGroups:
            return jsonify({"error": "List of promotional groups not provided."}), 400
    if not keyword:
        return jsonify({"error": "No Keyword Provided."}), 400

    blog = generateBaseBlogUsingKeyword(
        keyword, companyUrl, companyProfile, structure, tone
    )
    if companyUrl:
        blog = addPromotionalUrlsToBlog(blog, keyword, groupedUrls, promotionalGroups)
    blog = addImagesToBlog(blog)
    response = (
        supabase.table("Blogs")
        .insert(
            {
                "markdown": blog,
                "status": "DONE",
                "user_id": userId,
                "company": companyId,
            }
        )
        .execute()
    )
    return jsonify(response.data), 200


@app.route("/crawl", methods=["GET"])
def crawl():
    # Retrieve the URL from the query parameters.
    url = request.args.get("url")
    if not url:
        return jsonify({"error": 'Missing "url" query parameter'}), 400

    try:
        # Get the page content using the Selenium function.
        content, screenshot = getJavascriptRenderedPage(url)
        # Return the content as HTML.
        return jsonify(parse_html_page(content, url, screenshot)), 200
    except Exception as e:
        # Handle exceptions and return an error response.
        return jsonify({
                "url": "https://www.pinenlime.com/collections/anniversary-gifts",
                "status": "unsuccessful",
                "reason": str(e)
            }), 500



@app.route("/get-token", methods=["GET"])
def getToken():
    data = request.form
    email = data.get("email")
    password = data.get("password")
    supabase: Client = create_client(supabase_url, supabase_key)
    supabase.auth.sign_in_with_password({"email": email, "password": password })
    return supabase.auth.get_session().access_token

app.run(debug=True)
