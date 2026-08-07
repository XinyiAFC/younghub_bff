from flask import Blueprint, jsonify, request
from app.util.azure_cosmos_util import AzureCosmosUtil

card_bp = Blueprint('cards', __name__)

_cosmos = AzureCosmosUtil()

@card_bp.route('/articles')
def get_card():
    # 支持：/articles?channel=11 或 111；/articles?channel=111&top=50
    channel = request.args.get("channel")     # 可为 "11" / "111" / None
    top = request.args.get("top", type=int)   # 可选：限制返回条数
    items = _cosmos.read_article_list(channel_id=channel, top=top)
    resp = jsonify(items)
    resp.headers["Cache-Control"] = "no-store"
    return resp, 200
